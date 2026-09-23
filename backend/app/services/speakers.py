"""Speaker → participant mapping and assignee recalculation after manual edits."""

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
        match = _match_name(t.assignee_name, participants.values())
        if match is not None:
            t.assignee_participant_id = match.id


def _match_name(name: str, participants) -> Participant | None:
    n = name.lower().strip()
    if not n:
        return None
    first = n.split()[0]
    for p in participants:
        pn = p.name.lower()
        if pn == n or pn.startswith(n) or n.startswith(pn):
            return p
    for p in participants:
        if first and p.name.lower().split()[0].startswith(first[: max(3, len(first) - 2)]):
            return p
    return None
