# Phase 09 - API and Telegram Authentication

| | |
|---|---|
| Status | Done |
| Depends on | 08 |
| Unblocks | 10 |
| Read first | [Roadmap](../mini-app-plan.md), [target architecture](../mini-app-architecture.md) sections 2-6 |

## Goal

A FastAPI app that authenticates Mini App users from Telegram `initData`, applies the bot's permissions and reuses existing services. No screens yet.

## Tasks

1. Add `fastapi` and `uvicorn`. Create `src/sheepbot/api/app.py` with its own entry point (`python -m sheepbot.api` or `uvicorn sheepbot.api.app:app`). The API never starts bot polling.
2. Add a session dependency (one `AsyncSession` per request). Write endpoints commit explicitly before returning.
3. Implement `api/auth.py`: read `Authorization: tma <initData>`, validate with aiogram's `safe_parse_webapp_init_data`, reject `auth_date` older than `WEBAPP_AUTH_MAX_AGE_HOURS` (default 24), load the `bot_user`, and return 401/403 as described in the target architecture. Add `require(Perm.X)` dependencies that reuse the bot's permission logic.
4. Add the dev-only shortcut: `APP_ENV=dev` plus `DEV_AUTH_TELEGRAM_ID` acts as that user when no initData is sent, with a startup warning.
5. Implement `GET /api/v1/me` (name, admin flag, permissions) and `GET /api/v1/catalog` (products, animal types, currencies, payment methods with Russian labels).
6. Add the error format from the target architecture and a `GET /api/v1/health` that checks the DB connection.
7. Add an `api` service to `docker-compose.yml` sharing the image, `.env` and uploads volume; it depends on `migrate`.
8. Document the run commands in README and the new settings in architecture section 4.

## Manual Checks

Use a small script or `curl` with initData signed by the development bot token.

| Input | Expected |
|---|---|
| Valid initData, active user | 200 with correct permissions |
| Tampered hash or user | 401 |
| initData older than the max age | 401 |
| Valid initData, unknown/pending/blocked user | 403 |
| View-only user on an Upload endpoint (once one exists) | 403 |
| Admin blocks the user, next request | 403 |
| No Authorization header, `APP_ENV` not `dev` | 401 |

## Out of Scope

Session tables, logout, idempotency keys, audit log, rate limiting, CORS, frontend.

## Done When

- [x] Bot and API run side by side on the same PostgreSQL database.
- [x] All manual checks above give the expected result. (View-only on an Upload endpoint checked through `require(Perm.UPLOAD)` directly; no Upload endpoint exists yet.)
- [x] `/api/docs` (OpenAPI) shows `/me`, `/catalog`, `/health`.
- [x] The Authorization header and initData do not appear in logs.
- [x] `ruff format . && ruff check .` pass.

## Handoff

Done 2026-10-31; details in the AGENTS.md Phase 09 handoff note and architecture section 9a. FastAPI 0.162.0, Uvicorn 0.54.0. Run: `docker compose up -d --build` (service `api`, `127.0.0.1:8000`) or `python -m sheepbot.api`. Manual checks used initData signed locally with the bot token by an inline script (not committed).