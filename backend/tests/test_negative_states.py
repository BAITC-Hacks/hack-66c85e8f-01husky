"""QA5: negative scenarios for meetings / live / bot state machine and access."""

import io

import pytest
from sqlalchemy import select
from starlette.websockets import WebSocketDisconnect

from app.models import Meeting
from app.models.enums import MeetingStatus
from tests.helpers import create_meeting, wav_bytes

TOKEN = {"X-Bot-Token": "change-me-bot-token"}


def _files():
    return {"file": ("rec.wav", io.BytesIO(wav_bytes()), "audio/wav")}


@pytest.fixture
def draft(admin_client, monkeypatch):
    monkeypatch.setenv("CELERY_EAGER", "1")
    m = create_meeting(admin_client).json()
    return admin_client.get(f"/api/v1/meetings/{m['id']}").json()


def _set_status(db, meeting_id: int, status: MeetingStatus, stage: str | None = None) -> None:
    m = db.scalar(select(Meeting).where(Meeting.id == meeting_id))
    m.status, m.progress_stage = status, stage
    db.commit()


def test_reprocess_while_processing_conflicts(admin_client, draft, db) -> None:
    _set_status(db, draft["id"], MeetingStatus.processing, "stt")
    assert admin_client.post(f"/api/v1/meetings/{draft['id']}/reprocess").status_code == 409
    assert admin_client.delete(f"/api/v1/meetings/{draft['id']}/audio").status_code == 409


def test_reprocess_failed_meeting_recovers(admin_client, draft, db) -> None:
    _set_status(db, draft["id"], MeetingStatus.failed, None)
    r = admin_client.post(f"/api/v1/meetings/{draft['id']}/reprocess")
    assert r.status_code == 200 and r.json()["status"] == "draft"


def test_audio_upload_states(client, admin_client, draft, db) -> None:
    url = f"/api/v1/meetings/{draft['id']}/audio"
    _set_status(db, draft["id"], MeetingStatus.processing, "extract")
    assert admin_client.post(url, files=_files()).status_code == 409
    _set_status(db, draft["id"], MeetingStatus.processing, "bot_joining")
    assert admin_client.post(url, files=_files()).status_code == 200
    admin_client.post(f"/api/v1/meetings/{draft['id']}/confirm")
    assert admin_client.post(url, files=_files()).status_code == 409
    assert client.post(url, files=_files(), headers=TOKEN).status_code == 401
    assert client.post(url, files=_files(), headers={"X-Bot-Token": "wrong"}).status_code == 401
    assert (
        client.post("/api/v1/meetings/99999/audio", files=_files(), headers=TOKEN).status_code
        == 404
    )


def test_audio_upload_by_non_editor_forbidden(user_client, draft) -> None:
    r = user_client.post(f"/api/v1/meetings/{draft['id']}/audio", files=_files())
    assert r.status_code == 403


def test_stranger_cannot_touch_meeting(user_client, draft) -> None:
    mid = draft["id"]
    assert user_client.get(f"/api/v1/meetings/{mid}").status_code == 403
    assert user_client.post(f"/api/v1/meetings/{mid}/confirm").status_code == 403
    assert user_client.post(f"/api/v1/meetings/{mid}/reprocess").status_code == 403
    assert user_client.put(f"/api/v1/meetings/{mid}/speakers", json=[]).status_code == 403
    assert user_client.delete(f"/api/v1/meetings/{mid}/audio").status_code == 403
    assert user_client.delete(f"/api/v1/meetings/{mid}").status_code == 403
    # Dana is not a participant, but the fake result assigns her one task: she sees only it.
    visible = user_client.get("/api/v1/tasks", params={"meeting_id": mid}).json()
    assert [t["assignee_name"] for t in visible] == ["Дана"]
    tid = next(t["id"] for t in draft["tasks"] if t["assignee_name"] != "Дана")
    assert (
        user_client.patch(f"/api/v1/tasks/{visible[0]['id']}", json={"text": "hack"}).status_code
        == 403
    )
    assert (
        user_client.patch(f"/api/v1/tasks/{tid}", json={"status": "confirmed"}).status_code == 403
    )
    assert user_client.delete(f"/api/v1/tasks/{tid}").status_code == 403
    assert (
        user_client.post("/api/v1/tasks", json={"meeting_id": mid, "text": "x"}).status_code == 403
    )


def test_live_ws_rejects_wrong_source_and_confirmed(admin_client, draft, monkeypatch) -> None:
    monkeypatch.setenv("CELERY_EAGER", "1")
    # upload-source meeting: WS must close with 4409
    with (
        pytest.raises(WebSocketDisconnect) as e,
        admin_client.websocket_connect(f"/api/v1/meetings/{draft['id']}/live") as ws,
    ):
        ws.receive()
    assert e.value.code == 4409

    live = admin_client.post(
        "/api/v1/meetings/live", json={"title": "L", "meeting_date": "2026-09-23"}
    ).json()
    with admin_client.websocket_connect(f"/api/v1/meetings/{live['id']}/live") as ws:
        ws.send_bytes(wav_bytes(0.5))
        ws.send_text('{"event":"stop"}')
        ws.receive_json()
    assert admin_client.get(f"/api/v1/meetings/{live['id']}").json()["status"] == "draft"
    admin_client.post(f"/api/v1/meetings/{live['id']}/confirm")
    with (
        pytest.raises(WebSocketDisconnect) as e,
        admin_client.websocket_connect(f"/api/v1/meetings/{live['id']}/live") as ws,
    ):
        ws.receive()
    assert e.value.code == 4409


def test_live_ws_stranger_closed_4401(user_client, admin_client) -> None:
    live = admin_client.post(
        "/api/v1/meetings/live", json={"title": "L", "meeting_date": "2026-09-23"}
    ).json()
    with (
        pytest.raises(WebSocketDisconnect) as e,
        user_client.websocket_connect(f"/api/v1/meetings/{live['id']}/live") as ws,
    ):
        ws.receive()
    assert e.value.code == 4401


def test_live_ws_disconnect_without_audio_resets_status(admin_client) -> None:
    live = admin_client.post(
        "/api/v1/meetings/live", json={"title": "L", "meeting_date": "2026-09-23"}
    ).json()
    with admin_client.websocket_connect(f"/api/v1/meetings/{live['id']}/live"):
        pass  # client drops immediately
    m = admin_client.get(f"/api/v1/meetings/{live['id']}").json()
    assert m["status"] == "uploaded" and m["audio_path"] is None


def test_bot_meeting_requires_valid_platform_and_url(admin_client) -> None:
    base = {"title": "B", "meeting_date": "2026-09-23"}
    assert (
        admin_client.post(
            "/api/v1/meetings/bot", json={**base, "platform": "meet", "url": "x"}
        ).status_code
        == 422
    )
    assert (
        admin_client.post(
            "/api/v1/meetings/bot", json={**base, "platform": "webex", "url": "https://x.y/1"}
        ).status_code
        == 422
    )
    assert (
        admin_client.post(
            "/api/v1/meetings/bot",
            json={**base, "platform": "meet", "url": "https://x.y/1", "participant_ids": [9999]},
        ).status_code
        == 422
    )


def test_confirm_twice_and_confirm_failed(admin_client, draft, db) -> None:
    assert admin_client.post(f"/api/v1/meetings/{draft['id']}/confirm").status_code == 200
    assert admin_client.post(f"/api/v1/meetings/{draft['id']}/confirm").status_code == 409
    m2 = create_meeting(admin_client).json()
    _set_status(db, m2["id"], MeetingStatus.failed)
    assert admin_client.post(f"/api/v1/meetings/{m2['id']}/confirm").status_code == 409
