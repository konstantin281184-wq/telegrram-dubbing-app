import subprocess
import os

def process_video(input_path: str, output_path: str, speed: float = 1.0):
    cmd = [
        "ffmpeg", "-y", "-i", input_path,
        "-filter:v", f"setpts={1/speed}*PTS",
        output_path
    ]
    subprocess.run(cmd, check=True)
