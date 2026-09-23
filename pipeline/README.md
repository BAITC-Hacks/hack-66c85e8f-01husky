# Kenes AI: pipeline

Библиотека без веб-сервера и БД: аудиозапись → `MeetingResult` (сегменты, карта спикеров, поручения, саммари). Backend вызывает одну функцию:

```python
process(audio_path, meeting_date, participants, directions, output_language, progress) -> MeetingResult
```

Контракт описан в [`pipeline/models.py`](pipeline/models.py) и в разделе 5 [спецификации](../docs/superpowers/specs/2026-09-23-meeting-protocol-design.md). Все модели работают локально, аудио и текст не покидают машину.

[Главный README](../README.md) · [Локальный запуск с API](../docs/local-development.md) · [Диаризация](../docs/local-diarization.md)

## Этапы

| Этап | Реализация | Статус |
|---|---|---|
| Распознавание речи | faster-whisper `large-v3-turbo`, CPU int8, строго offline | ✅ работает |
| Диаризация | sherpa-onnx: pyannote segmentation 3.0 + NeMo TitaNet-large, слова распределяются по голосам | ✅ работает, метки `speaker1`, `speaker2`, … |
| Маскирование | Шаблоны телефонов и ИИН в тексте | ✅ работает |
| Язык каждой реплики | Разметка `ru` / `kk` / `mixed` | 🔜 сейчас `lang=other` |
| Поручения и саммари | Локальная LLM (Qwen3 через Ollama) | 🔜 в fake-режиме |
| Узнавание по голосу | Сравнение с голосовым эталоном участника | 🔜 в fake-режиме |

`PIPELINE_FAKE=1` подключает [`fake.py`](pipeline/fake.py): детерминированный результат с поручениями и саммари, чтобы backend и frontend работали без моделей. `PIPELINE_FAKE=0` подключает [`real.py`](pipeline/real.py). Имена участников реальный режим не угадывает: `speaker_map.participant_id=null`, привязку делает секретарь.

## Быстрый старт

```bash
cd pipeline
uv sync                      # только контракт и настройки
uv sync --extra stt          # + faster-whisper и sherpa-onnx
uv run pytest
PIPELINE_FAKE=1 uv run python -m pipeline.cli sample.wav --date 2026-09-23
```

## Локальная транскрипция Whisper

`transcribe_local.py` и backend используют общий провайдер `pipeline/stt/local_whisper.py`. Аудио не отправляется в облако. Транскрипция всегда offline: веса должны быть подготовлены заранее, иначе будет ошибка. `--offline` оставлен для совместимости.

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

`transcribe_local.py` — утилита только для STT, чтобы сравнивать языковые режимы. Backend и `pipeline.cli` запускают полный процесс с разделением по голосам. Во время обработки веса не скачиваются.
