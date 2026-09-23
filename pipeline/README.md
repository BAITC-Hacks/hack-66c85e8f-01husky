# pipeline

Чистая библиотека: аудио → `MeetingResult`. Контракт: `pipeline/models.py` (спека, раздел 5).

```bash
cd pipeline
uv sync                      # контракт + настройки
uv sync --extra stt          # + локальный Whisper и sherpa-onnx
uv sync --extra ml           # + whisper, pyannote, speechbrain
uv run pytest
PIPELINE_FAKE=1 uv run python -m pipeline.cli sample.wav --date 2026-09-23
```

`PIPELINE_FAKE=1` → `fake.py`. Иначе `real.py` (владелец: Ардак).

## Локальная транскрипция Whisper

`transcribe_local.py` и backend используют общий провайдер `pipeline/stt/local_whisper.py`. Аудио не отправляется в облако. Транскрипция всегда offline: веса должны быть подготовлены заранее, иначе будет ошибка. `--offline` оставлен для совместимости.

При `PIPELINE_FAKE=0` работают STT и локальная акустическая диаризация: метки `speaker1`, `speaker2`, …, слова распределяются по голосам. Поручения, саммари и voiceprint-идентификация пока не реализованы; имена не угадываются, `speaker_map.participant_id=null`. Общий язык файла не считается языком каждой реплики; сегменты пока имеют `lang=other`.

### Установка минимального окружения

```bash
cd pipeline
/opt/homebrew/bin/python3.12 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/pip install -r requirements-local.txt
# Отдельная подготовка с доступом в интернет, без аудио/текста:
HF_HUB_OFFLINE=0 .venv/bin/python -m pipeline.download_model
.venv/bin/python -m pipeline.download_diarization_models
```

### Расшифровка

Поместите запись в `pipeline/recordings/` и выполните:

```bash
.venv/bin/python transcribe_local.py recordings/meeting.m4a
# Текст + разделение по голосам (полный MeetingResult):
PIPELINE_FAKE=0 .venv/bin/python -m pipeline.cli recordings/meeting.m4a --date 2026-09-23
```

Для проверки шала-казахской речи сделайте два прогона и сравните JSON:

```bash
.venv/bin/python transcribe_local.py recordings/meeting.m4a --output recordings/auto.transcript.json
.venv/bin/python transcribe_local.py recordings/meeting.m4a --language ru --output recordings/ru.transcript.json
```

Режим всегда строго локальный, в том числе с прежним флагом:

```bash
.venv/bin/python transcribe_local.py recordings/meeting.m4a --offline
```

По умолчанию используется `large-v3-turbo` в CPU-режиме `int8`. Качество русского, казахского и смешанной речи нужно оценить на размеченных записях, сравнив auto/ru/kk. Другую модель необходимо сначала отдельно скачать.

Настройки из корневого `.env` и окружения: `STT_MODEL`, `STT_MODEL_DIR` (по умолчанию `pipeline/.models`), `STT_LANGUAGE=auto|ru|kk`, `STT_DEVICE=cpu`, `STT_COMPUTE_TYPE=int8`, `STT_CPU_THREADS=4`. `STT_BACKEND` допускает только `local`.

В JSON сохраняются текст и таймкоды; цифровые шаблоны телефонов и ИИН маскируются. Это не полная анонимизация. Сырые word-level тексты не экспортируются. Записи и кеш весов не входят в Git.

[Запуск с PostgreSQL, Redis, Celery и API](../docs/local-development.md).

[Модели, настройки и ограничения диаризации](../docs/local-diarization.md).
`transcribe_local.py` остаётся STT-only утилитой сравнения языков; backend и `pipeline.cli`
вызывают полный процесс с разделением по голосам. Веса не скачиваются во время обработки.
