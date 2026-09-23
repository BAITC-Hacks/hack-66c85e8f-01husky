from datetime import datetime

from pydantic import EmailStr, Field

from app.schemas.common import ORMModel


class ParticipantIn(ORMModel):
    name: str = Field(min_length=1, max_length=255)
    email: EmailStr | None = None
    position: str | None = Field(default=None, max_length=255)


class ParticipantPatch(ORMModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    email: EmailStr | None = None
    position: str | None = Field(default=None, max_length=255)


class ParticipantOut(ORMModel):
    id: int
    name: str
    email: EmailStr | None
    position: str | None
    user_id: int | None
    has_voiceprint: bool = False
    created_at: datetime


class VoiceprintOut(ORMModel):
    ok: bool
    embedding_dim: int


class DirectionIn(ORMModel):
    name: str = Field(min_length=1, max_length=100)
    is_active: bool = True


class DirectionPatch(ORMModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    is_active: bool | None = None


class DirectionOut(ORMModel):
    id: int
    name: str
    is_active: bool
