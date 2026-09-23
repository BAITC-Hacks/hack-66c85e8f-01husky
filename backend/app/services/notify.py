"""In-app notifications with transaction-safe deduplication, including meeting events."""

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.models import Notification, Participant, Task
from app.models.enums import NotificationKind

TITLES = {
    NotificationKind.assigned: "Новое поручение",
    NotificationKind.due_soon: "Срок поручения истекает",
    NotificationKind.overdue: "Поручение просрочено",
    NotificationKind.protocol_ready: "Протокол совещания готов",
}


def create(
    db: Session,
    user_id: int,
    kind: NotificationKind,
    body: str,
    *,
    task_id: int | None = None,
    meeting_id: int | None = None,
    title: str | None = None,
) -> Notification | None:
    """Returns the created notification, or None if an identical one already exists."""
    kind = NotificationKind(kind)
    # Hold through commit/rollback so a concurrent request sees the committed result.
    # Meeting-scoped events have task_id=NULL, which the unique constraint cannot dedupe.
    scope = f"task:{task_id}" if task_id is not None else f"meeting:{meeting_id}"
    db.execute(
        text("SELECT pg_advisory_xact_lock(hashtextextended(current_schema() || :key, 0))"),
        {"key": f":notification:{user_id}:{kind.value}:{scope}"},
    )
    exists = db.scalar(
        select(Notification.id).where(
            Notification.user_id == user_id,
            Notification.task_id.is_(task_id)
            if task_id is None
            else Notification.task_id == task_id,
            Notification.kind == kind,
            Notification.meeting_id == meeting_id if task_id is None else True,
        )
    )
    if exists:
        return None
    n = Notification(
        user_id=user_id,
        kind=kind,
        title=title or TITLES[kind],
        body=body,
        task_id=task_id,
        meeting_id=meeting_id,
    )
    db.add(n)
    db.flush()
    return n


def user_id_for_task(db: Session, task: Task) -> int | None:
    if not task.assignee_participant_id:
        return None
    return db.scalar(
        select(Participant.user_id).where(Participant.id == task.assignee_participant_id)
    )


def notify_task(db: Session, task: Task, kind: NotificationKind, body: str) -> Notification | None:
    uid = user_id_for_task(db, task)
    return create(db, uid, kind, body, task_id=task.id, meeting_id=task.meeting_id) if uid else None
