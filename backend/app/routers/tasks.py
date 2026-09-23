from datetime import UTC, datetime, timedelta
from typing import Annotated
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select

from app.config import get_settings
from app.deps import DbDep, current_user
from app.models import Meeting, Participant, Task, User
from app.models.enums import TASK_TRANSITIONS, MeetingStatus, TaskStatus, Urgency, UserRole
from app.routers.meetings import task_out
from app.schemas.meeting import TaskOut
from app.schemas.task import TaskCreate, TaskPatch, TaskStats
from app.services.access import get_meeting_or_404, require_editor, visible_meetings

ALMATY = ZoneInfo("Asia/Almaty")

router = APIRouter(prefix="/tasks", tags=["tasks"])

UserDep = Annotated[User, Depends(current_user)]


def _my_participant_id(db, user: User) -> int | None:
    return db.scalar(select(Participant.id).where(Participant.user_id == user.id))


def _visible_tasks(db, user: User):
    """Tasks of meetings the user can see, plus tasks assigned to them."""
    q = select(Task).join(Meeting, Meeting.id == Task.meeting_id)
    if user.role == UserRole.admin:
        return q
    meeting_ids = visible_meetings(db, user).with_only_columns(Meeting.id)
    pid = _my_participant_id(db, user)
    cond = Task.meeting_id.in_(meeting_ids)
    if pid:
        cond = cond | (Task.assignee_participant_id == pid)
    return q.where(cond)


def _can_change_status(db, task: Task, user: User) -> bool:
    if user.role == UserRole.admin or task.meeting.created_by == user.id:
        return True
    pid = _my_participant_id(db, user)
    return pid is not None and task.assignee_participant_id == pid


@router.get("", response_model=list[TaskOut])
def list_tasks(
    db: DbDep,
    user: UserDep,
    status_: Annotated[TaskStatus | None, Query(alias="status")] = None,
    assignee_id: int | None = None,
    direction_id: int | None = None,
    urgency: Urgency | None = None,
    meeting_id: int | None = None,
    mine: bool = False,
    include_draft: bool = True,
) -> list[TaskOut]:
    q = _visible_tasks(db, user)
    if status_:
        q = q.where(Task.status == status_)
    elif not include_draft:
        q = q.where(Task.status != TaskStatus.draft)
    if assignee_id:
        q = q.where(Task.assignee_participant_id == assignee_id)
    if direction_id:
        q = q.where(Task.direction_id == direction_id)
    if urgency:
        q = q.where(Task.urgency == urgency)
    if meeting_id:
        q = q.where(Task.meeting_id == meeting_id)
    if mine:
        pid = _my_participant_id(db, user)
        q = q.where(Task.assignee_participant_id == pid) if pid else q.where(False)
    q = q.order_by(Task.deadline.asc().nulls_last(), Task.id.asc())
    return [task_out(t, t.meeting) for t in db.scalars(q).unique()]


@router.get("/stats", response_model=TaskStats)
def task_stats(db: DbDep, user: UserDep, mine: bool = False) -> TaskStats:
    q = _visible_tasks(db, user)
    if mine:
        pid = _my_participant_id(db, user)
        q = q.where(Task.assignee_participant_id == pid) if pid else q.where(False)
    sub = q.subquery()
    rows = db.execute(select(sub.c.status, func.count()).group_by(sub.c.status)).all()
    stats = TaskStats(**{str(s.value if hasattr(s, "value") else s): n for s, n in rows})
    stats.total = sum(n for _, n in rows)
    today = datetime.now(tz=ALMATY).date()
    horizon = today + timedelta(hours=get_settings().due_soon_hours)
    stats.due_soon = (
        db.scalar(
            select(func.count())
            .select_from(sub)
            .where(
                sub.c.status.in_([TaskStatus.confirmed, TaskStatus.in_progress]),
                sub.c.deadline.is_not(None),
                sub.c.deadline <= horizon,
                sub.c.deadline >= today,
            )
        )
        or 0
    )
    return stats


@router.post("", response_model=TaskOut, status_code=status.HTTP_201_CREATED)
def create_task(body: TaskCreate, db: DbDep, user: UserDep) -> TaskOut:
    m = get_meeting_or_404(db, user, body.meeting_id)
    require_editor(m, user)
    data = body.model_dump()
    if data["assignee_participant_id"] and not data["assignee_name"]:
        p = db.get(Participant, data["assignee_participant_id"])
        data["assignee_name"] = p.name if p else ""
    t = Task(
        **data,
        status=TaskStatus.draft if m.status != MeetingStatus.confirmed else TaskStatus.confirmed,
    )
    db.add(t)
    db.commit()
    db.refresh(t)
    return task_out(t, m)


@router.patch("/{task_id}", response_model=TaskOut)
def patch_task(task_id: int, body: TaskPatch, db: DbDep, user: UserDep) -> TaskOut:
    t = db.get(Task, task_id)
    if not t:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Task not found")
    m = (
        get_meeting_or_404(db, user, t.meeting_id)
        if not _can_change_status(db, t, user)
        else t.meeting
    )
    data = body.model_dump(exclude_unset=True)
    new_status = data.pop("status", None)

    if data:
        require_editor(m, user)
        if (
            "assignee_participant_id" in data
            and data["assignee_participant_id"]
            and "assignee_name" not in data
        ):
            p = db.get(Participant, data["assignee_participant_id"])
            data["assignee_name"] = p.name if p else t.assignee_name
        for k, v in data.items():
            setattr(t, k, v)

    if new_status and new_status != t.status:
        if not _can_change_status(db, t, user):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Cannot change status of this task")
        if new_status not in TASK_TRANSITIONS.get(t.status, set()):
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                f"Transition {t.status.value} -> {new_status.value} not allowed",
            )
        t.status = new_status
        t.done_at = datetime.now(UTC) if new_status == TaskStatus.done else None

    db.commit()
    db.refresh(t)
    return task_out(t, t.meeting)


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(task_id: int, db: DbDep, user: UserDep) -> None:
    t = db.get(Task, task_id)
    if not t:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Task not found")
    m = get_meeting_or_404(db, user, t.meeting_id)
    require_editor(m, user)
    db.delete(t)
    db.commit()
