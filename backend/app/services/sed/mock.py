"""Filesystem SED adapter with a process-safe sequence and retry-stable references."""

import fcntl
import json
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from app.config import get_settings
from app.models import Meeting


def _write_atomic(path: Path, content: bytes) -> None:
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as tmp:
        temporary = Path(tmp.name)
        try:
            tmp.write(content)
            tmp.flush()
            temporary.replace(path)
        finally:
            temporary.unlink(missing_ok=True)


class MockSED:
    def __init__(self, outbox: Path | None = None) -> None:
        self.outbox = outbox if outbox is not None else get_settings().outbox_dir

    def push_protocol(self, meeting: Meeting, pdf_path: Path) -> str:
        payload = pdf_path.read_bytes()
        if not payload.startswith(b"%PDF-"):
            raise ValueError("SED requires a PDF document")
        self.outbox.mkdir(parents=True, exist_ok=True)
        with (self.outbox / ".sed.lock").open("a+b") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            directory = self.outbox / str(int(meeting.id))
            directory.mkdir(exist_ok=True)
            metadata_path = directory / "meta.json"
            now = datetime.now(UTC)
            if metadata_path.exists():
                reference = json.loads(metadata_path.read_text())["sed_ref"]
            else:
                counter_path = self.outbox / ".sequence"
                number = int(counter_path.read_text()) + 1 if counter_path.exists() else 1
                _write_atomic(counter_path, str(number).encode())
                reference = f"SED-{now.year}-{number:06d}"
            metadata = {
                "sed_ref": reference,
                "meeting_id": meeting.id,
                "title": meeting.title,
                "meeting_date": meeting.meeting_date.isoformat(),
                "output_language": meeting.output_language,
                "exported_at": now.isoformat(),
            }
            _write_atomic(directory / "protocol.pdf", payload)
            _write_atomic(
                metadata_path,
                json.dumps(metadata, ensure_ascii=False, indent=2).encode("utf-8"),
            )
            return reference
