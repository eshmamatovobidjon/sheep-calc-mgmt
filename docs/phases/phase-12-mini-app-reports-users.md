# Phase 12 - Reports and Users

| | |
|---|---|
| Status | Done |
| Depends on | 11 |
| Unblocks | 13; Release A |
| Read first | [Roadmap](../mini-app-plan.md), [target architecture](../mini-app-architecture.md) sections 4, 10 |

## Goal

Trips, debtors and reports can be viewed and downloaded in the app, and the admin manages users there. Trips still come in through the bot's Excel upload.

## Tasks

1. `GET /trips` (recent, paginated) and `GET /trips/{number}` with the `TripTotals` figures: purchases, expenses, revenue, cost, profit and return on cost (`margin_pct`, profit/cost).
2. `GET /debtors`: clients with non-zero balance and totals for debt, credit and net, from `debtors_data`.
3. `GET /reports/{kind}?format=pdf|xlsx` for `statement` (client, optional period), `trip` and `debtors`, using the existing data loaders and builders in `asyncio.to_thread`. Return the file with a safe filename and `Cache-Control: no-store`.
4. `POST /reports/{kind}/send`: the bot sends the same file to the requesting user's own chat. If the user never started the bot, return a clear message.
5. Screens: Trips list and trip summary; Debtors; Reports (choose report, client/trip/period, format, then "Скачать" or "Отправить в чат").
6. `GET /users` and `PATCH /users/{id}` (approve, block/unblock, Upload/View) reusing `services/users.py`. Granting a permission to a pending user activates them, and the bot notifies them as it does today. The configured admin cannot be changed.
7. Users screen for the admin, with pending users at the top.
8. Navigation: Clients, Trips, Payments (Upload), More -> Reports (View), Users (admin).

## Manual Checks

- Trip summary in the app, bot, PDF and XLSX show the same revenue, cost and profit for demo trips 101/102.
- Statement closing balance equals the client balance; a period statement's opening + shipped - paid = closing.
- Debtors totals equal the sum of client balances.
- PDF/XLSX open correctly; Cyrillic text renders; "Отправить в чат" delivers to the requester only.
- A user without View gets 403 on report endpoints.
- Admin approves a pending user, removes Upload from an accountant (their next write gets 403), blocks a user; the bot's `/users` shows the same state.

## Release A Walkthrough (fictional data)

1. A new staff member presses /start in the bot; the admin approves them in the app.
2. An accountant records a payment and deletes a mistaken one.
3. A viewer checks debtors and sends a statement PDF to their chat.
4. An accountant uploads `demo_trip_101.xlsx` through the bot; the app's trip and debtor screens show the same numbers.

Record friction points in the handoff. Running this with real users requires Phase 15 first.

## Out of Scope

Report scheduling, sending reports to customers, debt aging, audit view, report limits.

## Done When

- [x] All report types work as screens and as PDF/XLSX with matching figures.
- [x] User administration works from the app and agrees with the bot. (Same services and transitions; checked through the API and the Users screen.)
- [x] Manual checks and the walkthrough pass. (Walkthrough steps covered individually in the browser and API; a full run in real Telegram by the owner is still recommended.)
- [x] Ruff plus frontend lint/typecheck/build pass.

## Handoff

Done 2026-10-31; details in the AGENTS.md Phase 12 note and architecture sections 9a/9b.