from tests.helpers import create_meeting


def test_notifications_flow(admin_client, user_client, monkeypatch) -> None:
    monkeypatch.setenv("CELERY_EAGER", "1")
    pids = [p["id"] for p in admin_client.get("/api/v1/participants").json()]
    m = create_meeting(admin_client, participant_ids=pids).json()
    assert user_client.get("/api/v1/notifications/unread-count").json()["unread"] == 0
    admin_client.post(f"/api/v1/meetings/{m['id']}/confirm")

    assert user_client.get("/api/v1/notifications/unread-count").json()["unread"] == 2
    items = user_client.get("/api/v1/notifications", params={"unread": "true"}).json()
    assert {i["kind"] for i in items} == {"assigned", "protocol_ready"}
    assert all(i["meeting_id"] == m["id"] for i in items)
    assert admin_client.get("/api/v1/notifications").json() == []

    first = items[0]["id"]
    assert admin_client.post(f"/api/v1/notifications/{first}/read").status_code == 404
    assert user_client.post(f"/api/v1/notifications/{first}/read").json()["read_at"]
    assert user_client.get("/api/v1/notifications/unread-count").json()["unread"] == 1
    assert user_client.post("/api/v1/notifications/read-all").json()["unread"] == 0
    assert user_client.get("/api/v1/notifications", params={"unread": "true"}).json() == []
    assert len(user_client.get("/api/v1/notifications").json()) == 2
