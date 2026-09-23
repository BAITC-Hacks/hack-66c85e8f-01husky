"""Local STT and acoustic speaker diarization; identities/LLM stages remain unavailable."""

from datetime import date

from pipeline.diarization import diarize
from pipeline.models import MeetingResult, OutputLanguage, Participant, ProgressCallback
from pipeline.settings import PipelineSettings
from pipeline.speaker_alignment import align_speakers
from pipeline.stt.local_whisper import transcribe


def process(
    audio_path: str,
    meeting_date: date,
    participants: list[Participant],
    directions: list[str],
    output_language: OutputLanguage = "ru",
    progress: ProgressCallback | None = None,
) -> MeetingResult:
    settings = PipelineSettings()
    transcript = transcribe(
        audio_path,
        settings,
        progress=(lambda stage, pct: progress(stage, pct * 0.75)) if progress else None,
    )
    if progress:
        progress("diarize", 0.70)
    turns = (
        diarize(
            audio_path,
            settings,
            progress=(lambda pct: progress("diarize", 0.70 + 0.24 * pct)) if progress else None,
        )
        if transcript.segments
        else []
    )
    aligned = align_speakers(transcript.segments, turns)
    if progress:
        progress("privacy", 0.95)
    segments = aligned.segments
    result = MeetingResult(
        segments=segments,
        speaker_map=aligned.speaker_map,
        tasks=[],
        summary="",
        language_stats={"other": 1.0} if segments else {},
        duration_sec=transcript.duration,
        model_info={
            "stt": f"faster-whisper {transcript.model}",
            "processing_mode": "local_offline_stt_diarization",
            "detected_language": transcript.detected_language,
            "language_probability": str(transcript.language_probability),
            "segment_language": "unavailable",
            "diarize": "sherpa-onnx pyannote-segmentation-3.0 + NeMo TitaNet-large",
            "speaker_count": str(len(aligned.speaker_map)),
            "speaker_labels": "meeting_local_first_occurrence",
            "diarization_threshold": str(settings.diarization_threshold),
            "diarization_num_speakers": str(settings.diarization_num_speakers or "auto"),
            "alignment_nearest_words": str(aligned.nearest_words),
            "alignment_distant_words": str(aligned.distant_words),
            "alignment_overlapping_words": str(aligned.overlapping_words),
            "alignment_coarse_segments": str(aligned.coarse_segments),
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
