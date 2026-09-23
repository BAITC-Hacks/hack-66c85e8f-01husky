import pytest

from tests.helpers import create_meeting


@pytest.fixture
def processed(admin_client, monkeypatch):
    monkeypatch.setenv("CELERY_EAGER", "1")
    pids = [p["id"] for p in admin_client.get("/api/v1/participants").json()]
    m = create_meeting(admin_client, participant_ids=pids).json()
    return admin_client.get(f"/api/v1/meetings/{m['id']}").json()


def test_list_filters_and_stats(admin_client, processed) -> None:
    tasks = admin_client.get("/api/v1/tasks").json()
    assert len(tasks) == 4 and all(t["meeting_title"] == "Планёрка" for t in tasks)
    assert [t["deadline"] for t in tasks] == sorted(t["deadline"] for t in tasks)
    fin = admin_client.get("/api/v1/tasks", params={"urgency": "high"}).json()
    assert len(fin) == 1 and fin[0]["deadline_raw"] == "до пятницы"
    aibek = next(p for p in processed["participants"] if p["name"].startswith("Айбек"))
    assert len(admin_client.get("/api/v1/tasks", params={"assignee_id": aibek["id"]}).json()) == 3
    assert admin_client.get("/api/v1/tasks", params={"include_draft": "false"}).json() == []
    s = admin_client.get("/api/v1/tasks/stats").json()
    assert s["draft"] == 4 and s["total"] == 4 and s["done"] == 0


def test_status_transitions(admin_client, processed) -> None:
    t = processed["tasks"][0]
    url = f"/api/v1/tasks/{t['id']}"
    assert admin_client.patch(url, json={"status": "done"}).status_code == 409
    assert admin_client.patch(url, json={"status": "confirmed"}).json()["status"] == "confirmed"
    assert admin_client.patch(url, json={"status": "in_progress"}).json()["status"] == "in_progress"
    r = admin_client.patch(url, json={"status": "done"}).json()
    assert r["status"] == "done" and r["done_at"]
    assert admin_client.patch(url, json={"status": "draft"}).status_code == 409
    assert admin_client.get("/api/v1/tasks/stats").json()["done"] == 1


def test_assignee_can_change_status_but_not_text(user_client, admin_client, processed) -> None:
    dana = next(p for p in processed["participants"] if p["email"] == "user@example.com")
    mine = user_client.get("/api/v1/tasks", params={"mine": "true"}).json()
    assert len(mine) == 1 and mine[0]["assignee_participant_id"] == dana["id"]
    url = f"/api/v1/tasks/{mine[0]['id']}"
    admin_client.patch(url, json={"status": "confirmed"})
    assert user_client.patch(url, json={"text": "hack"}).status_code == 403
    assert user_client.patch(url, json={"status": "in_progress"}).status_code == 200
    assert user_client.delete(url).status_code == 403


def test_create_patch_delete(admin_client, processed) -> None:
    dirs = admin_client.get("/api/v1/directions").json()
    p = processed["participants"][0]
    r = admin_client.post(
        "/api/v1/tasks",
        json={
            "meeting_id": processed["id"],
            "text": "Ручное поручение",
            "assignee_participant_id": p["id"],
            "direction_id": dirs[0]["id"],
        },
    )
    assert (
        r.status_code == 201
        and r.json()["assignee_name"] == p["name"]
        and r.json()["status"] == "draft"
    )
    tid = r.json()["id"]
    r = admin_client.patch(
        f"/api/v1/tasks/{tid}", json={"deadline": "2026-10-01", "urgency": "critical"}
    )
    assert r.json()["deadline"] == "2026-10-01" and r.json()["urgency"] == "critical"
    assert admin_client.delete(f"/api/v1/tasks/{tid}").status_code == 204
    assert (
        admin_client.get("/api/v1/tasks", params={"meeting_id": processed["id"]}).json().__len__()
        == 4
    )
