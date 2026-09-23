from types import SimpleNamespace

from pipeline import real
from pipeline.diarization import SpeakerTurn
from pipeline.extract import Extraction
from pipeline.models import Task
from pipeline.stt import local_whisper

from tests.helpers import create_meeting


def test_api_persists_real_pipeline_result(admin_client, monkeypatch):
    monkeypatch.setenv("PIPELINE_FAKE", "0")
    monkeypatch.setenv("CELERY_EAGER", "1")
    model = SimpleNamespace(
        transcribe=lambda *a, **kw: (
            iter([SimpleNamespace(start=0.0, end=1.0, text="Позвонить +7 (701) 123-45-67")]),
            SimpleNamespace(duration=2.0, language="ru", language_probability=0.99),
        )
    )
    monkeypatch.setattr(local_whisper, "_load_model", lambda *args: model)
    monkeypatch.setattr(real, "diarize", lambda *args, **kwargs: [SpeakerTurn(0, 1, 9)])
    monkeypatch.setattr(real, "OllamaLLM", lambda *a: object())

    def extraction(segments, *args, **kwargs):
        assert segments[0].text == "Позвонить [PHONE]"
        return Extraction(
            [
                Task(
                    text="Позвонить",
                    assignee_participant_id=None,
                    assignee_name="",
                    deadline=None,
                    deadline_raw=None,
                    urgency="normal",
                    direction="Другое",
                    quote=segments[0].text,
                    segment_index=0,
                    confidence=0.8,
                )
            ],
            "Запланирован звонок.",
        )

    monkeypatch.setattr(real, "extract", extraction)
    meeting = create_meeting(admin_client).json()
    detail = admin_client.get(f"/api/v1/meetings/{meeting['id']}").json()
    assert detail["status"] == "draft", detail.get("error")
    assert detail["segments"][0]["text"] == "Позвонить [PHONE]"
    assert detail["model_info"]["processing_mode"] == "local_stt_diarization_ollama"
    assert len(detail["tasks"]) == 1
    assert detail["tasks"][0]["status"] == "draft"
    assert detail["tasks"][0]["quote"] == "Позвонить [PHONE]"
    assert detail["tasks"][0]["segment_idx"] == 0
    assert detail["segments"][0]["speaker"] == "speaker1"
    assert detail["speaker_map"][0]["speaker"] == "speaker1"
    assert detail["speaker_map"][0]["participant_id"] is None
    assert detail["speaker_map"][0]["source"] == "none"
    assert detail["summary"] == "Запланирован звонок."
    assert detail["progress_pct"] == 100
