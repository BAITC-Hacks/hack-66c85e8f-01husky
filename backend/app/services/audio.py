"""Audio file handling: store upload, normalize to 16 kHz mono WAV with ffmpeg, probe duration."""

import json
import shutil
import subprocess
from pathlib import Path

from fastapi import UploadFile

from app.config import get_settings

ALLOWED_EXT = {"wav", "mp3", "m4a", "aac", "ogg", "opus", "webm", "flac", "mp4", "mkv", "mov"}


def meeting_dir(meeting_id: int) -> Path:
    d = get_settings().audio_dir / str(meeting_id)
    d.mkdir(parents=True, exist_ok=True)
    return d


def save_upload(meeting_id: int, upload: UploadFile) -> Path:
    ext = (upload.filename or "audio.wav").rsplit(".", 1)[-1].lower()
    if ext not in ALLOWED_EXT:
        raise ValueError(f"Unsupported file type .{ext}")
    dest = meeting_dir(meeting_id) / f"source.{ext}"
    with dest.open("wb") as f:
        shutil.copyfileobj(upload.file, f)
    return dest


def to_wav(src: Path) -> Path:
    dest = src.parent / "audio.wav"
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-loglevel",
            "error",
            "-i",
            str(src),
            "-ac",
            "1",
            "-ar",
            "16000",
            str(dest),
        ],
        check=True,
    )
    return dest


def probe_duration(path: Path) -> float | None:
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", str(path)],
            check=True,
            capture_output=True,
            text=True,
        ).stdout
        return float(json.loads(out)["format"]["duration"])
    except (subprocess.CalledProcessError, KeyError, ValueError, FileNotFoundError):
        return None


def delete_meeting_audio(meeting_id: int) -> None:
    d = get_settings().audio_dir / str(meeting_id)
    if d.exists():
        shutil.rmtree(d)
