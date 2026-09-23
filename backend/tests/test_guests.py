from datetime import date

from pipeline.models import MeetingResult, SpeakerMapping, Task
from sqlalchemy import select

from app.models import Meeting, Participant
from app.models.enums import Locale, MeetingSource
from app.services.guests import resolve_guests


def result(name="Ерлан"):
    return MeetingResult(
        segments=[],
        speaker_map=[
            SpeakerMapping(
                speaker="speaker2",
                participant_id=None,
                participant_name=name,
                source="llm",
                confidence=0.75,
            )
        ],
        tasks=[
            Task(
                text="Подготовить отчет",
                assignee_participant_id=None,
                assignee_name=name,
                deadline=None,
                deadline_raw=None,
                urgency="normal",
                direction="Другое",
                quote=f"{name}, подготовь отчет.",
                segment_index=0,
                confidence=0.8,
            ),
            Task(
                text="Подготовить смету",
                assignee_participant_id=None,
                assignee_name="speaker2",
                deadline=None,
                deadline_raw=None,
                urgency="normal",
                direction="Другое",
                quote="Я подготовлю смету.",
                segment_index=1,
                confidence=0.8,
            ),
        ],
        summary="",
        language_stats={},
        duration_sec=1,
        model_info={"processing_mode": "local_stt_diarization_ollama"},
    )


def meeting(db, seed):
    m = Meeting(
        title="Guest test",
        meeting_date=date(2026, 9, 23),
        source=MeetingSource.upload,
        output_language=Locale.ru,
        created_by=seed["admin"].id,
    )
    db.add(m)
    db.flush()
    return m


def test_guest_created_attached_and_reused(db, seed):
    m = meeting(db, seed)
    r = result()
    resolve_guests(db, m, r)
    db.commit()
    pid = r.speaker_map[0].participant_id
    assert pid and all(t.assignee_participant_id == pid for t in r.tasks)
    assert [p.id for p in m.participants] == [pid]
    guest = db.get(Participant, pid)
    assert guest.email is None and guest.user_id is None
    r = result()
    resolve_guests(db, m, r)
    db.commit()
    assert r.speaker_map[0].participant_id == pid
    assert len(list(db.scalars(select(Participant).where(Participant.name == "Ерлан")))) == 1


def test_ambiguous_name_does_not_create_third_person(db, seed):
    db.add_all([Participant(name="Ерлан Нурланов"), Participant(name="Ерлан Касымов")])
    db.flush()
    m = meeting(db, seed)
    r = result()
    resolve_guests(db, m, r)
    assert r.speaker_map[0].participant_id is None
    assert all(t.assignee_participant_id is None for t in r.tasks)
    assert db.scalar(select(Participant).where(Participant.name == "Ерлан")) is None


def test_labels_and_roles_are_not_guests(db, seed):
    m = meeting(db, seed)
    for name in ("speaker3", "Юрист", "Вы", "Неизвестно", ""):
        r = result(name)
        resolve_guests(db, m, r)
        assert r.speaker_map[0].participant_id is None
    assert m.participants == []


def test_patronymic_case_does_not_duplicate_guest(db, seed):
    m = meeting(db, seed)
    r = result("Батагус Нурлановны")
    resolve_guests(db, m, r)
    db.commit()
    pid = r.speaker_map[0].participant_id
    assert db.get(Participant, pid).name == "Батагус Нурлановна"
    r = result("Батагус Нурлановна")
    resolve_guests(db, m, r)
    db.commit()
    assert r.speaker_map[0].participant_id == pid
