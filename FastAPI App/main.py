# Image captioning model 
import ollama
# import json
# import requests
import base64
# FastAPI imports
from pathlib import Path
from fastapi import FastAPI, HTTPException, File, UploadFile, Form
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel
from typing import List, Sequence, Tuple, Iterable
from uuid import uuid4

# initiate ollama client
ollama_client = ollama.Client()
OLLAMA_MODEL = "llava"
OLLAMA_STORY_PROMPT = (
    "You are a compassionate storyteller. Receive a sequence of photos and "
    "the contextual details (date, weather, place). Craft a vivid, coherent "
    "narrative that connects all of the photos into a single memory, written "
    "in the first person. Avoid bullet points and reference visual details "
    "from the images when possible."
)
# Class to interact with the Ollama API for story generation
class OllamaStoryTeller:
    def __init__(self, client: ollama.Client, model: str = OLLAMA_MODEL) -> None:
        self.client = client
        self.model = model
    async def generate_story(self, *, prompt: str, encoded_images: Sequence[str]) -> str:
        try:
            response = self.client.chat(
                model=self.model,
                messages=[{"role": "user", "content": prompt, "images": list(encoded_images),}],
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Ollama request error: {str(e)}")
        # Parse the response to extract the story text
        return response.message.content
        # raise HTTPException(status_code=500, detail="Ollama response parsing error.")

# Start FastAPI App
app = FastAPI(title="Memory Garden FastAPI", description="Accepts image input and returns a description of the image using the Ollama LLaVA model.", version="0.1.0")

# Create upload directory for storing uploaded photos
UPLOAD_DIR = Path(__file__).resolve().parent / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True, parents=True)

# Simple file-system storage that can be swapped for MongoDB in the future.
class PhotoStorage:
    def __init__(self, base_dir: Path) -> None:
        self._base_dir = base_dir

    # Save uploads to disk and return their metadata alongside the raw bytes.
    async def persist(self, photos: Sequence[UploadFile]) -> List[Tuple["StoredPhoto", bytes]]:
        stored_photos: List[Tuple[StoredPhoto, bytes]] = []

        for upload in photos:
            contents = await upload.read()
            if not contents:
                raise HTTPException(
                    status_code=400,
                    detail=f"Uploaded file '{upload.filename or 'unnamed'}' was empty.",
                )
            # Use original file extension or default to .jpg
            extension = Path(upload.filename or "").suffix or ".jpg"
            # Ensure unique filenames using UUIDs
            generated_name = f"{uuid4().hex}{extension}"
            destination = self._base_dir / generated_name
            destination.write_bytes(contents)

            stored_photos.append(
                (
                    StoredPhoto(
                        filename=upload.filename or generated_name,
                        content_type=upload.content_type or "application/octet-stream",
                        size=len(contents),
                        path=str(destination.relative_to(self._base_dir.parent)),
                    ),
                    contents,
                )
            )

        return stored_photos

photo_storage = PhotoStorage(UPLOAD_DIR)
story_generator = OllamaStoryTeller(ollama_client)

# Metadata model for the uploaded photos
class StoredPhoto(BaseModel):
    filename: str
    content_type: str
    size: int
    path: str
# Response returned after successful upload and processing
class MemoryResponse(BaseModel):
    message: str
    date: str
    weather: str
    location: str
    photos: List[StoredPhoto]

# Response model including stories for each photo
class MemoryResponseWithStories(BaseModel):
    message: str
    date: str
    weather: str
    location: str
    photos: List[StoredPhoto]
    story: str
        
# Function to save uploaded files to disk
# async def _persist_uploads(photos: Sequence[UploadFile]) -> List[Tuple[StoredPhoto, bytes]]:
#     stored_photos: List[Tuple[StoredPhoto, bytes]] = []

#     for upload in photos:
#         contents = await upload.read()
#         if not contents:
#             raise HTTPException(
#                 status_code=400,
#                 detail=f"Uploaded file '{upload.filename or 'unnamed'}' was empty.",
#             )

#         extension = Path(upload.filename or "").suffix or ".bin"
#         generated_name = f"{uuid4().hex}{extension}"
#         destination = UPLOAD_DIR / generated_name
#         destination.write_bytes(contents)

#         stored_photos.append(
#             (
#                 StoredPhoto(
#                     filename=upload.filename or generated_name,
#                     content_type=upload.content_type or "application/octet-stream",
#                     size=len(contents),
#                     path=str(destination.relative_to(UPLOAD_DIR.parent)),
#                 ),
#                 contents,
#             )
#         )

#     return stored_photos

@app.get("/")
def read_root():
    return {"message": "Welcome to the Memory Garden FastAPI. Use the /upload endpoint to upload photos and metadata."}

# Endpoint to upload photos and metadata
@app.post("/upload", response_model=MemoryResponse)
async def upload_photos(
    date: str = Form(..., description="Date of the memory in YYYY-MM-DD format"),
    weather: str = Form(..., description="Weather description"),
    location: str = Form(..., description="Location of the memory"),
    photos: List[UploadFile] = File(..., description="List of photos to upload (max 10 photos)", max_items=10)
) -> MemoryResponse:
    if not photos:
        raise HTTPException(status_code=400, detail="No photos uploaded.")
    # stored_photos: List[StoredPhoto] = []
    # for photo in photos:
    #     contents = await photo.read()
    #     if not contents:
    #         raise HTTPException(status_code=400, detail=f"Uploaded file {photo.filename} is empty.")
    #     extension = Path(photo.filename or "").suffix or ".jpg" # Default to .jpg if no extension
    #     generated_filename = f"{uuid4().hex}{extension}" # Generate unique filename
    #     destination = UPLOAD_DIR / generated_filename
    #     destination.write_bytes(contents) # Save the file

    #     stored_photos.append(StoredPhoto(
    #         filename=generated_filename,
    #         content_type=photo.content_type or "application/octet-stream",
    #         size=len(contents),
    #         path=str(destination.relative_to(UPLOAD_DIR.parent))
    #     ))
    stored_photos_with_bytes = await photo_storage.persist(photos)
    stored_photos = [stored for stored, _ in stored_photos_with_bytes]  # Unpack stored photos

    return MemoryResponse(
        message="Photos uploaded successfully.",
        date=date,
        weather=weather,
        location=location,
        photos=stored_photos
    )
# Helper function to build the story prompt
def _build_story_prompt(*, date: str, weather: str, location: str) -> str:
    return (
        f"{OLLAMA_STORY_PROMPT}"
        f"Date: {date}\n"
        f"Weather: {weather}\n"
        f"Location: {location}\n\n"
    )
# Base64 encode the images for Ollama
def _encode_images(photos_with_bytes: Iterable[bytes]) -> List[str]: 
    encoded: List[str] = []
    for contents in photos_with_bytes:
        encoded.append(base64.b64encode(contents).decode('utf-8'))
    return encoded

@app.post("/upload/stories", response_model=MemoryResponseWithStories)
async def upload_photos_and_generate_story(
    date: str = Form(..., description="Date of the memory in YYYY-MM-DD format"),
    weather: str = Form(..., description="Weather description"),
    location: str = Form(..., description="Location of the memory"),
    photos: List[UploadFile] = File(..., description="List of photos to upload (max 10 photos)", max_items=10)
) -> MemoryResponseWithStories:
    if not photos:
        raise HTTPException(status_code=400, detail="At least one photo is required.")

    stored_photos_with_bytes = await photo_storage.persist(photos)
    stored_photos = [stored for stored, _ in stored_photos_with_bytes]  # Unpack stored photos
    prompt = _build_story_prompt(date=date, weather=weather, location=location)
    encoded_images = _encode_images(contents for _, contents in stored_photos_with_bytes)

    # Generate the story using Ollama
    story = await story_generator.generate_story(prompt=prompt, encoded_images=encoded_images)

    return MemoryResponseWithStories(
        message="Photos uploaded and story generated successfully.",
        date=date,
        weather=weather,
        location=location,
        photos=stored_photos,
        story=story
    )
# # Image file path
# image_path = "image/family.jpeg"

# # Read and encode the image file
# with open(image_path, "rb") as image_file:
#     encoded_image = base64.b64encode(image_file.read()).decode('utf-8')

# # print(encoded_image)

# # method 3: Using the Ollama Python client library
# client = ollama.Client()
# model = "llava"
# prompt = "Describe the image in detail."
# # generate a response
# response = client.chat(
#     model=model,
#     messages = [{"role": "user", "content": prompt, "images":[encoded_image]}],
# )
# print(response)

# # method 1 Download the model and run model
# # response = ollama.chat(
# #     model="llava",
# #     messages = [{"role": "user", "content": "Describe the image in detail.", "images":[encoded_image]}],
# #     stream=False,
# # )
# # print(response['messages']['content'])

# # method 2: Using requests to send a POST request to the Ollama server
# # url = "http://localhost:11434"
# # payload = {
# #     "model": 'llava',
# #     "prompt": "Describe the image in detail.",
# #     "stream": False,
# #     "image": [encoded_image]
# # }
# # # send POST request
# # response = requests.post(url, data=json.dumps(payload))

# # # print the response
# # print(response.text)