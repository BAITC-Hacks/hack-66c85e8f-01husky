# pipeline

Чистая библиотека: аудио → `MeetingResult`. Контракт: `pipeline/models.py` (спека, раздел 5).

```bash
cd pipeline
uv sync                      # только контракт + pydantic
uv sync --extra ml           # + whisper, pyannote, speechbrain
uv run pytest
PIPELINE_FAKE=1 uv run python -m pipeline.cli sample.wav --date 2026-09-23
```

`PIPELINE_FAKE=1` → `fake.py`. Иначе `real.py` (владелец: Ардак).
