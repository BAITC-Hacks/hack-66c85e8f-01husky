"""Read-only database explorer; only explicitly selected columns are exposed."""

from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy import String, cast, func, or_, select

from app.db import Base
from app.deps import DbDep, require_admin

ASSETS = Path(__file__).resolve().parents[1] / "admin_assets"
pages = APIRouter()
router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin)])

# Explicit allowlist: passwords, voice embeddings, recording paths and call URLs stay private.
TABLES = {
    "meetings": (
        "Совещания",
        "id title meeting_date source platform duration_sec output_language status progress_stage progress_pct summary language_stats model_info error sed_ref created_by created_at confirmed_at",
    ),
    "segments": ("Транскрипт", "id meeting_id idx start end speaker text lang"),
    "tasks": (
        "Поручения",
        "id meeting_id assignee_participant_id assignee_name text deadline deadline_raw urgency direction_id quote segment_idx confidence status sed_ref created_at updated_at done_at",
    ),
    "participants": ("Участники", "id name email position user_id created_at"),
    "users": ("Пользователи", "id email name role locale created_at"),
    "speaker_map": ("Говорящие", "id meeting_id speaker participant_id source confidence"),
    "meeting_participants": ("Участники встреч", "meeting_id participant_id"),
    "directions": ("Направления", "id name is_active"),
    "notifications": (
        "Уведомления",
        "id user_id task_id meeting_id kind title body read_at created_at",
    ),
}


@pages.get("/admin", include_in_schema=False)
@pages.get("/admin/", include_in_schema=False)
def admin_page() -> FileResponse:
    return FileResponse(
        ASSETS / "index.html",
        headers={
            "Cache-Control": "no-store",
            "Content-Security-Policy": "default-src 'self'; script-src 'self'; style-src 'self'; "
            "connect-src 'self'; object-src 'none'; frame-ancestors 'none'; base-uri 'none'; "
            "form-action 'self'",
            "X-Content-Type-Options": "nosniff",
            "Referrer-Policy": "no-referrer",
        },
    )


@router.get("/tables")
def tables(db: DbDep) -> dict[str, Any]:
    result = []
    for name, (label, fields) in TABLES.items():
        table = Base.metadata.tables[name]
        result.append(
            {
                "name": name,
                "label": label,
                "count": db.scalar(select(func.count()).select_from(table)),
                "columns": [
                    {"name": key, "type": str(table.c[key].type), "nullable": table.c[key].nullable}
                    for key in fields.split()
                ],
                "meeting_filter": name == "meetings" or "meeting_id" in table.c,
            }
        )
    return {"tables": result, "read_only": True}


@router.get("/tables/{name}")
def rows(
    name: str,
    db: DbDep,
    q: Annotated[str, Query(max_length=200)] = "",
    meeting_id: Annotated[int | None, Query(ge=1)] = None,
    offset: Annotated[int, Query(ge=0, le=1_000_000)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> dict[str, Any]:
    if name not in TABLES:
        raise HTTPException(404, "Unknown table")
    table = Base.metadata.tables[name]
    columns = [table.c[key] for key in TABLES[name][1].split()]
    conditions = []
    if q.strip():
        escaped = q.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        conditions.append(
            or_(*(cast(c, String).ilike(f"%{escaped}%", escape="\\") for c in columns))
        )
    if meeting_id is not None:
        key = table.c.id if name == "meetings" else table.c.get("meeting_id")
        if key is None:
            raise HTTPException(422, "This table has no meeting filter")
        conditions.append(key == meeting_id)
    order = (
        [table.c.meeting_id, table.c.idx, table.c.id]
        if name == "segments"
        else list(table.primary_key)
    )
    total = db.scalar(select(func.count()).select_from(table).where(*conditions))
    records = db.execute(
        select(*columns).where(*conditions).order_by(*order).offset(offset).limit(limit)
    )
    return {
        "rows": [dict(row) for row in records.mappings()],
        "total": total,
        "offset": offset,
        "limit": limit,
    }
