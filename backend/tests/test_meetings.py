import io
from pathlib import Path

from tests.helpers import create_meeting


def test_create_upload_and_get(admin_client, monkeypatch) -> None:
    monkeypatch.setenv("CELERY_EAGER", "0")
    called: list[int] = []
    monkeypatch.setattr("app.routers.meetings.enqueue_processing", lambda mid: called.append(mid))
    pids = [p["id"] for p in admin_client.get("/api/v1/participants").json()[:2]]
    r = create_meeting(admin_client, participant_ids=pids)
    assert r.status_code == 201, r.text
    m = r.json()
    assert m["status"] == "uploaded" and m["source"] == "upload"
    assert m["participants_count"] == 2 and m["duration_sec"] and m["duration_sec"] > 0.5
    assert Path(m["audio_path"]).name == "audio.wav" and Path(m["audio_path"]).exists()
    assert called == [m["id"]]
    d = admin_client.get(f"/api/v1/meetings/{m['id']}").json()
    assert len(d["participants"]) == 2 and d["segments"] == [] and d["tasks"] == []


def test_bad_file_rejected(admin_client, monkeypatch) -> None:
    monkeypatch.setattr("app.routers.meetings.enqueue_processing", lambda mid: None)
    r = admin_client.post(
        "/api/v1/meetings",
        data={"title": "x", "meeting_date": "2026-09-23"},
        files={"file": ("doc.txt", io.BytesIO(b"hello"), "text/plain")},
    )
    assert r.status_code == 422
    assert admin_client.get("/api/v1/meetings").json() == []


def test_visibility_and_edit_rights(admin_client, user_client, monkeypatch) -> None:
    monkeypatch.setattr("app.routers.meetings.enqueue_processing", lambda mid: None)
    dana = next(
        p
        for p in admin_client.get("/api/v1/participants").json()
        if p["email"] == "user@example.com"
    )
    hidden = create_meeting(admin_client, title="Секретное").json()
    shared = create_meeting(admin_client, title="Общее", participant_ids=[dana["id"]]).json()
    own = create_meeting(user_client, title="Моё").json()

    titles = {m["title"] for m in user_client.get("/api/v1/meetings").json()}
    assert titles == {"Общее", "Моё"}
    assert user_client.get(f"/api/v1/meetings/{hidden['id']}").status_code == 403
    assert user_client.get(f"/api/v1/meetings/{shared['id']}").status_code == 200
    assert (
        user_client.patch(f"/api/v1/meetings/{shared['id']}", json={"title": "x"}).status_code
        == 403
    )
    assert (
        user_client.patch(f"/api/v1/meetings/{own['id']}", json={"title": "Моё 2"}).json()["title"]
        == "Моё 2"
    )
    assert len(admin_client.get("/api/v1/meetings").json()) == 3
    assert admin_client.get("/api/v1/meetings?status=uploaded").json()
    assert admin_client.get("/api/v1/meetings?status=confirmed").json() == []


def test_delete_audio_and_meeting(admin_client, monkeypatch) -> None:
    monkeypatch.setattr("app.routers.meetings.enqueue_processing", lambda mid: None)
    m = create_meeting(admin_client).json()
    path = Path(m["audio_path"])
    assert admin_client.delete(f"/api/v1/meetings/{m['id']}/audio").status_code == 204
    assert not path.exists()
    assert admin_client.get(f"/api/v1/meetings/{m['id']}").json()["audio_path"] is None
    assert admin_client.post(f"/api/v1/meetings/{m['id']}/reprocess").status_code == 409
    assert admin_client.delete(f"/api/v1/meetings/{m['id']}").status_code == 204
    assert admin_client.get(f"/api/v1/meetings/{m['id']}").status_code == 404
