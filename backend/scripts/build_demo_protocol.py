"""Build the README's simulated protocol using the production export service.

Run from the repository root:
    uv run --project backend python backend/scripts/build_demo_protocol.py
Requires LibreOffice. No database, audio recording or ML model is used.
"""

import shutil
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory

from pipeline.fake import process
from pipeline.models import Participant

from app.config import get_settings
from app.services.export import build_docx, to_pdf

OUTPUT = Path(__file__).resolve().parents[2] / "docs" / "demo"


def main() -> None:
    participants = [
        Participant(id=1, name="Серик", role="Руководитель совещания"),
        Participant(id=2, name="Дана", role="Юрист"),
        Participant(id=3, name="Айбек", role="Финансист"),
    ]
    meeting_date = date(2026, 9, 23)
    result = process("unused.wav", meeting_date, participants, ["Финансы", "Юридическое", "ИТ"])
    detail = {
        **result.model_dump(),
        "id": "demo",
        "title": "Бюджет и запуск нового склада",
        "meeting_date": meeting_date,
        "participants": [p.model_dump() for p in participants],
    }
    settings = get_settings()
    previous_data_dir, previous_organization = settings.data_dir, settings.organization_name
    OUTPUT.mkdir(parents=True, exist_ok=True)
    try:
        with TemporaryDirectory(prefix="hackalem-demo-") as temporary:
            settings.data_dir = Path(temporary)
            settings.organization_name = "Смоделированный пример · вымышленные участники"
            docx = build_docx(detail, "ru")
            pdf = to_pdf(docx)
            shutil.copyfile(docx, OUTPUT / "protocol.docx")
            shutil.copyfile(pdf, OUTPUT / "protocol.pdf")
    finally:
        settings.data_dir, settings.organization_name = previous_data_dir, previous_organization
    print(f"Created {OUTPUT / 'protocol.docx'} and {OUTPUT / 'protocol.pdf'}")


if __name__ == "__main__":
    main()
