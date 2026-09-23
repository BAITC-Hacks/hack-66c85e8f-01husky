from datetime import date
from pathlib import Path
from types import SimpleNamespace

import pytest

from pipeline import real
from pipeline.diarization import SpeakerTurn, _load_diarizer, diarize
from pipeline.models import Participant
from pipeline.privacy import mask_sensitive_parts
from pipeline.settings import PipelineSettings
from pipeline.speaker_alignment import align_speakers
from pipeline.stt.local_whisper import Transcript, TranscriptSegment, TranscriptWord


def test_split_words_at_speaker_change_and_reuse_cluster_label():
    transcript = [
        TranscriptSegment(
            0,
            3,
            "Привет Да Снова",
            [
                TranscriptWord(0, 1, "Привет"),
                TranscriptWord(1, 2, " Да"),
                TranscriptWord(2, 3, " Снова"),
            ],
        )
    ]
    result = align_speakers(
        transcript, [SpeakerTurn(0, 1, 42), SpeakerTurn(1, 2, 9), SpeakerTurn(2, 3, 42)]
    )
    assert [s.speaker for s in result.segments] == ["speaker1", "speaker2", "speaker1"]
    assert [s.text for s in result.segments] == ["Привет", "Да", "Снова"]
    assert [(s.start, s.end) for s in result.segments] == [(0, 1), (1, 2), (2, 3)]
    assert all(s.participant_id is None and s.confidence == 0 for s in result.speaker_map)
    assert result.coarse_segments == 0


def test_identity_is_not_inferred_from_names_or_participant_order(monkeypatch):
    transcript = Transcript([TranscriptSegment(0, 1, "Дана, сделай")], 1, "ru", 1, "test")
    monkeypatch.setattr(real, "transcribe", lambda *a, **k: transcript)
    monkeypatch.setattr(real, "diarize", lambda *a, **k: [SpeakerTurn(0, 1, 8)])
    result = real.process("unused", date(2026, 9, 23), [Participant(id=5, name="Дана")], [])
    assert result.speaker_map[0].participant_id is None
    assert result.segments[0].speaker == "speaker1"
    assert result.model_info["voiceprint"] == "unavailable"


def test_mask_phone_even_across_speaker_and_word_boundaries():
    words = [
        TranscriptWord(0, 1, "Телефон +7"),
        TranscriptWord(1, 2, " 701"),
        TranscriptWord(2, 3, " 123-45-67"),
    ]
    result = align_speakers(
        [TranscriptSegment(0, 3, "Телефон [PHONE]", words)],
        [SpeakerTurn(0, 1, 2), SpeakerTurn(1, 3, 3)],
    )
    assert [s.text for s in result.segments] == ["Телефон [PHONE]", "[PHONE]"]
    assert mask_sensitive_parts(["ИИН 900101300123", "15.10.2026"]) == ["ИИН [IIN]", "15.10.2026"]


def test_no_speakers_is_failure_not_fabricated_labels():
    with pytest.raises(RuntimeError, match="no speakers"):
        align_speakers([TranscriptSegment(0, 1, "Речь")], [])
    assert align_speakers([], []).segments == []


def test_nearest_turn_and_overlap_are_reported():
    result = align_speakers(
        [
            TranscriptSegment(0, 1, "Начало"),
            TranscriptSegment(3, 4, "Два голоса"),
        ],
        [SpeakerTurn(2, 5, 1), SpeakerTurn(3, 5, 2)],
    )
    assert result.nearest_words == result.distant_words == result.overlapping_words == 1
    assert result.coarse_segments == 2


def test_inconsistent_word_text_is_not_lost():
    result = align_speakers(
        [TranscriptSegment(0, 3, "Целая реплика", [TranscriptWord(0, 1, "Часть")])],
        [SpeakerTurn(0, 3, 0)],
    )
    assert result.segments[0].text == "Целая реплика"
    assert result.coarse_segments == 1


def test_missing_diarization_model_never_downloads(tmp_path):
    with pytest.raises(RuntimeError, match="download_diarization_models"):
        _load_diarizer(str(tmp_path), 1, None, 0.5)


def test_runtime_uses_only_local_files_and_cpu(tmp_path, monkeypatch):
    import sys

    from pipeline.diarization import EMBEDDING, SEGMENTATION

    for name in [EMBEDDING, SEGMENTATION]:
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch()
    seen = []

    def config(**kwargs):
        seen.append(kwargs)
        return SimpleNamespace(**kwargs, validate=lambda: True)

    monkeypatch.setitem(
        sys.modules,
        "sherpa_onnx",
        SimpleNamespace(
            OfflineSpeakerDiarizationConfig=config,
            OfflineSpeakerSegmentationModelConfig=config,
            OfflineSpeakerSegmentationPyannoteModelConfig=config,
            SpeakerEmbeddingExtractorConfig=config,
            FastClusteringConfig=config,
            OfflineSpeakerDiarization=lambda cfg: cfg,
        ),
    )
    _load_diarizer.cache_clear()
    try:
        first = _load_diarizer(str(tmp_path), 2, None, 0.5)
        assert _load_diarizer(str(tmp_path), 2, None, 0.5) is first
        assert first.embedding.provider == first.segmentation.provider == "cpu"
        assert first.clustering.num_clusters == -1
        assert Path(first.embedding.model).is_file()
    finally:
        _load_diarizer.cache_clear()


def test_decoder_failure_does_not_leak_data(tmp_path, monkeypatch):
    import sys

    from pipeline import diarization

    path = tmp_path / "bad.wav"
    path.write_bytes(b"invalid")
    monkeypatch.setattr(
        diarization, "_load_diarizer", lambda *a: SimpleNamespace(sample_rate=16000)
    )

    def fail(*args, **kwargs):
        raise ValueError("private audio details")

    monkeypatch.setitem(sys.modules, "faster_whisper.audio", SimpleNamespace(decode_audio=fail))
    with pytest.raises(RuntimeError, match="Local speaker diarization failed"):
        diarize(str(path), PipelineSettings())
