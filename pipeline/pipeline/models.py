"""Contract between pipeline and backend. Spec section 5. Do not change without a `spec:` commit."""

from collections.abc import Callable
from datetime import date
from typing import Literal, Protocol

from pydantic import BaseModel, Field

Urgency = Literal["low", "normal", "high", "critical"]
SpeakerSource = Literal["voiceprint", "llm", "manual", "none"]
Lang = Literal["ru", "kk", "mixed", "other"]
OutputLanguage = Literal["ru", "kk"]

ProgressCallback = Callable[[str, float], None]


class Participant(BaseModel):
    id: int
    name: str
    role: str | None = None
    voice_embedding: list[float] | None = None


class Segment(BaseModel):
    start: float
    end: float
    speaker: str
    text: str
    lang: Lang


class SpeakerMapping(BaseModel):
    speaker: str
    participant_id: int | None
    source: SpeakerSource
    confidence: float = Field(ge=0.0, le=1.0)
    participant_name: str | None = Field(default=None, max_length=255)


class Task(BaseModel):
    text: str
    assignee_participant_id: int | None
    assignee_name: str
    deadline: date | None
    deadline_raw: str | None
    urgency: Urgency
    direction: str
    quote: str
    segment_index: int
    confidence: float = Field(ge=0.0, le=1.0)


class MeetingResult(BaseModel):
    segments: list[Segment]
    speaker_map: list[SpeakerMapping]
    tasks: list[Task]
    summary: str
    language_stats: dict[str, float]
    duration_sec: float
    model_info: dict[str, str]


class ProcessFn(Protocol):
    def __call__(
        self,
        audio_path: str,
        meeting_date: date,
        participants: list[Participant],
        directions: list[str],
        output_language: OutputLanguage = "ru",
        progress: ProgressCallback | None = None,
    ) -> MeetingResult: ...
