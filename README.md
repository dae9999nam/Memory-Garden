# Memory-Garden

## Recent updates

- Switched the `/generate-stories/` endpoint to call Hugging Face's hosted
  `Qwen/Qwen2.5-VL-7B-Instruct` model, so the FastAPI service no longer needs to
  download or serve the weights locally.
- Documented how mobile apps can POST multiple images to the endpoint and what
  to expect in the JSON response, including deployment and HTTPS guidance.
- Added an alternate `/generate-stories/from-remote/` workflow for base64 or
  URL-sourced images, matching Hugging Face's API guidance for Qwen VL inputs.

## Testing

To verify that the application source files have no syntax errors you can run:

```bash
python -m compileall app
```

This command asks Python to byte-compile every module under `app/`. It does **not** start the FastAPI server or download the Qwen model; it simply emits `.pyc` files under `app/__pycache__` if the code parses successfully.

## Hugging Face Inference API configuration

Story generation now calls the public Inference API for [`Qwen/Qwen2.5-VL-7B-Instruct`](https://huggingface.co/Qwen/Qwen2.5-VL-7B-Instruct). Set a Hugging Face access token in the `HUGGING_FACE_API_TOKEN` environment variable before starting the FastAPI server. You can also override the model id using `HUGGING_FACE_MODEL_ID` if you would like to target a different hosted checkpoint listed on the Hugging Face model page:

```bash
export HUGGING_FACE_API_TOKEN="hf_your_token_here"
# Optional: override the default model id of Qwen/Qwen2.5-VL-7B-Instruct
export HUGGING_FACE_MODEL_ID="Qwen/Qwen2.5-VL-7B-Instruct"
uvicorn app.main:app --reload
```

The `/generate-stories/` endpoint accepts multiple image uploads and forwards each photo and the storytelling prompt to Hugging Face for inference.

## Integrating with a mobile app

Yes—FastAPI exposes standard HTTP endpoints that mobile clients can call just like any other REST or JSON API. To integrate the `/generate-stories/` route into a native iOS or Android application:

1. Deploy the FastAPI service (for example with `uvicorn app.main:app --host 0.0.0.0 --port 8000`).
2. From the mobile app, send a `POST` request to `https://<your-backend-host>/generate-stories/` with a `multipart/form-data` body that contains one or more image files under the form field name `images`.
3. Parse the JSON response. Each entry under the `results` array contains the original filename and the generated story text.

Because mobile apps typically talk to HTTPS backends, make sure the deployment includes TLS termination (for example behind an API gateway or managed load balancer). You can also add authentication or request signing at the FastAPI layer if the mobile integration requires it.

## Manually testing with real photos

To try the `/generate-stories/` endpoint yourself with actual image files:

1. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```
   If you want helper utilities that mirror Hugging Face's Qwen VL API helpers
   for base64, URL, or video inputs you can also install the optional toolkit:

   ```bash
   # Linux users can install the faster decord extras.
   pip install "qwen-vl-utils[decord]==0.0.8"
   
   # On non-Linux systems fall back to the torchvision-backed build.
   pip install qwen-vl-utils==0.0.8
   ```
2. **Export your Hugging Face credentials** so the service can call the hosted model:
   ```bash
   export HUGGING_FACE_API_TOKEN="hf_your_token_here"
   # Optional: point to a different hosted checkpoint
   export HUGGING_FACE_MODEL_ID="Qwen/Qwen2.5-VL-7B-Instruct"
   ```
3. **Start the FastAPI server** (this example runs it locally on port 8000):
   ```bash
   uvicorn app.main:app --reload
   ```
4. **Send a test request with your photos.** In a separate terminal, use `curl` (or a REST client such as Postman or Thunder Client) to upload one or more image files. Replace the sample filenames with the paths to your pictures:
   ```bash
   curl -X POST "http://127.0.0.1:8000/generate-stories/" \
        -H "Authorization: Bearer $HUGGING_FACE_API_TOKEN" \
        -F "images=@/path/to/first_photo.jpg" \
        -F "images=@/path/to/second_photo.png" \
        -F "prompt=Write a gentle story about seasonal celebrations"
   ```
   The endpoint returns JSON that lists each uploaded filename and the generated story text. If the Hugging Face model is still loading you may receive a `202 Accepted` response—retry the request after a few seconds.
5. **Review the output** in the terminal or your REST client. You can share the JSON back with the mobile team or plug it into your UI to validate the storytelling experience.

If you deploy the service remotely, adjust the URL in step 4 to match the public HTTPS address and ensure that the `HUGGING_FACE_API_TOKEN` environment variable is set on the server.

## Calling the API with base64 or URLs

The Hugging Face Inference API for Qwen VL also accepts interleaved text and
vision inputs via base64 payloads or remote URLs. To mirror that flexibility the
FastAPI service exposes `/generate-stories/from-remote/`, which accepts JSON
payloads describing each image source:

```bash
curl -X POST "http://127.0.0.1:8000/generate-stories/from-remote/" \
     -H "Content-Type: application/json" \
     -d '{
           "prompt": "Gently narrate the family moment in these pictures.",
           "sources": [
             {"type": "url", "value": "https://example.com/family-photo.jpg"},
             {"type": "base64", "value": "<base64-encoded-image>"}
           ]
         }'
```

The response mirrors the multipart endpoint with a `results` array. When you
need to generate the base64 strings yourself, the `qwen-vl-utils` package listed
above provides convenience methods for turning local files, URLs, or even video
frames into the JSON format Hugging Face documents on the
[Qwen/Qwen2.5-VL-7B-Instruct](https://huggingface.co/Qwen/Qwen2.5-VL-7B-Instruct)
model card.
