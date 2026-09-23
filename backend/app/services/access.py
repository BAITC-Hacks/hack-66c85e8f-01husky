from fastapi import HTTPException, status
from sqlalchemy import exists, select
from sqlalchemy.orm import Session

from app.models import Meeting, MeetingParticipant, Participant, User
from app.models.enums import UserRole


def visible_meetings(db: Session, user: User):
    q = select(Meeting)
    if user.role == UserRole.admin:
        return q
    mine = (
        select(MeetingParticipant.meeting_id)
        .join(Participant, Participant.id == MeetingParticipant.participant_id)
        .where(Participant.user_id == user.id)
    )
    return q.where((Meeting.created_by == user.id) | Meeting.id.in_(mine))


def get_meeting_or_404(db: Session, user: User, meeting_id: int) -> Meeting:
    m = db.get(Meeting, meeting_id)
    if not m:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Meeting not found")
    if user.role != UserRole.admin and m.created_by != user.id:
        is_participant = db.scalar(
            select(
                exists().where(
                    MeetingParticipant.meeting_id == meeting_id,
                    MeetingParticipant.participant_id == Participant.id,
                    Participant.user_id == user.id,
                )
            )
        )
        if not is_participant:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "No access to this meeting")
    return m


def require_editor(m: Meeting, user: User) -> None:
    if user.role != UserRole.admin and m.created_by != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only creator or admin can edit")
