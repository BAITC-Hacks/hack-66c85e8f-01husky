"""Offline STT/diarization followed by a self-hosted LLM; no external processing APIs."""

from datetime import date

from pipeline.diarization import diarize
from pipeline.extract import extract
from pipeline.identity import identify_speakers
from pipeline.llm import OllamaLLM
from pipeline.models import MeetingResult, OutputLanguage, Participant, ProgressCallback
from pipeline.settings import PipelineSettings
from pipeline.speaker_alignment import align_speakers, join_continuations
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
        progress=(lambda stage, pct: progress(stage, pct * 0.55)) if progress else None,
    )
    if progress:
        progress("diarize", 0.50)
    turns = (
        diarize(
            audio_path,
            settings,
            progress=(lambda pct: progress("diarize", 0.50 + 0.22 * pct)) if progress else None,
        )
        if transcript.segments
        else []
    )
    aligned = align_speakers(
        transcript.segments,
        turns,
        boundary_grace=settings.diarization_boundary_grace_sec,
    )
    if progress:
        progress("extract", 0.74)
    segments = join_continuations(aligned.segments)
    llm = OllamaLLM(settings) if segments else None
    speaker_map, identity_hints = identify_speakers(
        segments,
        aligned.speaker_map,
        participants,
        llm,
    )
    extracted = extract(
        segments,
        meeting_date,
        participants,
        directions,
        output_language,
        settings,
        progress,
        llm=llm,
    )
    mapped_ids = {sm.speaker: sm.participant_id for sm in speaker_map}
    for task in extracted.tasks:
        if task.assignee_name in mapped_ids:
            task.assignee_participant_id = mapped_ids[task.assignee_name]
    result = MeetingResult(
        segments=segments,
        speaker_map=speaker_map,
        tasks=extracted.tasks,
        summary=extracted.summary,
        language_stats={"other": 1.0} if segments else {},
        duration_sec=transcript.duration,
        model_info={
            "stt": f"faster-whisper {transcript.model}",
            "processing_mode": "local_stt_diarization_ollama",
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
            "alignment_adjusted_boundary_words": str(aligned.adjusted_boundary_words),
            "boundary_grace_sec": str(settings.diarization_boundary_grace_sec),
            "voiceprint": "unavailable",
            "llm": settings.llm_model,
            "extract": "local_candidates_verified_classified_v1",
            "extract_rejected": str(extracted.rejected),
            "summary": "local_ollama",
            "speaker_identity": "explicit_handoff_or_introduction",
            "identity_hints": str(identity_hints),
            "privacy": "phone_iin_patterns_v1",
        },
    )
    if progress:
        progress("done", 1.0)
    return result


def enroll_voice(audio_path: str) -> list[float]:
    raise NotImplementedError("Real voiceprint not implemented yet. Set PIPELINE_FAKE=1.")
