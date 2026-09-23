from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select

from app.deps import DbDep, current_user, require_admin
from app.models import Direction, User
from app.schemas.participant import DirectionIn, DirectionOut, DirectionPatch

router = APIRouter(prefix="/directions", tags=["directions"])

AdminDep = Annotated[User, Depends(require_admin)]


@router.get("", response_model=list[DirectionOut])
def list_directions(
    db: DbDep, _: Annotated[User, Depends(current_user)], include_inactive: bool = False
) -> list[Direction]:
    q = select(Direction).order_by(Direction.id)
    if not include_inactive:
        q = q.where(Direction.is_active.is_(True))
    return list(db.scalars(q))


@router.post("", response_model=DirectionOut, status_code=status.HTTP_201_CREATED)
def create_direction(body: DirectionIn, db: DbDep, _: AdminDep) -> Direction:
    if db.scalar(select(Direction).where(Direction.name == body.name)):
        raise HTTPException(status.HTTP_409_CONFLICT, "Direction exists")
    d = Direction(name=body.name, is_active=body.is_active)
    db.add(d)
    db.commit()
    db.refresh(d)
    return d


@router.patch("/{direction_id}", response_model=DirectionOut)
def patch_direction(direction_id: int, body: DirectionPatch, db: DbDep, _: AdminDep) -> Direction:
    d = db.get(Direction, direction_id)
    if not d:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Direction not found")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(d, k, v)
    db.commit()
    db.refresh(d)
    return d
