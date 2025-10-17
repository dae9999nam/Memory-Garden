# 🌺 Memory Garden FastAPI

<div align="center">

![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)
![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)
![Ollama](https://img.shields.io/badge/Ollama-000000?style=for-the-badge&logo=ollama&logoColor=white)

**Transform your precious memories into beautiful stories with AI-powered image captioning**

_A modern, high-performance FastAPI service that turns your photos into vivid narratives using advanced vision-language models_

</div>

---

## ✨ Features

🖼️ **Multi-Image Processing** - Upload multiple photos and create cohesive stories  
🤖 **AI-Powered Storytelling** - Leverages Ollama's LLaVA model for intelligent image understanding  
⚡ **High Performance** - Built with FastAPI for blazing-fast async operations  
📁 **Smart Storage** - Efficient file system storage with unique identifiers  
🎨 **Rich Context** - Include date, location, weather, and personal notes  
📖 **Interactive Documentation** - Auto-generated API docs with Swagger UI

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- [Ollama](https://ollama.ai/) with LLaVA model installed

```bash
# Install Ollama (macOS)
brew install ollama

# Pull the LLaVA model
ollama pull llava
```

### Installation

1. **Clone the repository**

   ```bash
   git clone https://github.com/siwookim1114/elderly-connect-hk.git
   cd elderly-connect-hk
   ```

2. **Set up virtual environment**

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

4. **Start Ollama service**

   ```bash
   ollama serve
   ```

5. **Run the FastAPI server**
   ```bash
   cd "FastAPI App"
   uvicorn main:app --host 0.0.0.0 --port 8000 --reload
   ```

🎉 **Your Memory Garden is now running at** `http://localhost:8000`

## 📚 API Documentation

### Interactive Documentation

- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

### 🔄 Generate Story

**`POST /upload/stories`**

Transform your photos into a beautiful narrative with contextual information.

#### Request Format

```bash
curl -X POST "http://localhost:8000/upload/stories" \
  -F "photos=@photo1.jpg" \
  -F "photos=@photo2.jpg" \
  -F "date=2024-10-15" \
  -F "place=Central Park, New York" \
  -F "weather=Sunny and crisp autumn day" \
  -F "notes=Family picnic with grandchildren"
```

#### Response Example

```json
{
  "story_id": "550e8400-e29b-41d4-a716-446655440000",
  "story": "The golden autumn sun filtered through the changing leaves as we gathered in Central Park for our family picnic. The crisp air carried the laughter of children as they played on the grass, their joy infectious and warming our hearts even more than the bright sunshine...",
  "context": {
    "date": "2024-10-15",
    "place": "Central Park, New York",
    "weather": "Sunny and crisp autumn day",
    "notes": "Family picnic with grandchildren"
  },
  "photos": [
    {
      "id": "photo_001",
      "filename": "photo1.jpg",
      "stored_path": "uploads/550e8400-e29b-41d4-a716-446655440000_photo1.jpg"
    }
  ],
  "created_at": "2024-10-15T14:30:00Z"
}
```

#### Parameters

| Parameter | Type   | Required | Description                   |
| --------- | ------ | -------- | ----------------------------- |
| `photos`  | File[] | ✅       | Image files (JPEG, PNG, WebP) |
| `date`    | String | ❌       | When photos were taken        |
| `place`   | String | ❌       | Location context              |
| `weather` | String | ❌       | Weather conditions            |
| `notes`   | String | ❌       | Additional context            |

### 📸 Retrieve Story

**`GET /story/{story_id}`**

Fetch a previously generated story and its metadata.

### 🖼️ Download Photo

**`GET /photo/{photo_id}`**

Download original uploaded photos by their unique identifier.

## 🏗️ Architecture

```
Memory Garden FastAPI
├── 🚀 FastAPI Application
├── 🤖 Ollama Integration
│   └── LLaVA Vision-Language Model
├── 📁 File Storage System
│   └── Local uploads directory
├── 🔧 Pydantic Models
│   └── Type-safe data validation
└── ⚡ Async Request Handling
```

## 🛠️ Development

### Project Structure

```
FastAPI App/
├── main.py              # FastAPI application
├── uploads/             # Photo storage directory
└── __pycache__/         # Python cache (gitignored)
```

### Environment Configuration

The application uses sensible defaults but can be customized:

- **Ollama Model**: `llava` (configurable in code)
- **Upload Directory**: `FastAPI App/uploads/`
- **Server Port**: `8000`
- **Ollama Host**: `http://localhost:11434`

### Development Commands

```bash
# Start with auto-reload
uvicorn main:app --reload

# Run with custom host/port
uvicorn main:app --host 0.0.0.0 --port 9000

# Generate OpenAPI schema
python -c "import json; from main import app; print(json.dumps(app.openapi(), indent=2))"
```

## 🔧 Technical Details

- **Framework**: FastAPI 0.104+
- **Python**: 3.8+
- **AI Model**: Ollama LLaVA
- **Async Support**: Full async/await implementation
- **File Handling**: Secure multipart upload processing
- **Validation**: Pydantic models for type safety
- **Documentation**: Auto-generated OpenAPI/Swagger

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guidelines](CONTRIBUTING.md) for details.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

<div align="center">
Made with ❤️ for preserving precious memories

**[Documentation](http://localhost:8000/docs)** • **[Issues](https://github.com/siwookim1114/elderly-connect-hk/issues)** • **[Discussions](https://github.com/siwookim1114/elderly-connect-hk/discussions)**

</div>
