from types import SimpleNamespace

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
    meeting = create_meeting(admin_client).json()
    detail = admin_client.get(f"/api/v1/meetings/{meeting['id']}").json()
    assert detail["status"] == "draft", detail.get("error")
    assert detail["segments"][0]["text"] == "Позвонить [PHONE]"
    assert detail["model_info"]["processing_mode"] == "local_offline_stt_only"
    assert detail["tasks"] == detail["speaker_map"] == []
    assert detail["summary"] == ""
    assert detail["progress_pct"] == 100
