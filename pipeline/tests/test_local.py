from datetime import date
from types import SimpleNamespace

import pytest

from pipeline import process
from pipeline.privacy import mask_sensitive
from pipeline.settings import PipelineSettings
from pipeline.stt import local_whisper


@pytest.mark.parametrize("phone", ["+7 (701) 123-45-67", "87011234567", "8 701 123 45 67"])
def test_masks_private_values_but_preserves_dates(phone):
    text = f"Телефон {phone}, ИИН 900101300123. Срок 15.10.2026, бюджет 71000."
    assert mask_sensitive(text) == ("Телефон [PHONE], ИИН [IIN]. Срок 15.10.2026, бюджет 71000.")


def test_real_pipeline_masks_before_result_and_does_not_invent_tasks(tmp_path, monkeypatch):
    audio = tmp_path / "audio.wav"
    audio.write_bytes(b"test input; decoder mocked")
    monkeypatch.setenv("PIPELINE_FAKE", "0")
    monkeypatch.setenv("STT_BACKEND", "local")

    class Model:
        def transcribe(self, path, **kwargs):
            assert path == str(audio)
            assert kwargs["language"] is None
            return iter(
                [
                    SimpleNamespace(start=0, end=1, text="ИИН 900101300123, +7 701 123 45 67"),
                ]
            ), SimpleNamespace(duration=2, language="ru", language_probability=0.9)

    monkeypatch.setattr(local_whisper, "_load_model", lambda *args: Model())
    stages = []
    result = process(str(audio), date(2026, 9, 23), [], [], progress=lambda s, p: stages.append(p))
    assert result.segments[0].text == "ИИН [IIN], [PHONE]"
    assert result.segments[0].speaker == "SPEAKER_UNKNOWN"
    assert result.segments[0].lang == "other"
    assert result.tasks == result.speaker_map == []
    assert result.summary == ""
    assert result.model_info["extract"] == "unavailable"
    assert stages == sorted(stages) and stages[-1] == 1


def test_model_is_cached_and_load_is_offline(tmp_path, monkeypatch):
    import sys

    calls = []
    sentinel = object()

    def model(*args, **kwargs):
        calls.append(kwargs)
        return sentinel

    local_whisper._load_model.cache_clear()
    monkeypatch.setitem(sys.modules, "faster_whisper", SimpleNamespace(WhisperModel=model))
    try:
        for _ in range(2):
            assert local_whisper._load_model("test", str(tmp_path), "cpu", "int8", 2) is sentinel
        assert len(calls) == 1 and calls[0]["local_files_only"] is True
    finally:
        local_whisper._load_model.cache_clear()


def test_missing_model_does_not_download(tmp_path, monkeypatch):
    import sys

    def missing(*args, **kwargs):
        assert kwargs["local_files_only"] is True
        raise OSError("private internal details")

    local_whisper._load_model.cache_clear()
    monkeypatch.setitem(sys.modules, "faster_whisper", SimpleNamespace(WhisperModel=missing))
    with pytest.raises(RuntimeError, match="prepare weights") as error:
        local_whisper._load_model("missing", str(tmp_path), "cpu", "int8", 2)
    assert "private internal" not in str(error.value)


@pytest.mark.parametrize("empty", [True, False])
def test_empty_or_invalid_audio(tmp_path, monkeypatch, empty):
    audio = tmp_path / "bad.wav"
    audio.write_bytes(b"" if empty else b"not audio")

    class Model:
        def transcribe(self, *args, **kwargs):
            raise ValueError("decoder contains private details")

    monkeypatch.setattr(local_whisper, "_load_model", lambda *args: Model())
    with pytest.raises((ValueError, RuntimeError)) as error:
        local_whisper.transcribe(str(audio))
    assert "private details" not in str(error.value)


def test_silence_has_no_hallucinated_content(tmp_path, monkeypatch):
    audio = tmp_path / "silence.wav"
    audio.write_bytes(b"mocked silence")
    monkeypatch.setenv("PIPELINE_FAKE", "0")
    model = SimpleNamespace(
        transcribe=lambda *a, **k: (
            iter([]),
            SimpleNamespace(duration=3, language="en", language_probability=0),
        )
    )
    monkeypatch.setattr(local_whisper, "_load_model", lambda *args: model)
    result = process(str(audio), date(2026, 9, 23), [], [])
    assert result.segments == result.tasks == []
    assert result.language_stats == {} and result.duration_sec == 3


def test_settings_load_dotenv(tmp_path):
    env = tmp_path / ".env"
    env.write_text("STT_LANGUAGE=kk\nUNRELATED=value\n")
    assert PipelineSettings(_env_file=env).stt_language == "kk"
