from datetime import datetime

from app.models.enums import NotificationKind
from app.schemas.common import ORMModel


class NotificationOut(ORMModel):
    id: int
    kind: NotificationKind
    title: str
    body: str
    task_id: int | None
    meeting_id: int | None
    read_at: datetime | None
    created_at: datetime


class UnreadCount(ORMModel):
    unread: int
