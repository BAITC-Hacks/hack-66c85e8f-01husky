# Kenes AI: frontend

Веб-интерфейс Kenes AI для секретаря, участников и руководителя. Через него создают совещание, проверяют транскрипт и поручения, утверждают протокол и следят за исполнением.

[Главный README](../README.md) · [Соглашения по коду](CLAUDE.md) · [Спецификация: API §7, экраны §8](../docs/superpowers/specs/2026-09-23-meeting-protocol-design.md)

<img src="../docs/screenshots/meeting-detail.png" alt="Карточка совещания: хронология выступлений, транскрипт и поручения" width="860">

## Быстрый старт

Нужны Node.js 20+ и pnpm.

```bash
pnpm install
pnpm mock      # всё на моках, backend не нужен: http://localhost:3000
pnpm dev       # с настоящим backend (BACKEND_URL, по умолчанию http://localhost:8000)
```

| Режим | Вход | Особенности |
|---|---|---|
| `pnpm mock` | `admin@kenes.ai`, пароль любой | Данные хранятся в браузере. `?reset-mocks` в адресе сбрасывает их. Моки работают без Service Worker, поэтому демо открывается и по локальной сети |
| `pnpm dev` | `admin@example.com` / `admin123` из seed | `/api/v1/*` проксируется на backend. Открывайте `localhost`, а не `127.0.0.1`: WebSocket live-записи использует cookie того же хоста |

Настройки описаны в `.env.example`: `BACKEND_URL`, `NEXT_PUBLIC_WS_URL`, `NEXT_PUBLIC_API_MOCKING`.

## Экраны

| Маршрут | Что на экране |
|---|---|
| `/login`, `/register` | Вход и регистрация. Гость, добавленный секретарём, при регистрации получает свои поручения |
| `/meetings` | Реестр протоколов: фильтр по статусу, источник, длительность, язык |
| `/meetings/new` | Новое совещание: загрузка файла, запись с микрофона с индикатором уровня или бот во встречу Meet / Zoom / Teams |
| `/meetings/[id]` | Этапы обработки, хронология выступлений, доля RU / KK / смешанной речи, транскрипт, привязка спикеров к участникам, поручения с цитатой-основанием, саммари, подтверждение протокола, экспорт DOCX / PDF, отправка в СЭД |
| `/tasks` | Контроль исполнения: счётчики, фильтры, три вида: список, канбан-доска и по срокам |
| `/participants` | Участники и загрузка голосовых эталонов |
| `/admin/directions` | Справочник направлений (для администратора) |

Во всех экранах есть колокольчик уведомлений, переключатель RU / ҚАЗ и светлая и тёмная тема. Вёрстка проверена на ширине 375 px.

## Стек

Next.js 15 (App Router) · React 19 · TypeScript strict · Tailwind v4 · shadcn/ui (Radix) · next-intl · TanStack Query · react-hook-form + zod · date-fns · MSW-обработчики для моков.

## Принципы

- **Типы из backend.** `pnpm gen:api` генерирует `src/lib/api/schema.gen.ts` из `/openapi.json`. Мок-обработчики возвращают те же схемы, поэтому `pnpm mock` и `pnpm dev` ведут себя одинаково.
- **Два языка.** Все строки интерфейса находятся в `messages/ru.json` и `messages/kk.json` с одинаковым набором ключей.
- **Без внешних запросов.** Шрифты включаются в сборку, аналитики и CDN нет. Это соответствует требованию on-premise.
- **Единые токены дизайна.** Цвета заданы в `src/app/globals.css` для светлой и тёмной темы; в компонентах они не хардкодятся.

## Проверки

```bash
pnpm lint      # eslint
pnpm test      # vitest
pnpm build     # production-сборка (output: standalone)
```

## Структура

```
messages/{ru,kk}.json     строки интерфейса
mocks/                    фикстуры, stateful mock-БД с fake-пайплайном, обработчики всех эндпоинтов
src/app/(auth)/           вход и регистрация
src/app/(app)/            meetings, meetings/new, meetings/[id], tasks, participants, admin/directions
src/lib/api/              клиент, сгенерированные типы, хуки TanStack Query
src/lib/audio/            запись с микрофона и индикатор уровня
src/components/           ui (shadcn), brand, meeting, meetings, new-meeting, tasks, participants, shell
```

Подробные соглашения: [CLAUDE.md](CLAUDE.md).
