from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import os
from models import DubbingRequest
from ffmpeg_utils import process_video

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

STORAGE_DIR = "storage/videos"
os.makedirs(STORAGE_DIR, exist_ok=True)

@app.post("/api/dub")
async def dub_video(file: UploadFile = File(...), voice: str = "default", speed: float = 1.0):
    input_path = os.path.join(STORAGE_DIR, f"input_{file.filename}")
    output_path = os.path.join(STORAGE_DIR, f"output_{file.filename}")
    
    with open(input_path, "wb") as buffer:
        content = await file.read()
        buffer.write(content)
        
    try:
        process_video(input_path, output_path, speed)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
        
    return {"message": "Success", "video_url": f"/api/download/{os.path.basename(output_path)}"}

@app.get("/api/download/{filename}")
async def download_video(filename: str):
    file_path = os.path.join(STORAGE_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(file_path)
