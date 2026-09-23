# Автопротокол

**Протокол совещания на русском и казахском: кто делает, что и к какому сроку.**

HackAlem AI · команда 01husky · кейс «Система автопротоколирования совещаний с фиксацией поручений».

Секретарь проверяет поручения по исходным репликам, уточняет ответственных и утверждает протокол. Исполнители получают задачи, руководитель отслеживает сроки. Для закрытого контура проект предусматривает локальную обработку аудио и текста.

[Посмотреть PDF](docs/demo/protocol.pdf) · [Скачать DOCX](docs/demo/protocol.docx) · [Сценарий защиты](#сценарий-демо) · [Запустить backend](#запуск-без-docker-разработка)

## Демо за минуту чтения

**Смоделированное совещание, 23 сентября 2026 года.** Команда обсуждает бюджет и запуск склада. В одной реплике участники переключаются между русским и казахским:

> **[00:14] Серик:** «Айбек, подготовь обновлённую смету по складу до пятницы. Керек болса, Данамен бірге отырыңдар.»
>
> **[00:22] Айбек:** «Жақсы, пятницаға дейін жасаймын. Данамен бүгін кездесемін.»

Секретарь получает черновик с поручениями и основаниями для проверки:

| Фрагмент реплики | Поручение | Ответственный | Дата |
|---|---|---|---|
| «подготовь обновлённую смету по складу до пятницы» | Подготовить смету склада | Айбек | 25.09.2026 |
| «Данамен бүгін кездесемін» | Встретиться с Даной по смете | Айбек | 23.09.2026 |
| «согласуй с юристами договор аренды до конца следующей недели» | Согласовать договор аренды | Дана | 04.10.2026 |
| «передай айтишникам заявку на подключение склада, срок конец месяца» | Передать заявку в ИТ | Айбек | 30.09.2026 |

В демо «конец следующей недели» означает воскресенье, 4 октября. Секретарь может изменить дату перед подтверждением. Каждое поручение хранит цитату и индекс реплики: решение можно сверить с контекстом.

После подтверждения секретарь скачивает протокол, а ответственные получают уведомления. В PDF входят саммари, таблица поручений и приложение с репликами по спикерам.

<a href="docs/demo/protocol.pdf"><img src="docs/demo/protocol-preview.png" alt="Первая страница демонстрационного протокола: саммари и четыре поручения с ответственными и сроками" width="760"></a>

**Источник примера:** детерминированная [фикстура pipeline.fake](pipeline/pipeline/fake.py), вымышленные участники. DOCX/PDF выше созданы рабочим сервисом экспорта. Этот пример показывает формат и связь данных; качество распознавания речи и определения спикеров предстоит измерить на реальных моделях. [Воспроизвести образец и подготовить запись](docs/demo/README.md).

## Содержание

- [Демо за минуту чтения](#демо-за-минуту-чтения)
- [Что умеет](#что-умеет)
- [Статус реализации](#статус-реализации)
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

Сопоставление с ТЗ и текущим состоянием ветки `feat/pipeline`:

| Требование | Что показать | Готовность |
|---|---|---|
| Русская, казахская и смешанная речь | Реальный локальный Whisper через API | STT подключён; качество RU/KK/mixed ещё нужно оценить |
| Диаризация и привязка поручения к человеку | Спикер, участник и ответственный за поручение | Контракт и ручная правка через API готовы; модели в работе |
| Поручения с ответственным и сроком | Цитата → суть → человек → календарная дата | Хранение и редактирование готовы; извлечение проверено на fake |
| Саммари | Тема, решения, поручения, открытые вопросы | Backend принимает и экспортирует; генерация моделью в работе |
| Экспорт PDF/DOCX | Открыть файлы из демо выше | Проверен с LibreOffice |
| Статусы и напоминания | Подтверждение → уведомление → выполнение; отдельный пример просрочки | API и логика напоминаний покрыты тестами; интерфейс в работе |
| Срочность и направление | Поля поручения и фильтры `/tasks` | Backend готов; реальная классификация зависит от пайплайна |
| Голосовая идентификация | Привязка участника по голосовому эталону | API есть; качество модели ещё не проверено |
| СЭД | PDF и регистрационный номер | Работает MockSED, интеграция с конкретной СЭД вне обязательной части |
| Закрытый контур | Локальные модели и развёртывание Compose | Конфигурация есть; контейнерный прогон и проверка сетевой изоляции впереди |
| Meet / Zoom / Teams | Запись встречи через бота | Backend и CLI-контракт есть; адаптеры платформ в работе |

Полная [проектная спецификация](docs/superpowers/specs/2026-09-23-meeting-protocol-design.md) содержит контракты и распределение работ.

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

Схема API для фронта: `GET /openapi.json` на запущенном бэке.

Поток данных: запись → `data/audio/<id>/audio.wav` (ffmpeg, 16 kHz mono) → Celery `process_meeting` → `pipeline.process()` возвращает `MeetingResult` (контракт в `pipeline/pipeline/models.py`) → сегменты, карта спикеров, поручения-черновики и саммари в БД → секретарь правит спикеров и поручения → «Подтвердить протокол» → уведомления ответственным, экспорт DOCX / PDF, отправка в СЭД → beat следит за сроками.

Границы модулей:

- `pipeline/`: чистая библиотека без веба и БД. Одна функция `process(audio_path, meeting_date, participants, directions, output_language, progress) -> MeetingResult`. `PIPELINE_FAKE=1` подменяет её детерминированной заглушкой, чтобы бэкенд и фронт работали без ML-моделей.
- `backend/`: FastAPI + Celery. Хранит, раздаёт, экспортирует, уведомляет. Пайплайн вызывает как библиотеку.
- `frontend/`: Next.js, ходит только в REST API.
- `bots/`: отдельный процесс, общается с бэком через `POST /meetings/{id}/audio` с токеном `BOT_API_TOKEN`.

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
- Фронтенд разрабатывается отдельно; в текущей ветке доступен backend API.
- Учётная запись: `admin@example.com` / `admin123`

По умолчанию Compose использует `PIPELINE_FAKE=1`: результат детерминированный, ML-модели не нужны. Контейнер worker с ML-зависимостями и томом весов ещё предстоит подготовить; простого переключения флага недостаточно. Проверенный запуск настоящего STT сейчас — [локально без Docker](docs/local-development.md).

```bash
# один раз: скачать LLM внутрь контейнера ollama
docker compose exec ollama ollama pull qwen3:14b
```

Способ загрузки и хранения весов whisper/pyannote нужно уточнить при интеграции реального пайплайна. Ollama хранит свои модели в volume `ollama-data`.

## Запуск без Docker (разработка)

Локальная админ-панель для просмотра таблиц БД: <http://localhost:8000/admin>.
Вход под администратором; поиск, фильтры и полный текст записей, без редактирования/удаления.

**Для настоящего Whisper и локальной БД используйте [проверенную инструкцию macOS](docs/local-development.md).** Она поднимает отдельный PostgreSQL/Redis и API на localhost с приватной конфигурацией. Ниже — ручная конфигурация backend с fake-пайплайном; не смешивайте её с автоматически созданным `.env`.

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

**Четыре минуты на защиту.** Это распределение времени выступления; скорость обработки моделью в него не заложена. Основной сюжет: поручение Айбека о смете проходит от исходной фразы до протокола и уведомления.

| Время показа | Действие ведущего | Что видит жюри |
|---|---|---|
| 0:00–0:30 | Прочитать две реплики из примера выше. «В поручении есть человек, срок “до пятницы” и переключение языка». | Исходный смысл, который требуется сохранить |
| 0:30–1:20 | Открыть поручение о смете рядом с цитатой. Показать дату встречи и срок 25 сентября. Затем показать «бүгін» и дату 23 сентября. | Связь поручения с репликой и нормализация сроков |
| 1:20–2:00 | Показать ручную правку ответственного или срока и подтверждение протокола. | Секретарь проверяет черновик перед отправкой исполнителям |
| 2:00–3:00 | Открыть PDF: таблица поручений, затем приложение с репликами. | Документ, который можно передать участникам после встречи |
| 3:00–4:00 | Показать уведомление ответственного и переход поручения в «выполнено». Завершить коротким показом MockSED, если остаётся время. | Продолжение работы с поручением после совещания |

### Режим показа на текущей сборке

- **Образец результата:** открыть PDF/DOCX из этого README. Данные смоделированы, экспорт настоящий. Для первого просмотра ничего устанавливать не требуется.
- **Backend с fake-пайплайном:** пройти [curl-сценарий](#проверка-бэкенда-через-curl) или HTTP smoke. Используется `PIPELINE_FAKE=1`; распознавание, диаризация и извлечение заменены фиксированным результатом. Авторизация, сохранение, правки, подтверждение, уведомления и экспорт выполняются кодом backend. До готовности UI показываем ответы API и файл протокола.
- **Полный показ с аудио:** после интеграции реального пайплайна и frontend загрузить смоделированную запись из [сценария](docs/demo/README.md), выбрать дату 23.09.2026 и участников. Указать фактически использованные модели и измеренное время. Готовый PDF держать доступным на случай задержки; его происхождение обозначить.

### Подготовка ведущего

1. Открыть README, PDF и запущенный API. Для backend-прогона использовать отдельную тестовую БД, как в `smoke_backend.py`.
2. Для показа через UI добавить участников Серик, Дана и Айбек. Эти имена совпадают с фикстурой; seed содержит другой состав участников.
3. Зафиксировать режим демонстрации: fake или реальная локальная обработка. При записи уведомить участников о записи и транскрибации ИИ.
4. До защиты проверить чтение казахских символов, ссылки на цитаты, подтверждение и экспорт. В финале показать результат одного поручения, затем дополнительные возможности по запросу жюри.

Напоминания о просрочке показываются отдельным примером с прошедшей датой и запуском `check_deadlines`; изменение даты в демонстрационных данных нужно объяснить. Meet/Zoom/Teams и узнавание по голосу добавляются в живой показ после отдельной проверки этих функций.

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

ТЗ запрещает передачу аудио и текста во внешние облачные API. Для демонстрации распознавания используются локальные/self-hosted модели.

- `.env.example` задаёт `STT_BACKEND=local`, `LLM_PROVIDER=ollama` и `PIPELINE_FAKE=1`. При fake модели не запускаются. Для реального режима нужны реализация пайплайна, локальные веса и отдельная проверка сетевых обращений.
- `DELETE /meetings/{id}/audio` удаляет запись после обработки; транскрипт и поручения остаются. Операция проверена в HTTP smoke.
- Маскирование телефонов и ИИН предусмотрено в пайплайне. Его нужно проверить на реальной реализации до использования чувствительных данных.
- Секреты хранятся в `.env`, исключённом из git. Перед развёртыванием меняются `SECRET_KEY` и `BOT_API_TOKEN`.

Материалы в `docs/demo/` содержат вымышленные имена и смоделированный разговор. Исходные реальные записи из рабочей папки `samples/` в репозиторий не включены; для демонстрации ТЗ требует их анонимизации.

## Тесты

CI на GitHub для репозитория хакатона не используется. Локальная проверка перед каждым PR:

```bash
./scripts/check.sh             # ruff, pytest backend / pipeline / bots, HTTP smoke
./scripts/check.sh --compose   # плюс полный docker compose стек, тесты и smoke внутри контейнеров
```

По отдельности:

```bash
cd pipeline && uv run pytest          # контракт и fake-пайплайн
cd backend && uv run pytest           # API, Celery-задачи, напоминания, экспорт (нужен Postgres protocol_test, ffmpeg, soffice)
cd backend && uv run ruff check . && uv run ruff format --check .
cd backend && uv run python scripts/smoke_backend.py   # end-to-end через реальный HTTP и curl
cd bots && uv run pytest              # контракт CLI и жизненный цикл бота
```

Тесты бэкенда используют `PIPELINE_FAKE=1` и `CELERY_EAGER=1`: пайплайн подменяется детерминированной заглушкой, Celery-задачи выполняются в процессе без Redis.

### Проверка контейнеров и очереди

`./scripts/check.sh --compose` собирает и запускает Compose, создаёт тестовую БД, выполняет тесты и HTTP-сценарий через Redis и отдельный Celery worker. Используется `PIPELINE_FAKE=1`, аудио генерируется скриптом. Контейнерный прогон пока не подтверждён; на текущей машине разработки нет Docker. GitHub Actions в проекте отключён.

На уже запущенном тестовом Compose можно отдельно выполнить HTTP-сценарий, создающий синтетические данные:

```bash
docker compose exec -T api uv run --no-sync python scripts/smoke_backend.py --api-url http://api:8000/api/v1
```

## Статус реализации

Честная карта того, что работает сегодня и что в работе:

| Компонент | Состояние |
|---|---|
| Бэкенд: auth, участники, совещания (файл / live / бот), поручения, уведомления, напоминания, экспорт DOCX / PDF, СЭД-mock | готово, покрыто тестами и end-to-end smoke |
| Контракт пайплайна и `PIPELINE_FAKE` | готово; интеграция backend проверена на детерминированной заглушке |
| Локальный STT и маскирование телефонов/ИИН | работают CLI и API → Redis/Celery → PostgreSQL; реальная запись проверена |
| Диаризация, voiceprint, извлечение поручений и саммари | ещё не реализованы; реальный режим возвращает только текст/таймкоды и явные `unavailable` |
| Фронтенд | отдельное Next.js-приложение, в работе |
| Бот Meet / Zoom / Teams | жизненный цикл, запись, загрузка и CLI-контракт готовы; адаптеры селекторов web-клиентов в работе |
| Docker Compose | конфигурация и локальный check.sh добавлены; сборка и запуск контейнеров пока не подтверждены |

## Структура репозитория

```
frontend/      Next.js-приложение, полностью делает Эмир (свой каркас, типы и Dockerfile)
backend/       FastAPI, Celery, Alembic, экспорт, СЭД-адаптер (владелец: Ардак)
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
bots/          Playwright-бот для Meet / Zoom / Teams (другой участник)
docs/superpowers/specs/   проектная спецификация
docker-compose.yml, .env.example, backend/Dockerfile
```

Рабочий процесс: ветки `feat/<task>` от `develop`, PR в `develop`, после интеграционного теста PR `develop → main`.

## Ограничения и roadmap

Сделано как прототип:

- СЭД: mock-адаптер с контрактом `SEDClient.push_protocol()`. Реальный адаптер под конкретную СЭД (Documentolog, Directum) пишется по этому интерфейсу.
- Бот-участник: web-клиенты через Playwright. Официальные SDK Zoom / Teams требуют регистрации приложений и не входят в прототип.
- Live-транскрипт появляется после кнопки «Стоп», не в реальном времени.
- Уведомления in-app. Email / Telegram возможны как отдельное расширение.

Развитие:

- Стриминговое распознавание по ходу совещания.
- Дообучение whisper на казахских корпусах (ISSAI KSC2) для шала-казахского.
- Голосовая идентификация без эталона: кластеризация по совещаниям организации.
- Контроль исполнения: эскалация руководителю при повторной просрочке, отчёт по исполнительской дисциплине.
- Интеграция с календарём: автозапуск бота по расписанию встречи.
