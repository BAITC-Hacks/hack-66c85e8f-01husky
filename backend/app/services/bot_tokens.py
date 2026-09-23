"""Meeting-scoped upload credentials, deliberately incompatible with login JWTs."""

from datetime import UTC, datetime, timedelta

from jose import JWTError, jwt

from app.config import get_settings
from app.models.enums import MeetingSource, MeetingStatus
from app.security import ALGORITHM

AUDIENCE = "kenes-bot-upload"
PURPOSE = "meeting-audio-upload"
BOT_STAGES = {"bot_joining", "bot_recording"}


def _signing_key() -> str:
    key = get_settings().secret_key
    if not key.strip() or key.strip() in {"change-me-in-env", "change-me-before-deployment"}:
        raise ValueError("A non-default SECRET_KEY is required for meeting bots")
    return key


def create_bot_upload_token(meeting_id: int) -> str:
    settings = get_settings()
    key = _signing_key()
    now = datetime.now(UTC)
    return jwt.encode(
        {
            "sub": f"meeting:{meeting_id}",
            "meeting_id": meeting_id,
            "aud": AUDIENCE,
            "purpose": PURPOSE,
            "iat": now,
            "exp": now + timedelta(seconds=settings.bot_timeout_sec + 120),
        },
        key,
        algorithm=ALGORITHM,
    )


def valid_bot_upload_token(token: str, meeting_id: int) -> bool:
    try:
        claims = jwt.decode(
            token,
            _signing_key(),
            algorithms=[ALGORITHM],
            audience=AUDIENCE,
            options={"require_exp": True, "require_iat": True, "require_sub": True},
        )
    except (JWTError, ValueError):
        return False
    return (
        claims.get("sub") == f"meeting:{meeting_id}"
        and claims.get("meeting_id") == meeting_id
        and claims.get("aud") == AUDIENCE
        and claims.get("purpose") == PURPOSE
    )


def awaiting_bot_audio(meeting) -> bool:
    return (
        meeting.source == MeetingSource.bot
        and meeting.status == MeetingStatus.processing
        and meeting.progress_stage in BOT_STAGES
        and meeting.audio_path is None
    )
