import axios from "axios";

const DEFAULT_MODEL = process.env.OLLAMA_MODEL || "llava";
const BASE_URL = process.env.OLLAMA_BASE_URL || "http://localhost:11434";

export async function generateStoryFromImages({
  prompt,
  images,
  model = DEFAULT_MODEL,
}) {
  if (!Array.isArray(images) || images.length === 0) {
    const error = new Error(
      "At least one image is required to generate a story."
    );
    error.status = 400;
    throw error;
  }

  const payload = {
    model: model,
    prompt: prompt,
    images: images,
    stream: false,
  };

  try {
    const response = await axios.post(`${BASE_URL}/api/generate`, payload, {
      headers: {
        "Content-Type": "application/json",
      },
      timeout: 60000,
    });

    if (typeof response.data?.response !== "string") {
      throw new Error("Ollama response did not include generated text.");
    }

    return response.data.response.trim();
  } catch (error) {
    const err = new Error("Failed to generate story using Ollama.");
    err.status = error.response?.status || 502;
    err.details = error.response?.data || error.message;
    throw err;
  }
}
