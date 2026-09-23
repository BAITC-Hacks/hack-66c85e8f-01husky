from tests.helpers import create_meeting


def test_upload_reaches_draft_with_tasks(admin_client, monkeypatch) -> None:
    monkeypatch.setenv("CELERY_EAGER", "1")
    pids = [p["id"] for p in admin_client.get("/api/v1/participants").json()]
    m = create_meeting(admin_client, participant_ids=pids).json()
    d = admin_client.get(f"/api/v1/meetings/{m['id']}").json()
    assert d["status"] == "draft", d.get("error")
    assert d["progress_pct"] == 100.0 and d["progress_stage"] == "done"
    assert len(d["segments"]) == 7 and len(d["speaker_map"]) == 3 and len(d["tasks"]) == 4
    assert d["summary"].startswith("## Тема")
    assert d["model_info"]["stt"] == "fake" and d["language_stats"]["kk"] > 0
    aibek = next(p for p in d["participants"] if p["name"].startswith("Айбек"))
    t = next(t for t in d["tasks"] if t["deadline_raw"] == "до пятницы")
    assert t["assignee_participant_id"] == aibek["id"] and t["status"] == "draft"
    assert t["deadline"] == "2026-09-25" and t["direction_name"] == "Финансы"
    assert t["quote"] in d["segments"][t["segment_idx"]]["text"]


def test_reprocess_replaces_results(admin_client, monkeypatch) -> None:
    monkeypatch.setenv("CELERY_EAGER", "1")
    m = create_meeting(admin_client).json()
    assert admin_client.post(f"/api/v1/meetings/{m['id']}/reprocess").status_code == 200
    d = admin_client.get(f"/api/v1/meetings/{m['id']}").json()
    assert d["status"] == "draft" and len(d["tasks"]) == 4 and len(d["segments"]) == 7


def test_pipeline_failure_marks_failed(admin_client, monkeypatch) -> None:
    monkeypatch.setenv("CELERY_EAGER", "1")

    def boom(*a, **k):
        raise RuntimeError("whisper exploded")

    monkeypatch.setattr("app.tasks.process_meeting.pipeline.process", boom)
    m = create_meeting(admin_client).json()
    d = admin_client.get(f"/api/v1/meetings/{m['id']}").json()
    assert d["status"] == "failed" and "whisper exploded" in d["error"]
