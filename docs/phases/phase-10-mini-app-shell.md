# Phase 10 - Mini App Shell and Client List

| | |
|---|---|
| Status | Done |
| Depends on | 09 |
| Unblocks | 11 |
| Read first | [Roadmap](../mini-app-plan.md), [target architecture](../mini-app-architecture.md) sections 2-5, 9 |

## Goal

The Mini App opens inside Telegram, authenticates, and shows the real client list with balances.

## Tasks

1. Create `web/` with Vite + React + TypeScript (strict), React Router and TanStack Query. Commit `package-lock.json`. Scripts: `dev`, `build`, `lint`, `typecheck`.
2. Load `telegram-web-app.js`; wrap what is used (`ready`, `expand`, `initData`, theme params, `BackButton`) in one small module.
3. One API client that adds `Authorization: tma <initData>` to every request and turns error responses into readable messages. A 401/403 shows a screen telling the user to reopen the app or ask the admin for access.
4. API: `GET /clients` (search `q`, filter debt/credit/zero, `limit`/`offset`) and `GET /clients/{id}` (shipped, paid, balance), using the existing client and balance services.
5. Screens: client list with search and filter, client detail with balance. Back returns to the list with the search kept. Bottom navigation shows only destinations the user may open (just Clients for now).
6. Russian strings in one module; Telegram theme colors; debt and credit labelled in text, not only by color.
7. The API serves `web/dist` at `/` with an SPA fallback after the API routes. Vite proxies `/api` in development.
8. Bot: if `MINI_APP_URL` is set, set the chat menu button to open it, and set the Russian bot description and short description (carried over from Phase 07).
9. For a real Telegram check, with the owner's approval, expose the local app through a temporary HTTPS tunnel and point a development bot's menu button at it.

## Out of Scope

Writes, payments, reports, trips, offline support.

## Done When

- [x] A development bot opens the app in Telegram on a phone and on Desktop; the client list shows real balances. (Opened by the owner from the current bot's menu button through a Cloudflare quick tunnel; API logs show authenticated `/me`, list, filters and details with 200.)
- [x] Accountant, viewer and admin see the list; unknown/blocked users see the no-access screen. (API checks from Phase 09 + browser access screen.)
- [x] Search, filter, detail and back navigation work.
- [x] Layout is usable on a 360 px phone and on desktop, in light and dark themes.
- [x] Refreshing a nested route works; unknown `/api/...` paths return JSON 404.
- [x] Bot commands still work with `MINI_APP_URL` unset. (Bot starts, profile calls succeed, polling runs; commands not re-clicked by hand.)
- [x] Ruff plus frontend lint/typecheck/build pass.

## Handoff

Done 2026-10-31; details in the AGENTS.md Phase 10 note and architecture sections 9a/9b.