"""Celery beat task: due_soon / overdue notifications and automatic overdue status."""

import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import SessionLocal
from app.models import Meeting, Task
from app.models.enums import NotificationKind, TaskStatus
from app.services import notify
from app.tasks.celery_app import celery_app

log = logging.getLogger(__name__)
ALMATY = ZoneInfo("Asia/Almaty")
ACTIVE = (TaskStatus.confirmed, TaskStatus.in_progress)


def run_check(db: Session, now: datetime | None = None) -> dict[str, int]:
    """Pure core, testable with a fixed `now`. Returns counters."""
    now = now or datetime.now(tz=ALMATY)
    today = now.date()
    horizon = today + timedelta(hours=get_settings().due_soon_hours)
    counters = {"due_soon": 0, "overdue": 0}

    q = (
        select(Task)
        .join(Meeting, Meeting.id == Task.meeting_id)
        .where(Task.deadline.is_not(None), Task.status.in_((*ACTIVE, TaskStatus.overdue)))
    )
    for t in db.scalars(q).unique():
        title = t.meeting.title
        if t.deadline < today:
            if t.status in ACTIVE:
                t.status = TaskStatus.overdue
            if notify.notify_task(
                db,
                t,
                NotificationKind.overdue,
                f"«{title}»: {t.text}. Срок был {t.deadline.isoformat()}",
            ):
                counters["overdue"] += 1
            _notify_creator(db, t, NotificationKind.overdue, title)
        elif t.status in ACTIVE and t.deadline <= horizon:
            if notify.notify_task(
                db,
                t,
                NotificationKind.due_soon,
                f"«{title}»: {t.text}. Срок {t.deadline.isoformat()}",
            ):
                counters["due_soon"] += 1
    db.commit()
    return counters


def _notify_creator(db: Session, t: Task, kind: NotificationKind, title: str) -> None:
    """The meeting creator (secretary / manager) also learns about overdue tasks."""
    creator_id = t.meeting.created_by
    if creator_id and creator_id != notify.user_id_for_task(db, t):
        notify.create(
            db,
            creator_id,
            kind,
            f"«{title}»: {t.text} ({t.assignee_name or 'без ответственного'}). Срок был {t.deadline.isoformat()}",
            task_id=t.id,
            meeting_id=t.meeting_id,
            title="Поручение подчинённого просрочено",
        )


@celery_app.task(name="app.tasks.reminders.check_deadlines")
def check_deadlines() -> dict[str, int]:
    with SessionLocal() as db:
        counters = run_check(db)
    log.info("check_deadlines: %s", counters)
    return counters
