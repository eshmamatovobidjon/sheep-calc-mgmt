# Phase 08 - PostgreSQL and Alembic

| | |
|---|---|
| Status | Done |
| Depends on | Existing phases 01-06; no dependency on unfinished bot-only Phase 07 |
| Unblocks | 09 |
| Read first | [Roadmap](../mini-app-plan.md), [target architecture](../mini-app-architecture.md) sections 1, 2, 7, 11; [current architecture](../architecture.md) sections 4, 6 |

## Goal

The existing bot runs on PostgreSQL, the schema is managed by Alembic, and a demo loader fills an empty database. No API, no trip redesign.

The current SQLite data is test/demo only (owner decision 2026-10-31), so PostgreSQL starts empty. There is no SQLite import or reconciliation.

## Scope

Local development on the Mac only. Run PostgreSQL in Docker with a loopback-only port. Do not start a second poller with the token of a bot that is already running; use a separate development bot or stop the old one first.

## Tasks

1. Add `asyncpg` and `alembic` to `pyproject.toml`; drop `aiosqlite`. Note the reason in the handoff.
2. Add a `postgres:17` service to `docker-compose.yml` with a named volume and a health check. Publish the port as `127.0.0.1:5432` only. Add `POSTGRES_*` values and the new `DATABASE_URL` example to `.env.example`.
3. Change the `DATABASE_URL` default in `config.py` to PostgreSQL and remove the SQLite foreign-key hook from `db/session.py`.
4. Set up Alembic (`alembic.ini`, `migrations/env.py` using the async engine and `Base.metadata`). Create the baseline revision with autogenerate, then read it and fix anything wrong: FKs with `ON DELETE CASCADE`, unique keys, Numeric scales, BigInteger columns, plain-string enums.
5. Replace `create_all` in `init_db()` with nothing; the bot only seeds. Add a one-shot `migrate` Compose service (`alembic upgrade head`) that `bot` depends on with `condition: service_completed_successfully`. Locally, run `alembic upgrade head` before `python -m sheepbot`.
6. Implement `scripts/load_demo.py`: load `assets/demo/demo_trip_101.xlsx` and `demo_trip_102.xlsx` through `parse_trip_workbook` -> `save_trip` as the admin, then add fictional payments (some clients fully paid, some partly, some not at all, one small overpayment) and print a summary. It refuses to run if any trip already exists unless `--reset` is given; `--reset` empties the business tables after a typed confirmation (or `--yes`).
7. Update README run instructions and architecture sections 1, 4 and 6 to the PostgreSQL setup.

## Out of Scope

SQLite data import, reconciliation scripts, production deployment, backups automation, API, frontend, trip schema changes.

## Done When

- [x] `docker compose up -d postgres`, `alembic upgrade head` and `python -m sheepbot` start the bot on an empty PostgreSQL database.
- [x] `alembic check` reports no difference between models and migrations.
- [x] `load_demo.py` fills an empty database; trips 101/102 totals match the Phase 03 table in AGENTS.md; a second run without `--reset` refuses.
- [ ] Bot flows work on PostgreSQL: access request/approval, template, upload and re-upload ("ЗАМЕНИТ"), clients, payment and deletion, all PDF/XLSX reports. *Services and report builders verified offline; chat flows still to be clicked through in Telegram.*
- [x] Data survives `docker compose restart postgres`.
- [x] `ruff format . && ruff check .` pass.

## Handoff

Done 2026-10-31; details in the AGENTS.md Phase 08 handoff note. PostgreSQL 17, asyncpg 0.32.0, Alembic 1.20.1, baseline revision `0001`. Verified commands are in README.