from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select, update

from app.deps import DbDep, current_user
from app.models import Notification, User
from app.schemas.notification import NotificationOut, UnreadCount

router = APIRouter(prefix="/notifications", tags=["notifications"])

UserDep = Annotated[User, Depends(current_user)]


@router.get("", response_model=list[NotificationOut])
def list_notifications(
    db: DbDep, user: UserDep, unread: bool = False, limit: int = 50
) -> list[Notification]:
    q = select(Notification).where(Notification.user_id == user.id)
    if unread:
        q = q.where(Notification.read_at.is_(None))
    q = q.order_by(Notification.created_at.desc(), Notification.id.desc()).limit(min(limit, 200))
    return list(db.scalars(q))


@router.get("/unread-count", response_model=UnreadCount)
def unread_count(db: DbDep, user: UserDep) -> UnreadCount:
    n = db.scalar(
        select(func.count())
        .select_from(Notification)
        .where(Notification.user_id == user.id, Notification.read_at.is_(None))
    )
    return UnreadCount(unread=n or 0)


@router.post("/{notification_id}/read", response_model=NotificationOut)
def mark_read(notification_id: int, db: DbDep, user: UserDep) -> Notification:
    n = db.get(Notification, notification_id)
    if not n or n.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Notification not found")
    if n.read_at is None:
        n.read_at = datetime.now(UTC)
        db.commit()
        db.refresh(n)
    return n


@router.post("/read-all", response_model=UnreadCount)
def mark_all_read(db: DbDep, user: UserDep) -> UnreadCount:
    db.execute(
        update(Notification)
        .where(Notification.user_id == user.id, Notification.read_at.is_(None))
        .values(read_at=datetime.now(UTC))
    )
    db.commit()
    return UnreadCount(unread=0)
