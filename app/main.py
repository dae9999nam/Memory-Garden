from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse
from typing import List
from transformers import AutoModelForVision2Seq, AutoTokenizer, AutoProcessor
import torch
from PIL import Image
import tempfile
import os

app = FastAPI()

qwen_model_id = "Qwen/Qwen2.5-VL-7B-Instruct"
qwen_model = AutoModelForVision2Seq.from_pretrained(
    qwen_model_id,
    dtype=torch.float16,
    device_map="auto"
)
qwen_tokenizer = AutoTokenizer.from_pretrained(qwen_model_id)
qwen_processor = AutoProcessor.from_pretrained(qwen_model_id)

short_prompt = """Write a 120–180 word micro‑story inspired by this photo for an older adult and their family. Describe the photo honestly, write the story to evoke gentle reminiscence and well‑being. Use warm, simple language, 2–3 sensory details, and avoid object lists. Use tentative phrasing for uncertain facts. Emphasize connection and small rituals."""
long_prompt = """
You are a compassionate storyteller. Using the attached photo, craft a 120–180 word micro‑story intended for an older adult and their family. The story should gently evoke memories, spark warm conversation, and support emotional well‑being.

Guidelines:
- Focus on mood, place, season, and relationships; avoid listing objects.
- Weave in 2–3 sensory details (sounds, scents, textures, light).
- Use warm, respectful language and short, vivid sentences.
- Avoid definitive claims about names, ages, or locations. Use gentle, tentative phrasing (perhaps, it seems, maybe).
- If people appear, emphasize connection and small rituals rather than appearance.
- Be inclusive and avoid stereotypes; balance nostalgia with quiet hope.
- If text is clearly legible in the image, you may thoughtfully incorporate it.
- If the scene is ambiguous, lean into universal themes (family, gatherings, journeys, everyday moments).

Output:
- 1–2 paragraphs of story.

Variants (pick one voice if you want to steer style):
- Voice A (third‑person close): Tell the story from a gentle narrator’s view.
- Voice B (first‑person elder): Write as if an older adult is recalling the moment in the photo.
- Voice C (second person): Address a loved one directly, with tenderness and gratitude.

Examples of style knobs you can add:
- Tone: warm and hopeful; lightly bittersweet; playful nostalgia.
- Era cues: hint at a decade only if strongly suggested by the image.
- Cultural touch: include respectful, non‑stereotyped details only if clearly present.

"""
def generate_story_qwen(image_path, prompt=short_prompt): # use short_prompt by default
    image = Image.open(image_path).convert("RGB")
    messages = [
        {"role": "user", "content": [
            {"type": "image"},
            {"type": "text", "text": prompt}
        ]}
    ]
    text_prompt = qwen_processor.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True
    )
    inputs = qwen_processor(text=[text_prompt], images=[image], return_tensors="pt").to("cuda")
    output_ids = qwen_model.generate(**inputs, max_new_tokens=300)
    generated_text = qwen_tokenizer.decode(
        output_ids[0][inputs["input_ids"].shape[1]:],
        skip_special_tokens=True
    )
    return generated_text.strip()

@app.get("/")
def read_root():
    return {"Hello": "World"}

@app.post("/generate-stories/")
async def generate_stories(images: List[UploadFile] = File(...)):
    results = []
    for image_file in images:
        # Save image temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
            contents = await image_file.read()
            tmp.write(contents)
            tmp_path = tmp.name

        try:
            story = generate_story_qwen(tmp_path)
        except Exception as e:
            story = f"Error processing image: {str(e)}"
        finally:
            # Clean up temp file
            os.remove(tmp_path)

        results.append({
            "filename": image_file.filename,
            "story": story
        })

    return JSONResponse(content={"results": results})