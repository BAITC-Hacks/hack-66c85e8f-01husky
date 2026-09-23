import shutil
from typing import Annotated

import pipeline
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select

from app.config import get_settings
from app.deps import DbDep, current_user, require_admin
from app.models import Participant, User
from app.schemas.participant import (
    ParticipantIn,
    ParticipantOut,
    ParticipantPatch,
    VoiceprintOut,
)

router = APIRouter(prefix="/participants", tags=["participants"])

UserDep = Annotated[User, Depends(current_user)]


def _out(p: Participant) -> ParticipantOut:
    out = ParticipantOut.model_validate(p)
    out.has_voiceprint = p.voice_embedding is not None
    return out


def _get(db, participant_id: int) -> Participant:
    p = db.get(Participant, participant_id)
    if not p:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Participant not found")
    return p


@router.get("", response_model=list[ParticipantOut])
def list_participants(db: DbDep, _: UserDep) -> list[ParticipantOut]:
    return [_out(p) for p in db.scalars(select(Participant).order_by(Participant.name))]


@router.post("", response_model=ParticipantOut, status_code=status.HTTP_201_CREATED)
def create_participant(body: ParticipantIn, db: DbDep, _: UserDep) -> ParticipantOut:
    email = body.email.lower() if body.email else None
    if email and db.scalar(select(Participant).where(Participant.email == email)):
        raise HTTPException(status.HTTP_409_CONFLICT, "Participant with this email exists")
    user_id = db.scalar(select(User.id).where(User.email == email)) if email else None
    p = Participant(name=body.name, email=email, position=body.position, user_id=user_id)
    db.add(p)
    db.commit()
    db.refresh(p)
    return _out(p)


@router.patch("/{participant_id}", response_model=ParticipantOut)
def patch_participant(
    participant_id: int, body: ParticipantPatch, db: DbDep, user: UserDep
) -> ParticipantOut:
    p = _get(db, participant_id)
    if user.role != "admin" and p.user_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not your participant")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(p, k, v.lower() if k == "email" and v else v)
    db.commit()
    db.refresh(p)
    return _out(p)


@router.post("/{participant_id}/voiceprint", response_model=VoiceprintOut)
def enroll_voiceprint(
    participant_id: int,
    db: DbDep,
    user: UserDep,
    file: Annotated[UploadFile, File()],
) -> VoiceprintOut:
    p = _get(db, participant_id)
    if user.role != "admin" and p.user_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not your participant")
    dest_dir = get_settings().audio_dir / "voiceprints"
    dest_dir.mkdir(parents=True, exist_ok=True)
    ext = (file.filename or "sample.webm").rsplit(".", 1)[-1]
    dest = dest_dir / f"{participant_id}.{ext}"
    with dest.open("wb") as f:
        shutil.copyfileobj(file.file, f)
    try:
        embedding = pipeline.enroll_voice(str(dest))
    except NotImplementedError as e:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(e)) from e
    p.voice_embedding = embedding
    db.commit()
    return VoiceprintOut(ok=True, embedding_dim=len(embedding))


@router.delete("/{participant_id}/voiceprint", status_code=status.HTTP_204_NO_CONTENT)
def delete_voiceprint(participant_id: int, db: DbDep, user: UserDep) -> None:
    p = _get(db, participant_id)
    if user.role != "admin" and p.user_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not your participant")
    p.voice_embedding = None
    db.commit()


@router.delete("/{participant_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_participant(
    participant_id: int, db: DbDep, _: Annotated[User, Depends(require_admin)]
) -> None:
    db.delete(_get(db, participant_id))
    db.commit()
