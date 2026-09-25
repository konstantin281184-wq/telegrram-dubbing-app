"""
Thin wrapper around the `ffmpeg` CLI for replacing / mixing the audio
track of a scene video with a user's recorded dub.
"""

import shutil
import subprocess
from pathlib import Path


class FFmpegError(RuntimeError):
    """Raised when the ffmpeg subprocess fails or is unavailable."""


def _ensure_ffmpeg_available() -> None:
    if shutil.which("ffmpeg") is None:
        raise FFmpegError(
            "Бинарь ffmpeg не найден в PATH. Установите ffmpeg на сервере "
            "(например: apt-get install ffmpeg)."
        )


def merge_audio_with_video(
    video_path: Path,
    audio_path: Path,
    output_path: Path,
    mode: str = "replace",
    timeout_sec: int = 120,
) -> Path:
    """
    Combine `audio_path` with the video track of `video_path`, writing
    the result to `output_path`.

    mode:
      - "replace": the user's audio fully replaces the original audio track
                    (typical for a clean dub-over).
      - "mix":      the user's audio is mixed with the original track at
                    reduced volume (useful to keep background music/SFX).

    The output length matches the shortest of the two inputs, so a short
    dub simply trims the clip rather than looping — swap `-shortest` for
    explicit `-t <seconds>` if you want scene-length padding instead.
    """
    _ensure_ffmpeg_available()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if mode == "mix":
        # Keep some of the original bed under the new voice track.
        filter_complex = (
            "[0:a]volume=0.25[bg];[1:a]volume=1.0[voice];"
            "[bg][voice]amix=inputs=2:duration=shortest:dropout_transition=2[aout]"
        )
        cmd = [
            "ffmpeg", "-y",
            "-i", str(video_path),
            "-i", str(audio_path),
            "-filter_complex", filter_complex,
            "-map", "0:v:0",
            "-map", "[aout]",
            "-c:v", "copy",
            "-c:a", "aac", "-b:a", "192k",
            "-shortest",
            str(output_path),
        ]
    else:
        # Straight replace: take video from input 0, audio from input 1.
        cmd = [
            "ffmpeg", "-y",
            "-i", str(video_path),
            "-i", str(audio_path),
            "-map", "0:v:0",
            "-map", "1:a:0",
            "-c:v", "copy",
            "-c:a", "aac", "-b:a", "192k",
            "-shortest",
            str(output_path),
        ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_sec,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise FFmpegError(f"ffmpeg не уложился в {timeout_sec} сек.") from exc

    if result.returncode != 0:
        # ffmpeg writes its diagnostics to stderr
        raise FFmpegError(result.stderr[-2000:] if result.stderr else "неизвестная ошибка ffmpeg")

    if not output_path.exists():
        raise FFmpegError("ffmpeg завершился без ошибки, но выходной файл не создан")

    return output_path
