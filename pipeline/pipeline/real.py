"""Real pipeline entry point. Owner: Ардак. Wire stt/, diarize, voiceprint, extract, summary here."""

from datetime import date

from pipeline.models import MeetingResult, OutputLanguage, Participant, ProgressCallback


def process(
    audio_path: str,
    meeting_date: date,
    participants: list[Participant],
    directions: list[str],
    output_language: OutputLanguage = "ru",
    progress: ProgressCallback | None = None,
) -> MeetingResult:
    raise NotImplementedError("Real pipeline not implemented yet. Set PIPELINE_FAKE=1.")


def enroll_voice(audio_path: str) -> list[float]:
    raise NotImplementedError("Real voiceprint not implemented yet. Set PIPELINE_FAKE=1.")
