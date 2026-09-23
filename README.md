# Автопротокол: ИИ-ассистент протоколирования совещаний с фиксацией поручений

Хакатон HackAlem AI, команда 01husky. Кейс: «Система автопротоколирования совещаний с фиксацией поручений».

Система принимает запись совещания (файл, live-микрофон в браузере или бот-участник Meet / Zoom / Teams), распознаёт речь на русском, казахском и смешанном языке, различает говорящих, привязывает реплики к участникам, извлекает поручения (ответственный, суть, срок), формирует саммари, экспортирует протокол в DOCX / PDF, ведёт дашборд поручений и напоминает о сроках. Все ИИ-компоненты работают локально (on-premise), облачные провайдеры включаются флагом только для разработки.

Полная проектная спецификация: [docs/superpowers/specs/2026-09-23-meeting-protocol-design.md](docs/superpowers/specs/2026-09-23-meeting-protocol-design.md).

## Содержание

- [Что умеет](#что-умеет)
- [Архитектура](#архитектура)
- [Стек](#стек)
- [Быстрый старт (Docker)](#быстрый-старт-docker)
- [Запуск без Docker (разработка)](#запуск-без-docker-разработка)
- [Сценарий демо](#сценарий-демо)
- [Проверка бэкенда через curl](#проверка-бэкенда-через-curl)
- [API](#api)
- [On-premise и приватность](#on-premise-и-приватность)
- [Тесты](#тесты)
- [Структура репозитория](#структура-репозитория)
- [Ограничения и roadmap](#ограничения-и-roadmap)

## Что умеет

Обязательный минимум кейса:

| Требование | Реализация |
|---|---|
| Распознавание речи | `pipeline/stt/`: faster-whisper large-v3-turbo локально (`STT_BACKEND=local`) |
| Русский, казахский, шала-казахский | whisper с автоопределением языка, у каждого сегмента метка `ru / kk / mixed`, статистика языков по совещанию |
| Диаризация и привязка к человеку | pyannote.audio 3.1 → `SPEAKER_XX`; привязка к участнику по голосовому эталону (ECAPA-эмбеддинг), по контексту обращений (LLM) и вручную в UI |
| Поручения с ответственным и сроком | агент извлечения (`pipeline/extract.py`): кандидаты → проверка дословной цитатой → нормализация срока в дату → резолв ответственного → срочность и направление |
| Саммари | `pipeline/summary.py`: тема, решения, поручения, открытые вопросы, на русском или казахском |
| Экспорт DOCX / PDF | `backend/app/services/export.py`: python-docx + LibreOffice headless |

Дополнительно:

| Пункт | Реализация |
|---|---|
| Дашборд статусов поручений | `/tasks`, `/tasks/stats`; статусы черновик → подтверждено → в работе → выполнено, просрочено ставится автоматически |
| Напоминания руководителю и ответственному | Celery beat раз в час: `due_soon` за 24 ч, `overdue` после срока (`backend/app/tasks/reminders.py`) |
| Рассылка выдержки из протокола | при подтверждении протокола каждый ответственный получает in-app уведомления `assigned` и `protocol_ready` |
| Классификация поручений | `urgency` (low / normal / high / critical) и `direction` из справочника, который админ правит в UI |
| Голосовая идентификация по тембру | `POST /participants/{id}/voiceprint`: 10-секундный эталон → эмбеддинг → авто-подпись спикеров на следующих совещаниях |
| Интеграция с СЭД | интерфейс `SEDClient` + `MockSED`: `POST /meetings/{id}/sed` кладёт PDF и `meta.json` в `backend/outbox/` и возвращает регистрационный номер |
| On-premise | `docker-compose.yml`: api, worker, beat, postgres, redis, ollama. Ни одного внешнего вызова при значениях по умолчанию |
| Вход из Meet / Zoom / Teams | `POST /meetings/bot` → Playwright-бот (`bots/`) заходит в звонок, пишет аудио и загружает через `POST /meetings/{id}/audio` |

## Архитектура

```
 браузер (Next.js)            бот-участник (Playwright)
   │ файл / live WS               │ запись звонка
   ▼                              ▼
 ┌──────────────────────── FastAPI  api ────────────────────────┐
 │ auth · meetings · tasks · participants · notifications · export│
 └───────────────┬───────────────────────────────┬───────────────┘
                 │ Celery (Redis)                │ SQLAlchemy
                 ▼                               ▼
 ┌──────── worker ────────┐              ┌── PostgreSQL ──┐
 │ pipeline.process()     │              │ users          │
 │  stt → diarize →       │              │ participants   │
 │  voiceprint → extract →│─── result ──▶│ meetings       │
 │  summary → privacy     │              │ segments       │
 └──────────┬─────────────┘              │ speaker_map    │
            │ LLM (Ollama, локально)      │ tasks          │
            ▼                            │ notifications  │
        qwen3:14b                        └────────────────┘
                 ┌──── beat ────┐
                 │ check_deadlines каждый час → due_soon / overdue │
                 └──────────────┘
```

Поток данных: запись → `data/audio/<id>/audio.wav` (ffmpeg, 16 kHz mono) → Celery `process_meeting` → `pipeline.process()` возвращает `MeetingResult` (контракт в `pipeline/pipeline/models.py`) → сегменты, карта спикеров, поручения-черновики и саммари в БД → секретарь правит спикеров и поручения → «Подтвердить протокол» → уведомления ответственным, экспорт DOCX / PDF, отправка в СЭД → beat следит за сроками.

Границы модулей:

- `pipeline/` — чистая библиотека без веба и БД. Одна функция `process(audio_path, meeting_date, participants, directions, output_language, progress) -> MeetingResult`. `PIPELINE_FAKE=1` подменяет её детерминированной заглушкой, чтобы бэкенд и фронт работали без ML-моделей.
- `backend/` — FastAPI + Celery. Хранит, раздаёт, экспортирует, уведомляет. Пайплайн вызывает как библиотеку.
- `frontend/` — Next.js, ходит только в REST API.
- `bots/` — отдельный процесс, общается с бэком через `POST /meetings/{id}/audio` с токеном `BOT_API_TOKEN`.

## Стек

| Слой | Технологии |
|---|---|
| Пайплайн | Python 3.12, faster-whisper, pyannote.audio 3.1, speechbrain (ECAPA), Ollama (Qwen3), pydantic v2 |
| Бэкенд | FastAPI, SQLAlchemy 2, Alembic, PostgreSQL 16, Celery 5 + Redis, python-docx, LibreOffice, ffmpeg |
| Фронтенд | Next.js 15 (App Router), React 19, TypeScript, Tailwind v4, next-intl (ru / kk) |
| Бот | Playwright (Chromium), ffmpeg |
| Инфра | Docker Compose, uv, pnpm |

## Быстрый старт (Docker)

Требования: Docker с Compose v2, 16 ГБ ОЗУ для Ollama с `qwen3:14b` (или поменяйте `LLM_MODEL=qwen3:8b`).

```bash
cp .env.example .env
docker compose up -d --build
```

Сервис `api` при старте сам применяет миграции (`alembic upgrade head`) и заполняет справочники и демо-участников (`app.seed`, идемпотентно); `worker` и `beat` ждут его healthcheck.

Дальше:

- API и Swagger: http://localhost:8000/docs
- Фронтенд: http://localhost:3000 → `/ru/meetings` (см. `frontend/README.md`)
- Учётная запись: `admin@example.com` / `admin123`

По умолчанию `PIPELINE_FAKE=1`: обработка мгновенная, результат детерминированный, ML-модели не нужны. Для реального распознавания:

```bash
# один раз: скачать LLM внутрь контейнера ollama
docker compose exec ollama ollama pull qwen3:14b
# в .env
PIPELINE_FAKE=0
HF_TOKEN=hf_...          # нужен для загрузки весов pyannote (лицензия принимается на huggingface.co)
docker compose restart api worker
```

Первый запуск пайплайна скачивает веса whisper и pyannote в volume контейнера, дальше работает без сети.

## Запуск без Docker (разработка)

Нужны: Python 3.12, [uv](https://docs.astral.sh/uv/), PostgreSQL 16, Redis, ffmpeg, LibreOffice (для PDF).

```bash
# база
createuser -P protocol        # пароль protocol
createdb -O protocol protocol
createdb -O protocol protocol_test

# бэкенд
cp .env.example .env
# в .env для локального запуска замените хосты:
#   DATABASE_URL=postgresql+psycopg://protocol:protocol@localhost:5432/protocol
#   REDIS_URL=redis://localhost:6379/0
#   OLLAMA_URL=http://localhost:11434
#   DATA_DIR и OUTBOX_DIR удалите (возьмутся значения по умолчанию внутри backend/)
cd backend
uv sync
uv run alembic upgrade head
uv run python -m app.seed
uv run uvicorn app.main:app --reload --port 8000
```

В соседних терминалах:

```bash
cd backend && uv run celery -A app.tasks.celery_app:celery_app worker --loglevel=info
```

```bash
cd backend && uv run celery -A app.tasks.celery_app:celery_app beat --loglevel=info
```

Без Redis и worker'а можно гонять обработку прямо в процессе API: `CELERY_EAGER=1 uv run uvicorn app.main:app`.

Пайплайн отдельно, на любой записи (файл лежит вне репозитория):

```bash
cd pipeline
uv sync --extra ml
uv run python -m pipeline.cli /path/to/meeting.mp3 --date 2026-09-23 --participants participants.json
```

## Сценарий демо

1. Войти как `admin@example.com / admin123`.
2. Участники → у каждого записать 10-секундный голосовой эталон (кнопка «Записать эталон»).
3. Новое совещание → вкладка «Загрузить файл» → выбрать запись, дату, участников → «Создать». Баннер о записи и транскрибации ИИ показывается участникам.
4. Страница совещания: статус «Обработка» с прогрессом по этапам (stt → diarize → voiceprint → extract → summary). Через минуту-две: транскрипт по спикерам с языком каждой реплики, карта «SPEAKER_00 = Асхат Ерланович (по тембру, 0.92)», саммари, таблица поручений-черновиков с цитатой из транскрипта и уверенностью.
5. Секретарь правит спикера у одной реплики, срок у одного поручения, жмёт «Подтвердить протокол».
6. У ответственных в колокольчике появляются «Новое поручение» и «Протокол готов».
7. «Скачать DOCX» / «Скачать PDF»: протокол с шапкой, участниками, саммари, таблицей поручений и полным транскриптом приложением.
8. «Отправить в СЭД»: показывается регистрационный номер вида `SED-2026-000001`, файл лежит в `backend/outbox/<id>/`.
9. Дашборд поручений: фильтры по статусу / ответственному / направлению / срочности, счётчики «в работе / просрочено / выполнено / скоро срок», ответственный переводит своё поручение в «в работе» и «выполнено».
10. Просрочка: `docker compose exec api uv run python -c "from app.tasks.reminders import check_deadlines; print(check_deadlines())"` с датами в прошлом → уведомления `overdue` руководителю и ответственному, статус «просрочено».
11. Вкладка «Записать»: live-запись с микрофона в браузере, по «Стоп» та же обработка.
12. Вкладка «Подключить бота»: ссылка на Google Meet → бот заходит в звонок, по окончании запись попадает в обработку.

## Проверка бэкенда через curl

Полный сценарий без фронта, на `PIPELINE_FAKE=1`. Тот же сценарий автоматизирован в `backend/scripts/smoke_backend.py` (поднимает изолированный uvicorn на отдельной схеме PostgreSQL и прогоняет всё через curl).

```bash
API=http://localhost:8000/api/v1
curl -s $API/health

# тестовое аудио: любой файл или сгенерированный тон
ffmpeg -y -f lavfi -i "sine=frequency=440:duration=5" -ac 1 -ar 16000 sample.wav

# логин, cookie в файл
curl -s -c c.txt -X POST $API/auth/login -H 'Content-Type: application/json' \
  -d '{"email":"admin@example.com","password":"admin123"}'

# участники и направления из seed
curl -s -b c.txt $API/participants | python3 -m json.tool | head -30
curl -s -b c.txt $API/directions

# голосовой эталон первому участнику
PID=$(curl -s -b c.txt $API/participants | python3 -c 'import json,sys; print(json.load(sys.stdin)[0]["id"])')
curl -s -b c.txt -X POST $API/participants/$PID/voiceprint -F "file=@sample.wav"

# совещание из файла (PIPELINE_FAKE=1 обрабатывает мгновенно, иначе смотрите status/progress_pct)
MID=$(curl -s -b c.txt -X POST $API/meetings \
  -F title="Оперативное совещание" -F meeting_date=2026-09-23 \
  -F participant_ids=$PID -F "file=@sample.wav" | python3 -c 'import json,sys; print(json.load(sys.stdin)["id"])')
curl -s -b c.txt $API/meetings/$MID | python3 -m json.tool

# поправить спикера, подтвердить протокол
curl -s -b c.txt -X PUT $API/meetings/$MID/speakers -H 'Content-Type: application/json' \
  -d "[{\"speaker\":\"SPEAKER_00\",\"participant_id\":$PID}]"
curl -s -b c.txt -X POST $API/meetings/$MID/confirm

# экспорт и СЭД
curl -s -b c.txt "$API/meetings/$MID/export?format=docx&lang=ru" -o protocol.docx
curl -s -b c.txt "$API/meetings/$MID/export?format=pdf&lang=kk" -o protocol.pdf
curl -s -b c.txt -X POST $API/meetings/$MID/sed

# дашборд и статусы
curl -s -b c.txt "$API/tasks?status=confirmed"
curl -s -b c.txt $API/tasks/stats
TID=$(curl -s -b c.txt "$API/tasks?meeting_id=$MID" | python3 -c 'import json,sys; print(json.load(sys.stdin)[0]["id"])')
curl -s -b c.txt -X PATCH $API/tasks/$TID -H 'Content-Type: application/json' -d '{"status":"in_progress"}'

# уведомления
curl -s -b c.txt $API/notifications
curl -s -b c.txt $API/notifications/unread-count

# live-запись: создать совещание, дальше браузер шлёт бинарные чанки в ws://localhost:8000/api/v1/meetings/{id}/live
curl -s -b c.txt -X POST $API/meetings/live -H 'Content-Type: application/json' \
  -d "{\"title\":\"Live\",\"meeting_date\":\"2026-09-23\",\"participant_ids\":[$PID]}"

# бот (без пакета bots/ совещание получит статус failed с понятной ошибкой)
curl -s -b c.txt -X POST $API/meetings/bot -H 'Content-Type: application/json' \
  -d "{\"title\":\"Meet\",\"meeting_date\":\"2026-09-23\",\"platform\":\"meet\",\"url\":\"https://meet.google.com/abc-defg-hij\",\"participant_ids\":[$PID]}"
```

## API

Префикс `/api/v1`, схема в http://localhost:8000/docs. Аутентификация: JWT в httpOnly cookie `access_token`. Роли `user` и `admin`. Совещание может создать любой залогиненный; создатель и админ редактируют, участники видят. Ответственный меняет статус своего поручения.

| Группа | Эндпоинты |
|---|---|
| auth | `POST /auth/register`, `POST /auth/login`, `POST /auth/logout`, `GET /auth/me` |
| participants | `GET/POST /participants`, `PATCH/DELETE /participants/{id}`, `POST/DELETE /participants/{id}/voiceprint` |
| directions | `GET /directions`, `POST /directions`, `PATCH /directions/{id}` (admin) |
| meetings | `POST /meetings` (multipart), `POST /meetings/live`, `WS /meetings/{id}/live`, `POST /meetings/bot`, `POST /meetings/{id}/audio`, `GET /meetings`, `GET /meetings/{id}`, `PATCH /meetings/{id}`, `PUT /meetings/{id}/speakers`, `POST /meetings/{id}/confirm`, `POST /meetings/{id}/reprocess`, `GET /meetings/{id}/export?format=docx\|pdf&lang=ru\|kk`, `POST /meetings/{id}/sed`, `DELETE /meetings/{id}/audio`, `DELETE /meetings/{id}` |
| tasks | `GET /tasks?status=&assignee_id=&direction_id=&urgency=&meeting_id=&mine=1`, `GET /tasks/stats`, `POST /tasks`, `PATCH /tasks/{id}`, `DELETE /tasks/{id}` |
| notifications | `GET /notifications?unread=1`, `GET /notifications/unread-count`, `POST /notifications/{id}/read`, `POST /notifications/read-all` |

Гость: секретарь добавляет участника по имени и email до того, как у того есть аккаунт. Поручения ставятся на участника. Когда человек регистрируется с тем же email, участник и все его поручения привязываются к аккаунту автоматически.

Жизненный цикл поручения: `draft` (после пайплайна) → `confirmed` (подтверждение протокола) → `in_progress` → `done`. `overdue` ставит beat, если срок прошёл; из `overdue` можно в `in_progress` или `done`.

## On-premise и приватность

Кейс запрещает передавать аудио и текст во внешние облачные API. Как это соблюдается:

- **Значения по умолчанию локальные.** `.env.example` и `docker-compose.yml`: `STT_BACKEND=local` (faster-whisper + pyannote в worker), `LLM_PROVIDER=ollama` (Qwen3 в контейнере `ollama`). При этих значениях контейнеры не открывают ни одного соединения наружу после первой загрузки весов.
- **Провайдеры за интерфейсом.** `pipeline/stt/base.py` и `pipeline/llm/base.py`. Реализации `openai` и `nvidia` существуют для ускорения разработки и помечены как dev-only; в закрытом контуре они не включаются. NVIDIA NIM разворачивается on-prem как контейнер, код при этом не меняется.
- **Аудио живёт только в `backend/data/audio/`.** Есть `DELETE /meetings/{id}/audio`: после подтверждения протокола запись удаляется, транскрипт и поручения остаются.
- **Маскирование.** `pipeline/privacy.py` закрывает телефоны и ИИН в транскрипте до сохранения в БД.
- **Секреты** только в `.env` (в `.gitignore`). `SECRET_KEY` и `BOT_API_TOKEN` обязательно сменить перед развёртыванием.
- **Без телеметрии.** Ни PostHog, ни Sentry, ни внешних CDN в контейнерах.

Тестовые записи в `samples/` не входят в репозиторий: реальные совещания, для показа используются в анонимизированном виде.

## Тесты

```bash
cd pipeline && uv run pytest          # контракт и fake-пайплайн
cd backend && uv run pytest           # API, Celery-задачи, напоминания, экспорт (нужен Postgres protocol_test, ffmpeg, soffice)
cd backend && uv run ruff check . && uv run ruff format --check .
cd backend && uv run python scripts/smoke_backend.py   # end-to-end через реальный HTTP и curl
cd bots && uv run pytest              # контракт CLI и жизненный цикл бота
cd frontend && pnpm typecheck && pnpm lint && pnpm build
```

Тесты бэкенда используют `PIPELINE_FAKE=1` и `CELERY_EAGER=1`: пайплайн подменяется детерминированной заглушкой, Celery-задачи выполняются в процессе без Redis.

## Статус реализации

Честная карта того, что работает сегодня и что в работе:

| Компонент | Состояние |
|---|---|
| Бэкенд: auth, участники, совещания (файл / live / бот), поручения, уведомления, напоминания, экспорт DOCX / PDF, СЭД-mock | готово, покрыто тестами и end-to-end smoke |
| Контракт пайплайна и `PIPELINE_FAKE` | готово; бэкенд и фронт работают на детерминированной заглушке |
| Реальный пайплайн (`pipeline/real.py`: whisper, pyannote, voiceprint, LLM-агент, саммари, privacy) | в работе; до его появления `pipeline.cli` без `PIPELINE_FAKE=1` завершается `NotImplementedError` |
| Фронтенд | каркас, i18n, типизированный API-клиент и логин готовы; экраны совещаний, дашборда и участников в работе |
| Бот Meet / Zoom / Teams | жизненный цикл, запись, загрузка и CLI-контракт готовы; адаптеры селекторов web-клиентов в работе |
| Docker Compose | описан и собирается; на машине разработки проверялся локальный запуск без Docker |

## Структура репозитория

```
frontend/      Next.js-приложение (владелец: Эмир)
backend/       FastAPI, Celery, Alembic, экспорт, СЭД-адаптер (владелец: Никита)
  app/routers/     auth, participants, directions, meetings, tasks, notifications, exports
  app/services/    audio, access, speakers, notify, export, sed/
  app/tasks/       celery_app, process_meeting, reminders, run_bot
  alembic/         миграции
  tests/
pipeline/      ML-пайплайн как библиотека (владелец: Ардак)
  pipeline/models.py   контракт MeetingResult
  pipeline/fake.py     детерминированная заглушка (PIPELINE_FAKE=1)
  pipeline/real.py     реальная реализация: stt/, diarize, voiceprint, extract, summary, privacy
  pipeline/cli.py      python -m pipeline.cli <audio> --date ...
bots/          Playwright-бот для Meet / Zoom / Teams (владелец: Ардак)
docs/superpowers/specs/   проектная спецификация
docker-compose.yml, .env.example, backend/Dockerfile
```

Рабочий процесс: ветки `feat/<task>` от `develop`, PR в `develop`, после интеграционного теста PR `develop → main`.

## Ограничения и roadmap

Сделано как прототип:

- СЭД: mock-адаптер с контрактом `SEDClient.push_protocol()`. Реальный адаптер под конкретную СЭД (Documentolog, Directum) пишется по этому интерфейсу.
- Бот-участник: web-клиенты через Playwright. Официальные SDK Zoom / Teams требуют регистрации приложений и не входят в прототип.
- Live-транскрипт появляется после кнопки «Стоп», не в реальном времени.
- Уведомления in-app. Интерфейс `Notifier` позволяет добавить email / Telegram.

Развитие:

- Стриминговое распознавание по ходу совещания.
- Дообучение whisper на казахских корпусах (ISSAI KSC2) для шала-казахского.
- Голосовая идентификация без эталона: кластеризация по совещаниям организации.
- Контроль исполнения: эскалация руководителю при повторной просрочке, отчёт по исполнительской дисциплине.
- Интеграция с календарём: автозапуск бота по расписанию встречи.
