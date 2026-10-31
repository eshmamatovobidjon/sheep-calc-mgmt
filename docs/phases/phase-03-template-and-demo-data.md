# Phase 03 — Template and Demo Data

| | |
|---|---|
| **Depends on** | 01 |
| **Can run in parallel with** | 02, 05 |
| **Unblocks** | 04 (parser uses the spec and demo files) |
| **Read first** | [AGENTS.md](../../AGENTS.md), [architecture.md](../architecture.md) sections 5, 8, 12; [analysis-and-plan.md](../analysis-and-plan.md) sections 3 and 5 |

## Goal

Define the trip template once in code, generate the blank Excel template from it, generate realistic **fictional** demo trip files, and let accountants download the template from the bot.

## Starting point

Phase 01 is done (enums, product catalog). Phase 02 may or may not be done: if `HasPermission` and `texts.BTN_TEMPLATE` don't exist yet, add the handler last and coordinate via the handoff notes.

## Tasks

1. **`excel/template_spec.py`**: `TEMPLATE_VERSION`, `ColumnSpec`, `SheetSpec`, and the specs for `Рейс`, `Закуп`, `Расходы`, `Продажи` exactly as in architecture section 8. Choice lists come from `domain/enums.py` labels and `domain/catalog.py:PRODUCT_CATALOG` (don't duplicate them).
2. **`scripts/build_template.py`** → `assets/templates/trip_template_v1.xlsx`:
   - Sheets in order: `Инструкция`, `Рейс`, `Закуп`, `Расходы`, `Продажи`, `Справочник` (hidden).
   - Bold header row, frozen panes, sensible column widths; `DD.MM.YYYY` format on date columns, `0.0` on kg columns.
   - Dropdowns (data validation) for Тип, Валюта and Товар, sourced from `Справочник`. `Справочник!A1` = `TEMPLATE_VERSION`.
   - `Рейс`: field names in column A (rows 2–7), values in column B.
   - `Инструкция` (Russian): what each sheet is for; required fields (`*`); units (purchase price in KZT/kg, sale price in **thousand** so'm/kg, rates in so'm per 1 KZT / 1 USD); what product codes mean (`SOV (-1KG)` = Совлик, 1 kg discount per head); "don't rename sheets or headers; no empty rows inside a table; no formulas needed — the bot calculates everything"; payments are **not** in this file (they're entered in the bot).
3. **`scripts/build_demo_files.py`** → `assets/demo/demo_trip_101.xlsx` and `assets/demo/demo_trip_102.xlsx`, written through the same spec (filled template). Deterministic (fixed random seed). **Fictional names only** — don't use names from the real samples.
   - ~15 fictional clients, most appearing in both trips (so statements span trips).
   - Purchases: ~550–650 heads per trip across all 4 types; ~30–40 kg gross per head; discount ≈ 6–8% of gross; prices 2,400–4,100 KZT/kg (echki cheapest, quzi highest).
   - Expenses: e.g. Мясник (qty = heads, 1,200 KZT), Грузчики (KZT), Документы (USD), Водитель (USD), Арава (qty = heads, 7,000 UZS), Прочее (UZS).
   - Rates: KZT ≈ 26.8, USD ≈ 11,900.
   - Sales: 2–3 days, 40–70 lines; heads sold ≈ heads bought; animal prices 105–126 thousand so'm/kg; a few by-product lines (CHARVI, UPKA, JIGAR…) at 17–45 thousand so'm/kg.
   - Resulting profit should be positive and plausible (roughly 5–10% of cost).
   - Trip 102 departs about a week after trip 101.
4. **`/template` and "Шаблон"** (`handlers/template.py`, Upload permission): send `trip_template_v1.xlsx` as a document with a short caption: "Заполните и отправьте файл в этот чат."
5. **README**: how to regenerate the template and demo files.

## Out of scope

Parsing uploads (phase 04). Client dropdown and template version check (after MVP).

## Done when

- [ ] `python scripts/build_template.py` and `python scripts/build_demo_files.py` produce the files; both open in Excel and LibreOffice without warnings.
- [ ] Dropdowns work; `Справочник` is hidden; the instructions read well in Russian.
- [ ] Demo files follow the spec exactly (same sheets, headers, column order) and contain no formulas.
- [ ] An Upload user gets the template from `/template` and the "Шаблон" button; a View-only user does not.

## Handoff

Update the Status column and add a handoff note in [AGENTS.md](../../AGENTS.md), including per demo file: heads and gross kg in `Закуп`, number of sale lines and clients in `Продажи` (phase 04 uses them to sanity-check its preview).
