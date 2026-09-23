"""Lazy, cached offline Whisper. Never downloads models while processing audio."""

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from pipeline.models import ProgressCallback
from pipeline.privacy import mask_sensitive
from pipeline.settings import PipelineSettings


@dataclass
class TranscriptSegment:
    start: float
    end: float
    text: str


@dataclass
class Transcript:
    segments: list[TranscriptSegment]
    duration: float
    detected_language: str
    language_probability: float
    model: str


@lru_cache(maxsize=1)
def _load_model(model: str, directory: str, device: str, compute: str, threads: int):
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        raise RuntimeError("Install local STT dependencies: uv sync --extra stt") from None
    try:
        return WhisperModel(
            model,
            device=device,
            compute_type=compute,
            cpu_threads=threads,
            download_root=directory,
            local_files_only=True,
        )
    except Exception:  # noqa: BLE001 -- sanitize model-loader errors at the provider boundary
        raise RuntimeError(
            "Cannot load local Whisper model. Check STT_MODEL/STT_MODEL_DIR and prepare "
            "weights with python -m pipeline.download_model before offline processing."
        ) from None


def transcribe(
    audio_path: str,
    settings: PipelineSettings | None = None,
    progress: ProgressCallback | None = None,
) -> Transcript:
    cfg = settings or PipelineSettings()
    path = Path(audio_path)
    if not path.is_file():
        raise FileNotFoundError("Audio file not found")
    if path.stat().st_size == 0:
        raise ValueError("Audio file is empty")
    if progress:
        progress("loading_model", 0.05)
    model = _load_model(
        cfg.stt_model,
        str(cfg.stt_model_dir),
        cfg.stt_device,
        cfg.stt_compute_type,
        cfg.stt_cpu_threads,
    )
    if progress:
        progress("stt", 0.1)
    try:
        segments, info = model.transcribe(
            str(path),
            language=None if cfg.stt_language == "auto" else cfg.stt_language,
            vad_filter=True,
            beam_size=5,
            word_timestamps=True,
        )
        result = []
        for segment in segments:
            text = mask_sensitive(segment.text.strip())
            if text:
                result.append(TranscriptSegment(segment.start, segment.end, text))
            if progress:
                progress("stt", 0.1 + 0.8 * min(segment.end / max(info.duration, 0.01), 1))
    except Exception:  # noqa: BLE001 -- sanitize decoder errors at the provider boundary
        # Decoder/provider exceptions may contain raw input; do not forward it to logs/API.
        raise RuntimeError(
            "Local transcription failed; check audio format and available memory"
        ) from None
    return Transcript(
        result, info.duration, info.language, info.language_probability, cfg.stt_model
    )
