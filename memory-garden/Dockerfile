FROM python:3.12.4

WORKDIR /app

# Prevent Python from writing .pyc files and ensure output is sent straight to the terminal for easier debugging
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Document the intended port for the application; optional for most orchestrators
EXPOSE 8001

# If your entrypoint is not main.py or the app object is named differently, update as follows:
# CMD ["uvicorn", "your_entrypoint:your_app_object", "--host", "0.0.0.0", "--port", "8001"]
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]