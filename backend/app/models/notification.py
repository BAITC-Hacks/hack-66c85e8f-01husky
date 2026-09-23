from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models.enums import NotificationKind


class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = (UniqueConstraint("user_id", "task_id", "kind", name="uq_notification_once"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    task_id: Mapped[int | None] = mapped_column(
        ForeignKey("tasks.id", ondelete="CASCADE"), nullable=True
    )
    meeting_id: Mapped[int | None] = mapped_column(
        ForeignKey("meetings.id", ondelete="CASCADE"), nullable=True
    )
    kind: Mapped[NotificationKind] = mapped_column(Enum(NotificationKind, name="notification_kind"))
    title: Mapped[str] = mapped_column(String(500))
    body: Mapped[str] = mapped_column(Text, default="")
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
