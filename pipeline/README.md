# Локальная транскрипция Whisper

Этот набор запускает `faster-whisper` локально на Mac. Аудиофайлы не передаются в облачные сервисы. При первом запуске модель скачивается один раз в `pipeline/.models/`; далее можно использовать режим `--offline`, который полностью запрещает сетевое получение модели.

## Установка

```bash
cd /Users/ardak/Desktop/HackAlem/pipeline
/opt/homebrew/bin/python3.12 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/pip install -r requirements-local.txt
```

## Расшифровка

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
