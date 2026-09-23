from datetime import date

from pydantic import Field

from app.models.enums import TaskStatus, Urgency
from app.schemas.common import ORMModel


class TaskCreate(ORMModel):
    meeting_id: int
    text: str = Field(min_length=1)
    assignee_participant_id: int | None = None
    assignee_name: str = ""
    deadline: date | None = None
    deadline_raw: str | None = None
    urgency: Urgency = Urgency.normal
    direction_id: int | None = None
    quote: str | None = None
    segment_idx: int | None = None


class TaskPatch(ORMModel):
    text: str | None = Field(default=None, min_length=1)
    assignee_participant_id: int | None = None
    assignee_name: str | None = None
    deadline: date | None = None
    deadline_raw: str | None = None
    urgency: Urgency | None = None
    direction_id: int | None = None
    status: TaskStatus | None = None


class TaskStats(ORMModel):
    draft: int = 0
    confirmed: int = 0
    in_progress: int = 0
    done: int = 0
    overdue: int = 0
    due_soon: int = 0
    total: int = 0
