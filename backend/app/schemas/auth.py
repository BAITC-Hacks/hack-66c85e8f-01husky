from datetime import datetime

from pydantic import EmailStr, Field

from app.models.enums import Locale, UserRole
from app.schemas.common import ORMModel


class RegisterIn(ORMModel):
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)
    name: str = Field(min_length=1, max_length=255)
    locale: Locale = Locale.ru


class LoginIn(ORMModel):
    email: EmailStr
    password: str


class UserOut(ORMModel):
    id: int
    email: EmailStr
    name: str
    role: UserRole
    locale: Locale
    participant_id: int | None = None
    created_at: datetime
