import pytest
from sqlalchemy import select

from app.models import Notification
from tests.helpers import create_meeting


@pytest.fixture
def draft(admin_client, monkeypatch):
    monkeypatch.setenv("CELERY_EAGER", "1")
    pids = [p["id"] for p in admin_client.get("/api/v1/participants").json()]
    m = create_meeting(admin_client, participant_ids=pids).json()
    return admin_client.get(f"/api/v1/meetings/{m['id']}").json()


def test_manual_speaker_map_recalcs_assignees(admin_client, draft) -> None:
    serik = next(p for p in draft["participants"] if p["name"].startswith("Серик"))
    dana = next(p for p in draft["participants"] if p["name"].startswith("Дана"))
    r = admin_client.put(
        f"/api/v1/meetings/{draft['id']}/speakers",
        json=[
            {"speaker": "SPEAKER_00", "participant_id": serik["id"]},
            {"speaker": "SPEAKER_02", "participant_id": dana["id"]},
        ],
    )
    assert r.status_code == 200, r.text
    sm = {x["speaker"]: x for x in r.json()["speaker_map"]}
    assert (
        sm["SPEAKER_00"]["participant_id"] == serik["id"] and sm["SPEAKER_00"]["source"] == "manual"
    )
    assert (
        sm["SPEAKER_02"]["participant_id"] == dana["id"] and sm["SPEAKER_02"]["confidence"] == 1.0
    )
    assert sm["SPEAKER_01"]["source"] == "voiceprint"
    assert all(t["assignee_participant_id"] for t in r.json()["tasks"])
    assert (
        admin_client.put(
            f"/api/v1/meetings/{draft['id']}/speakers",
            json=[{"speaker": "SPEAKER_00", "participant_id": 9999}],
        ).status_code
        == 422
    )


def test_confirm_flow(admin_client, user_client, draft, db) -> None:
    mid = draft["id"]
    assert user_client.post(f"/api/v1/meetings/{mid}/confirm").status_code == 403
    r = admin_client.post(f"/api/v1/meetings/{mid}/confirm")
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["status"] == "confirmed" and d["confirmed_at"]
    assert all(t["status"] == "confirmed" for t in d["tasks"])
    assert admin_client.post(f"/api/v1/meetings/{mid}/confirm").status_code == 409
    assert admin_client.post(f"/api/v1/meetings/{mid}/reprocess").status_code == 409

    # Dana (user@example.com) has one task in the fake result → assigned + protocol_ready
    ns = list(db.scalars(select(Notification).order_by(Notification.id)))
    kinds = sorted(n.kind.value for n in ns)
    assert kinds == ["assigned", "protocol_ready"]
    assert all(n.user_id == user_client.get("/api/v1/auth/me").json()["id"] for n in ns)
    # confirm is idempotent w.r.t. notifications even if called through other paths
    admin_client.patch(f"/api/v1/tasks/{d['tasks'][0]['id']}", json={"text": "x"})
    assert len(list(db.scalars(select(Notification)))) == 2


def test_manual_mapping_resolves_self_assignment_and_can_unassign(admin_client, draft):
    task = draft["tasks"][0]
    admin_client.patch(
        f"/api/v1/tasks/{task['id']}",
        json={
            "assignee_name": "SPEAKER_00",
            "assignee_participant_id": None,
        },
    ).raise_for_status()
    pid = draft["participants"][0]["id"]
    for target in (pid, None):
        result = admin_client.put(
            f"/api/v1/meetings/{draft['id']}/speakers",
            json=[{"speaker": "SPEAKER_00", "participant_id": target}],
        )
        result.raise_for_status()
        assert (
            next(t for t in result.json()["tasks"] if t["id"] == task["id"])[
                "assignee_participant_id"
            ]
            == target
        )
