import io
import os
from typing import List, Optional

from fastapi import FastAPI, UploadFile, File, HTTPException, Query
from fastapi.responses import JSONResponse
from PIL import Image
import torch
from transformers import VisionEncoderDecoderModel, ViTImageProcessor, AutoTokenizer

app = FastAPI(
    title="Image Captioning API",
    description="Generate image captions using Hugging Face ViT-GPT2 model.",
    version="1.0.0",
)

# Settings
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
MODEL_ID = os.getenv("MODEL_ID", "nlpconnect/vit-gpt2-image-captioning")
MAX_LENGTH_DEFAULT = int(os.getenv("MAX_LENGTH", "16"))
NUM_BEAMS_DEFAULT = int(os.getenv("NUM_BEAMS", "4"))
BATCH_LIMIT = int(os.getenv("BATCH_LIMIT", "16"))  # safety for very large uploads

# Load model once at startup
try:
    model = VisionEncoderDecoderModel.from_pretrained(MODEL_ID)
    feature_extractor = ViTImageProcessor.from_pretrained(MODEL_ID)
    tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
    # --- NEW: make GPT-2 padding explicit ---
    if tokenizer.pad_token is None:
        # use EOS as PAD for GPT-2-style decoders
        tokenizer.pad_token = tokenizer.eos_token
    
    model.config.pad_token_id = tokenizer.pad_token_id
    model.config.eos_token_id = tokenizer.eos_token_id

    model.to(DEVICE)
    model.eval()
except Exception as e:
    # If model fails to load, raise at startup
    raise RuntimeError(f"Failed to load model '{MODEL_ID}': {e}") from e


def _generate_captions(
    images: List[Image.Image],
    max_length: int,
    num_beams: int,
) -> List[str]:
    pixel_values = feature_extractor(images=images, return_tensors="pt", padding=True).pixel_values
    pixel_values = pixel_values.to(DEVICE)

    output_ids = model.generate(
        pixel_values,
        max_length=max_length,
        num_beams=num_beams,
        pad_token_id=tokenizer.pad_token_id,
        eos_token_id=tokenizer.eos_token_id,
    )

    captions = tokenizer.batch_decode(output_ids, skip_special_tokens=True)
    captions = [c.strip() for c in captions]
    return captions


@app.get("/health")
def health():
    return {
        "status": "ok",
        "model_id": MODEL_ID,
        "device": DEVICE,
        "defaults": {
            "max_length": MAX_LENGTH_DEFAULT,
            "num_beams": NUM_BEAMS_DEFAULT,
        },
    }


@app.post("/caption")
async def caption(
    files: List[UploadFile] = File(..., description="One or more image files."),
    max_length: Optional[int] = Query(
        None, ge=1, le=128, description="Max token length for caption generation."
    ),
    num_beams: Optional[int] = Query(
        None, ge=1, le=8, description="Beam count for beam search decoding."
    ),
):
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded.")

    if len(files) > BATCH_LIMIT:
        raise HTTPException(
            status_code=413,
            detail=f"Too many files. Limit is {BATCH_LIMIT}.",
        )

    images: List[Image.Image] = []
    filenames: List[str] = []

    for f in files:
        if not f.content_type or not f.content_type.startswith("image/"):
            raise HTTPException(
                status_code=415,
                detail=f"Unsupported content type for file '{f.filename}'. Expected an image.",
            )
        try:
            content = await f.read()
            img = Image.open(io.BytesIO(content))
            img.load()  # verify image can be loaded
            if img.mode != "RGB":
                img = img.convert("RGB")
            images.append(img)
            filenames.append(f.filename or "unknown")
        except Exception:
            raise HTTPException(
                status_code=400, detail=f"Failed to read image '{f.filename}'."
            )

    use_max_length = max_length if max_length is not None else MAX_LENGTH_DEFAULT
    use_num_beams = num_beams if num_beams is not None else NUM_BEAMS_DEFAULT

    try:
        captions = _generate_captions(
            images=images,
            max_length=use_max_length,
            num_beams=use_num_beams,
        )
    except torch.cuda.OutOfMemoryError:
        raise HTTPException(
            status_code=503,
            detail="Out of GPU memory. Reduce batch size or num_beams and try again.",
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Inference failed: {str(e)}"
        )

    results = [{"filename": name, "caption": cap} for name, cap in zip(filenames, captions)]
    return JSONResponse(content={"results": results})


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)