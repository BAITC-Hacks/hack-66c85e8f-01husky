from concurrent.futures import ThreadPoolExecutor, TimeoutError
from datetime import date
from threading import Event

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Meeting, Notification, Task
from app.models.enums import MeetingSource, NotificationKind
from app.services import notify


@pytest.mark.parametrize("kind", [NotificationKind.assigned, NotificationKind.protocol_ready])
def test_create_serializes_duplicate_notifications(db, seed, _schema, kind):
    meeting = Meeting(
        title="Concurrent notifications",
        meeting_date=date(2026, 9, 23),
        source=MeetingSource.upload,
        created_by=seed["admin"].id,
    )
    db.add(meeting)
    db.flush()
    task = Task(meeting_id=meeting.id, text="Check race")
    db.add(task)
    db.commit()
    uid, mid = seed["user"].id, meeting.id
    tid = task.id if kind == NotificationKind.assigned else None
    started = Event()

    def competing_request():
        with Session(_schema) as other:
            started.set()
            created = notify.create(other, uid, kind, "Same event", task_id=tid, meeting_id=mid)
            other.commit()
            return created is not None

    with Session(_schema) as first:
        assert notify.create(first, uid, kind, "Same event", task_id=tid, meeting_id=mid)
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(competing_request)
            assert started.wait(timeout=5)
            try:
                future.result(timeout=0.25)
                waited = False
            except TimeoutError:
                waited = True
            finally:
                first.commit()
            created_again = future.result(timeout=5)
    assert waited, "A duplicate notification must wait for the first transaction"
    assert created_again is False
    assert db.scalar(select(func.count()).select_from(Notification)) == 1


def test_protocol_ready_is_scoped_to_meeting_and_rollback_releases_lock(db, seed):
    meetings = [
        Meeting(
            title=f"Meeting {i}",
            meeting_date=date(2026, 9, 23),
            source=MeetingSource.upload,
            created_by=seed["admin"].id,
        )
        for i in range(2)
    ]
    db.add_all(meetings)
    db.commit()
    uid = seed["user"].id
    for meeting in meetings:
        assert notify.create(
            db, uid, NotificationKind.protocol_ready, "Ready", meeting_id=meeting.id
        )
    db.commit()
    assert db.scalar(select(func.count()).select_from(Notification)) == 2
    assert notify.create(db, uid, NotificationKind.assigned, "Temporary")
    db.rollback()
    assert notify.create(db, uid, NotificationKind.assigned, "Retry")
    db.commit()
