FROM python:3.11-slim

# ffmpeg is not in the base image — install it at build time so hosting
# platforms (Render, Railway, Fly.io, etc.) have it available at runtime.
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
