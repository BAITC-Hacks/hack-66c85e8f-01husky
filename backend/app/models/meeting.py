from datetime import date, datetime

from sqlalchemy import JSON, Date, DateTime, Enum, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base
from app.models.enums import Locale, MeetingSource, MeetingStatus, SpeakerSource


class Meeting(Base):
    __tablename__ = "meetings"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(500))
    meeting_date: Mapped[date] = mapped_column(Date)
    source: Mapped[MeetingSource] = mapped_column(Enum(MeetingSource, name="meeting_source"))
    platform: Mapped[str | None] = mapped_column(String(50), nullable=True)
    bot_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    audio_path: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    duration_sec: Mapped[float | None] = mapped_column(Float, nullable=True)
    output_language: Mapped[Locale] = mapped_column(Enum(Locale, name="locale"), default=Locale.ru)
    status: Mapped[MeetingStatus] = mapped_column(
        Enum(MeetingStatus, name="meeting_status"), default=MeetingStatus.uploaded, index=True
    )
    progress_stage: Mapped[str | None] = mapped_column(String(50), nullable=True)
    progress_pct: Mapped[float] = mapped_column(Float, default=0.0)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    language_stats: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    model_info: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    sed_ref: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    participants = relationship(
        "Participant", secondary="meeting_participants", lazy="selectin", order_by="Participant.id"
    )
    segments = relationship(
        "Segment", cascade="all, delete-orphan", lazy="selectin", order_by="Segment.idx"
    )
    speaker_map = relationship(
        "SpeakerMap", cascade="all, delete-orphan", lazy="selectin", order_by="SpeakerMap.speaker"
    )
    tasks = relationship("Task", cascade="all, delete-orphan", lazy="selectin", order_by="Task.id")


class MeetingParticipant(Base):
    __tablename__ = "meeting_participants"

    meeting_id: Mapped[int] = mapped_column(
        ForeignKey("meetings.id", ondelete="CASCADE"), primary_key=True
    )
    participant_id: Mapped[int] = mapped_column(
        ForeignKey("participants.id", ondelete="CASCADE"), primary_key=True
    )


class Segment(Base):
    __tablename__ = "segments"

    id: Mapped[int] = mapped_column(primary_key=True)
    meeting_id: Mapped[int] = mapped_column(
        ForeignKey("meetings.id", ondelete="CASCADE"), index=True
    )
    idx: Mapped[int] = mapped_column(Integer)
    start: Mapped[float] = mapped_column(Float)
    end: Mapped[float] = mapped_column(Float)
    speaker: Mapped[str] = mapped_column(String(50))
    text: Mapped[str] = mapped_column(Text)
    lang: Mapped[str] = mapped_column(String(10))


class SpeakerMap(Base):
    __tablename__ = "speaker_map"

    id: Mapped[int] = mapped_column(primary_key=True)
    meeting_id: Mapped[int] = mapped_column(
        ForeignKey("meetings.id", ondelete="CASCADE"), index=True
    )
    speaker: Mapped[str] = mapped_column(String(50))
    participant_id: Mapped[int | None] = mapped_column(
        ForeignKey("participants.id", ondelete="SET NULL"), nullable=True
    )
    source: Mapped[SpeakerSource] = mapped_column(Enum(SpeakerSource, name="speaker_source"))
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
