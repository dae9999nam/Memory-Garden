import base64
import binascii
import os
from io import BytesIO
from typing import Any, Dict, List, Literal, Optional
from urllib.parse import urlparse

import requests
from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from PIL import Image, UnidentifiedImageError

app = FastAPI()

DEFAULT_QWEN_MODEL_ID = "Qwen/Qwen2.5-VL-7B-Instruct"
# The model card lists the public Inference API endpoint and identifier:
# https://huggingface.co/Qwen/Qwen2.5-VL-7B-Instruct


def _resolve_model_id() -> str:
    """Return the configured Hugging Face model identifier."""

    model_id = os.getenv("HUGGING_FACE_MODEL_ID", DEFAULT_QWEN_MODEL_ID).strip()
    if not model_id:
        raise RuntimeError("HUGGING_FACE_MODEL_ID is set but empty. Provide a valid Hugging Face model id.")
    return model_id

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


def _extract_text_from_response(payload: Any) -> Optional[str]:
    """Return the first text completion found in a Hugging Face response payload."""

    if isinstance(payload, dict):
        if "choices" in payload and isinstance(payload["choices"], list):
            for choice in payload["choices"]:
                message = choice.get("message") if isinstance(choice, dict) else None
                if isinstance(message, dict):
                    content = message.get("content")
                    if isinstance(content, list):
                        for item in content:
                            if isinstance(item, dict) and item.get("type") == "text":
                                text = item.get("text")
                                if isinstance(text, str):
                                    return text
                    text = message.get("content")
                    if isinstance(text, str):
                        return text
                text = choice.get("text") if isinstance(choice, dict) else None
                if isinstance(text, str):
                    return text
        generated_text = payload.get("generated_text")
        if isinstance(generated_text, str):
            return generated_text
    if isinstance(payload, list):
        for item in payload:
            text = _extract_text_from_response(item)
            if text:
                return text
    return None


def generate_story_qwen(image_bytes: bytes, prompt: str = short_prompt) -> str:
    """Generate a story for a single image.

    Args:
        image_bytes: Raw bytes of the uploaded image.
        prompt: Prompt text used when querying the model.

    Returns:
        The generated story as a string.
    """

    try:
        # Validate the bytes represent an image; discard the converted copy afterwards.
        Image.open(BytesIO(image_bytes)).convert("RGB")
    except (UnidentifiedImageError, OSError) as exc:
        raise ValueError("Uploaded file is not a valid image.") from exc

    hf_token = os.getenv("HUGGING_FACE_API_TOKEN")
    if not hf_token:
        raise RuntimeError(
            "Missing HUGGING_FACE_API_TOKEN environment variable required for Hugging Face Inference API access."
        )

    image_base64 = base64.b64encode(image_bytes).decode("utf-8")
    payload: Dict[str, Any] = {
        "inputs": {
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "image", "image": image_base64},
                        {"type": "text", "text": prompt},
                    ],
                }
            ]
        },
        "parameters": {"max_new_tokens": 320},
    }

    headers = {
        "Authorization": f"Bearer {hf_token}",
        "Content-Type": "application/json",
    }

    hf_api_url = f"https://api-inference.huggingface.co/models/{_resolve_model_id()}"

    try:
        response = requests.post(hf_api_url, headers=headers, json=payload, timeout=60)
    except requests.RequestException as exc:
        raise RuntimeError("Failed to reach Hugging Face Inference API.") from exc

    if response.status_code in {202, 503}:
        raise RuntimeError("Model is loading on Hugging Face; please retry in a few moments.")

    if response.status_code >= 400:
        raise RuntimeError(f"Hugging Face API error ({response.status_code}): {response.text}")

    try:
        response_payload: Any = response.json()
    except ValueError as exc:
        raise RuntimeError("Invalid JSON response from Hugging Face API.") from exc

    text = _extract_text_from_response(response_payload)
    if not text:
        raise RuntimeError("Unable to parse generated story from Hugging Face response.")

    return text.strip()


class RemoteVisionInput(BaseModel):
    """Vision input provided via base64 string or URL."""

    type: Literal["base64", "url"] = Field(
        ..., description="How the model input should be interpreted (base64 data or remote URL)."
    )
    value: str = Field(..., description="The base64 payload or URL to the image resource.")


class RemoteStoryRequest(BaseModel):
    """Request payload for generating stories from non-upload sources."""

    sources: List[RemoteVisionInput] = Field(
        ..., description="List of base64 strings or URLs that point to the images to narrate."
    )
    prompt: Optional[str] = Field(
        default=None,
        description="Optional custom prompt to send to the Hugging Face model.",
    )


def _load_bytes_from_remote_source(source: RemoteVisionInput) -> bytes:
    """Decode a RemoteVisionInput into image bytes."""

    if source.type == "base64":
        try:
            return base64.b64decode(source.value, validate=True)
        except (ValueError, binascii.Error) as exc:
            raise ValueError("Invalid base64 image payload.") from exc

    # URL path
    parsed = urlparse(source.value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("Image URL is not valid. Provide an absolute HTTP(S) URL.")

    try:
        response = requests.get(source.value, timeout=30)
    except requests.RequestException as exc:
        raise RuntimeError("Failed to download image from URL.") from exc

    if response.status_code >= 400:
        raise RuntimeError(f"Image download failed with status {response.status_code}.")

    return response.content

@app.get("/")
def read_root():
    return {"Hello": "World"}

@app.post("/generate-stories/")
async def generate_stories(images: List[UploadFile] = File(...), prompt: Optional[str] = Form(None)):
    results = []
    prompt_text = prompt.strip() if isinstance(prompt, str) and prompt.strip() else short_prompt
    for image_file in images:
        contents = await image_file.read()
        try:
            if not contents:
                raise ValueError("Uploaded file is empty.")
            story = generate_story_qwen(contents, prompt=prompt_text)
        except Exception as e:
            story = f"Error processing image: {str(e)}"
        finally:
            await image_file.close()

        results.append({
            "filename": image_file.filename,
            "story": story
        })

    return JSONResponse(content={"results": results})


@app.post("/generate-stories/from-remote/")
async def generate_stories_from_remote(request: RemoteStoryRequest):
    """Generate stories for images referenced by base64 payloads or URLs."""

    results = []
    prompt_text = request.prompt.strip() if request.prompt else short_prompt

    for index, source in enumerate(request.sources, start=1):
        label = source.value if source.type == "url" else f"base64_{index}"
        try:
            image_bytes = _load_bytes_from_remote_source(source)
            if not image_bytes:
                raise ValueError("No data received for remote image.")
            story = generate_story_qwen(image_bytes, prompt=prompt_text)
        except Exception as exc:
            story = f"Error processing image: {exc}"

        results.append({"source": label, "story": story})

    return JSONResponse(content={"results": results})

