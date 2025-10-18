# Image captioning model 
import ollama
# Image Decoding and Encoding
import base64
import json
# File system path handling, UUID generation and datetime
from pathlib import Path
from uuid import uuid4
from datetime import datetime, timezone
# FastAPI imports
from fastapi import HTTPException, File, UploadFile, Form, Query
from fastapi import FastAPI
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse, StreamingResponse
# Pydantic for data modeling
from pydantic import BaseModel
# Threading for safe file operations
from threading import Lock
# Typing imports
from typing import List, Sequence, Tuple, Iterable, Optional, Union
# Translation
from googletrans import Translator
# Text-to-speech (TTS)
from gtts import gTTS

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
    def generate_story(self, *, prompt: str, encoded_images: Sequence[str]) -> str:
        # Send the prompt and images to the Ollama API
        try:
            response = self.client.chat(
                model=self.model,
                messages=[{"role": "user", "content": prompt, "images": list(encoded_images)}],
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Ollama request error: {str(e)}")
        # Parse the response to extract the story text
        return response.message.content

# Start FastAPI App
app = FastAPI(title="Memory Garden FastAPI", description="Accepts image input and returns a description of the image using the Ollama LLaVA model.", version="0.1.0")

# Create upload directory for storing uploaded photos
UPLOAD_DIR = Path(__file__).resolve().parent / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True, parents=True)
# Data directory for storing stories
DATA_DIR = Path(__file__).resolve().parent / "data"
DATA_DIR.mkdir(exist_ok=True, parents=True)
STORIES_FILE = DATA_DIR / "stories.json"
AUDIO_DIR = Path(__file__).resolve().parent / "audio"
AUDIO_DIR.mkdir(exist_ok=True, parents=True)

# Simple file-system storage that can be swapped for MongoDB in the future.
class PhotoStorage:
    def __init__(self, base_dir: Path) -> None:
        self._base_dir = base_dir

    def _resolve_path(self, path: str) -> Path:
        candidate = Path(path)
        if candidate.is_absolute():
            return candidate
        if candidate.parts and candidate.parts[0] == self._base_dir.name:
            return self._base_dir.parent / candidate
        return self._base_dir / candidate
    
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
            photo_id = uuid4().hex
            generated_name = f"{photo_id}{extension}"
            destination = self._base_dir / generated_name
            destination.write_bytes(contents)

            stored_photos.append(
                (
                    StoredPhoto(
                        id=photo_id,
                        filename=upload.filename or generated_name,
                        content_type=upload.content_type or "application/octet-stream",
                        size=len(contents),
                        # path=generated_name,
                        path=str(destination.relative_to(self._base_dir.parent)),
                    ),
                    contents,
                )
            )

        return stored_photos
    # Load the raw bytes of a stored photo
    def load_bytes(self, photo: "StoredPhoto") -> bytes:
        return self._resolve_path(photo.path).read_bytes()
    # Get the file path for a stored photo
    def get_path(self, photo: "StoredPhoto") -> Path:
        return self._resolve_path(photo.path)
    # Delete a single photo
    def delete(self, photo: "StoredPhoto") -> None:
        try:
            self._resolve_path(photo.path).unlink()
        except FileNotFoundError:
            return
    # Delete multiple photos
    def delete_many(self, photos: Sequence["StoredPhoto"]) -> None:
        for photo in photos:
            self.delete(photo)
    # Delete all files in the storage directory (useful for testing)
    # def delete_all(self) -> None:
    #     for child in self._base_dir.iterdir():
    #         if child.is_file():
    #             child.unlink()

photo_storage = PhotoStorage(UPLOAD_DIR)
story_generator = OllamaStoryTeller(ollama_client)
translator = Translator()

# Metadata model for the uploaded photos
class StoredPhoto(BaseModel):
    id: str
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
class StoryRecord(BaseModel):
    id: str
    date: str
    weather: str
    location: str
    photos: List[StoredPhoto]
    story:  Optional[str]
    created_at: datetime 
    updated_at: datetime

    class Config:
        json_encoders = {datetime: lambda value: value.isoformat()}

# Extended response model to include messages
class StoryResponse(BaseModel):
    message: Optional[str] = None
    id: str
    date: str
    weather: str
    location: str
    photos: List[StoredPhoto]
    story: Optional[str]
    created_at: datetime
    updated_at: datetime
    class Config:
        json_encoders = {datetime: lambda value: value.isoformat()}

class StoryRepository:
    def __init__(self, storage_path: Path) -> None:
        self._storage_path = storage_path
        self._lock = Lock()
        self._storage_path.parent.mkdir(exist_ok=True, parents=True)
        if not self._storage_path.exists():
            self._storage_path.write_text("[]", encoding="utf-8")
    # Read all stories from the JSON file
    def _read_all(self) -> List[dict]:
        if not self._storage_path.exists():
            return []
        raw = self._storage_path.read_text(encoding="utf-8")
        if not raw.strip():
            return []
        return json.loads(raw)
    # Write all stories to the JSON file atomically
    def _write_all(self, data: List[dict]) -> None:
        temp_path = self._storage_path.with_suffix(".tmp")
        temp_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        temp_path.replace(self._storage_path)
    # Serialize and deserialize StoryRecord objects to/from dicts for JSON storage
    def _serialize(self, record: StoryRecord) -> dict:
        payload = record.model_dump()  # This is correct - record should be a StoryRecord
        payload["created_at"] = record.created_at.isoformat()
        payload["updated_at"] = record.updated_at.isoformat()
        return payload
    # Deserialize a dict to a StoryRecord object
    def _deserialize(self, payload: dict) -> StoryRecord:
        data = payload.copy()
        data["created_at"] = datetime.fromisoformat(data["created_at"])
        data["updated_at"] = datetime.fromisoformat(data["updated_at"])
        return StoryRecord(**data)
    # add a new story to the repository
    def add(self, record: StoryRecord) -> StoryResponse:
        serialized = self._serialize(record)
        with self._lock:
            data = self._read_all()
            data.append(serialized)
            self._write_all(data)
        return record
    # List all stored stories
    def list(self) -> List[StoryRecord]:
        with self._lock:
            data = self._read_all()
        return [self._deserialize(item) for item in data]
    # Get a specific story by ID
    def get(self, story_id: str) -> Optional[StoryRecord]:
        with self._lock:
            data = self._read_all()
        for item in data:
            if item.get("id") == story_id:
                return self._deserialize(item)
        return None
    # Update an existing story
    def update(self, record: StoryRecord) -> None:
        serialized = self._serialize(record)
        with self._lock:
            data = self._read_all()
            for index, item in enumerate(data):
                if item.get("id") == record.id:
                    data[index] = serialized
                    self._write_all(data)
                    return
        raise KeyError(f"Story {record.id} not found")

# Initialize the story repository
story_repository = StoryRepository(STORIES_FILE)


@app.get("/")
def read_root():
    return {"message": "Welcome to the Memory Garden FastAPI. Use the /upload endpoint to upload photos and metadata."}

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
# Parse a list of IDs from a string or sequence input
def _parse_id_list(value: Optional[Union[str, Sequence[str]]]) -> List[str]:
    if value is None:
        return []
    def normalize(item: Union[str, Sequence[str]]) -> List[str]:
        if item is None:
            return None
        if isinstance(item, str):
            trimmed = item.strip()
            return trimmed or None
        return str(item)
    
    if isinstance(value, str):
        trimmed = value.strip()
        if not trimmed:
            return []
        if trimmed.startswith('['):
            try:
                parsed = json.loads(trimmed)
                if isinstance(parsed,(list, tuple)):
                    return [item for item in (normalize(element) for element in parsed) if item]
            except json.JSONDecodeError:
                pass
        return [item for item in (normalize(part) for part in trimmed.split(',')) if item]
    if isinstance(value, (list, tuple)):
        return [item for item in (normalize(part) for part in value) if item]
    
    normalized = normalize(value)
    return [normalized] if normalized else []
# Convert StoryRecord to StoryResponse
def _story_to_response(record: StoryRecord, message: Optional[str] = None) -> StoryResponse:
    payload = record.model_dump()
    return StoryResponse(message=message, **payload)
# Async function to translate text to Cantonese
async def _translate_to_cantonese(text: str) -> str:
    async with translator:
        result = await translator.translate(text, dest='yue')
        return result.text
# Async function to synthesize Cantonese speech and save to file
async def _synthesize_cantonese_speech(text: str, output_path: Path) -> Path:
    lan = 'yue'
    tts = gTTS(text=text, lang=lan, slow=False)
    tts.save(output_path)
    return output_path

def _get_audio_file_path(story_id: str) -> Path:
    return AUDIO_DIR / f"{story_id}_cantonese.mp3"

def _delete_audio_file(story_id: str) -> None:
    audio_path = _get_audio_file_path(story_id)
    try:
        audio_path.unlink()
    except FileNotFoundError:
        pass
async def _ensure_cantonese_audio_exits(story: StoryRecord) -> Path:
    if not story.story:
        raise HTTPException(status_code=404, detail="No story text available for this story.")
    audio_path = _get_audio_file_path(story.id)
    if audio_path.exists():
        return audio_path
    cantonese_text = await _translate_to_cantonese(story.story)
    return await _synthesize_cantonese_speech(cantonese_text, audio_path)

# Endpoint to upload photos and generate a story
@app.post("/upload/stories", response_model=StoryResponse)
async def upload_photos_and_generate_story(
    date: Optional[str] = Form(..., description="Date of the memory in YYYY-MM-DD format"),
    weather: Optional[str] = Form(..., description="Weather description"),
    location: Optional[str] = Form(..., description="Location of the memory"),
    photos: List[UploadFile] = File(..., description="List of photos to upload (max 10 photos)", max_items=10)
) -> StoryResponse:
    if not photos:
        raise HTTPException(status_code=400, detail="At least one photo is required.")

    stored_photos_with_bytes = await photo_storage.persist(photos)
    stored_photos = [stored for stored, _ in stored_photos_with_bytes]  # Unpack stored photos
    prompt = _build_story_prompt(date=date, weather=weather, location=location)
    encoded_images = _encode_images(contents for _, contents in stored_photos_with_bytes)

    # Generate the story using Ollama
    story_text = story_generator.generate_story(prompt=prompt, encoded_images=encoded_images)
    # try: 
    #     story_text = story_generator.generate_story(prompt=prompt, encoded_images=encoded_images)
    # except HTTPException:
    #     await run_in_threadpool(photo_storage.delete_many, [photo for photo, _ in stored_photos_with_bytes])
    #     raise
    current_time = datetime.now(timezone.utc)
    
    story_record = StoryRecord(
        id=uuid4().hex,
        date=date,
        weather=weather,
        location=location,
        photos=stored_photos,
        story=story_text,
        created_at=current_time,
        updated_at=current_time,
    )
    await run_in_threadpool(story_repository.add, story_record)
    return _story_to_response(story_record, message="Photo uploaded and story generated successfully.")
    
# Endpoint to list all stories
@app.get("/stories", response_model=List[StoryResponse])
async def list_stories() -> List[StoryResponse]:
    stories = await run_in_threadpool(story_repository.list)
    return [_story_to_response(story) for story in stories]
# Endpoint to get a specific story by ID
@app.get("/stories/{story_id}", response_model=StoryResponse)
async def get_story(story_id: str) -> StoryResponse:
    story = await run_in_threadpool(story_repository.get, story_id)
    if not story:
        raise HTTPException(status_code=404, detail=f"Story with ID {story_id} not found.")
    return _story_to_response(story)
# Endpoint to get Cantonese audio for a specific story
@app.get("/stories/{story_id}/audio")
async def get_story_cantonese_audio(story_id: str):
    story = await run_in_threadpool(story_repository.get, story_id)
    if not story:
        raise HTTPException(status_code=404, detail="Story not found.")
    audio_path = await _ensure_cantonese_audio_exits(story)
    audio_filename = f"{story.id}_cantonese.mp3"
    return FileResponse(audio_path, media_type="audio/mpeg", filename=audio_filename)
# Endpoint to stream Cantonese audio for a specific story
@app.get("/stories/{story_id}/audio/stream")
async def stream_story_cantonese_audio(story_id: str):
    story = await run_in_threadpool(story_repository.get, story_id)
    if not story:
        raise HTTPException(status_code=404, detail="Story not found.")
    audio_path = await _ensure_cantonese_audio_exits(story)
    audio_filename = f"{story.id}_cantonese.mp3"
    def iterfile():
        with audio_path.open("rb") as file_like:
            yield from file_like
    return StreamingResponse(iterfile(), media_type="audio/mpeg", headers={"Content-Disposition": f"inline; filename={audio_filename}"})

# Endpoint to list photos for a specific story
@app.get("/stories/{story_id}/photos", response_model=List[StoredPhoto])
async def list_story_photos(story_id: str) -> List[StoredPhoto]:
    story = await run_in_threadpool(story_repository.get, story_id)
    if not story:
        raise HTTPException(status_code=404, detail="Story not found.")
    return story.photos
# Endpoint to download a specific photo from a story
@app.get("/stories/{story_id}/photos/{photo_id}")
async def download_story_photo(story_id: str, photo_id: str):
    story = await run_in_threadpool(story_repository.get, story_id)
    if not story:
        raise HTTPException(status_code=404, detail="Story not found.")
    target = next((photo for photo in story.photos if photo.id == photo_id), None)
    if not target:
        raise HTTPException(status_code=404, detail="Photo not found for this story.")
    file_path = photo_storage.get_path(target)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Photo file is unavailable.")
    return FileResponse(file_path, media_type=target.content_type, filename=target.filename)
# Endpoint to update story metadata and photos
@app.put("/stories/{story_id}/photos", response_model=StoryResponse)
async def update_story_photos(
    story_id: str,
    date: Optional[str] = Form(None),
    weather: Optional[str] = Form(None),
    location: Optional[str] = Form(None),
    keep_photo_ids: Optional[str] = Form(None),
    photos: Optional[List[UploadFile]] = File(None, description="Optional new photos to include"),
) -> StoryResponse:
    story = await run_in_threadpool(story_repository.get, story_id)
    if not story:
        raise HTTPException(status_code=404, detail="Story not found.")

    updated_date = date or story.date
    updated_weather = weather or story.weather
    updated_location = location or story.location

    # if not updated_date or not updated_weather or not updated_location:
    #     raise HTTPException(status_code=400, detail="Date, weather, and location are required.")

    keep_ids = _parse_id_list(keep_photo_ids)
    if keep_ids:
        keep_set = set(keep_ids)
    else:
        keep_set = {photo.id for photo in story.photos}

    photos_to_keep = [photo for photo in story.photos if photo.id in keep_set]
    if keep_ids and len(photos_to_keep) != len(keep_set):
        raise HTTPException(status_code=400, detail="One or more keep_photo_ids do not belong to this story.")

    new_uploads = photos or []
    new_photos_with_bytes: List[Tuple[StoredPhoto, bytes]] = []
    if new_uploads:
        new_photos_with_bytes = await photo_storage.persist(new_uploads)

    kept_bytes = [await run_in_threadpool(photo_storage.load_bytes, photo) for photo in photos_to_keep]
    new_bytes = [contents for _, contents in new_photos_with_bytes]

    if not kept_bytes and not new_bytes:
        raise HTTPException(status_code=400, detail="At least one photo is required.")

    prompt = _build_story_prompt(date=updated_date, weather=updated_weather, location=updated_location)
    encoded_images = _encode_images([*kept_bytes, *new_bytes])
    story_text = story_generator.generate_story(prompt=prompt, encoded_images=encoded_images)

    await run_in_threadpool(_delete_audio_file, story.id)

    removed_photos = [photo for photo in story.photos if photo.id not in keep_set]
    if removed_photos:
        await run_in_threadpool(photo_storage.delete_many, removed_photos)

    updated_record = story.model_copy(
        update={
            "date": updated_date,
            "weather": updated_weather,
            "location": updated_location,
            "photos": photos_to_keep + [photo for photo, _ in new_photos_with_bytes],
            "story": story_text,
            "updated_at": datetime.now(timezone.utc)
        }
    )
    await run_in_threadpool(story_repository.update, updated_record)

    return _story_to_response(updated_record, message="Story updated successfully.")
# Endpoint to delete specific photos from a story
@app.delete("/stories/{story_id}/photos", response_model=StoryRecord)
async def delete_story_photos(
    story_id: str,
    photo_ids: Optional[Union[str, List[str]]] = Query(None, alias="photoIds"),
) -> StoryRecord:
    story = await run_in_threadpool(story_repository.get, story_id)
    if not story:
        raise HTTPException(status_code=404, detail="Story not found.")

    ids_to_remove = set(_parse_id_list(photo_ids))
    if not ids_to_remove:
        raise HTTPException(status_code=400, detail="photoIds are required to delete photos.")

    photos_to_delete = [photo for photo in story.photos if photo.id in ids_to_remove]
    if not photos_to_delete:
        raise HTTPException(status_code=400, detail="None of the requested photos belong to this story.")

    remaining_photos = [photo for photo in story.photos if photo.id not in ids_to_remove]

    await run_in_threadpool(photo_storage.delete_many, photos_to_delete)
    await run_in_threadpool(_delete_audio_file, story.id)
    updated_record = story.model_copy(
        update={
            "photos": remaining_photos,
            "story": None,
            "updated_at": datetime.utcnow(),
        }
    )
    await run_in_threadpool(story_repository.update, updated_record)
    return updated_record