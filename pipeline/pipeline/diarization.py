"""Offline acoustic diarization. Cluster IDs are not participant identities."""

from collections.abc import Callable
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from pipeline.settings import PipelineSettings

SEGMENTATION = "sherpa-onnx-pyannote-segmentation-3-0/model.onnx"
EMBEDDING = "nemo_en_titanet_large.onnx"


@dataclass(frozen=True)
class SpeakerTurn:
    start: float
    end: float
    speaker: int


@lru_cache(maxsize=1)
def _load_diarizer(directory: str, threads: int, count: int | None, threshold: float):
    root = Path(directory)
    for name in (SEGMENTATION, EMBEDDING):
        if not (root / name).is_file():
            raise RuntimeError(
                "Local diarization weights are missing. Run python -m "
                "pipeline.download_diarization_models before offline processing."
            )
    try:
        import sherpa_onnx as sherpa
    except ImportError:
        raise RuntimeError("Install local models runtime: uv sync --extra stt") from None
    config = sherpa.OfflineSpeakerDiarizationConfig(
        segmentation=sherpa.OfflineSpeakerSegmentationModelConfig(
            pyannote=sherpa.OfflineSpeakerSegmentationPyannoteModelConfig(
                model=str(root / SEGMENTATION),
            ),
            num_threads=threads,
            provider="cpu",
            debug=False,
        ),
        embedding=sherpa.SpeakerEmbeddingExtractorConfig(
            model=str(root / EMBEDDING),
            num_threads=threads,
            provider="cpu",
            debug=False,
        ),
        clustering=sherpa.FastClusteringConfig(num_clusters=count or -1, threshold=threshold),
        min_duration_on=0.2,
        min_duration_off=0.3,
    )
    if not config.validate():
        raise RuntimeError("Invalid local diarization configuration")
    return sherpa.OfflineSpeakerDiarization(config)


def diarize(
    audio_path: str,
    settings: PipelineSettings | None = None,
    progress: Callable[[float], None] | None = None,
) -> list[SpeakerTurn]:
    cfg = settings or PipelineSettings()
    if not Path(audio_path).is_file():
        raise FileNotFoundError("Audio file not found")
    model = _load_diarizer(
        str(cfg.diarization_model_dir),
        cfg.diarization_cpu_threads,
        cfg.diarization_num_speakers,
        cfg.diarization_threshold,
    )
    from faster_whisper.audio import decode_audio

    def callback(done: int, total: int) -> int:
        if progress:
            progress(min(done / max(total, 1), 1.0))
        return 0

    try:
        samples = decode_audio(audio_path, sampling_rate=model.sample_rate)
        if samples.size == 0:
            return []
        output = model.process(samples, callback=callback).sort_by_start_time()
        return [SpeakerTurn(t.start, t.end, t.speaker) for t in output if t.end > t.start]
    except Exception:  # noqa: BLE001 -- never expose audio/decoder internals
        raise RuntimeError(
            "Local speaker diarization failed; check audio and model files"
        ) from None
