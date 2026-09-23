"""Speaker → participant mapping and assignee recalculation after manual edits."""

from pipeline.assignees import resolve_assignee
from pipeline.models import Participant as PipelineParticipant
from sqlalchemy.orm import Session

from app.models import Meeting, Participant, SpeakerMap
from app.models.enums import SpeakerSource


def apply_speaker_map(db: Session, m: Meeting, mapping: dict[str, int | None]) -> None:
    by_speaker = {sm.speaker: sm for sm in m.speaker_map}
    for speaker, pid in mapping.items():
        sm = by_speaker.get(speaker)
        if sm is None:
            sm = SpeakerMap(
                speaker=speaker, participant_id=None, source=SpeakerSource.none, confidence=0.0
            )
            m.speaker_map.append(sm)
        sm.participant_id = pid
        sm.source = SpeakerSource.manual
        sm.confidence = 1.0
    db.flush()
    recalc_assignees(db, m)


def recalc_assignees(db: Session, m: Meeting) -> None:
    """A task whose assignee_name matches a mapped speaker's participant gets that participant.

    Tasks already resolved (assignee_participant_id set) are left alone unless the name
    clearly points at a participant of the meeting.
    """
    participants = {p.id: p for p in m.participants} or {
        p.id: p for p in db.query(Participant).all()
    }
    for t in m.tasks:
        if not t.assignee_name:
            continue
        by_speaker = {sm.speaker: sm.participant_id for sm in m.speaker_map}
        if t.assignee_name in by_speaker:
            t.assignee_participant_id = by_speaker[t.assignee_name]
            continue
        match = _match_name(t.assignee_name, participants.values())
        if match is not None:
            t.assignee_participant_id = match.id


def _match_name(name: str, participants) -> Participant | None:
    people = list(participants)
    pid = resolve_assignee(name, [PipelineParticipant(id=p.id, name=p.name) for p in people])
    return next((p for p in people if p.id == pid), None)
