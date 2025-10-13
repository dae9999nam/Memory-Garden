# Memory Garden API

A Node.js/Express service that turns image uploads and contextual metadata into narrated stories using MongoDB for storage and an Ollama vision-language model for generation.

## Features
- Upload up to ten photos alongside date, place, weather, and optional notes.
- Persist photo binaries in MongoDB GridFS with metadata and prompts in a `stories` collection.
- Generate descriptive narratives with Ollama and automatically refresh stories when photos change.
- Retrieve stories with downloadable photo links or selectively delete prompts, stories, or photo sets.

## Getting started
1. **Install dependencies**
   ```bash
   npm install
   ```
2. **Configure environment** – Copy `.env.example` to `.env` and adjust values:
   ```env
   MONGODB_URI=mongodb://localhost:27017/memory-garden
   MONGODB_DB=memory-garden
   OLLAMA_BASE_URL=http://localhost:11434
   OLLAMA_MODEL=llava
   PORT=8000
   ```
3. **Run the server**
   ```bash
   npm run dev
   ```
   The API listens on `http://localhost:8000` by default.

## API reference
### Create a story
`POST /stories`

Multipart form fields:
- `photos` – one or more image files (max 10, up to 15 MB each)
- `date` – when the photos were taken (ISO string or free text)
- `place` – where the photos were taken
- `weather` – description of the weather conditions
- `notes` – optional extra context for the storyteller

Response example:
```json
{
  "id": "665f75c6c5f4d3e3c5a17c09",
  "prompt": "You are a warm and imaginative storyteller...",
  "context": {
    "date": "2024-05-24",
    "place": "Lisbon, Portugal",
    "weather": "Sunny with a sea breeze",
    "notes": "Family reunion at the lookout point"
  },
  "story": "The afternoon sun rested gently on the tiled rooftops...",
  "photos": [
    {
      "id": "665f75c6c5f4d3e3c5a17c0a",
      "filename": "lookout.jpg",
      "contentType": "image/jpeg",
      "length": 234829,
      "uploadDate": "2024-05-24T15:08:54.365Z",
      "downloadUrl": "http://localhost:8000/stories/665f75c6c5f4d3e3c5a17c09/photos/665f75c6c5f4d3e3c5a17c0a"
    }
  ],
  "createdAt": "2024-05-24T15:08:54.365Z",
  "updatedAt": "2024-05-24T15:08:54.365Z"
}
```

### Update photos and regenerate
`PUT /stories/:id/photos`

- Accepts the same multipart payload as `POST /stories` (photos required).
- Optionally include any of `date`, `place`, `weather`, or `notes` to refresh stored context.
- Replaces all stored photos, regenerates the prompt and story, and deletes superseded GridFS files.

### Retrieve a story
`GET /stories/:id`

Returns the saved prompt, context, generated story, and photo descriptors including download URLs.

### Download a stored photo
`GET /stories/:id/photos/:photoId`

Streams the binary image content directly from GridFS.

### Delete
`DELETE /stories/:id`

Supports targeted deletions via the optional `target` query parameter:
- `target=photos` – delete photos only
- `target=prompt` – remove the stored prompt text
- `target=story` – clear the generated story text
- (default) – delete the entire story document and all associated photos

All photo deletions remove the underlying GridFS files.

## Development notes
- Ollama requests are synchronous with a 60 second timeout; configure asynchronous workers if you expect longer generations.
- `multer` stores uploads in memory. For larger uploads consider swapping to disk storage before piping to GridFS.
- Lint the project with `npm run lint` once dependencies are installed.
