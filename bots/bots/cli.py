"""Entry point used by the backend (app/tasks/run_bot.py):

    python -m bots.cli --platform meet --url https://meet.google.com/abc-defg-hij \
        --meeting-id 12 --api-url http://api:8000/api/v1 --api-token $BOT_API_TOKEN

Exit code 0 = recording uploaded. Any other = backend marks the meeting failed.
"""

import argparse
import logging
import sys
from pathlib import Path

from bots.base import BotConfig

log = logging.getLogger(__name__)

ADAPTERS = {
    "meet": "bots.meet:MeetBot",
    "zoom": "bots.zoom:ZoomBot",
    "teams": "bots.teams:TeamsBot",
}


def build(cfg: BotConfig):
    module, cls = ADAPTERS[cfg.platform].split(":")
    mod = __import__(module, fromlist=[cls])
    return getattr(mod, cls)(cfg)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Meeting bot: join, record, upload")
    ap.add_argument("--platform", choices=sorted(ADAPTERS), required=True)
    ap.add_argument("--url", required=True)
    ap.add_argument("--meeting-id", type=int, required=True)
    ap.add_argument("--api-url", required=True)
    ap.add_argument("--api-token", required=True)
    ap.add_argument("--display-name", default="Протокол-бот")
    ap.add_argument("--max-duration", type=int, default=3 * 3600, help="seconds")
    ap.add_argument("--audio-device", default="pulse:default", help="ffmpeg input, fmt:device")
    ap.add_argument("--out-dir", type=Path, default=Path("recordings"))
    ap.add_argument("--headed", action="store_true")
    args = ap.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    cfg = BotConfig(
        platform=args.platform,
        url=args.url,
        meeting_id=args.meeting_id,
        api_url=args.api_url.rstrip("/"),
        api_token=args.api_token,
        display_name=args.display_name,
        max_duration_sec=args.max_duration,
        out_dir=args.out_dir,
        audio_device=args.audio_device,
        headless=not args.headed,
    )
    try:
        result = build(cfg).run()
    except NotImplementedError as e:
        log.error("adapter not implemented: %s", e)
        return 2
    log.info("uploaded: %s", result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
