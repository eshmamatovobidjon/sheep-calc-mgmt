# Phase 07 — Deployment and Demo Prep

| | |
|---|---|
| **Depends on** | 01–06 |
| **Read first** | [AGENTS.md](../../AGENTS.md), [architecture.md](../architecture.md) sections 1, 4, 12; [analysis-and-plan.md](../analysis-and-plan.md) section 8 |

## Goal

The bot runs on a server, is loaded with realistic demo data, and a walkthrough for the business demo is ready.

## Relationship to the Mini App Track

This unfinished brief remains the legacy bot-only deployment option. It is not a prerequisite for [phases 08-15](../mini-app-plan.md): demo loading moves into [Phase 08](phase-08-postgresql.md), bot profile/launch into [Phase 10](phase-10-mini-app-shell.md), and production deployment/walkthrough into [Phase 15](phase-15-mini-app-rollout.md). Do not implement this SQLite reset procedure against PostgreSQL or mark Phase 07 complete merely because its tasks were planned elsewhere.

## Starting point

All features (phases 01–06) work locally.

## Tasks

1. **`scripts/load_demo.py`**
   - `--reset` deletes `storage/app.db` (asks for confirmation unless `--yes`), then `init_db()` + `seed()`.
   - Loads `assets/demo/demo_trip_101.xlsx` and `demo_trip_102.xlsx` through the **same** code path as the bot (`parse_trip_workbook` → `save_trip`), as the admin user.
   - Adds fictional payments over the weeks after each trip, mixed methods: some clients fully paid, some partially, a few with no payments and one small overpayment — so the debtors list looks realistic.
   - Prints a short summary (trips, clients, payments, total debt).
2. **Docker hardening**: run as a non-root user; `.dockerignore` (`.venv`, `.git`, `storage`, `.env`); keep image small.
3. **Bot profile**: `set_my_description` and `set_my_short_description` in Russian on startup.
4. **README → "Deploy to a server"**: install Docker; clone; create `.env`; `docker compose up -d --build`; view logs; update (`git pull` + rebuild); back up = copy `storage/`; load demo data inside the container.
5. **README → "Demo walkthrough"** (Russian-speaking audience, steps in English are fine):
   1. New user → `/start` → admin approves as accountant; another as viewer.
   2. Accountant: **Шаблон** → show the instructions sheet.
   3. Accountant: upload a broken file → precise errors; upload `demo_trip_101.xlsx` → preview → **Сохранить**.
   4. Accountant: **Оплата** → record a payment → debt goes down; **Последние оплаты** → delete one.
   5. Viewer: **Должники** → list; **Отчёты** → client statement PDF, trip summary Excel.
   6. Re-upload a corrected trip file → "ЗАМЕНИТ" → numbers update.
   7. Collect feedback; list the MVP assumptions (analysis 9.1) to confirm.

## Out of scope

PostgreSQL, backups automation, monitoring, CI (after MVP).

## Done when

- [ ] On a clean server, the README steps bring the bot up with `docker compose`.
- [ ] `load_demo.py --reset --yes` produces a populated DB; reports show both trips and realistic debts.
- [ ] The full walkthrough runs end to end without errors.

## Handoff

Update the Status column and add a final handoff note in [AGENTS.md](../../AGENTS.md) with known gaps to raise after the demo.
