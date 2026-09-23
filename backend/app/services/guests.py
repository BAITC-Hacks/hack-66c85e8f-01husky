"""Resolve verified pipeline names into meeting guests, without duplicate/ambiguous people."""

from pipeline.assignees import is_person_name, normalize_guest_name, resolve_assignee
from pipeline.models import MeetingResult
from pipeline.models import Participant as PipelineParticipant
from sqlalchemy import select, text

from app.models import Meeting, Participant


def resolve_guests(db, meeting: Meeting, result: MeetingResult) -> None:
    if result.model_info.get("processing_mode") != "local_stt_diarization_ollama":
        return
    # Serialize automatic guest resolution across workers. Manual participant creation is separate.
    db.execute(text("SELECT pg_advisory_xact_lock(73451, 1)"))
    people = list(db.scalars(select(Participant).order_by(Participant.id)))
    attached = {p.id for p in meeting.participants}

    def person(name: str) -> int | None:
        name = normalize_guest_name(name)
        if not is_person_name(name):
            return None
        roster = [PipelineParticipant(id=p.id, name=p.name) for p in people]
        pid = resolve_assignee(name, roster)
        if pid is None and any(resolve_assignee(name, [p]) for p in roster):
            return None
        if pid is None:
            p = Participant(name=name)
            db.add(p)
            db.flush()
            people.append(p)
        else:
            p = next(p for p in people if p.id == pid)
        if p.id not in attached:
            meeting.participants.append(p)
            attached.add(p.id)
        return p.id

    for mapping in result.speaker_map:
        if mapping.participant_id is None and mapping.source == "llm" and mapping.participant_name:
            mapping.participant_id = person(mapping.participant_name)
    speakers = {sm.speaker: sm.participant_id for sm in result.speaker_map}
    for task in result.tasks:
        if task.assignee_participant_id is None:
            task.assignee_participant_id = (
                speakers[task.assignee_name]
                if task.assignee_name in speakers
                else person(task.assignee_name)
            )
