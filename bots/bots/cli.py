"""Guest meeting runner; the scoped callback credential is passed only via env."""

import argparse
import logging
import os
import signal
import sys
import tempfile
from pathlib import Path

from bots.base import BotConfig, BotError
from bots.urls import validate_meeting_url

log = logging.getLogger(__name__)
ADAPTERS = {
    "meet": "bots.meet:MeetBot",
    "zoom": "bots.zoom:ZoomBot",
    "teams": "bots.teams:TeamsBot",
}


def build(cfg: BotConfig):
    module, cls = ADAPTERS[cfg.platform].split(":")
    return getattr(__import__(module, fromlist=[cls]), cls)(cfg)


def positive(value):
    number = int(value)
    if number <= 0:
        raise argparse.ArgumentTypeError("must be positive")
    return number


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Kenes AI guest: join, record, upload")
    ap.add_argument("--platform", choices=sorted(ADAPTERS), required=True)
    ap.add_argument("--url", help="Manual use only; worker uses KENES_BOT_MEETING_URL")
    ap.add_argument("--meeting-id", type=positive, required=True)
    ap.add_argument("--api-url", required=True)
    ap.add_argument("--display-name", default="Kenes AI")
    ap.add_argument("--max-duration-sec", "--max-duration", type=positive, default=3 * 3600)
    ap.add_argument("--lobby-timeout-sec", "--lobby-timeout", type=positive, default=600)
    ap.add_argument("--upload-timeout-sec", type=positive, default=120)
    ap.add_argument(
        "--audio-device",
        default=os.getenv("KENES_AUDIO_DEVICE", os.getenv("BOT_AUDIO_DEVICE", "pulse:default")),
    )
    ap.add_argument(
        "--out-dir", type=Path, default=Path(tempfile.gettempdir()) / "kenes-recordings"
    )
    ap.add_argument("--headed", action="store_true")
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    token = os.environ.pop("KENES_BOT_UPLOAD_TOKEN", "")
    invitation = os.environ.pop("KENES_BOT_MEETING_URL", "") or args.url or ""
    if not token:
        log.error("Scoped upload credential is missing")
        return 1
    try:
        url = validate_meeting_url(args.platform, invitation)
    except ValueError:
        log.error("Meeting invitation URL is invalid")
        return 1
    cfg = BotConfig(
        platform=args.platform,
        url=url,
        meeting_id=args.meeting_id,
        api_url=args.api_url.rstrip("/"),
        api_token=token,
        display_name=args.display_name,
        max_duration_sec=args.max_duration_sec,
        lobby_timeout_sec=args.lobby_timeout_sec,
        upload_timeout_sec=args.upload_timeout_sec,
        out_dir=args.out_dir,
        audio_device=args.audio_device,
        headless=not args.headed,
    )

    def terminate(signum, frame):
        raise KeyboardInterrupt

    previous = signal.signal(signal.SIGTERM, terminate)
    try:
        build(cfg).run()
    except KeyboardInterrupt:
        log.error("Meeting bot interrupted; resources released")
        return 130
    except BotError as error:
        log.error("%s", error)
        return 1
    except Exception:  # noqa: BLE001 - CLI boundary must redact provider exception text.
        # Playwright/http clients include invitation URLs and tokens in exception text.
        log.error("Meeting bot failed; check browser/audio runtime or provider UI compatibility")
        return 1
    finally:
        signal.signal(signal.SIGTERM, previous)
    log.info("Recording uploaded")
    return 0


if __name__ == "__main__":
    sys.exit(main())
