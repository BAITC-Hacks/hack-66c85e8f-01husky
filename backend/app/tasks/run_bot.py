"""Celery task: launch the Playwright meeting bot (bots/ package, owner Ардак) as a subprocess.

The bot joins the call, records audio and uploads it to POST /meetings/{id}/audio using
BOT_API_TOKEN. Until bots/ exists, the meeting is marked failed with a clear error.
"""

import logging
import subprocess
from pathlib import Path

from app.config import get_settings
from app.db import SessionLocal
from app.models import Meeting
from app.models.enums import MeetingStatus
from app.tasks.celery_app import celery_app

log = logging.getLogger(__name__)

BOTS_DIR = Path(__file__).resolve().parents[3] / "bots"


def _fail(meeting_id: int, error: str) -> None:
    with SessionLocal() as db:
        m = db.get(Meeting, meeting_id)
        if m:
            m.status, m.error = MeetingStatus.failed, error[:2000]
            db.commit()


@celery_app.task(name="app.tasks.run_bot.run_bot")
def run_bot(meeting_id: int, platform: str, url: str) -> None:
    if not (BOTS_DIR / "bots" / "cli.py").exists():
        _fail(meeting_id, "Meeting bot is not installed (bots/ package missing)")
        return
    s = get_settings()
    cmd = [
        "uv",
        "run",
        "python",
        "-m",
        "bots.cli",
        "--platform",
        platform,
        "--url",
        url,
        "--meeting-id",
        str(meeting_id),
        "--api-url",
        s.public_api_url,
        "--api-token",
        s.bot_api_token,
    ]
    log.info("run_bot %s: %s", meeting_id, " ".join(cmd[:8]))
    try:
        subprocess.run(cmd, cwd=BOTS_DIR, check=True, timeout=s.bot_timeout_sec)
    except subprocess.CalledProcessError as e:
        _fail(meeting_id, f"Bot exited with code {e.returncode}")
    except subprocess.TimeoutExpired:
        _fail(meeting_id, f"Bot timed out after {s.bot_timeout_sec}s")
