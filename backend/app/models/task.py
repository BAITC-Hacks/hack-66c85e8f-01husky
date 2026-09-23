from datetime import date, datetime

from sqlalchemy import Date, DateTime, Enum, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models.enums import TaskStatus, Urgency


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(primary_key=True)
    meeting_id: Mapped[int] = mapped_column(
        ForeignKey("meetings.id", ondelete="CASCADE"), index=True
    )
    assignee_participant_id: Mapped[int | None] = mapped_column(
        ForeignKey("participants.id", ondelete="SET NULL"), nullable=True, index=True
    )
    assignee_name: Mapped[str] = mapped_column(String(255), default="")
    text: Mapped[str] = mapped_column(Text)
    deadline: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    deadline_raw: Mapped[str | None] = mapped_column(String(255), nullable=True)
    urgency: Mapped[Urgency] = mapped_column(Enum(Urgency, name="urgency"), default=Urgency.normal)
    direction_id: Mapped[int | None] = mapped_column(
        ForeignKey("directions.id", ondelete="SET NULL"), nullable=True
    )
    quote: Mapped[str | None] = mapped_column(Text, nullable=True)
    segment_idx: Mapped[int | None] = mapped_column(Integer, nullable=True)
    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    status: Mapped[TaskStatus] = mapped_column(
        Enum(TaskStatus, name="task_status"), default=TaskStatus.draft, index=True
    )
    sed_ref: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    done_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    assignee = relationship("Participant", lazy="joined")
    direction = relationship("Direction", lazy="joined")
