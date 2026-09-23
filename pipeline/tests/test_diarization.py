from datetime import date
from pathlib import Path
from types import SimpleNamespace

import pytest

from pipeline import real
from pipeline.diarization import SpeakerTurn, _load_diarizer, diarize
from pipeline.models import Participant
from pipeline.privacy import mask_sensitive_parts
from pipeline.settings import PipelineSettings
from pipeline.speaker_alignment import align_speakers, join_continuations
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
    from pipeline.extract import Extraction

    monkeypatch.setattr(real, "OllamaLLM", lambda *a: object())
    monkeypatch.setattr(real, "extract", lambda *a, **k: Extraction([], ""))
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


def test_mid_sentence_jitter_snaps_to_sentence_end_but_not_next_reply():
    words = [
        TranscriptWord(55.02, 55.3, "Алло"),
        TranscriptWord(55.3, 55.5, " Столгатович,"),
        TranscriptWord(55.5, 55.78, " по"),
        TranscriptWord(55.78, 56.1, " инвестициям"),
        TranscriptWord(56.1, 56.3, " что"),
        TranscriptWord(56.3, 56.66, " у нас?"),
    ]
    transcript = [
        TranscriptSegment(55.02, 56.66, "Алло Столгатович, по инвестициям что у нас?", words),
        TranscriptSegment(56.66, 61.58, "По инвестпрограмме освоение 68%."),
    ]
    turns = [SpeakerTurn(50, 55.78, 3), SpeakerTurn(55.78, 62, 4)]
    result = align_speakers(transcript, turns, boundary_grace=1.2)
    assert len(result.segments) == 2
    assert result.segments[0].text == transcript[0].text
    assert result.segments[0].speaker != result.segments[1].speaker
    assert result.adjusted_boundary_words == 3
    assert len(align_speakers(transcript, turns, boundary_grace=0).segments) == 3
    # An audible pause at the switch means do NOT smooth.
    words[2].end = 55.5
    assert align_speakers(transcript, turns, boundary_grace=1.2).adjusted_boundary_words == 0


def test_earlier_overlapping_voice_does_not_disable_later_boundary_correction():
    words = [
        TranscriptWord(55.02, 55.12, " Алло"),
        TranscriptWord(55.12, 55.56, " Столгатович,"),
        TranscriptWord(55.64, 55.78, " по"),
        TranscriptWord(55.78, 56.26, " инвестициям"),
        TranscriptWord(56.26, 56.4, " что"),
        TranscriptWord(56.4, 56.52, " у"),
        TranscriptWord(56.52, 56.66, " нас?"),
    ]
    segment = TranscriptSegment(55.02, 56.66, "Алло Столгатович, по инвестициям что у нас?", words)
    turns = [
        SpeakerTurn(54.149, 55.972, 2),
        SpeakerTurn(54.858, 55.364, 6),
        SpeakerTurn(55.972, 68.61, 6),
    ]
    result = align_speakers([segment], turns, boundary_grace=1.2)
    assert len(result.segments) == 1 and result.adjusted_boundary_words == 4
    # Simultaneous speech at the actual switch is NOT corrected.
    turns.append(SpeakerTurn(55.7, 56.3, 2))
    assert align_speakers([segment], turns, boundary_grace=1.2).adjusted_boundary_words == 0


def test_join_asr_line_wraps_preserves_real_turns_and_sentences():
    from pipeline.models import Segment

    parts = [
        Segment(start=i, end=i + 1, speaker=s, text=t, lang="ru")
        for i, (s, t) in enumerate(
            [
                ("speaker1", "Пропишите в договорах срок выставления"),
                ("speaker1", "счета."),
                ("speaker1", "Следующий вопрос."),
                ("speaker2", "Подготовлю уведомление"),
                ("speaker3", "Хорошо."),
            ]
        )
    ]
    joined = join_continuations(parts)
    assert len(joined) == 4
    assert joined[0].text == "Пропишите в договорах срок выставления счета."
    assert parts[0].text == "Пропишите в договорах срок выставления"
