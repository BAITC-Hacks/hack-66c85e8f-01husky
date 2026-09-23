"""Linux Chromium -> PulseAudio -> ffmpeg smoke using the production bot lifecycle.

Run inside the bot-worker image with its normal entrypoint. No meeting is joined and
no recording is uploaded. All browser requests are fulfilled locally or blocked.
A missing browser, sink, ffmpeg, audible tone, or valid WAV is an error, never a skip.
"""

from __future__ import annotations

import json
import math
import os
import signal
import struct
import sys
import tempfile
import time
import wave
from itertools import pairwise
from pathlib import Path

from bots.base import BotConfig, BotError
from bots.browser import BrowserBot

# This synthetic address satisfies production URL validation. Playwright fulfills
# its document locally, before network access; there are no remote page assets.
FIXTURE_URL = "https://meet.google.com/abc-defg-hij"
RECORD_SECONDS = 4


class AudioSmokeBot(BrowserBot):
    def _route(self, route) -> None:
        if route.request.url == FIXTURE_URL and route.request.resource_type == "document":
            route.fulfill(
                status=200,
                content_type="text/html",
                body="<!doctype html><html><body>Kenes audio fixture</body></html>",
            )
        else:
            route.abort("blockedbyclient")

    @staticmethod
    def _websocket(route) -> None:
        route.close()

    def join(self) -> None:
        # Keep the actual launch options: sandbox, env allowlist, fake capture
        # devices, unmuted output, persistent temporary profile, and route hooks.
        self.open_browser()

    def wait_admitted(self, timeout_sec: int = 600) -> None:
        state = self.page.evaluate(
            """async () => {
                const audio = new AudioContext();
                const oscillator = audio.createOscillator();
                const gain = audio.createGain();
                oscillator.type = 'sine';
                oscillator.frequency.value = 440;
                gain.gain.value = 0.2;
                oscillator.connect(gain).connect(audio.destination);
                oscillator.start();
                await audio.resume();
                window.kenesAudio = {audio, oscillator, gain};
                return audio.state;
            }"""
        )
        if state != "running":
            raise BotError("Chromium did not start the WebAudio tone")

    def start_recording(self) -> None:
        super().start_recording()
        self.end_at = time.monotonic() + RECORD_SECONDS

    def call_ended(self) -> bool:
        if self.page.is_closed():
            raise BotError("Audio fixture browser closed unexpectedly")
        return time.monotonic() >= self.end_at

    def upload(self) -> dict:
        # MeetingBot.run already stopped ffmpeg, validated WAV, and closed Chromium.
        # Inspect the actual recording before its temporary directory is removed.
        with wave.open(str(self.audio_path), "rb") as recording:
            frames = recording.getnframes()
            if frames < 32000:
                raise BotError("Audio smoke captured less than two seconds")
            samples = [value[0] for value in struct.iter_unpack("<h", recording.readframes(frames))]
        active = [index for index, sample in enumerate(samples) if abs(sample) >= 100]
        if not active:
            raise BotError("Chromium output did not reach the PulseAudio monitor")
        first, last = active[0], active[-1]
        duration = (last - first) / 16000
        if duration < 2:
            raise BotError("Audio smoke captured less than two seconds of tone")
        segment = samples[first : last + 1]
        crossings = sum((left < 0) != (right < 0) for left, right in pairwise(segment))
        frequency = crossings / (2 * duration)
        rms = math.sqrt(sum(sample * sample for sample in segment) / len(segment)) / 32768
        if not 420 <= frequency <= 460 or rms < 0.03:
            raise BotError("PulseAudio recording does not contain the expected 440 Hz tone")
        return {
            "status": "passed",
            "sample_rate": 16000,
            "channels": 1,
            "frames": frames,
            "tone_seconds": round(duration, 3),
            "tone_hz": round(frequency, 1),
            "rms": round(rms, 4),
        }


def main() -> int:
    if sys.platform != "linux":
        print("Audio smoke requires the Linux bot-worker runtime", file=sys.stderr)
        return 2
    # Neither the Playwright driver nor its browser should inherit meeting credentials.
    os.environ.pop("KENES_BOT_UPLOAD_TOKEN", None)
    os.environ.pop("KENES_BOT_MEETING_URL", None)

    def interrupted(signum, frame):
        raise KeyboardInterrupt

    previous_term = signal.signal(signal.SIGTERM, interrupted)
    previous_alarm = signal.signal(signal.SIGALRM, interrupted)
    signal.alarm(90)
    try:
        with tempfile.TemporaryDirectory(prefix="kenes-audio-smoke-") as directory:
            config = BotConfig(
                platform="meet",
                url=FIXTURE_URL,
                meeting_id=1,
                api_url="",
                api_token="",
                out_dir=Path(directory),
                audio_device="pulse:kenes.monitor",
                max_duration_sec=8,
                lobby_timeout_sec=5,
            )
            result = AudioSmokeBot(config).run()
        print(json.dumps(result, sort_keys=True))
        return 0
    except KeyboardInterrupt:
        print("Audio smoke interrupted or exceeded its 90-second limit", file=sys.stderr)
        return 1
    except BotError as error:
        print(str(error), file=sys.stderr)
        return 1
    except Exception:  # noqa: BLE001 - runtime failures must not expose inherited credentials.
        print(
            "Audio smoke failed; inspect the Linux Chromium/PulseAudio/ffmpeg runtime",
            file=sys.stderr,
        )
        return 1
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGTERM, previous_term)
        signal.signal(signal.SIGALRM, previous_alarm)


if __name__ == "__main__":
    sys.exit(main())
