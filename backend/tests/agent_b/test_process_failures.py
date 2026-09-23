from datetime import date

import pytest
from pipeline.fake import process as fake_process
from sqlalchemy.orm import sessionmaker

from app.models import Meeting, Segment
from app.models.enums import MeetingSource, MeetingStatus
from app.tasks import process_meeting as worker


@pytest.fixture
def pending_meeting(db, seed, _schema, monkeypatch):
    monkeypatch.setattr(worker, "SessionLocal", sessionmaker(bind=_schema))
    meeting = Meeting(
        title="Worker failure regression",
        meeting_date=date(2026, 9, 23),
        source=MeetingSource.upload,
        created_by=seed["admin"].id,
        audio_path="synthetic.wav",
        summary="Previous draft",
        segments=[Segment(idx=0, start=0, end=1, speaker="S0", text="Previous text", lang="ru")],
    )
    db.add(meeting)
    db.commit()
    return meeting.id


def test_database_failure_marks_failed_and_preserves_previous_draft(
    db, pending_meeting, monkeypatch
):
    result = fake_process("synthetic.wav", date(2026, 9, 23), [], ["Другое"])
    # Invalid FK fails the actual commit after persist_result has cleared old rows.
    result.tasks[0].assignee_participant_id = 999999
    monkeypatch.setattr(worker.pipeline, "process", lambda *args: result)

    worker.process_meeting.run(pending_meeting)

    db.expire_all()
    meeting = db.get(Meeting, pending_meeting)
    assert meeting.status == MeetingStatus.failed
    assert "IntegrityError" in meeting.error
    assert meeting.summary == "Previous draft"
    assert [segment.text for segment in meeting.segments] == ["Previous text"]
    assert meeting.tasks == []


@pytest.mark.parametrize("fails", [False, True])
def test_meeting_deleted_during_pipeline_does_not_crash(db, pending_meeting, monkeypatch, fails):
    def process_and_delete(*args):
        with worker.SessionLocal() as other:
            other.delete(other.get(Meeting, pending_meeting))
            other.commit()
        if fails:
            raise RuntimeError("Pipeline stopped after deletion")
        return fake_process("synthetic.wav", date(2026, 9, 23), [], ["Другое"])

    monkeypatch.setattr(worker.pipeline, "process", process_and_delete)
    worker.process_meeting.run(pending_meeting)
    db.expire_all()
    assert db.get(Meeting, pending_meeting) is None


def test_success_replaces_previous_draft(db, pending_meeting, monkeypatch):
    monkeypatch.setattr(worker.pipeline, "process", fake_process)
    worker.process_meeting.run(pending_meeting)
    db.expire_all()
    meeting = db.get(Meeting, pending_meeting)
    assert meeting.status == MeetingStatus.draft
    assert meeting.progress_stage == "done" and meeting.progress_pct == 100
    assert meeting.error is None and len(meeting.tasks) == 4
    assert meeting.summary != "Previous draft"
