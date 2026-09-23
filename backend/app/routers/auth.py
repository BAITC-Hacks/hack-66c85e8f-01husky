from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select

from app.config import get_settings
from app.deps import COOKIE_NAME, DbDep, current_user
from app.models import Participant, User
from app.schemas.auth import LoginIn, RegisterIn, UserOut
from app.security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])

UserDep = Annotated[User, Depends(current_user)]


def _user_out(db, user: User) -> UserOut:
    participant_id = db.scalar(select(Participant.id).where(Participant.user_id == user.id))
    out = UserOut.model_validate(user)
    out.participant_id = participant_id
    return out


def _set_cookie(response: Response, user_id: int) -> None:
    s = get_settings()
    response.set_cookie(
        COOKIE_NAME,
        create_access_token(user_id),
        httponly=True,
        samesite="lax",
        secure=s.cookie_secure,
        max_age=s.access_token_days * 86400,
        path="/",
    )


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(body: RegisterIn, db: DbDep, response: Response) -> UserOut:
    email = body.email.lower()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")
    user = User(
        email=email, password_hash=hash_password(body.password), name=body.name, locale=body.locale
    )
    db.add(user)
    db.flush()
    # Guest participant created earlier by a secretary gets claimed by email.
    participant = db.scalar(select(Participant).where(Participant.email == email))
    if participant and participant.user_id is None:
        participant.user_id = user.id
    elif not participant:
        db.add(Participant(name=body.name, email=email, user_id=user.id))
    db.commit()
    db.refresh(user)
    _set_cookie(response, user.id)
    return _user_out(db, user)


@router.post("/login", response_model=UserOut)
def login(body: LoginIn, db: DbDep, response: Response) -> UserOut:
    user = db.scalar(select(User).where(User.email == body.email.lower()))
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password")
    _set_cookie(response, user.id)
    return _user_out(db, user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response) -> None:
    response.delete_cookie(COOKIE_NAME, path="/")


@router.get("/me", response_model=UserOut)
def me(user: UserDep, db: DbDep) -> UserOut:
    return _user_out(db, user)
