"""File-backed fake devices: static Kenes logo and PCM digital silence."""

import subprocess
import wave
from pathlib import Path

from bots.base import BotError, child_environment

CAMERA_WIDTH = 1920
CAMERA_HEIGHT = 1080
CAMERA_ASSET = Path(__file__).with_name("assets") / "camera.png"


def prepare_media(directory: Path) -> tuple[Path, Path]:
    """Create both inputs before Chromium starts. Never fall back to generated devices."""
    camera = directory / "camera.y4m"
    microphone = directory / "microphone.wav"
    try:
        subprocess.run(
            [
                "ffmpeg",
                "-nostdin",
                "-y",
                "-loglevel",
                "error",
                "-i",
                str(CAMERA_ASSET),
                "-frames:v",
                "1",
                "-pix_fmt",
                "yuv420p",
                "-f",
                "yuv4mpegpipe",
                str(camera),
            ],
            check=True,
            timeout=20,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env=child_environment(),
        )
        with camera.open("rb") as frame:
            header = frame.readline()
            marker = frame.readline()
            pixels = frame.read()
        if (
            not header.startswith(b"YUV4MPEG2 ")
            or f" W{CAMERA_WIDTH} ".encode() not in header
            or f" H{CAMERA_HEIGHT} ".encode() not in header
            or b" C420" not in header
            or not marker.startswith(b"FRAME")
            or len(pixels) != CAMERA_WIDTH * CAMERA_HEIGHT * 3 // 2
        ):
            raise BotError("Static camera input failed validation; browser was not started")
        with wave.open(str(microphone), "wb") as audio:
            audio.setnchannels(1)
            audio.setsampwidth(2)
            audio.setframerate(48000)
            audio.writeframes(bytes(48000 * 2))
        camera.chmod(0o600)
        microphone.chmod(0o600)
        return camera, microphone
    except (OSError, subprocess.SubprocessError, wave.Error):
        raise BotError(
            "Safe camera/microphone preparation failed; browser was not started"
        ) from None
