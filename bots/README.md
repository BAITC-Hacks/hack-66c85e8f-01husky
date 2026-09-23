# bots

Бот-участник для Google Meet / Zoom / Teams через web-клиенты (Playwright). Владелец: Ардак.

Контракт с бэкендом (`backend/app/tasks/run_bot.py` запускает это subprocess'ом):

```bash
cd bots
uv sync && uv run playwright install chromium
uv run python -m bots.cli --platform meet --url https://meet.google.com/abc-defg-hij \
  --meeting-id 12 --api-url http://localhost:8000/api/v1 --api-token "$BOT_API_TOKEN"
```

По окончании звонка бот делает `POST {api-url}/meetings/{id}/audio` с заголовком `X-Bot-Token`,
бэкенд ставит запись в обработку. Код выхода 0 = загружено, иначе бэкенд помечает совещание `failed`.

Что реализовать: `join / wait_admitted / call_ended / leave` в `meet.py`, `zoom.py`, `teams.py`
(селекторы web-клиентов). Запись и загрузка уже в `base.py`. Захват звука: PulseAudio null sink +
`ffmpeg -f pulse` в docker, BlackHole на macOS (`--audio-device avfoundation::BlackHole 2ch`).

```bash
uv run pytest
```
