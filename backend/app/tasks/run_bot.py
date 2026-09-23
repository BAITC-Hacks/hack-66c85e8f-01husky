"""Run a meeting bot in its dedicated worker, with bounded lifetime and scoped upload."""

import logging
import os
import signal
import subprocess
import sys

from bots.urls import validate_meeting_url
from sqlalchemy import select

from app.config import get_settings
from app.db import SessionLocal
from app.models import Meeting
from app.models.enums import MeetingStatus
from app.services.bot_tokens import awaiting_bot_audio, create_bot_upload_token
from app.tasks.celery_app import celery_app

log = logging.getLogger(__name__)


def _fail(meeting_id: int, error: str) -> None:
    with SessionLocal() as db:
        meeting = db.scalar(select(Meeting).where(Meeting.id == meeting_id).with_for_update())
        # The callback may already have handed the audio to the processing worker.
        if meeting and awaiting_bot_audio(meeting):
            meeting.status, meeting.error = MeetingStatus.failed, error[:2000]
            db.commit()


def _terminate_group(process: subprocess.Popen) -> None:
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    try:
        process.wait(timeout=20)
    except subprocess.TimeoutExpired:
        pass
    finally:
        # The parent may exit before Chromium or ffmpeg. Kill any remaining children.
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait()


def _environment(token: str, meeting_url: str) -> dict[str, str]:
    # The bot process needs its runtime, not API/DB/AI credentials from the worker.
    allowed = {
        "PATH",
        "HOME",
        "LANG",
        "LC_ALL",
        "TMPDIR",
        "DISPLAY",
        "XAUTHORITY",
        "PULSE_SERVER",
        "PULSE_COOKIE",
        "PULSE_SINK",
        "PULSE_SOURCE",
        "BOT_AUDIO_DEVICE",
        "XDG_RUNTIME_DIR",
        "PLAYWRIGHT_BROWSERS_PATH",
        "SSL_CERT_FILE",
        "SSL_CERT_DIR",
    }
    env = {key: value for key, value in os.environ.items() if key in allowed}
    env["KENES_BOT_UPLOAD_TOKEN"] = token
    env["KENES_BOT_MEETING_URL"] = meeting_url
    return env


@celery_app.task(name="app.tasks.run_bot.run_bot")
def run_bot(meeting_id: int) -> None:
    with SessionLocal() as db:
        meeting = db.scalar(select(Meeting).where(Meeting.id == meeting_id).with_for_update())
        if not meeting or not awaiting_bot_audio(meeting):
            return
        # A redelivery must not start a second browser for an already claimed meeting.
        if meeting.progress_stage != "bot_joining":
            return
        try:
            platform = meeting.platform
            url = validate_meeting_url(platform, meeting.bot_url)
        except (TypeError, ValueError):
            meeting.status, meeting.error = MeetingStatus.failed, "Invalid meeting URL"
            db.commit()
            return
        meeting.progress_stage = "bot_recording"
        db.commit()

    settings = get_settings()
    max_duration = min(
        settings.bot_max_recording_sec,
        settings.bot_timeout_sec
        - settings.bot_lobby_timeout_sec
        - settings.bot_upload_timeout_sec
        - 30,
    )
    if max_duration < 1:
        _fail(meeting_id, "Bot timeout must allow lobby, recording and upload")
        return
    cmd = [
        sys.executable,
        "-m",
        "bots.cli",
        "--headed",
        "--platform",
        platform,
        "--meeting-id",
        str(meeting_id),
        "--api-url",
        settings.public_api_url,
        "--lobby-timeout-sec",
        str(settings.bot_lobby_timeout_sec),
        "--max-duration-sec",
        str(max_duration),
        "--upload-timeout-sec",
        str(settings.bot_upload_timeout_sec),
        "--audio-device",
        settings.bot_audio_device,
        "--out-dir",
        "/tmp/kenes-recordings",
    ]
    try:
        token = create_bot_upload_token(meeting_id)
    except ValueError:
        _fail(meeting_id, "A non-default SECRET_KEY is required for meeting bots")
        return
    log.info("Starting meeting bot for meeting %s (%s)", meeting_id, platform)
    try:
        process = subprocess.Popen(
            cmd,
            env=_environment(token, url),
            start_new_session=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except OSError:
        _fail(meeting_id, "Cannot start meeting bot runtime")
        return
    try:
        returncode = process.wait(timeout=settings.bot_timeout_sec)
    except subprocess.TimeoutExpired:
        _terminate_group(process)
        _fail(meeting_id, "Meeting bot timed out")
        return
    except BaseException:
        _terminate_group(process)
        _fail(meeting_id, "Meeting bot worker was interrupted")
        raise
    _terminate_group(process)
    if returncode:
        _fail(meeting_id, f"Meeting bot exited with code {returncode}; check guest access")
    else:
        # Exit 0 without the accepted callback must not leave an endless spinner.
        _fail(meeting_id, "Meeting bot ended without uploading a recording")
