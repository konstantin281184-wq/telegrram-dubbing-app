"""
FastAPI backend for the "Dubl" Telegram Mini App.

Responsibilities:
  - serve the scene catalog (GET /api/scenes, /api/scenes/{id})
  - accept a user's audio recording for a given scene
  - merge that audio onto the scene's source video with FFmpeg
  - return a URL to the rendered result

Run locally:
    uvicorn main:app --reload --port 8000

Requires the `ffmpeg` binary to be installed and on PATH.
"""

import logging
import uuid
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from ffmpeg_utils import FFmpegError, merge_audio_with_video
from models import DubResponse, Scene

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("dubl")

BASE_DIR = Path(__file__).resolve().parent
STORAGE_DIR = BASE_DIR / "storage"
VIDEOS_DIR = STORAGE_DIR / "videos"      # original scene videos, e.g. 0.mp4, 1.mp4 ...
UPLOADS_DIR = STORAGE_DIR / "uploads"    # raw audio uploads from users
OUTPUT_DIR = STORAGE_DIR / "output"      # rendered, merged videos

for d in (VIDEOS_DIR, UPLOADS_DIR, OUTPUT_DIR):
    d.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="Dubl API", version="1.0.0")

# In production, replace "*" with your Mini App's actual origin.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve only the rendered videos and source scenes as static files, e.g.
#   /media/output/<file>.mp4   /media/videos/<file>.mp4
# `uploads/` (raw user recordings) is deliberately NOT mounted here, so
# users' unedited voice recordings stay off the public web.
app.mount("/media/output", StaticFiles(directory=OUTPUT_DIR), name="media-output")
app.mount("/media/videos", StaticFiles(directory=VIDEOS_DIR), name="media-videos")


# ---------------------------------------------------------------------------
# Catalog — replace this in-memory list with a real database (Postgres etc.)
# ---------------------------------------------------------------------------
SCENES: list[Scene] = [
    Scene(id=0, film="Планета Оксана", title="Финальный монолог перед стартом",
          duration_sec=42, level=2, category="Драма", video_file="0.mp4"),
    Scene(id=1, film="Ночной патруль", title="Допрос в участке, реплики Волкова",
          duration_sec=70, level=3, category="Драма", video_file="1.mp4"),
    Scene(id=2, film="Сырники и звёзды", title="Утренний диалог на кухне",
          duration_sec=35, level=1, category="Комедия", video_file="2.mp4"),
    Scene(id=3, film="Красный шторм", title="Радиообмен на мостике",
          duration_sec=58, level=2, category="Экшн", video_file="3.mp4"),
]
SCENES_BY_ID = {s.id: s for s in SCENES}


@app.get("/api/scenes", response_model=list[Scene])
def list_scenes():
    """Return the full scene catalog for the Mini App's main screen."""
    return SCENES


@app.get("/api/scenes/{scene_id}", response_model=Scene)
def get_scene(scene_id: int):
    scene = SCENES_BY_ID.get(scene_id)
    if scene is None:
        raise HTTPException(status_code=404, detail="Сцена не найдена")
    return scene


@app.post("/api/scenes/{scene_id}/dub", response_model=DubResponse)
async def dub_scene(
    scene_id: int,
    audio: UploadFile = File(..., description="User's recorded/uploaded voice track"),
    init_data: str | None = Form(None, description="Telegram WebApp initData, for auth/verification"),
):
    """
    Accept a user's audio track, merge it onto the scene's source video
    with FFmpeg, and return a link to the rendered file.
    """
    scene = SCENES_BY_ID.get(scene_id)
    if scene is None:
        raise HTTPException(status_code=404, detail="Сцена не найдена")

    source_video = VIDEOS_DIR / scene.video_file
    if not source_video.exists():
        raise HTTPException(
            status_code=500,
            detail=f"Исходное видео для сцены не найдено на сервере: {scene.video_file}",
        )

    # TODO: verify `init_data` against your bot token before trusting the request.
    # See: https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app

    job_id = uuid.uuid4().hex[:12]
    audio_suffix = Path(audio.filename or "audio.webm").suffix or ".webm"
    audio_path = UPLOADS_DIR / f"{job_id}{audio_suffix}"
    output_path = OUTPUT_DIR / f"{job_id}.mp4"

    with audio_path.open("wb") as f:
        f.write(await audio.read())

    try:
        merge_audio_with_video(
            video_path=source_video,
            audio_path=audio_path,
            output_path=output_path,
        )
    except FFmpegError as exc:
        logger.exception("FFmpeg merge failed for job %s", job_id)
        raise HTTPException(status_code=500, detail=f"Ошибка монтажа: {exc}") from exc

    return DubResponse(
        job_id=job_id,
        scene_id=scene_id,
        output_url=f"/media/output/{output_path.name}",
    )
