from datetime import UTC, datetime, timedelta

import pytest
from jose import jwt

from app.config import get_settings
from app.models import Meeting
from app.models.enums import MeetingSource, MeetingStatus
from app.security import create_access_token, decode_access_token
from app.services.bot_tokens import create_bot_upload_token, valid_bot_upload_token
from tests.helpers import wav_bytes


def bot_meeting(client):
    response = client.post(
        "/api/v1/meetings/bot",
        json={
            "title": "Bot",
            "meeting_date": "2026-09-23",
            "platform": "meet",
            "url": "https://meet.google.com/abc-defg-hij",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


@pytest.fixture(autouse=True)
def disable_queue(monkeypatch):
    monkeypatch.setattr("app.tasks.run_bot.run_bot.delay", lambda *args: None)


def upload(client, meeting_id, token):
    return client.post(
        f"/api/v1/meetings/{meeting_id}/audio",
        files={"file": ("recording.wav", wav_bytes(), "audio/wav")},
        headers={"X-Bot-Token": token},
    )


def test_token_is_meeting_scoped_and_not_a_login_token():
    token = create_bot_upload_token(42)
    assert valid_bot_upload_token(token, 42)
    assert not valid_bot_upload_token(token, 43)
    assert decode_access_token(token) is None
    assert not valid_bot_upload_token(create_access_token(42), 42)
    assert not valid_bot_upload_token("change-me-bot-token", 42)


@pytest.mark.parametrize(
    "claim,value",
    [
        ("exp", datetime.now(UTC) - timedelta(seconds=10)),
        ("aud", "other"),
        ("purpose", "login"),
        ("sub", "42"),
        ("meeting_id", 43),
    ],
)
def test_token_rejects_invalid_claims(claim, value):
    payload = jwt.get_unverified_claims(create_bot_upload_token(42))
    payload[claim] = value
    token = jwt.encode(payload, get_settings().secret_key, algorithm="HS256")
    assert not valid_bot_upload_token(token, 42)


def test_scoped_callback_rejects_replay_and_legacy_token(client, admin_client, db, monkeypatch):
    meeting_id = bot_meeting(admin_client)
    calls = []
    monkeypatch.setattr("app.routers.meetings.enqueue_processing", calls.append)
    token = create_bot_upload_token(meeting_id)
    assert upload(client, meeting_id, "change-me-bot-token").status_code == 401
    assert upload(client, meeting_id, create_bot_upload_token(meeting_id + 1)).status_code == 401
    assert upload(client, meeting_id, token).status_code == 200
    assert calls == [meeting_id]
    assert upload(client, meeting_id, token).status_code == 409
    assert calls == [meeting_id]


@pytest.mark.parametrize(
    "source,status,stage",
    [
        (MeetingSource.live, MeetingStatus.processing, "recording"),
        (MeetingSource.upload, MeetingStatus.uploaded, None),
        (MeetingSource.bot, MeetingStatus.failed, "bot_joining"),
        (MeetingSource.bot, MeetingStatus.processing, "transcribing"),
        (MeetingSource.bot, MeetingStatus.confirmed, None),
    ],
)
def test_callback_requires_pending_bot_state(client, admin_client, db, source, status, stage):
    meeting_id = bot_meeting(admin_client)
    meeting = db.get(Meeting, meeting_id)
    meeting.source, meeting.status, meeting.progress_stage = source, status, stage
    db.commit()
    assert upload(client, meeting_id, create_bot_upload_token(meeting_id)).status_code == 409


def test_cookie_editor_can_still_attach_audio(admin_client, monkeypatch):
    monkeypatch.setattr("app.routers.meetings.enqueue_processing", lambda *args: None)
    response = admin_client.post(
        "/api/v1/meetings/live", json={"title": "Live", "meeting_date": "2026-09-23"}
    )
    meeting_id = response.json()["id"]
    response = admin_client.post(
        f"/api/v1/meetings/{meeting_id}/audio",
        files={"file": ("recording.wav", wav_bytes(), "audio/wav")},
    )
    assert response.status_code == 200, response.text


def test_dispatch_contains_only_id(admin_client, monkeypatch):
    calls = []
    monkeypatch.setattr("app.tasks.run_bot.run_bot.delay", lambda *args: calls.append(args))
    meeting_id = bot_meeting(admin_client)
    assert calls == [(meeting_id,)]


def test_broker_failure_does_not_leave_processing(admin_client, db, monkeypatch):
    def unavailable(*args):
        raise OSError("broker offline")

    monkeypatch.setattr("app.tasks.run_bot.run_bot.delay", unavailable)
    response = admin_client.post(
        "/api/v1/meetings/bot",
        json={
            "title": "Bot",
            "meeting_date": "2026-09-23",
            "platform": "meet",
            "url": "https://meet.google.com/abc-defg-hij",
        },
    )
    assert response.status_code == 503
    db.expire_all()
    assert db.query(Meeting).one().status == MeetingStatus.failed


def test_simultaneous_callbacks_accept_audio_only_once(admin_client, _schema, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from io import BytesIO
    from threading import Barrier

    from fastapi import HTTPException, UploadFile
    from sqlalchemy.orm import Session

    from app.routers.meetings import upload_meeting_audio

    meeting_id = bot_meeting(admin_client)
    token = create_bot_upload_token(meeting_id)
    barrier = Barrier(2)
    enqueued = []
    monkeypatch.setattr("app.routers.meetings.enqueue_processing", enqueued.append)

    def callback():
        with Session(_schema) as session:
            barrier.wait(timeout=10)
            try:
                upload_meeting_audio(
                    meeting_id,
                    session,
                    UploadFile(filename="recording.wav", file=BytesIO(wav_bytes())),
                    x_bot_token=token,
                    access_token=None,
                )
                return 200
            except HTTPException as error:
                return error.status_code

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(callback) for _ in range(2)]
        results = [future.result(timeout=20) for future in futures]
    assert sorted(results) == [200, 409]
    assert enqueued == [meeting_id]


@pytest.mark.parametrize("key", ["", "   ", "change-me-in-env", "change-me-before-deployment"])
def test_placeholder_secret_cannot_issue_or_verify_bot_tokens(monkeypatch, key):
    payload = jwt.get_unverified_claims(create_bot_upload_token(42))
    forged = jwt.encode(payload, key, algorithm="HS256")
    monkeypatch.setattr(get_settings(), "secret_key", key)
    with pytest.raises(ValueError, match="non-default SECRET_KEY"):
        create_bot_upload_token(42)
    assert not valid_bot_upload_token(forged, 42)
