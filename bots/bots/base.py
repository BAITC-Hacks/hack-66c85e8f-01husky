"""Meeting bot contract. Owner: Ардак.

Lifecycle: join(url) → wait_admitted() → record(...) until the call ends or max duration → leave()
→ upload(). Platform adapters (meet.py, zoom.py, teams.py) implement the selectors; recording and
upload are shared here.

Audio capture strategy (Linux/docker): Chromium with a PulseAudio null sink, `ffmpeg -f pulse`
records the sink monitor to a WAV. On macOS during development a BlackHole virtual device works
the same way with `-f avfoundation`.
"""

from __future__ import annotations

import logging
import subprocess
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

import httpx

log = logging.getLogger(__name__)


@dataclass
class BotConfig:
    platform: str
    url: str
    meeting_id: int
    api_url: str
    api_token: str
    display_name: str = "Протокол-бот"
    max_duration_sec: int = 3 * 3600
    out_dir: Path = Path("recordings")
    audio_device: str = "pulse:default"  # ffmpeg input, e.g. "pulse:protocol_sink.monitor"
    headless: bool = True


class MeetingBot(ABC):
    def __init__(self, cfg: BotConfig) -> None:
        self.cfg = cfg
        self._ffmpeg: subprocess.Popen[bytes] | None = None
        self.audio_path = cfg.out_dir / f"meeting_{cfg.meeting_id}.wav"

    # --- platform-specific -------------------------------------------------
    @abstractmethod
    def join(self) -> None:
        """Open the meeting URL, set display name, mute mic/cam, click Join / Ask to join."""

    @abstractmethod
    def wait_admitted(self, timeout_sec: int = 600) -> None:
        """Block until the host admits the bot (lobby) or raise TimeoutError."""

    @abstractmethod
    def call_ended(self) -> bool:
        """True when the meeting UI shows the call is over or the bot was removed."""

    @abstractmethod
    def leave(self) -> None:
        """Click Leave and close the browser."""

    # --- shared ---------------------------------------------------------------
    def start_recording(self) -> None:
        self.cfg.out_dir.mkdir(parents=True, exist_ok=True)
        fmt, device = self.cfg.audio_device.split(":", 1)
        self._ffmpeg = subprocess.Popen(
            [
                "ffmpeg",
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
                str(self.audio_path),
            ],
        )
        log.info("recording to %s", self.audio_path)

    def stop_recording(self) -> None:
        if self._ffmpeg and self._ffmpeg.poll() is None:
            self._ffmpeg.terminate()
            self._ffmpeg.wait(timeout=30)

    def record_until_end(self, poll_sec: int = 10) -> None:
        started = time.monotonic()
        while time.monotonic() - started < self.cfg.max_duration_sec:
            if self.call_ended():
                return
            time.sleep(poll_sec)
        log.warning("max duration reached, leaving")

    def upload(self) -> dict:
        with self.audio_path.open("rb") as f:
            r = httpx.post(
                f"{self.cfg.api_url}/meetings/{self.cfg.meeting_id}/audio",
                files={"file": (self.audio_path.name, f, "audio/wav")},
                headers={"X-Bot-Token": self.cfg.api_token},
                timeout=300,
            )
        r.raise_for_status()
        return r.json()

    def run(self) -> dict:
        self.join()
        self.wait_admitted()
        self.start_recording()
        try:
            self.record_until_end()
        finally:
            self.stop_recording()
            self.leave()
        return self.upload()
