import shutil
import subprocess
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import select
from starlette.background import BackgroundTask

from app.deps import DbDep, UserDep
from app.models import Meeting
from app.models.enums import MeetingStatus
from app.services.access import get_meeting_or_404, require_editor
from app.services.export import build_docx, to_pdf
from app.services.sed import MockSED

router = APIRouter(prefix="/meetings", tags=["exports"])


def _protocol(meeting: Meeting, format: str, lang: str) -> Path:
    if meeting.status not in (MeetingStatus.draft, MeetingStatus.confirmed):
        raise HTTPException(409, "Protocol is not ready")
    docx = build_docx(meeting, lang)
    try:
        return to_pdf(docx) if format == "pdf" else docx
    except (OSError, RuntimeError, subprocess.SubprocessError) as exc:
        shutil.rmtree(docx.parent, ignore_errors=True)
        raise HTTPException(503, "PDF conversion is unavailable") from exc


@router.get("/{meeting_id}/export")
def export_protocol(
    meeting_id: int,
    db: DbDep,
    user: UserDep,
    format: Literal["docx", "pdf"] = "docx",
    lang: Literal["ru", "kk"] | None = None,
) -> FileResponse:
    meeting = get_meeting_or_404(db, user, meeting_id)
    language = lang or meeting.output_language.value
    path = _protocol(meeting, format, language)
    media_type = (
        "application/pdf"
        if format == "pdf"
        else "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    return FileResponse(
        path,
        filename=f"protocol-{meeting_id}-{language}.{format}",
        media_type=media_type,
        background=BackgroundTask(shutil.rmtree, path.parent, ignore_errors=True),
    )


@router.post("/{meeting_id}/sed")
def push_to_sed(meeting_id: int, db: DbDep, user: UserDep) -> dict[str, str]:
    meeting = get_meeting_or_404(db, user, meeting_id)
    require_editor(meeting, user)
    meeting = db.scalar(
        select(Meeting)
        .where(Meeting.id == meeting_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if meeting.status != MeetingStatus.confirmed:
        raise HTTPException(409, "Confirm the protocol before sending to SED")
    pdf = _protocol(meeting, "pdf", meeting.output_language.value)
    adapter = MockSED()
    try:
        reference = adapter.push_protocol(meeting, pdf)
        meeting.sed_ref = reference
        for task in meeting.tasks:
            task.sed_ref = reference
        db.commit()
    finally:
        shutil.rmtree(pdf.parent, ignore_errors=True)
    return {"sed_ref": reference, "outbox_path": str(adapter.outbox / str(meeting.id))}
