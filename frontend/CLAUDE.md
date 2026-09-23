# frontend/ — Kenes AI web app

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

Mock data persists in localStorage. Open any page with `?reset-mocks` to start over. Demo login: `admin@kenes.ai`, any password.

## Stack

Next.js 15 App Router · React 19 · TS strict · Tailwind v4 · shadcn/ui (Radix, `radix-nova` style) · next-intl (ru/kk) · TanStack Query · react-hook-form + zod · date-fns · MSW handlers (run in-process, see below).

## Layout

```
messages/{ru,kk}.json      all UI strings; both files must have the same keys
mocks/                     seed.ts (fixtures), db.ts (stateful mock db + fake pipeline), handlers.ts (every §7 endpoint),
                           transport.ts (mockFetch + MockLiveSocket), pdf.ts
src/app/(auth)/            /login, /register (split layout, indigo `.bg-hero` panel)
src/app/(app)/             authed area; layout = AuthGuard + AppHeader + footer
  meetings/, meetings/new, meetings/[id], tasks/, participants/, admin/directions/
src/i18n/                  locale from NEXT_LOCALE cookie (no URL prefix; routes match spec §8 exactly)
src/lib/api/types.ts       hand-written from §6/§7 until the backend has /openapi.json
src/lib/api/client.ts      api.get/post/..., ApiError, transport(), openLiveSocket()
src/lib/api/queries/*.ts   ALL data access goes through these hooks (query keys in keys.ts)
src/lib/audio/             useRecorder: MediaRecorder + AnalyserNode level meter
src/lib/format.ts          timecodes, dates, deadline tone, speaker colors (+ format.test.ts)
src/components/ui/         shadcn-generated. Add with `pnpm dlx shadcn@latest add <name>`; don't restyle here
src/components/brand/      wordmark/logo mark, seal stamp, privacy badge
src/components/{common,meeting,meetings,new-meeting,participants,tasks,notifications,shell}/
```

## Conventions

- **Strings:** no hardcoded UI text. Add the key to both `messages/ru.json` and `messages/kk.json`. Kazakh plurals are `{count} ...` (no plural forms).
- **Data:** components never call `fetch` directly. Use a hook in `lib/api/queries`. Mutations invalidate through the helpers there (meeting, tasks, stats, notifications).
- **New endpoint:** add the type to `types.ts`, a hook to `queries/`, and a handler + fixture to `mocks/`. `pnpm mock` must keep working.
- **Mocks without a Service Worker:** `transport()` resolves requests against the MSW `handlers` with `getResponse`. That works in embedded browsers and on plain-HTTP LAN demos where SWs fail. The mock branch is tree-shaken when `NEXT_PUBLIC_API_MOCKING` is not `1`.
- **Polling (spec §8):** a meeting refetches every 3 s while `uploaded|processing`. The bell refetches every 30 s.
- **Errors:** never `toast.error(e.message)`. Failed mutations are toasted globally (MutationCache in `providers.tsx`, localized by `errorKind()` in `lib/api/errors.ts`); opt out with `meta: { silent: true }` when the UI shows the error itself. For anything else use `useNotify()` (`hooks/use-notify.ts`). A query that fails on first load renders `<QueryError>`; route crashes and 404s use `ErrorScreen` via `error.tsx` / `not-found.tsx` / `global-error.tsx`.
- **Files:** exports download through `lib/api/download.ts` (fetch → blob), not `<a href>`, so cookies and mocks both work.
- **Live recording:** `openLiveSocket()` goes straight to `NEXT_PUBLIC_WS_URL`, because Next rewrites don't proxy WebSockets. Binary chunks go every 1 s, then `{"event":"stop"}`.
- **Privacy (spec §2):** no external runtime requests. Fonts come through `next/font` (self-hosted at build). No analytics, no CDNs.

## Design system: Loom-inspired

The look follows Loom's visual language (ref: the "Loom UI – Free UI Kit (Recreated)" Figma community file): an airy lavender-grey canvas, white cards with soft shadows, a "blurple" brand, and deep indigo hero surfaces.
- Tokens live in `src/app/globals.css`: `--paper` (canvas #F7F7FB), `--ink` (#1B1A3A), `--night` (hero indigo), `--brand` (#625DF5), `--brand-soft` (lavender tint), `--sun` (due soon/draft), `--coral` (overdue/failed), `--mint` (done/voiceprint), `--rec`, and `--speaker-0..5`. Use the Tailwind names (`bg-brand-soft`, `text-coral`, `bg-speaker-2`). **Never hardcode colors.** Add a token instead, for both light and `.dark`.
- Surfaces: cards are `rounded-xl border bg-card shadow-soft`; hover lift uses `shadow-lift`. Nav items and segmented filters are pills (`rounded-full`), with the active one on `bg-brand-soft` or `bg-primary`.
- Type: Onest for everything (`font-heading` = Onest bold, tight tracking). JetBrains Mono only for timecodes, `SPEAKER_00`, `№`, and `SED-…`. Eyebrows are `text-xs font-semibold tracking-wide text-primary uppercase`.
- Utilities: `.bg-hero` (indigo→blurple gradient with glows), `.text-gradient`, and `.marker-highlight` (evidence quotes). `SealStamp` still marks confirmed protocols.
- Status colors: brand = assigned/processing, sun = draft/in progress/due soon, mint = done/confirmed/voiceprint, coral = overdue/failed/unmatched.
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
