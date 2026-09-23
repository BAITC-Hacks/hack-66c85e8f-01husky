"""Stage 1: real local STT. Later stages remain explicitly unavailable."""

from datetime import date

from pipeline.models import MeetingResult, OutputLanguage, Participant, ProgressCallback, Segment
from pipeline.stt.local_whisper import transcribe


def process(
    audio_path: str,
    meeting_date: date,
    participants: list[Participant],
    directions: list[str],
    output_language: OutputLanguage = "ru",
    progress: ProgressCallback | None = None,
) -> MeetingResult:
    transcript = transcribe(audio_path, progress=progress)
    if progress:
        progress("privacy", 0.95)
    segments = [
        Segment(start=s.start, end=s.end, text=s.text, speaker="SPEAKER_UNKNOWN", lang="other")
        for s in transcript.segments
    ]
    result = MeetingResult(
        segments=segments,
        speaker_map=[],
        tasks=[],
        summary="",
        language_stats={"other": 1.0} if segments else {},
        duration_sec=transcript.duration,
        model_info={
            "stt": f"faster-whisper {transcript.model}",
            "processing_mode": "local_offline_stt_only",
            "detected_language": transcript.detected_language,
            "language_probability": str(transcript.language_probability),
            "segment_language": "unavailable",
            "diarize": "unavailable",
            "voiceprint": "unavailable",
            "extract": "unavailable",
            "summary": "unavailable",
            "privacy": "phone_iin_patterns_v1",
        },
    )
    if progress:
        progress("done", 1.0)
    return result


def enroll_voice(audio_path: str) -> list[float]:
    raise NotImplementedError("Real voiceprint not implemented yet. Set PIPELINE_FAKE=1.")
