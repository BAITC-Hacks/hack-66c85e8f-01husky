from datetime import date, datetime

from pydantic import Field

from app.models.enums import (
    Locale,
    MeetingSource,
    MeetingStatus,
    SpeakerSource,
    TaskStatus,
    Urgency,
)
from app.schemas.common import ORMModel
from app.schemas.participant import ParticipantOut


class SegmentOut(ORMModel):
    idx: int
    start: float
    end: float
    speaker: str
    text: str
    lang: str


class SpeakerMapOut(ORMModel):
    speaker: str
    participant_id: int | None
    source: SpeakerSource
    confidence: float


class SpeakerMapIn(ORMModel):
    speaker: str
    participant_id: int | None


class TaskOut(ORMModel):
    id: int
    meeting_id: int
    assignee_participant_id: int | None
    assignee_name: str
    text: str
    deadline: date | None
    deadline_raw: str | None
    urgency: Urgency
    direction_id: int | None
    direction_name: str | None = None
    quote: str | None
    segment_idx: int | None
    confidence: float
    status: TaskStatus
    sed_ref: str | None
    meeting_title: str | None = None
    meeting_date: date | None = None
    created_at: datetime
    updated_at: datetime
    done_at: datetime | None


class MeetingOut(ORMModel):
    id: int
    title: str
    meeting_date: date
    source: MeetingSource
    platform: str | None
    audio_path: str | None
    duration_sec: float | None
    output_language: Locale
    status: MeetingStatus
    progress_stage: str | None
    progress_pct: float
    error: str | None
    sed_ref: str | None
    created_by: int
    created_at: datetime
    confirmed_at: datetime | None
    tasks_count: int = 0
    participants_count: int = 0


class MeetingDetail(MeetingOut):
    summary: str | None
    language_stats: dict | None
    model_info: dict | None
    participants: list[ParticipantOut]
    segments: list[SegmentOut]
    speaker_map: list[SpeakerMapOut]
    tasks: list[TaskOut]


class MeetingPatch(ORMModel):
    title: str | None = Field(default=None, min_length=1, max_length=500)
    meeting_date: date | None = None
    summary: str | None = None
    output_language: Locale | None = None
    participant_ids: list[int] | None = None


class LiveMeetingIn(ORMModel):
    title: str = Field(min_length=1, max_length=500)
    meeting_date: date
    output_language: Locale = Locale.ru
    participant_ids: list[int] = Field(default_factory=list)


class BotMeetingIn(LiveMeetingIn):
    platform: str = Field(pattern="^(meet|zoom|teams)$")
    url: str = Field(min_length=8, max_length=1000)
