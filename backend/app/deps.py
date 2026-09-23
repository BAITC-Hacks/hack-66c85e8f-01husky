from typing import Annotated

from fastapi import Cookie, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.security import decode_access_token

COOKIE_NAME = "access_token"

DbDep = Annotated[Session, Depends(get_db)]


def current_user(db: DbDep, access_token: Annotated[str | None, Cookie()] = None):
    from app.models.user import User

    if not access_token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")
    user_id = decode_access_token(access_token)
    user = db.get(User, user_id) if user_id else None
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token")
    return user


UserDep = Annotated[object, Depends(current_user)]


def require_admin(user: UserDep):
    if user.role != "admin":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Admin only")
    return user
