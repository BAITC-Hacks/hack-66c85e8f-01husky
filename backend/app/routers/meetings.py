from datetime import UTC, date, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy import select

from app.deps import DbDep, current_user
from app.models import Meeting, Participant, Task, User
from app.models.enums import Locale, MeetingSource, MeetingStatus, NotificationKind, TaskStatus
from app.schemas.meeting import MeetingDetail, MeetingOut, MeetingPatch, SpeakerMapIn, TaskOut
from app.schemas.participant import ParticipantOut
from app.services import audio as audio_svc
from app.services import notify
from app.services.access import get_meeting_or_404, require_editor, visible_meetings
from app.services.processing import enqueue_processing
from app.services.speakers import apply_speaker_map

router = APIRouter(prefix="/meetings", tags=["meetings"])

UserDep = Annotated[User, Depends(current_user)]


def task_out(t: Task, m: Meeting | None = None) -> TaskOut:
    out = TaskOut.model_validate(t)
    out.direction_name = t.direction.name if t.direction else None
    if m:
        out.meeting_title, out.meeting_date = m.title, m.meeting_date
    return out


def meeting_out(m: Meeting) -> MeetingOut:
    out = MeetingOut.model_validate(m)
    out.tasks_count = len(m.tasks)
    out.participants_count = len(m.participants)
    return out


def meeting_detail(m: Meeting) -> MeetingDetail:
    base = meeting_out(m).model_dump()
    parts = []
    for p in m.participants:
        po = ParticipantOut.model_validate(p)
        po.has_voiceprint = p.voice_embedding is not None
        parts.append(po)
    return MeetingDetail(
        **base,
        summary=m.summary,
        language_stats=m.language_stats,
        model_info=m.model_info,
        participants=parts,
        segments=m.segments,
        speaker_map=m.speaker_map,
        tasks=[task_out(t, m) for t in m.tasks],
    )


def _load_participants(db, ids: list[int]) -> list[Participant]:
    if not ids:
        return []
    found = list(db.scalars(select(Participant).where(Participant.id.in_(ids))))
    if len(found) != len(set(ids)):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Unknown participant id")
    return found


@router.post("", response_model=MeetingOut, status_code=status.HTTP_201_CREATED)
def create_meeting(
    db: DbDep,
    user: UserDep,
    title: Annotated[str, Form(min_length=1, max_length=500)],
    meeting_date: Annotated[date, Form()],
    file: Annotated[UploadFile, File()],
    output_language: Annotated[Locale, Form()] = Locale.ru,
    participant_ids: Annotated[list[int] | None, Form()] = None,
) -> MeetingOut:
    m = Meeting(
        title=title,
        meeting_date=meeting_date,
        source=MeetingSource.upload,
        output_language=output_language,
        status=MeetingStatus.uploaded,
        created_by=user.id,
    )
    m.participants = _load_participants(db, participant_ids or [])
    db.add(m)
    db.flush()
    try:
        src = audio_svc.save_upload(m.id, file)
        wav = audio_svc.to_wav(src)
    except ValueError as e:
        db.rollback()
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(e)) from e
    except Exception as e:  # ffmpeg failure
        db.rollback()
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY, f"Cannot decode audio: {e}"
        ) from e
    m.audio_path = str(wav)
    m.duration_sec = audio_svc.probe_duration(wav)
    db.commit()
    db.refresh(m)
    enqueue_processing(m.id)
    db.refresh(m)
    return meeting_out(m)


@router.get("", response_model=list[MeetingOut])
def list_meetings(
    db: DbDep,
    user: UserDep,
    status_: Annotated[MeetingStatus | None, Query(alias="status")] = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> list[MeetingOut]:
    q = visible_meetings(db, user)
    if status_:
        q = q.where(Meeting.status == status_)
    if date_from:
        q = q.where(Meeting.meeting_date >= date_from)
    if date_to:
        q = q.where(Meeting.meeting_date <= date_to)
    return [
        meeting_out(m)
        for m in db.scalars(q.order_by(Meeting.meeting_date.desc(), Meeting.id.desc()))
    ]


@router.get("/{meeting_id}", response_model=MeetingDetail)
def get_meeting(meeting_id: int, db: DbDep, user: UserDep) -> MeetingDetail:
    return meeting_detail(get_meeting_or_404(db, user, meeting_id))


@router.patch("/{meeting_id}", response_model=MeetingDetail)
def patch_meeting(meeting_id: int, body: MeetingPatch, db: DbDep, user: UserDep) -> MeetingDetail:
    m = get_meeting_or_404(db, user, meeting_id)
    require_editor(m, user)
    data = body.model_dump(exclude_unset=True)
    ids = data.pop("participant_ids", None)
    for k, v in data.items():
        setattr(m, k, v)
    if ids is not None:
        m.participants = _load_participants(db, ids)
    db.commit()
    db.refresh(m)
    return meeting_detail(m)


@router.put("/{meeting_id}/speakers", response_model=MeetingDetail)
def set_speakers(
    meeting_id: int, body: list[SpeakerMapIn], db: DbDep, user: UserDep
) -> MeetingDetail:
    m = get_meeting_or_404(db, user, meeting_id)
    require_editor(m, user)
    ids = [x.participant_id for x in body if x.participant_id is not None]
    _load_participants(db, ids)
    apply_speaker_map(db, m, {x.speaker: x.participant_id for x in body})
    db.commit()
    db.refresh(m)
    return meeting_detail(m)


@router.post("/{meeting_id}/confirm", response_model=MeetingDetail)
def confirm_meeting(meeting_id: int, db: DbDep, user: UserDep) -> MeetingDetail:
    m = get_meeting_or_404(db, user, meeting_id)
    require_editor(m, user)
    if m.status != MeetingStatus.draft:
        raise HTTPException(
            status.HTTP_409_CONFLICT, f"Cannot confirm meeting in status {m.status.value}"
        )
    m.status = MeetingStatus.confirmed
    m.confirmed_at = datetime.now(UTC)
    notified: set[int] = set()
    for t in m.tasks:
        if t.status == TaskStatus.draft:
            t.status = TaskStatus.confirmed
        deadline = f", срок {t.deadline.isoformat()}" if t.deadline else ""
        n = notify.notify_task(db, t, NotificationKind.assigned, f"«{m.title}»: {t.text}{deadline}")
        if n:
            notified.add(n.user_id)
    for uid in notified:
        notify.create(
            db,
            uid,
            NotificationKind.protocol_ready,
            f"Протокол совещания «{m.title}» от {m.meeting_date.isoformat()} подтверждён",
            meeting_id=m.id,
        )
    db.commit()
    db.refresh(m)
    return meeting_detail(m)


@router.post("/{meeting_id}/reprocess", response_model=MeetingOut)
def reprocess_meeting(meeting_id: int, db: DbDep, user: UserDep) -> MeetingOut:
    m = get_meeting_or_404(db, user, meeting_id)
    require_editor(m, user)
    if not m.audio_path:
        raise HTTPException(status.HTTP_409_CONFLICT, "Audio was deleted, cannot reprocess")
    if m.status == MeetingStatus.confirmed:
        raise HTTPException(status.HTTP_409_CONFLICT, "Confirmed protocol cannot be reprocessed")
    m.status = MeetingStatus.uploaded
    m.error = None
    db.commit()
    enqueue_processing(m.id)
    db.refresh(m)
    return meeting_out(m)


@router.delete("/{meeting_id}/audio", status_code=status.HTTP_204_NO_CONTENT)
def delete_audio(meeting_id: int, db: DbDep, user: UserDep) -> None:
    m = get_meeting_or_404(db, user, meeting_id)
    require_editor(m, user)
    if m.status == MeetingStatus.processing:
        raise HTTPException(status.HTTP_409_CONFLICT, "Meeting is being processed")
    audio_svc.delete_meeting_audio(m.id)
    m.audio_path = None
    db.commit()


@router.delete("/{meeting_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_meeting(meeting_id: int, db: DbDep, user: UserDep) -> None:
    m = get_meeting_or_404(db, user, meeting_id)
    require_editor(m, user)
    audio_svc.delete_meeting_audio(m.id)
    db.delete(m)
    db.commit()
