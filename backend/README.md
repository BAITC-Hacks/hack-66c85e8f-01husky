# Kenes AI: backend

REST API и фоновые задачи Kenes AI. Сервис принимает записи совещаний, передаёт их в [пайплайн](../pipeline/README.md), хранит транскрипт и поручения, формирует протокол DOCX/PDF, отправляет его в СЭД и напоминает исполнителям о сроках.

[Главный README](../README.md) · [Спецификация API](../docs/superpowers/specs/2026-09-23-meeting-protocol-design.md) · Swagger: <http://localhost:8000/docs>

## Возможности

| Область | Что делает |
|---|---|
| Приём записи | Загрузка файла (multipart), live-запись по WebSocket, бот-участник через отдельную очередь `bots`. ffmpeg приводит аудио к WAV 16 kHz mono |
| Обработка | Celery-задача `process_meeting` вызывает `pipeline.process()`, сохраняет прогресс по этапам и результат `MeetingResult` |
| Проверка секретарём | Правка карты спикеров, поручений, сроков; подтверждение протокола и повторная обработка |
| Поручения | Статусы `draft → confirmed → in_progress → done`, `overdue`; фильтры и статистика для дашборда |
| Напоминания | Celery beat раз в час запускает `check_deadlines`, создаёт уведомления `due_soon` и `overdue` |
| Экспорт | DOCX через python-docx, PDF через LibreOffice; протокол на русском или казахском |
| СЭД | Интерфейс `SEDClient.push_protocol(meeting, pdf_path) -> sed_ref`; `MockSED` пишет `outbox/<id>/` и возвращает номер `SED-2026-…` |
| Доступ | JWT в httpOnly cookie, роли `user` / `admin`, гостевые участники с автоматической привязкой при регистрации |
| Безопасность бота | Callback принимает только временный токен конкретной встречи; повторная загрузка отклоняется с 409 |
| Админка | Просмотр таблиц БД на <http://localhost:8000/admin>, только чтение |

## Запуск

Нужны Python 3.12, [uv](https://docs.astral.sh/uv/), PostgreSQL 16, Redis, ffmpeg и LibreOffice (для PDF).

```bash
cp ../.env.example ../.env     # один раз; для запуска вне Docker замените хосты на localhost
uv sync
uv run alembic upgrade head
uv run python -m app.seed      # admin@example.com / admin123, участники, направления
uv run uvicorn app.main:app --reload --port 8000
```

Фоновые процессы, каждый в своём терминале:

```bash
uv run celery -A app.tasks.celery_app:celery_app worker -l info
uv run celery -A app.tasks.celery_app:celery_app beat -l info
```

Без Redis и worker задачи выполняются в процессе API: `CELERY_EAGER=1 uv run uvicorn app.main:app`.

`PIPELINE_FAKE=1` (значение по умолчанию) подключает детерминированную заглушку вместо ML-моделей. Для настоящего Whisper и диаризации используйте [инструкцию локального запуска](../docs/local-development.md).

## Тесты

```bash
uv run pytest                                  # нужна БД protocol_test, ffmpeg и soffice
uv run ruff check . && uv run ruff format --check .
uv run python scripts/smoke_backend.py         # end-to-end сценарий через настоящий HTTP
```

Тесты выполняются с `PIPELINE_FAKE=1` и `CELERY_EAGER=1`. Они покрывают авторизацию, права доступа, жизненный цикл совещания и поручений, напоминания, уведомления, экспорт, ошибки обработки и безопасность callback бота.

`scripts/build_demo_protocol.py` пересобирает [демонстрационный протокол](../docs/demo/README.md) без БД и моделей.

## Структура

```
app/
  main.py          приложение FastAPI, подключение роутеров
  config.py        настройки из .env
  models/          SQLAlchemy: user, participant, meeting, task, notification, direction
  schemas/         pydantic-схемы запросов и ответов
  routers/         auth, participants, directions, meetings, tasks, notifications, exports, admin
  services/        audio (ffmpeg), processing, speakers, access, notify, export, bot_tokens, sed/
  tasks/           celery_app, process_meeting, reminders, run_bot
  admin_assets/    статическая админ-панель
alembic/           миграции
scripts/           smoke_backend.py, build_demo_protocol.py
tests/
```
