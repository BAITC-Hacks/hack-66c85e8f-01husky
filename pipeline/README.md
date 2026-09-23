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

## Локальная транскрипция Whisper

`transcribe_local.py` — самостоятельный CLI для локальной проверки `faster-whisper` на macOS. Он не отправляет аудио в облачные сервисы. При первом запуске модель скачивается один раз в `pipeline/.models/`; затем `--offline` запрещает любые загрузки модели.

### Установка минимального окружения

```bash
cd pipeline
/opt/homebrew/bin/python3.12 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/pip install -r requirements-local.txt
```

### Расшифровка

Поместите запись в `pipeline/recordings/` и выполните:

```bash
.venv/bin/python transcribe_local.py recordings/meeting.m4a
```

Для проверки шала-казахской речи сделайте два прогона и сравните JSON:

```bash
.venv/bin/python transcribe_local.py recordings/meeting.m4a --output recordings/auto.transcript.json
.venv/bin/python transcribe_local.py recordings/meeting.m4a --language ru --output recordings/ru.transcript.json
```

После первой загрузки модели используйте строго локальный режим:

```bash
.venv/bin/python transcribe_local.py recordings/meeting.m4a --offline
```

По умолчанию используется `large-v3-turbo` в CPU-режиме `int8`, подходящий для русско-казахской речи на Apple Silicon. Для быстрой проверки можно указать `--model small`, но качество смешанной речи будет ниже.
