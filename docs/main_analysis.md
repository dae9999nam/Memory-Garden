# Memory Garden Express Service Overview

## Architecture summary
- **Express routing** – `app/server.js` boots an Express application, mounts the story router under `/stories`, and centralises error handling while deferring startup until a MongoDB connection is ready.
- **MongoDB/GridFS integration** – `app/db/mongo.js` manages the shared `MongoClient`, exposes helpers for typed `ObjectId` conversion, and provides a GridFS bucket named `storyImages` for storing uploaded photos alongside story documents.
- **Story workflow** – `app/routes/stories.js` wires uploads, persistence, and Ollama orchestration. The router streams uploaded buffers into GridFS, builds a contextual prompt via `app/utils/prompt.js`, calls `app/services/ollama.js` to request captions from the configured Ollama model, and stores the resulting narrative with photo metadata.

## Endpoint capabilities
1. **Create story (`POST /stories`)** – Accepts up to ten photos plus contextual fields (`date`, `place`, `weather`, optional `notes`). The service uploads photos to GridFS, generates a narrative from Ollama, and persists the prompt, metadata, and story text.
2. **Update photos (`PUT /stories/:id/photos`)** – Replaces the stored photo set (max ten images), optionally refreshes contextual metadata, deletes orphaned GridFS files, and regenerates the story.
3. **Retrieve story (`GET /stories/:id`)** – Returns the saved prompt, context, story text, and downloadable photo descriptors.
4. **Download photo (`GET /stories/:id/photos/:photoId`)** – Streams a stored image directly from GridFS.
5. **Delete story (`DELETE /stories/:id`)** – Supports targeted deletion via the `target` query (`photos`, `prompt`, `story`, or `all` for a full removal). Associated GridFS assets are purged when appropriate.

## Operational notes
- Requires `MONGODB_URI`, `MONGODB_DB`, `OLLAMA_BASE_URL`, and `OLLAMA_MODEL` environment variables (see `.env.example`).
- File uploads are memory-bound and limited to ten files at 15 MB each; adjust `app/middleware/uploads.js` if larger payloads are needed.
- Ollama requests are synchronously executed with a 60-second timeout; consider background processing if captions routinely exceed this window.
