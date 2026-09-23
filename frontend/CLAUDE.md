# frontend/ — Хаттама web app

Owner: Emir. This folder only. Backend (`backend/`), pipeline and bots belong to other people; do not edit them.

**Source of truth:** `../docs/superpowers/specs/2026-09-23-meeting-protocol-design.md`
- §7 REST API = the contract with the backend. §8 = the screens. §6 = domain/statuses.
- Contracts change only via an edit to the spec in a separate `spec: ...` commit. Never "fix" the API shape on the frontend side alone.

## Commands (pnpm)

```
pnpm mock       # dev server fully on mocks (NEXT_PUBLIC_API_MOCKING=1), no backend needed
pnpm dev        # dev server; /api/v1/* is proxied to BACKEND_URL (default http://localhost:8000)
pnpm build      # production build (output: standalone, for docker)
pnpm lint       # eslint
pnpm test       # vitest (src/**/*.test.ts)
pnpm gen:api    # openapi-typescript from ${BACKEND_URL}/openapi.json → src/lib/api/schema.gen.ts
```

Mock data persists in localStorage. Open any page with `?reset-mocks` to start over. Demo login: `admin@hattama.kz`, any password.

## Stack

Next.js 15 App Router · React 19 · TS strict · Tailwind v4 · shadcn/ui (Radix, `radix-nova` style) · next-intl (ru/kk) · TanStack Query · react-hook-form + zod · date-fns · MSW handlers (run in-process, see below).

## Layout

```
messages/{ru,kk}.json      all UI strings; both files must have the same keys
mocks/                     seed.ts (fixtures), db.ts (stateful mock db + fake pipeline), handlers.ts (every §7 endpoint),
                           transport.ts (mockFetch + MockLiveSocket), pdf.ts
src/app/(auth)/            /login, /register (split layout, ink hero panel)
src/app/(app)/             authed area; layout = AuthGuard + AppHeader + footer
  meetings/, meetings/new, meetings/[id], tasks/, participants/, admin/directions/
src/i18n/                  locale from NEXT_LOCALE cookie (no URL prefix; routes match spec §8 exactly)
src/lib/api/types.ts       hand-written from §6/§7 until the backend has /openapi.json
src/lib/api/client.ts      api.get/post/..., ApiError, transport(), openLiveSocket()
src/lib/api/queries/*.ts   ALL data access goes through these hooks (query keys in keys.ts)
src/lib/audio/             useRecorder: MediaRecorder + AnalyserNode level meter
src/lib/format.ts          timecodes, dates, deadline tone, speaker colors (+ format.test.ts)
src/components/ui/         shadcn-generated. Add with `pnpm dlx shadcn@latest add <name>`; don't restyle here
src/components/brand/      wordmark, seal stamp, ornament (qoshqar-muiz), privacy badge
src/components/{common,meeting,meetings,new-meeting,participants,tasks,notifications,shell}/
```

## Conventions

- **Strings:** no hardcoded UI text. Add the key to both `messages/ru.json` and `messages/kk.json`. Kazakh plurals are `{count} ...` (no plural forms).
- **Data:** components never call `fetch` directly. Use a hook in `lib/api/queries`. Mutations invalidate through the helpers there (meeting, tasks, stats, notifications).
- **New endpoint:** add the type to `types.ts`, a hook to `queries/`, and a handler + fixture to `mocks/`. `pnpm mock` must keep working.
- **Mocks without a Service Worker:** `transport()` resolves requests against the MSW `handlers` with `getResponse`. That works in embedded browsers and on plain-HTTP LAN demos where SWs fail. The mock branch is tree-shaken when `NEXT_PUBLIC_API_MOCKING` is not `1`.
- **Polling (spec §8):** a meeting refetches every 3 s while `uploaded|processing`. The bell refetches every 30 s.
- **Files:** exports download through `lib/api/download.ts` (fetch → blob), not `<a href>`, so cookies and mocks both work.
- **Live recording:** `openLiveSocket()` goes straight to `NEXT_PUBLIC_WS_URL`, because Next rewrites don't proxy WebSockets. Binary chunks go every 1 s, then `{"event":"stop"}`.
- **Privacy (spec §2):** no external runtime requests. Fonts come through `next/font` (self-hosted at build). No analytics, no CDNs.

## Design system: "digital chancellery × steppe"

The product is an official register of minutes. It should read as paper and ink, not generic SaaS.
- Tokens live in `src/app/globals.css` (`--paper --ink --steppe --gold --brick --sage --rec --speaker-0..5`). Use the Tailwind names (`bg-gold-soft`, `text-brick`, `bg-speaker-2`). **Never hardcode colors.** Add a token instead, for both light and `.dark`.
- Type: `font-heading` = Literata (titles, big numbers, task text), `font-sans` = Onest (UI), `font-mono` = JetBrains Mono (timecodes, `SPEAKER_00`, `№`, `SED-…`, eyebrows). All three have cyrillic-ext for the Kazakh letters.
- Motifs: hairline borders, small radii, mono uppercase eyebrows with wide tracking, the gold horn ornament used sparingly, the `SealStamp` for confirmed protocols, and `.marker-highlight` for evidence quotes.
- Status colors: steppe = assigned/processing, gold = draft/in progress/due soon, sage = done/confirmed/voiceprint, brick = overdue/failed/unmatched.
- Check each screen at 375 px (no horizontal scroll) and in dark mode.

## Git

Branch from `develop` as `feat/<desc>`, and open the PR into `develop` (no direct pushes to `develop`/`main`). Use Conventional Commits: `feat(frontend): ...`, `fix(frontend): ...`.

## Open contract questions for the backend (not yet in spec §7)

The frontend currently assumes these; confirm them with Nikita or add them to the spec:
- `Participant.has_voiceprint: bool` (the list omits the embedding, so the UI needs a flag).
- `Meeting.has_audio: bool` and `Meeting.sed_ref: str | null` (for the delete-audio and SED states).
- `PATCH /auth/me {locale}` to persist the UI language to `users.locale` (called best-effort; failures are ignored).
- `GET /tasks` items include `meeting_title` (optional; used on the dashboard).
- Progress stage names: `upload | stt | diarize | voiceprint | extract | summary` (plus `bot_recording`).
