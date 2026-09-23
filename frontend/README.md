# frontend

Next.js 15 (App Router) + React 19 + Tailwind v4 + next-intl (ru / kk). Владелец: Эмир.

```bash
cd frontend
cp .env.example .env.local        # NEXT_PUBLIC_API_URL
pnpm install
pnpm dev                          # http://localhost:3000 → /ru/meetings
pnpm gen:api                      # типы из openapi.json (обновить файл: см. ниже)
pnpm typecheck && pnpm lint && pnpm build
```

## Что уже есть

- `src/i18n/`: роутинг `/ru/...` и `/kk/...`, переключатель в шапке, словари в `src/messages/{ru,kk}.json`. Добавляй ключи в оба файла.
- `src/lib/api.ts`: типизированный клиент ко всем эндпоинтам бэка (`auth`, `meetings`, `tasks`, `participants`, `directions`, `notifications`), cookie-auth, `ApiError`. Типы ответов в `src/lib/api-types.ts` генерируются из `openapi.json`.
- `src/app/[locale]/layout.tsx`: шапка с навигацией. `login/page.tsx`: рабочий логин (admin@example.com / admin123 после seed).
- Остальные страницы: заглушки `<Todo>` с указанием экрана из спеки (раздел 8). Заменяй на реальные.

## Экраны (спека, раздел 8)

| Путь | Что |
|---|---|
| `/login`, `/register` | вход, регистрация (регистрация привязывает гостя-участника по email) |
| `/meetings` | список совещаний, статусы, кнопка «Новое совещание» |
| `/meetings/new` | вкладки: загрузить файл (multipart `meetings.upload`), записать (MediaRecorder → `meetings.liveSocket(id)`: бинарные чанки, в конце текст `{"event":"stop"}`), подключить бота (`meetings.createBot`). Обязательный баннер `meetings.recordingBanner` |
| `/meetings/[id]` | polling `meetings.get` каждые 3 с пока `status === "processing"` (`progress_stage`, `progress_pct`); спикеры (`setSpeakers`), транскрипт, саммари, поручения (inline `tasks.patch`), «Подтвердить» (`confirm`), DOCX/PDF (`exportUrl`), СЭД (`sendToSed`), удалить аудио |
| `/tasks` | `tasks.stats` счётчики + `tasks.list` с фильтрами, смена статуса, «только мои» |
| `/participants` | список, добавить, эталон голоса: MediaRecorder 10 с → `participants.enrollVoice(id, blob)` |
| `/admin/directions` | справочник (admin) |
| колокольчик | `notifications.unreadCount` polling 30 с, список, read / read-all |

## Обновить типы после изменений в бэке

```bash
cd ../backend && PIPELINE_FAKE=1 uv run python -c "import json; from app.main import app; json.dump(app.openapi(), open('../frontend/openapi.json','w'), ensure_ascii=False, indent=1)"
cd ../frontend && pnpm gen:api
```
