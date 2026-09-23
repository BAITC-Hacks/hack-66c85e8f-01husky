"""Public API. Real implementation lands in stt/, diarize.py, voiceprint.py, extract.py, summary.py.

PIPELINE_FAKE=1 routes everything to pipeline.fake so backend works without ML models.
"""

from datetime import date

from pipeline.models import (
    MeetingResult,
    OutputLanguage,
    Participant,
    ProgressCallback,
    Segment,
    SpeakerMapping,
    Task,
)

__all__ = [
    "MeetingResult",
    "Participant",
    "Segment",
    "SpeakerMapping",
    "Task",
    "enroll_voice",
    "is_fake",
    "process",
]


def is_fake() -> bool:
    from pipeline.settings import PipelineSettings

    return PipelineSettings().pipeline_fake


def process(
    audio_path: str,
    meeting_date: date,
    participants: list[Participant],
    directions: list[str],
    output_language: OutputLanguage = "ru",
    progress: ProgressCallback | None = None,
) -> MeetingResult:
    if is_fake():
        from pipeline import fake

        return fake.process(
            audio_path, meeting_date, participants, directions, output_language, progress
        )
    from pipeline import real

    return real.process(
        audio_path, meeting_date, participants, directions, output_language, progress
    )


def enroll_voice(audio_path: str) -> list[float]:
    if is_fake():
        from pipeline import fake

        return fake.enroll_voice(audio_path)
    from pipeline import real

    return real.enroll_voice(audio_path)
