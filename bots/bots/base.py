"""Recording lifecycle. Each call owns a temporary directory and subprocesses."""

from __future__ import annotations

import logging
import os
import signal
import stat
import struct
import subprocess
import tempfile
import time
import wave
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path

import httpx

log = logging.getLogger(__name__)


class BotError(RuntimeError):
    """A safe, fixed diagnostic; never include a provider URL or page contents."""


def child_environment() -> dict[str, str]:
    allowed = {
        "PATH",
        "HOME",
        "LANG",
        "LC_ALL",
        "DISPLAY",
        "XAUTHORITY",
        "XDG_RUNTIME_DIR",
        "PULSE_SERVER",
        "PULSE_SINK",
        "PULSE_SOURCE",
        "TMPDIR",
        "SYSTEMROOT",
    }
    return {key: value for key, value in os.environ.items() if key in allowed}


@dataclass
class BotConfig:
    platform: str
    url: str = field(repr=False)
    meeting_id: int
    api_url: str = field(repr=False)
    api_token: str = field(repr=False)
    display_name: str = "Kenes AI"
    max_duration_sec: int = 3 * 3600
    lobby_timeout_sec: int = 600
    upload_timeout_sec: int = 120
    out_dir: Path = field(default_factory=lambda: Path(tempfile.gettempdir()) / "kenes-recordings")
    audio_device: str = "pulse:default"
    headless: bool = True


class MeetingBot(ABC):
    def __init__(self, cfg: BotConfig) -> None:
        self.cfg = cfg
        self._ffmpeg: subprocess.Popen | None = None
        self.audio_path: Path | None = None
        self.work_dir: Path | None = None

    @abstractmethod
    def join(self) -> None: ...

    @abstractmethod
    def wait_admitted(self, timeout_sec: int = 600) -> None: ...

    @abstractmethod
    def call_ended(self) -> bool: ...

    @abstractmethod
    def leave(self) -> None: ...

    def start_recording(self) -> None:
        fmt, device = self.cfg.audio_device.split(":", 1)
        if fmt not in {"pulse", "avfoundation", "alsa"} or not device:
            raise BotError("Unsupported audio input")
        self._ffmpeg = subprocess.Popen(
            [
                "ffmpeg",
                "-nostdin",
                "-y",
                "-loglevel",
                "error",
                "-f",
                fmt,
                "-i",
                device,
                "-ac",
                "1",
                "-ar",
                "16000",
                "-c:a",
                "pcm_s16le",
                str(self.audio_path),
            ],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env=child_environment(),
        )

    def stop_recording(self) -> None:
        process = self._ffmpeg
        if process is None:
            return
        try:
            if process.poll() is None:
                process.send_signal(signal.SIGINT)
                try:
                    process.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)
                    raise BotError("Audio recorder did not stop cleanly") from None
        except ProcessLookupError:
            process.wait(timeout=5)
        finally:
            self._ffmpeg = None

    def record_until_end(self, poll_sec: float = 1) -> None:
        started = time.monotonic()
        while time.monotonic() - started < self.cfg.max_duration_sec:
            if self._ffmpeg is None or self._ffmpeg.poll() is not None:
                raise BotError("Audio recorder stopped unexpectedly")
            if self.call_ended():
                return
            time.sleep(poll_sec)
        log.info("Recording duration limit reached")

    def validate_audio(self) -> None:
        try:
            with wave.open(str(self.audio_path), "rb") as audio:
                if (
                    audio.getnchannels() != 1
                    or audio.getsampwidth() != 2
                    or audio.getframerate() != 16000
                    or audio.getnframes() < 16000
                ):
                    raise BotError("Recording is too short or has an invalid format")
                audible = 0
                frames = 0
                while data := audio.readframes(16000):
                    samples = tuple(v[0] for v in struct.iter_unpack("<h", data))
                    frames += len(samples)
                    audible += sum(abs(sample) >= 100 for sample in samples)
                if frames != audio.getnframes() or audible < 160:
                    raise BotError("Recording contains no usable audio or is truncated")
        except (OSError, wave.Error, EOFError, struct.error):
            raise BotError("Recording is not a valid WAV file") from None

    def upload(self) -> dict:
        with self.audio_path.open("rb") as audio:
            try:
                response = httpx.post(
                    f"{self.cfg.api_url}/meetings/{self.cfg.meeting_id}/audio",
                    files={"file": ("recording.wav", audio, "audio/wav")},
                    headers={"X-Bot-Token": self.cfg.api_token},
                    timeout=self.cfg.upload_timeout_sec,
                    follow_redirects=False,
                )
                response.raise_for_status()
                return response.json()
            except (httpx.HTTPError, ValueError):
                raise BotError("Recording upload failed") from None

    def run(self) -> dict:
        self.cfg.out_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        root = self.cfg.out_dir.lstat()
        if not stat.S_ISDIR(root.st_mode) or root.st_uid != os.getuid() or root.st_mode & 0o077:
            raise BotError("Recording directory must be private and owned by the bot user")
        with tempfile.TemporaryDirectory(prefix="kenes-call-", dir=self.cfg.out_dir) as directory:
            self.work_dir = Path(directory)
            self.audio_path = self.work_dir / "recording.wav"
            try:
                self.join()
                log.info("Join requested; waiting for admission")
                self.wait_admitted(self.cfg.lobby_timeout_sec)
                self.start_recording()
                log.info("Admitted; recording started")
                self.record_until_end()
                self.stop_recording()
                self.validate_audio()
            finally:
                try:
                    self.stop_recording()
                finally:
                    self.leave()
            return self.upload()
