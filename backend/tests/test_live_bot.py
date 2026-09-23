import io
from pathlib import Path

import pytest
from starlette.websockets import WebSocketDisconnect

from app.services.bot_tokens import create_bot_upload_token
from tests.helpers import wav_bytes


def test_live_ws_records_and_processes(admin_client, monkeypatch) -> None:
    monkeypatch.setenv("CELERY_EAGER", "1")
    m = admin_client.post(
        "/api/v1/meetings/live", json={"title": "Live", "meeting_date": "2026-09-23"}
    ).json()
    assert m["source"] == "live" and m["status"] == "uploaded"
    data = wav_bytes(1.0)
    with admin_client.websocket_connect(f"/api/v1/meetings/{m['id']}/live") as ws:
        for i in range(0, len(data), 8000):
            ws.send_bytes(data[i : i + 8000])
        ws.send_text('{"event":"stop"}')
        assert ws.receive_json()["bytes"] == len(data)
    d = admin_client.get(f"/api/v1/meetings/{m['id']}").json()
    assert d["status"] == "draft", d.get("error")
    assert Path(d["audio_path"]).name == "audio.wav" and len(d["tasks"]) == 4


def test_live_ws_rejects_anonymous_and_upload_meetings(
    client, admin_client, seed, monkeypatch
) -> None:
    m = admin_client.post(
        "/api/v1/meetings/live", json={"title": "Live", "meeting_date": "2026-09-23"}
    ).json()
    with (
        pytest.raises(WebSocketDisconnect),
        client.websocket_connect(f"/api/v1/meetings/{m['id']}/live") as ws,
    ):
        ws.receive()


def test_bot_meeting_dispatches_task(admin_client, monkeypatch) -> None:
    calls = []
    monkeypatch.setattr("app.tasks.run_bot.run_bot.delay", lambda *a: calls.append(a))
    r = admin_client.post(
        "/api/v1/meetings/bot",
        json={
            "title": "Bot",
            "meeting_date": "2026-09-23",
            "platform": "meet",
            "url": "https://meet.google.com/abc-defg-hij",
        },
    )
    assert r.status_code == 201, r.text
    m = r.json()
    assert m["source"] == "bot" and m["platform"] == "meet" and m["status"] == "processing"
    assert calls == [(m["id"],)]
    assert (
        admin_client.post(
            "/api/v1/meetings/bot",
            json={
                "title": "x",
                "meeting_date": "2026-09-23",
                "platform": "skype",
                "url": "https://x",
            },
        ).status_code
        == 422
    )


def test_bot_audio_callback_with_token(client, admin_client, monkeypatch) -> None:
    monkeypatch.setenv("CELERY_EAGER", "1")
    monkeypatch.setattr("app.tasks.run_bot.run_bot.delay", lambda *a: None)
    m = admin_client.post(
        "/api/v1/meetings/bot",
        json={
            "title": "Bot",
            "meeting_date": "2026-09-23",
            "platform": "zoom",
            "url": "https://zoom.us/j/12345678901",
        },
    ).json()
    files = {"file": ("rec.wav", io.BytesIO(wav_bytes()), "audio/wav")}
    assert client.post(f"/api/v1/meetings/{m['id']}/audio", files=files).status_code == 401
    r = client.post(
        f"/api/v1/meetings/{m['id']}/audio",
        files=files,
        headers={"X-Bot-Token": create_bot_upload_token(m["id"])},
    )
    assert r.status_code == 200, r.text
    d = admin_client.get(f"/api/v1/meetings/{m['id']}").json()
    assert d["status"] == "draft" and len(d["tasks"]) == 4


def test_run_bot_runtime_start_failure_marks_failed(admin_client, monkeypatch) -> None:
    from app.tasks import run_bot as rb

    def unavailable(*args, **kwargs):
        raise FileNotFoundError()

    monkeypatch.setattr(rb.subprocess, "Popen", unavailable)
    monkeypatch.setattr("app.tasks.run_bot.run_bot.delay", lambda *a: None)
    m = admin_client.post(
        "/api/v1/meetings/bot",
        json={
            "title": "Bot",
            "meeting_date": "2026-09-23",
            "platform": "teams",
            "url": "https://teams.microsoft.com/l/meetup-join/19%3ameeting_test%40thread.v2/0?context=%7B%7D",
        },
    ).json()
    rb.run_bot.apply(args=(m["id"],))
    d = admin_client.get(f"/api/v1/meetings/{m['id']}").json()
    assert d["status"] == "failed" and "runtime" in d["error"]
