# AGENTS.md

Context for AI coding agents working in this repository. Read this file first, then [docs/architecture.md](docs/architecture.md), then the phase document you were assigned.

## Project in short

A Telegram bot for a sheep-meat trading business:

- **Accountants** download a strict Excel template, fill in one **trip (рейс)**: purchase in Kazakhstan, trip expenses, sales to clients in Tashkent. They upload it; the bot validates, previews and saves it.
- Clients buy on credit and pay later. Accountants record **payments** in the bot.
- Users with **View** permission get reports (client statement, trip summary, debtors) as **PDF or XLSX**.
- One **admin** approves users and grants permissions.

Current goal: an **MVP for a business demo**, happy path only. Bot UI and reports are in **Russian**.

## Documents

| Document | Use it for |
|---|---|
| [docs/analysis-and-plan.md](docs/analysis-and-plan.md) | Business flow, decisions (D1–D13), MVP scope, open assumptions |
| [docs/architecture.md](docs/architecture.md) | **Binding contracts**: layout, layering, config, enums, DB schema, calculations, template spec, bot and report conventions |
| [docs/phases/](docs/phases/) | One self-contained brief per phase |

## Phases

| # | Phase | Depends on | Can run in parallel with | Status |
|---|---|---|---|---|
| 01 | [Foundation](docs/phases/phase-01-foundation.md) | — | — | Done |
| 02 | [Access control and bot shell](docs/phases/phase-02-access-control.md) | 01 | 03 | Done |
| 03 | [Template and demo data](docs/phases/phase-03-template-and-demo-data.md) | 01 | 02, 05 | Done |
| 04 | [Trip upload](docs/phases/phase-04-trip-upload.md) | 01, 02, 03 | 05 | Done |
| 05 | [Clients and payments](docs/phases/phase-05-clients-and-payments.md) | 01, 02 | 03, 04 | Not started |
| 06 | [Reports](docs/phases/phase-06-reports.md) | 04, 05 | — | Not started |
| 07 | [Deployment and demo prep](docs/phases/phase-07-deployment-and-demo.md) | 01–06 | — | Not started |

```mermaid
flowchart LR
  P1[01 Foundation] --> P2[02 Access]
  P1 --> P3[03 Template]
  P2 --> P4[04 Upload]
  P3 --> P4
  P2 --> P5[05 Clients & payments]
  P4 --> P6[06 Reports]
  P5 --> P6
  P6 --> P7[07 Deploy & demo]
```

## Working rules

1. **Stay in scope.** Build only what your phase document lists. Items marked "after MVP" are out of scope.
2. **Follow the contracts** in `docs/architecture.md`. If you must change one, update that file in the same change and mention it in the handoff notes below.
3. **Happy path first.** Handle the obvious user mistakes listed in your phase; don't chase rare edge cases.
4. **No automated tests for now** (project decision for the MVP). Verify manually using the "Done when" checklist of your phase.
5. **Language:** user-facing text in Russian; code, identifiers, comments, docs in English.
6. **Code style:** Python 3.12, type hints, `async` for DB and bot code, `Decimal` for kg and money calculations, ruff format + check clean. Keep comments short and only where the code can't speak for itself.
7. **Privacy:** never commit secrets, `storage/`, real sample files, or real client names/phones. Real samples live outside the repo (parent folder) and are reference only.
8. **Don't add dependencies** beyond the stack in `docs/architecture.md` without noting why in the handoff.

## Commands

```bash
python3.12 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env            # set BOT_TOKEN and ADMIN_TELEGRAM_ID
python -m sheepbot              # run the bot (long polling)
ruff format . && ruff check .   # format + lint
docker compose up -d --build    # run in Docker
```

## Glossary

| Term | Meaning |
|---|---|
| Рейс / reys / trip | One truck: purchase in Kazakhstan → sale in Tashkent. Unique by number. |
| Фура | Truck |
| Кун / день | Sales day of a trip (1, 2, 3 …) |
| Совлик, Кучкор, Кузи, Эчки | Ewe, ram, lamb, goat (carcasses) |
| Скидка | Weight discount. Purchase: kg per batch. Sale: kg per head from the product code, e.g. `SOV (-1KG)` = 1 kg per head |
| Брутто / нетто | Scale weight / weight after discount |
| Збой / субпродукты | By-products: думба, жигар, лахат, чарви, упка |
| Выписка (hisobot) | Client statement: shipments, payments, running balance |
| Долг / баланс | Client balance; positive = client owes |
| Бухгалтер | Accountant; user with Upload permission |

## Handoff notes

Each phase appends a short entry here when done: what was built, deviations from the docs, anything the next phase must know. Also update the **Status** column above.

### Phase 01 — Foundation

- Built: project files, full package skeleton (later-phase modules are one-line docstrings), config/logging, enums + catalog + formatting, all MVP tables, idempotent seed, `services/clients.py` helpers, `DbSessionMiddleware`, placeholder `/start`, Docker.
- DB access: use `get_engine()` / `get_sessionmaker()` from `db/session.py` (both cached, created lazily). `seed()` flushes but does not commit; `bot/app.py:prepare_db()` commits.
- `DbSessionMiddleware` is registered as `dp.update.outer_middleware`. Register `AuthMiddleware` the same way **after** it, so it can use `data["session"]`.
- Enums are stored by value via `db/base.py:str_enum()`. Reverse label lookup: `domain/enums.py:enum_from_label(labels, text)` plus per-enum wrappers like `animal_type_from_label()` (trimmed, case-insensitive, `ё`=`е`).
- `domain/catalog.py` also exports `PRODUCT_CODES` and the `ProductDef` dataclass.
- Models use `import datetime as dt` because columns named `date` would shadow the `date` type in annotations. Relationships use default lazy loading, so use `selectinload` in async code.
- Deviations: UZS columns are `BigInteger` (still whole so'm; same as INTEGER in SQLite, but no int32 overflow on other DBs). Dependency is `SQLAlchemy[asyncio]` because the async engine needs `greenlet`. `Client.name` also collapses inner whitespace. `bot/texts.py` holds `START_PLACEHOLDER`. The Dockerfile installs the `tzdata` OS package for `zoneinfo`. Added `.dockerignore`.
- Not verified here: live polling and `/start` with a real token; `docker compose up` persistence.

### Phase 02 — Access control and bot shell

- Built: `services/users.py`, `AuthMiddleware`, `HasPermission`, `texts.py` (every `BTN_*` and the `COMMANDS` list), `keyboards.py` (`main_menu`, `cancel_keyboard`, `MENU_ITEMS`, `find_menu_item`), `/start`, `/menu`, `/cancel`, the access request card, `/users`, the fallback router, the global error handler and `set_my_commands`.
- **Adding a feature router:** insert it into `ROUTERS` **between** `common.router` (first) and `common.fallback_router` (last). Because `common.router` comes first, `/start`, `/menu`, `/cancel` and "Отмена" work in any FSM state.
- **Gating a feature:** put `router.message.filter(HasPermission(Perm.X))` and `router.callback_query.filter(...)` on the router, as in `handlers/users.py`. If the filter fails, the update reaches the fallback. The fallback replies "Нет доступа" for known buttons/commands the user may not use, "Функция в разработке" for permitted ones without a handler, and "Не понял" otherwise.
- Handlers receive `session: AsyncSession` and `user: BotUser | None` from the middlewares. `users.is_allowed(user)` means the user has at least one permission.
- Messages use HTML parse mode, so escape user-provided text with `html.escape`.
- Unhandled exceptions: `common.on_error` logs them and replies with `texts.ERROR_GENERIC`. The DB session has already been rolled back by then.
- Deviations: `Perm` is defined in `domain/enums.py` (services need it) and re-exported from `bot/filters.py`. `AuthMiddleware` refreshes the stored `full_name`/`username` from Telegram, so the seeded admin name gets replaced. When the admin turns on a permission in `/users` for a pending user, that user is activated and notified. Unknown users who send anything other than `/start` get "Отправьте /start…". `/users` lists every user except the admin.
- Verified offline by feeding fake updates through the dispatcher: request → grant/reject, permission-gated menus, `/users` toggles, block/unblock, fallback replies. Not yet verified with live Telegram accounts.

### Phase 03 — Template and demo data

- Built: `excel/template_spec.py`, the new `excel/template_builder.py`, `scripts/build_template.py`, `scripts/build_demo_files.py`, `assets/templates/trip_template_v1.xlsx`, `assets/demo/demo_trip_101.xlsx` and `demo_trip_102.xlsx`, and `/template` plus the "Шаблон" button (Upload permission).
- **Contract changes** (architecture sections 2 and 8 are updated):
  - New module `excel/template_builder.py`. `build_template(trip, rows)` returns the workbook as `.xlsx` bytes; with no data it returns the blank template.
  - `ColumnSpec` gained `gt` / `ge` (numeric lower bounds) and `width`.
  - `header` is stored without `*`; `display_header` adds it for required columns.
- **For the parser (Phase 04):**
  - Use `DATA_SHEETS` / `TABLE_SHEETS`, `SheetSpec.column(key)` and `normalize_header()`.
  - The `Рейс` sheet is key/value: rows 2–7 follow the order of `TRIP_SHEET.columns`, values are in column B, and row 1 is `Поле | Значение`.
  - `Продажи.heads` is `required=False` in the spec; the parser must require it for animal products.
  - Column keys: purchases `date, animal_type, heads, gross_kg, discount_kg, price_kzt, note`; expenses `item, qty, unit_price, currency, note`; sales `day, date, client, product, heads, gross_kg, price_thousand_uzs, note`.
- The bot builds the template in memory (cached), so the Docker image doesn't need `assets/`.
- `Справочник` layout: `A1` = version; columns B/C/D hold the Тип / Валюта / Товар lists (header in row 1, values from row 2). Dropdowns cover data rows 2–1000.
- In the demo files, some expenses leave `Кол-во` empty, which tests the "defaults to 1" rule.
- Demo numbers from the generator, computed with the section 7 rounding rules. Phase 04's preview should match them.

  | File | Закуп rows | Heads | Gross kg | Net kg | Продажи lines | Clients | Sold heads | Cost UZS | Revenue UZS | Profit |
  |---|---|---|---|---|---|---|---|---|---|---|
  | `demo_trip_101.xlsx` | 10 | 606 | 20 750.9 | 19 252.7 | 51 | 13 | 606 | 1 868 413 480 | 1 990 946 550 | 122 533 070 (6.6%) |
  | `demo_trip_102.xlsx` | 9 | 602 | 20 724.9 | 19 247.9 | 56 | 13 | 602 | 1 866 720 696 | 2 026 045 700 | 159 325 004 (8.5%) |

  Trips 101 and 102 share 11 of the 15 fictional clients.
- Not verified here: opening the files in Excel or LibreOffice (LibreOffice isn't installed on this machine).

### Phase 04 — Trip upload

- Built: `domain/calculations.py`, `excel/parser.py`, `services/trips.py`, and `handlers/upload.py` (the "Загрузить рейс" prompt, `.xlsx` documents, Сохранить/Отмена with callback prefix `upl`).
- **Calculations:**
  - `trip_totals(purchase_lines, expense_uzs_values, sale_lines) -> TripTotals`. Inputs are the plain `PurchaseLine` / `SaleLine` dataclasses, so Phase 06 can build them from DB rows. A `SaleLine` needs `client_key` (from `normalize_client_name`) and `client_name`.
  - `TripTotals` holds `purchases` / `sales` groups plus by-type, by-day, by-product and by-client groups. It has properties `revenue_uzs`, `cost_uzs`, `profit_uzs`, `margin_pct`, and methods `cost_per_kg(type)` and `avg_sale_price(type)`.
  - The rounding helpers live in the same module.
- **Services:**
  - `trips.compute_trip(parsed, products)` gives per-row computed values plus totals. Preview and save both use it, so their numbers always match.
  - `save_trip` deletes an existing trip with the same number (children go via DB `ON DELETE CASCADE`), creates missing clients, inserts all rows, and marks the upload `saved`.
- **Uploads:**
  - Files are stored as `storage/uploads/<sha256>.xlsx`; identical files are stored once. Every upload gets its own `upload` row.
  - Only the uploader or the admin can press Save/Cancel on a pending upload. A stale button replies "Действие устарело".
  - Parsing runs in a worker thread (`asyncio.to_thread`).
- **Parser:**
  - Sheet names and headers are compared with `normalize_header`. Product codes and choice values are trimmed and case-insensitive (`ё`=`е`).
  - Numbers accept `,` or `.` and spaces. Integers must be whole. Errors are capped at 50, and `ParseResult.too_many_errors` flags the cut. Each sheet allows at most 5,000 rows.
  - If a sheet has a wrong header, its rows are skipped to avoid cascading errors.
- **Additions to the docs:**
  - `formatting.fmt_percent()` and `formatting.plural(n, forms)` (Russian plural forms).
  - The architecture doc now allows Russian validation messages in `excel/parser.py`.
  - The fallback answers "Нет доступа" to documents from users without Upload permission.
- Verified offline (fake updates through the dispatcher):
  - Both demo files preview and save, and the preview totals equal the Phase 03 table.
  - A re-upload shows "ЗАМЕНИТ" and the row counts stay at 10/6/51.
  - Clients go to 13, then to 15 after trip 102, with no duplicates.
  - A broken file is reported with sheet, row and column. `.pdf`, a file larger than 10 MB, a non-Excel `.xlsx`, and a View-only user all get a clear refusal.
