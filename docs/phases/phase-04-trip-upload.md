# Phase 04 — Trip Upload

| | |
|---|---|
| **Depends on** | 01, 02, 03 |
| **Can run in parallel with** | 05 |
| **Unblocks** | 06 |
| **Read first** | [AGENTS.md](../../AGENTS.md), [architecture.md](../architecture.md) sections 3, 6, 7, 8, 9; [analysis-and-plan.md](../analysis-and-plan.md) 5.4 and 7.4 |

## Goal

An accountant sends a filled template. The bot either lists precise errors, or shows a preview of the trip with totals and new client names. On **Сохранить** the trip is stored; uploading the same trip number again replaces it.

## Starting point

Phases 01–03 are done: DB schema, permissions and menu, `template_spec.py`, demo files in `assets/demo/`.

## Tasks

1. **`domain/calculations.py`**: the functions and `TripTotals` from architecture section 7. Pure functions, `Decimal`, `ROUND_HALF_UP`.
2. **`excel/parser.py`**
   - `parse_trip_workbook(data: bytes) -> ParseResult` where `ParseResult` has `trip: ParsedTrip | None` and `errors: list[ParseError]`.
   - `ParsedTrip`: header fields + lists of `PurchaseRow`, `ExpenseRow`, `SaleRow` (raw client name, product code, row numbers). Values already converted to `int` / `Decimal` / `date` / enum.
   - `ParseError(sheet, row, column, message)` with Russian messages, e.g. `Лист «Продажи», строка 12, «Цена, тыс. сум/кг»: ожидается число`.
   - Use `openpyxl.load_workbook(BytesIO(data), read_only=True, data_only=True)`. Everything driven by `template_spec.py`.
   - Checks (MVP): required sheets exist; headers match; required cells filled; numbers/dates/ints valid and in range (> 0 / ≥ 0 per spec); choice values valid (trimmed, case-insensitive for product codes); `Голов` present for animal products; at least one row in `Закуп` and `Продажи`. Stop collecting after 50 errors. Max 5,000 rows per sheet.
3. **`services/trips.py`**
   - `build_preview(session, parsed) -> TripPreview`: `TripTotals` + `replaces_existing: bool` + `new_client_names: list[str]` (names whose `normalize_client_name` key isn't in the DB; deduplicated).
   - `save_trip(session, parsed, upload, user) -> Trip`: delete the existing trip with the same number (cascade), create missing clients via `get_or_create_client`, insert trip + rows with all computed fields (net kg, amounts, `discount_per_head` copied from the product, `price_uzs_per_kg = value × 1000`). Payments are untouched.
4. **Upload storage**: save the file as `STORAGE_DIR/uploads/<sha256>.xlsx`; create an `upload` row (`pending`); set `rejected` on errors, `cancelled` on Отмена, `saved` on save.
5. **Bot flow** (`handlers/upload.py`, Upload permission)
   - "Загрузить рейс" button → "Отправьте заполненный файл .xlsx".
   - Any document from an Upload user: accept only `.xlsx` up to `MAX_UPLOAD_MB`; otherwise a clear message.
   - Errors → message with the list (fit Telegram's 4,096-char limit; end with "…и ещё N ошибок" if cut).
   - Valid → preview message with inline **Сохранить / Отмена** (callback carries `upload_id`):

     ```
     Рейс №101 — ЗАМЕНИТ существующий   (only if replaces_existing)
     Отправка: 22.10.2026
     Закуп: 612 гол., 21 933,0 кг брутто → 20 453,1 кг нетто
            76 467 300 KZT = 2 049 323 640 сум
     Расходы: 162 468 520 сум
     Продажи: 608 гол., 20 679,2 кг нетто, 2 374 003 400 сум
              58 строк, 14 клиентов
     Прибыль: 162 211 240 сум (7,3%)
     Новые клиенты (3): Алишер, Бахром, Дилшод
     ```
   - **Сохранить** → re-read the stored file, parse again, `save_trip`, reply "Рейс №101 сохранён". (Stateless: works even after a bot restart.)
   - **Отмена** → "Загрузка отменена".

## Out of scope

Warnings and cross-checks (heads/kg bought vs sold), template version check, client dropdown, upload history UI (all after MVP).

## Done when

- [ ] Both demo files upload, preview and save; numbers in the preview are plausible and consistent.
- [ ] Uploading `demo_trip_101.xlsx` again shows "ЗАМЕНИТ" and, after saving, row counts in `purchase`/`expense`/`sale` for that trip are unchanged (no duplicates).
- [ ] New clients appear in `client` after the first save; no duplicates after the second.
- [ ] A copy with a renamed header, text in a number cell, an unknown product code, and an empty required cell → each error is reported with sheet, row and column.
- [ ] A `.pdf` or an oversized file gets a clear refusal; a View-only user cannot upload.

## Handoff

Update the Status column and add a handoff note in [AGENTS.md](../../AGENTS.md).
