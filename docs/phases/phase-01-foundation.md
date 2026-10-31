# Phase 01 — Foundation

| | |
|---|---|
| **Depends on** | — |
| **Unblocks** | all other phases |
| **Read first** | [AGENTS.md](../../AGENTS.md), [architecture.md](../architecture.md) sections 1–7, 9, 11, 12 |

## Goal

A runnable project skeleton: config, logging, the full DB schema, seed data, shared domain helpers, and a bot that starts and answers `/start`. Runs locally and in Docker.

## Starting point

The repo contains only `README.md`, `AGENTS.md` and `docs/`.

## Tasks

1. **Project files**
   - `pyproject.toml`: package `sheepbot`, `src/` layout, Python ≥ 3.12. Dependencies: `aiogram>=3`, `SQLAlchemy>=2`, `aiosqlite`, `pydantic-settings`, `openpyxl`, `reportlab`. Optional `dev` extra: `ruff`. Ruff config: line length 100.
   - `.gitignore`: Python artefacts, `.venv/`, `.env`, `storage/`, `.DS_Store`.
   - `.env.example` with all variables from architecture section 4.
2. **Package skeleton**: create every package and module from architecture section 2 with `__init__.py` files. Modules owned by later phases may be empty (a one-line docstring is enough).
3. **Config and logging**: `config.py` (`Settings`, cached `get_settings()`); `log.py` (`setup_logging(level)`, readable single-line format).
4. **Domain**
   - `domain/enums.py`: all enums and Russian labels from architecture section 5, plus reverse label lookup helpers.
   - `domain/catalog.py`: `PRODUCT_CATALOG` — the product table from architecture section 5 as plain data (used by the seed, the template and the parser).
   - `domain/formatting.py`: all functions from architecture section 11.
5. **Database**
   - `db/base.py`: `DeclarativeBase` and a timestamp mixin (`created_at`, `updated_at`).
   - `db/models.py`: **all** MVP tables from architecture section 6, with relationships and cascade on trip children.
   - `db/session.py`: async engine from `DATABASE_URL`, `async_sessionmaker`, `init_db()` that creates `STORAGE_DIR` (and `uploads/`) and runs `create_all`. Enable SQLite foreign keys (`PRAGMA foreign_keys=ON`).
   - `db/seed.py`: `seed(session)` — idempotent upsert of the product catalog (architecture section 5) and of the admin `bot_user` (`ADMIN_TELEGRAM_ID`, `is_admin=True`, `can_upload=True`, `can_view=True`, `status=active`).
6. **Shared client helpers** (`services/clients.py`): `normalize_client_name(name) -> str` and `get_or_create_client(session, name, created_by_id) -> Client`. Phases 04 and 05 build on these.
7. **Bot shell**
   - `bot/middlewares.py`: `DbSessionMiddleware` (commit on success, rollback on error) — see architecture section 3.
   - `bot/handlers/common.py`: a router with a placeholder `/start` reply ("Бот работает"). Phase 02 replaces it.
   - `bot/handlers/__init__.py`: `ROUTERS = [common.router]`.
   - `bot/app.py`: build `Bot` and `Dispatcher(storage=MemoryStorage())`, register middleware and routers; on startup run `init_db()` and `seed()`.
   - `__main__.py`: `setup_logging`, then `asyncio.run(main())`.
8. **Docker**
   - `Dockerfile`: `python:3.12-slim`, install the package, run `python -m sheepbot`, working dir `/app`, `storage/` as a volume.
   - `docker-compose.yml`: one service `bot`, `env_file: .env`, volume `./storage:/app/storage`, `restart: unless-stopped`.
9. **README**: short "Run locally" and "Run with Docker" sections.

## Out of scope

Access control, menus, any feature handlers, template, reports.

## Done when

- [ ] `pip install -e ".[dev]"` works; `ruff format --check .` and `ruff check .` are clean.
- [ ] `python -m sheepbot` with a valid `.env` starts polling without errors.
- [ ] `/start` gets a reply.
- [ ] `storage/app.db` exists with all tables; `product` has 9 rows; the admin row exists. Restarting does not duplicate rows.
- [ ] `docker compose up -d --build` runs the bot; the DB persists in `./storage` across restarts.

## Handoff

Update the Status column and add a handoff note in [AGENTS.md](../../AGENTS.md).
