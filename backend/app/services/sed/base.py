from pathlib import Path
from typing import Protocol

from app.models import Meeting


class SEDClient(Protocol):
    def push_protocol(self, meeting: Meeting, pdf_path: Path) -> str: ...
