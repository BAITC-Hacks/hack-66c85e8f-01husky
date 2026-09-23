from datetime import datetime
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import select

from app.models import Notification, Task
from app.models.enums import TaskStatus
from app.tasks.reminders import run_check
from tests.helpers import create_meeting

ALMATY = ZoneInfo("Asia/Almaty")


@pytest.fixture
def confirmed(admin_client, monkeypatch):
    monkeypatch.setenv("CELERY_EAGER", "1")
    pids = [p["id"] for p in admin_client.get("/api/v1/participants").json()]
    m = create_meeting(admin_client, meeting_date="2026-09-23", participant_ids=pids).json()
    return admin_client.post(f"/api/v1/meetings/{m['id']}/confirm").json()


def test_due_soon_then_overdue_once(confirmed, db) -> None:
    # Dana's task: deadline = end of next week (2026-10-04). Fake meeting date 2026-09-23.
    dana_task = next(
        t for t in confirmed["tasks"] if t["deadline_raw"] == "до конца следующей недели"
    )
    before = len(list(db.scalars(select(Notification))))

    c = run_check(db, now=datetime(2026, 10, 3, 9, 0, tzinfo=ALMATY))
    assert c == {"due_soon": 1, "overdue": 0}
    c = run_check(db, now=datetime(2026, 10, 3, 10, 0, tzinfo=ALMATY))
    assert c == {"due_soon": 0, "overdue": 0}, "due_soon must not repeat"

    c = run_check(db, now=datetime(2026, 10, 6, 9, 0, tzinfo=ALMATY))
    assert c["overdue"] == 1
    db.expire_all()
    t = db.get(Task, dana_task["id"])
    assert t.status == TaskStatus.overdue
    # Aibek's tasks are overdue too but he has no user account → no user notification, status still flips
    assert all(
        x.status == TaskStatus.overdue for x in db.scalars(select(Task).where(Task.id != t.id))
    )
    c = run_check(db, now=datetime(2026, 10, 7, 9, 0, tzinfo=ALMATY))
    assert c == {"due_soon": 0, "overdue": 0}, "overdue notification must not repeat"

    kinds = [n.kind.value for n in db.scalars(select(Notification)) if n.task_id == t.id]
    assert sorted(kinds) == [
        "assigned",
        "due_soon",
        "overdue",
        "overdue",
    ]  # assignee + creator(admin)
    assert len(list(db.scalars(select(Notification)))) > before


def test_done_tasks_are_ignored(confirmed, db, admin_client) -> None:
    for t in confirmed["tasks"]:
        admin_client.patch(f"/api/v1/tasks/{t['id']}", json={"status": "done"})
    c = run_check(db, now=datetime(2027, 1, 1, tzinfo=ALMATY))
    assert c == {"due_soon": 0, "overdue": 0}
    db.expire_all()
    assert all(t.status == TaskStatus.done for t in db.scalars(select(Task)))
