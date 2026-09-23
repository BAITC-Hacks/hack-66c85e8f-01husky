# Kenes AI: система автопротоколирования совещаний

Рабочее название проекта: **Kenes AI**.

Дата: 2026-09-23. Статус: approved, ready for implementation.
Репозиторий: https://github.com/BAITC-Hacks/hack-66c85e8f-01husky

Этот документ: единый источник правды для всех участников и их агентов.
Каждый берёт свою часть (раздел 9), работает в своей папке, соблюдает контракты (разделы 5-7).
Контракты между частями менять только через правку этого файла и отдельный коммит `spec: ...`.

---

## 1. Задача

Прототип ИИ-ассистента, который принимает запись совещания (файл, live-микрофон, бот-участник Meet/Zoom/Teams),
распознаёт речь на русском, казахском и смешанном («шала-казахском»), различает говорящих, привязывает реплики
к участникам, извлекает поручения (кто, что, срок), формирует саммари, экспортирует протокол в DOCX/PDF,
ведёт дашборд поручений и напоминает о сроках.

Обязательный минимум и все «дополнительные» пункты кейса входят в scope:
СЭД-адаптер (mock), дашборд статусов, рассылка выдержек (in-app уведомления), классификация по срочности и
направлению, голосовая идентификация по тембру, on-premise через docker-compose.

## 2. Ограничение по приватности (жёсткое)

Кейс запрещает передачу аудио/текста во внешние облачные API. Решение:

- Каждый ИИ-компонент за интерфейсом провайдера. **Значения по умолчанию в `.env.example` и `docker-compose.yml`: локальные** (`STT_BACKEND=local`, `LLM_PROVIDER=ollama`).
- Облачные провайдеры (`openai`, `nvidia`) существуют как dev/ускорение демо и помечены в README как «dev-only, в закрытом контуре заменяются на local/ollama/nvidia_nim без изменения кода».
- Аудио хранится только в `backend/data/audio/`. Есть операция «удалить аудио после протокола».
- В транскрипте перед сохранением маскируются телефоны и ИИН (`pipeline/privacy.py`).
- Никакой телеметрии, аналитики, внешних CDN в проде-профиле compose.

## 3. Стек

| Слой | Технология |
|---|---|
| frontend/ | Next.js 15 (App Router), React 19, TypeScript, Tailwind v4, i18n ru/kk, pnpm |
| backend/ | Python 3.12, FastAPI, SQLAlchemy 2 + Alembic, PostgreSQL 16, Celery 5 + Redis, uv |
| pipeline/ | Python 3.12 библиотека, pydantic v2, faster-whisper, pyannote.audio 3.1, speechbrain (ECAPA), httpx; uv |
| bots/ | Python 3.12, Playwright (Chromium), ffmpeg; uv |
| infra | docker-compose: `frontend`, `api`, `worker`, `beat`, `postgres`, `redis`, `ollama` |
| экспорт | python-docx → DOCX; PDF через LibreOffice headless (`soffice --convert-to pdf`) |

## 4. Структура репозитория

```
frontend/            Next.js приложение
backend/
  app/
    main.py          FastAPI app, роутеры
    config.py        pydantic-settings, читает .env
    db.py            engine, session
    models/          SQLAlchemy модели
    schemas/         pydantic-схемы API
    routers/         auth, users, participants, meetings, tasks, directions, notifications, sed, live
    services/        export.py, notify.py, sed/ (SEDClient, MockSED), speaker_resolve.py
    tasks/           celery_app.py, process_meeting.py, reminders.py
  alembic/
  data/audio/        загруженные и записанные файлы (gitignored)
  outbox/            MockSED выгрузки (gitignored)
  tests/
pipeline/
  pipeline/
    __init__.py      process(), enroll_voice()
    models.py        контракт (раздел 5), единственный источник типов
    stt/             base.py, local_whisper.py, openai_whisper.py, nvidia_asr.py
    diarize.py       pyannote
    voiceprint.py    ECAPA embeddings, cosine match, enroll
    llm/             base.py, ollama.py, nvidia_nim.py, openai.py
    extract.py       агент извлечения поручений
    summary.py
    privacy.py
    fake.py          детерминированный MeetingResult для разработки без моделей
    cli.py           python -m pipeline.cli <audio> --date ... --participants ...
  tests/
bots/
  bots/
    base.py          MeetingBot: join(url) → record → leave → upload
    meet.py, zoom.py, teams.py   адаптеры селекторов
    cli.py           python -m bots.cli --platform meet --url ... --meeting-id ...
docs/superpowers/specs/   этот файл
docker-compose.yml
.env.example
README.md
```

## 5. Контракт pipeline (pydantic, `pipeline/pipeline/models.py`)

Это граница между Ардаком и Никитой. Backend импортирует эти типы как есть.

```python
from datetime import date
from typing import Literal
from pydantic import BaseModel

Urgency = Literal["low", "normal", "high", "critical"]
SpeakerSource = Literal["voiceprint", "llm", "manual", "none"]

class Participant(BaseModel):
    id: int
    name: str
    role: str | None = None            # должность, для контекста LLM
    voice_embedding: list[float] | None = None

class Segment(BaseModel):
    start: float                        # секунды
    end: float
    speaker: str                        # "SPEAKER_00"
    text: str                           # уже после privacy-маскирования
    lang: Literal["ru", "kk", "mixed", "other"]

class SpeakerMapping(BaseModel):
    speaker: str                        # "SPEAKER_00"
    participant_id: int | None
    source: SpeakerSource
    confidence: float                   # 0..1

class Task(BaseModel):
    text: str                           # суть поручения, одна фраза, императив
    assignee_participant_id: int | None
    assignee_name: str                  # как названо в речи, даже если не сматчилось
    deadline: date | None               # ISO, нормализовано от meeting_date
    deadline_raw: str | None            # "до пятницы", "келесі аптаға дейін"
    urgency: Urgency
    direction: str                      # одно из directions, переданных на вход, или "Другое"
    quote: str                          # дословная цитата из транскрипта
    segment_index: int                  # индекс в segments, откуда цитата
    confidence: float

class MeetingResult(BaseModel):
    segments: list[Segment]
    speaker_map: list[SpeakerMapping]
    tasks: list[Task]
    summary: str                        # markdown: Тема / Решения / Поручения / Открытые вопросы
    language_stats: dict[str, float]    # {"ru": 0.6, "kk": 0.3, "mixed": 0.1}
    duration_sec: float
    model_info: dict[str, str]          # {"stt": "faster-whisper large-v3-turbo", "llm": "qwen3:14b"}

def process(
    audio_path: str,
    meeting_date: date,
    participants: list[Participant],
    directions: list[str],
    output_language: Literal["ru", "kk"] = "ru",
    progress: Callable[[str, float], None] | None = None,   # ("stt", 0.4)
) -> MeetingResult: ...

def enroll_voice(audio_path: str) -> list[float]: ...      # эталон тембра, 5-15 сек речи
```

Правила:
- `process()` синхронная, без сети кроме провайдеров, без БД, без FastAPI.
- Все модели (whisper, pyannote, ECAPA) грузятся лениво и кешируются в процессе.
- Провайдеры выбираются из env: `STT_BACKEND=local|openai|nvidia`, `LLM_PROVIDER=ollama|nvidia_nim|openai`, `LLM_MODEL`, `OLLAMA_URL`, `NVIDIA_API_KEY`, `OPENAI_API_KEY`, `HF_TOKEN`.
- `pipeline.fake.process()` имеет ту же сигнатуру и возвращает правдоподобный результат с 3 спикерами и 4 поручениями. Backend использует его при `PIPELINE_FAKE=1`.

### 5.1 Агент извлечения поручений (`extract.py`)

Не один промпт. Шаги, каждый отдельный вызов LLM с JSON-выходом:
1. **Candidates**: по транскрипту (с метками спикеров) выделить кандидатов: `{speaker, assignee_name, text, deadline_raw, quote, segment_index}`.
2. **Verify**: для каждого кандидата проверить, что `quote` дословно присутствует в `segments[segment_index].text` (строковая проверка в коде, не LLM). Не прошедшие отбрасываются или чинятся повторным запросом с указанием ошибки.
3. **Normalize deadline**: `deadline_raw` → ISO-дата относительно `meeting_date`. Правила в коде для типовых («завтра», «до пятницы», «через неделю», «ертең», «келесі аптаға дейін», «айдың соңына дейін»), LLM для остального.
4. **Resolve assignee**: `assignee_name` → `participant_id` по нечёткому совпадению с именами участников (транслит, падежи, «Айбек Серикович» → «Айбек»). Если не нашли, `None`, имя остаётся в `assignee_name`.
5. **Classify**: `urgency` (из срока + маркеров «срочно», «жедел», «шұғыл») и `direction` из переданного списка.

### 5.2 Привязка спикеров (`voiceprint.py` + `extract.py`)

Приоритет: voiceprint (если у участника есть `voice_embedding` и cosine ≥ 0.75) → LLM по контексту обращений («Айбек, ты подготовь…» значит следующий говорящий, скорее всего, Айбек; самопредставления) → `none`. Секретарь правит вручную в UI, backend пересчитывает `assignee_participant_id` у задач без повторного прогона пайплайна.

## 6. Домен и БД (backend, Alembic)

```
users              id, email (unique), password_hash, name, role enum(user, admin), locale enum(ru, kk), created_at
participants       id, name, email (nullable, unique), position, user_id (nullable FK users), voice_embedding float[] (nullable), created_at
                   гость = participant без user_id; при регистрации user с тем же email привязывается автоматически
meetings           id, title, meeting_date, source enum(upload, live, bot), platform (nullable: meet/zoom/teams),
                   audio_path (nullable), duration_sec, output_language enum(ru, kk),
                   status enum(uploaded, processing, draft, confirmed, failed), progress_stage, progress_pct,
                   summary text, language_stats jsonb, model_info jsonb, error text, created_by FK users, created_at, confirmed_at
meeting_participants  meeting_id, participant_id (PK pair)
segments           id, meeting_id, idx, start, end, speaker, text, lang
speaker_map        id, meeting_id, speaker, participant_id (nullable), source enum, confidence
directions         id, name (unique), is_active        seed: Финансы, Кадры, ИТ, Юридическое, Закупки, Производство, Другое
tasks              id, meeting_id, assignee_participant_id (nullable), assignee_name, text, deadline (nullable), deadline_raw,
                   urgency enum, direction_id FK, quote, segment_idx, confidence,
                   status enum(draft, confirmed, in_progress, done, overdue), sed_ref (nullable), created_at, updated_at, done_at
notifications      id, user_id, task_id (nullable), meeting_id (nullable), kind enum(assigned, due_soon, overdue, protocol_ready), title, body, read_at, created_at
```

Статусы задач: `draft` после пайплайна → `confirmed` при подтверждении протокола → `in_progress` (ответственный или админ) → `done`. `overdue` ставится Celery beat автоматически, если `deadline < today` и статус в (`confirmed`, `in_progress`); при `done` из `overdue` разрешено.

## 7. REST API (backend, префикс `/api/v1`)

Auth: JWT в httpOnly cookie `access_token`, срок 7 дней. Роли: `user`, `admin`. Любой залогиненный может создать совещание. `admin` видит всё, правит справочники, всех участников. `user` видит совещания, где он создатель или участник, и свои задачи.

```
POST   /auth/register        {email, password, name, locale}      → User    (привязывает participant по email)
POST   /auth/login           {email, password}                    → User + cookie
POST   /auth/logout
GET    /auth/me                                                    → User

GET    /participants                                               → [Participant]  (admin: все; user: все, без embedding)
POST   /participants         {name, email?, position?}             → Participant   (гость)
PATCH  /participants/{id}
POST   /participants/{id}/voiceprint   multipart audio             → {ok, embedding_dim}
DELETE /participants/{id}/voiceprint

GET    /directions                                                 → [Direction]
POST   /directions  PATCH /directions/{id}                         (admin)

POST   /meetings             multipart: title, meeting_date, output_language, participant_ids[], file
                                                                   → Meeting {status: uploaded}; ставит celery process_meeting
POST   /meetings/live        {title, meeting_date, output_language, participant_ids[]}  → Meeting {source: live}
WS     /meetings/{id}/live   бинарные чанки webm/opus; текстовое сообщение {"event":"stop"} закрывает файл и ставит process_meeting
POST   /meetings/bot         {title, meeting_date, platform, url, participant_ids[]}    → Meeting {source: bot}; запускает bots.cli
POST   /meetings/{id}/audio  multipart file (используется ботом после записи)           → ставит process_meeting
GET    /meetings             ?status=&from=&to=                    → [MeetingListItem]
GET    /meetings/{id}                                              → MeetingDetail {meeting, participants, segments, speaker_map, tasks, summary}
PATCH  /meetings/{id}        {title?, meeting_date?, summary?}
PUT    /meetings/{id}/speakers  [{speaker, participant_id}]        → пересчёт assignee у задач, source=manual
POST   /meetings/{id}/reprocess
POST   /meetings/{id}/confirm                                      → status confirmed, tasks draft→confirmed, notifications assigned+protocol_ready
GET    /meetings/{id}/export ?format=docx|pdf&lang=ru|kk           → файл
POST   /meetings/{id}/sed                                          → {sed_ref, outbox_path}
DELETE /meetings/{id}/audio
DELETE /meetings/{id}

GET    /tasks                ?status=&assignee_id=&direction_id=&urgency=&meeting_id=&mine=1  → [Task]
GET    /tasks/stats                                                → {draft, confirmed, in_progress, done, overdue, due_soon}
POST   /tasks                {meeting_id, ...}                     (ручное добавление в черновик)
PATCH  /tasks/{id}           {text?, assignee_participant_id?, deadline?, urgency?, direction_id?, status?}
DELETE /tasks/{id}

GET    /notifications        ?unread=1                             → [Notification]
POST   /notifications/{id}/read
POST   /notifications/read-all
```

Ошибки: `{"detail": str}`; 401 без cookie, 403 не своя сущность, 404, 422 валидация.
OpenAPI: `http://localhost:8000/docs`. Фронт генерирует типы из `/openapi.json` (`pnpm gen:api`).

Celery:
- `process_meeting(meeting_id)`: status→processing, `pipeline.process(...)` с progress-колбэком в `meetings.progress_*`, запись segments/speaker_map/tasks/summary, status→draft; при исключении status→failed + error.
- `check_deadlines()` (beat, каждый час): `due_soon` за 24 ч до срока (одно уведомление на задачу), `overdue` при просрочке + смена статуса.
- `run_bot(meeting_id, platform, url)`: subprocess `python -m bots.cli ...`.

## 8. Frontend: экраны

Все экраны на русском и казахском (`next-intl`, переключатель в шапке, хранится в `users.locale`).

1. `/login`, `/register`
2. `/meetings` список: карточки со статусом, датой, числом поручений; кнопка «Новое совещание».
3. `/meetings/new`: три вкладки: **Загрузить файл** (drag-and-drop, аудио/видео), **Записать** (MediaRecorder → WS, таймер, индикатор уровня, обязательный баннер «Ведётся запись, транскрибация ИИ»), **Подключить бота** (платформа + ссылка). Общие поля: название, дата, язык протокола, участники (multi-select + «добавить гостя» по имени/email).
4. `/meetings/[id]`:
   - шапка: статус, прогресс обработки (polling `GET /meetings/{id}` каждые 3 с пока `processing`)
   - **Спикеры**: `SPEAKER_00 → [select участник]`, бейдж источника (тембр / по контексту / вручную) и уверенность
   - **Транскрипт**: сегменты с таймкодом, спикером, языком; клик по цитате задачи подсвечивает сегмент
   - **Саммари**: markdown, редактируемое
   - **Поручения**: таблица с inline-редактированием (текст, ответственный, срок, срочность, направление), цитата, confidence, удалить, добавить
   - действия: «Подтвердить протокол», «Скачать DOCX», «Скачать PDF», «Отправить в СЭД» (показывает `sed_ref`), «Удалить аудио», «Переобработать»
5. `/tasks` дашборд: счётчики (в работе / просрочено / выполнено / скоро срок), фильтры (статус, ответственный, направление, срочность, совещание), таблица, смена статуса, переключатель «только мои».
6. `/participants`: список, добавить, карточка с записью голосового эталона (MediaRecorder 10 с → `POST /voiceprint`), индикатор «эталон есть».
7. `/admin/directions` (admin): справочник направлений.
8. Колокольчик в шапке: непрочитанные уведомления, polling 30 с, список, «прочитать всё».

## 9. Разделение работы

Каждый работает только в своей папке. Стык: раздел 5 (pipeline ↔ backend) и раздел 7 (backend ↔ frontend, bots ↔ backend).

### Эмир: `frontend/` (полностью сам: каркас, типы из `/openapi.json`, Dockerfile, сервис в compose)
Вход: раздел 7 (API) и раздел 8 (экраны). До готовности бэка: `pnpm mock` поднимает msw/json-server с фикстурами из `frontend/mocks/`, повторяющими схемы раздела 7.
Готово, когда: все 8 экранов работают против реального бэка, сценарий «загрузить файл → увидеть черновик → поправить спикера → подтвердить → скачать PDF → увидеть задачу на дашборде → получить уведомление» проходит без перезагрузки.

### Никита: `backend/`, `docker-compose.yml`, `.env.example`, `README.md`
Вход: разделы 6, 7, контракт 5. До готовности пайплайна: `PIPELINE_FAKE=1` → `pipeline.fake.process`.
Также: `services/export.py` (DOCX-шаблон: шапка организации, название, дата, участники, саммари, таблица поручений, приложение с транскриптом; PDF через LibreOffice), `services/sed/` (интерфейс `SEDClient.push_protocol(meeting, pdf_path) -> sed_ref`, `MockSED` пишет `outbox/<meeting_id>/protocol.pdf + meta.json` и возвращает `SED-2026-000123`), `services/notify.py` (создание notifications), Celery beat, seed-скрипт (admin, 5 участников, направления), README (устройство, запуск в 3 команды, сценарий демо, on-prem раздел, dev-провайдеры).
Готово, когда: `docker compose up` поднимает всё, `pytest` зелёный, curl-сценарий из README проходит, DOCX/PDF открываются.

### Ардак: `pipeline/`, `bots/`
Вход: раздел 5. Первое действие: прогнать реальную тестовую запись через `python -m pipeline.cli`, сравнить `language=None` vs `language=ru` для шала-казахского, зафиксировать выбор в `pipeline/README.md`.
Порядок: stt local → diarize → cli печатает MeetingResult → extract агент → summary → voiceprint + enroll → privacy → провайдеры openai/nvidia → bots (meet первым, zoom/teams адаптерами).
Бот: Playwright Chromium с фейковым аудио-устройством, заходит по ссылке как «Протокол-бот», ждёт допуска, пишет аудио вкладки через `--use-fake-ui-for-media-stream` + ffmpeg/pulse (Linux в docker) или screen-capture API, по окончании `POST /meetings/{id}/audio`.
Готово, когда: cli на реальной записи даёт верных спикеров, поручения с верными датами и ответственными; `pytest` на `fake` и на unit-нормализации дат зелёный; бот записывает 1 минуту Meet и загружает файл.

### Camille (агент): каркас
Скаффолд репо: структура папок, `pipeline/models.py` с контрактом, `pipeline/fake.py`, `backend` с моделями и Alembic-миграцией 0001, пустые роутеры со схемами, `docker-compose.yml`, `.env.example`, README-заготовка. После скаффолда: интеграция стыков, README, ревью.

## 10. Конвенции

- Ветки: базовая ветка `develop`. Задачи в `feat/<task-desc>` от `develop`, только через Pull Request в `develop`, прямые пуши в `develop` и `main` запрещены. Маленькие PR, часто.
- `develop` → `main`: после интеграционного теста всей команды, одним PR.
- Коммиты: Conventional Commits (`feat(backend): ...`, `fix(pipeline): ...`, `spec: ...`).
- Python: ruff + ruff format, type hints обязательны, pydantic v2. TS: eslint + prettier, strict.
- Секреты только в `.env` (gitignored). `.env.example` с локальными значениями по умолчанию.
- CI только локально: `./scripts/check.sh` перед PR, GitHub Actions в репозитории хакатона не включаем.
- Тесты: backend pytest + httpx; pipeline pytest на fake и на чистые функции; frontend минимум vitest на утилиты.
- Никаких внешних вызовов из кода по умолчанию. Любой облачный провайдер за флагом.

## 11. Вне scope

Реальный адаптер к конкретной СЭД, официальные SDK Zoom/Teams, стриминговый транскрипт в реальном времени (после стопа хватает), email/Telegram-каналы (in-app достаточно, интерфейс `Notifier` оставляет дверь), мобильное приложение.

## 12. Риски

| Риск | Митигация |
|---|---|
| Whisper плохо берёт шала-казахский | Проверить на реальной записи в первый час; форс `ru` + LLM-постправка; казахский fine-tune whisper с HF как запасной |
| pyannote медленный на CPU | Демо-запись 3-5 минут; `STT_BACKEND=nvidia` для скорости на демо; в README честно |
| Бот Meet не пускают / не пишет звук | Meet первым, остальные адаптерами; если не взлетает, остаётся файл + live, бот в README как roadmap с кодом |
| LLM выдумывает поручения | Шаг Verify по дословной цитате в коде, confidence в UI, черновик подтверждает секретарь |
