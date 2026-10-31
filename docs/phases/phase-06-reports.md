# Phase 06 — Reports

| | |
|---|---|
| **Depends on** | 04, 05 |
| **Can run in parallel with** | — |
| **Unblocks** | 07 |
| **Read first** | [AGENTS.md](../../AGENTS.md), [architecture.md](../architecture.md) sections 3, 7, 9, 10, 11; [analysis-and-plan.md](../analysis-and-plan.md) 3.6 and 7.8 |

## Goal

Users with View permission get three reports, each as **PDF or XLSX**: client statement, trip summary, debtors. Plus quick in-chat lists of debtors and trips.

## Starting point

Phases 01–05 are done: trips are saved with computed fields; payments and `services/balances.py` exist; `bot/client_picker.py` is available.

## Tasks

1. **Fonts**: add `DejaVuSans.ttf`, `DejaVuSans-Bold.ttf` and the DejaVu license to `src/sheepbot/reports/fonts/`; register them in ReportLab once.
2. **`reports/data.py`**
   - `statement_data(session, client_id, date_from | None, date_to | None) -> StatementData`
     - Opening balance = balance before `date_from` (0 for "all time").
     - Lines sorted by date, shipments before payments on the same day, then by id. Each line: date, type (Отгрузка / Оплата), trip number and day, product, heads, gross kg, total discount kg, net kg, price/kg, amount, payment method, note, **running balance**.
     - Totals: shipped, paid; closing balance.
   - `trip_summary_data(session, trip_id) -> TripSummaryData` — built from `TripTotals` (architecture section 7) so numbers match the upload preview:
     - Header: number, dates, rates.
     - Purchase by type: heads, gross, discount, net kg, avg price KZT, KZT, UZS.
     - Expenses: item, qty, price, currency, amount, UZS.
     - Sales by day, by product (heads, net kg, avg price, amount) and by client (net kg, amount).
     - Revenue, cost, profit, margin %; cost per kg vs avg sale price per animal type.
   - `debtors_data(session) -> DebtorsData`: clients with balance ≠ 0, sorted by balance descending; total.
3. **`reports/xlsx_builder.py`** and **`reports/pdf_builder.py`**: `build_statement_*`, `build_trip_summary_*`, `build_debtors_*` following architecture section 10 (real numbers, `=SUM` totals, number formats, header/footer, page numbers). The trip summary XLSX may use one sheet per section.
4. **`/report` and "Отчёты"** (`handlers/reports.py`, View permission):
   - **Выписка по клиенту** → client picker → period **Всё время / Этот месяц / Прошлый месяц / Указать даты** (`ДД.ММ.ГГГГ – ДД.ММ.ГГГГ`) → **PDF / Excel** → file.
   - **Итоги рейса** → last 10 trips as buttons (`№101 · 22.10.2026`) → **PDF / Excel** → file.
   - **Должники** → **PDF / Excel** → file.
   - While building: send the "upload document" chat action.
5. **`/debts` and "Должники"**: in-chat list of the top 30 debtors (`Клиент — 85 155 400`) and the total, with an inline **Скачать Excel** button.
6. **`/trips` and "Рейсы"**: last 10 trips (`№101 · 22.10.2026 · выручка … · прибыль …`), each with a button for its trip summary (asks PDF / Excel).

## Out of scope

Debt aging, cash-flow report, scheduled reports, transfers in statements (all after MVP).

## Done when

- [ ] With both demo trips and a few payments loaded: the statement for a client present in both trips shows lines from both, a correct running balance, and a closing balance equal to the client's balance in `/clients`.
- [ ] A period statement's opening balance + period movements = closing balance.
- [ ] The trip summary's revenue, cost and profit equal the upload preview for that trip.
- [ ] The debtors total equals the sum of all positive and negative balances listed.
- [ ] PDFs render Cyrillic correctly, with page numbers; XLSX numbers are numeric and totals are formulas.
- [ ] An Upload-only user cannot open reports.

## Handoff

Update the Status column and add a handoff note in [AGENTS.md](../../AGENTS.md).
