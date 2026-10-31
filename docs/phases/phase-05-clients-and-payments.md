# Phase 05 — Clients and Payments

| | |
|---|---|
| **Depends on** | 01, 02 |
| **Can run in parallel with** | 03, 04 |
| **Unblocks** | 06 (reports use balances and the client picker) |
| **Read first** | [AGENTS.md](../../AGENTS.md), [architecture.md](../architecture.md) sections 3, 6 (`client`, `payment`), 7 (client balance), 9, 11; [analysis-and-plan.md](../analysis-and-plan.md) 3.4 and 7.5 |

## Goal

Accountants record client payments in the bot, fix mistakes by deleting a payment, and manage the client list. Client balances are available to the rest of the system.

## Starting point

Phases 01–02 are done. Trips may not exist yet (phase 04 may run in parallel), so balances can be zero or negative; that is fine.

## Tasks

1. **`services/balances.py`**
   - `client_balance(session, client_id, as_of: date | None = None) -> int`
   - `all_balances(session) -> list[ClientBalance]` with `client_id`, `name`, `shipped`, `paid`, `balance`, `last_sale_date`, `last_payment_date`.
   - Formula from architecture section 7; deleted payments excluded.
2. **`services/clients.py`** (extend phase 01): `search_clients(session, query, limit=10)` (substring on `name_key`), `list_clients(session, offset, limit)`, `create_client(session, name, created_by_id)` (error if the key exists), `rename_client(session, client_id, new_name)` (unique check).
3. **`services/payments.py`**: `create_payment(...)`, `list_recent(session, limit=20)`, `delete_payment(session, payment_id, user_id)` (soft delete).
4. **`bot/client_picker.py`** (reused by phase 06): a helper that, in any FSM state, asks for ≥ 2 letters, shows up to 10 matches as inline buttons (`cli` callback), says "Не найдено" otherwise, and hands the chosen `client_id` back to the caller.
5. **`/pay` and "Оплата"** (`handlers/payments.py`, Upload permission) — dialog as in analysis 7.5:
   1. Client (client picker) → shows current balance.
   2. Amount: `parse_amount`; must be > 0.
   3. Method: **Банк / Карта / Наличные**.
   4. Date: **Сегодня / Вчера / Другая** (then `ДД.ММ.ГГГГ`, not in the future). "Today" uses `TIMEZONE`.
   5. Comment: text or **Пропустить**.
   6. Confirmation card: client, amount, method, date, comment, **Долг: before → after** (negative balance shown as "Переплата"); **Сохранить / Отмена**.
   7. Saved → "Оплата сохранена" + main menu.
6. **`/payments` and "Последние оплаты"**: last 20 payments (`ДД.ММ.ГГГГ · Клиент · сумма · способ · кто внёс`), each with an inline **Удалить** button → confirm **Да / Нет** → soft delete → "Оплата удалена".
7. **`/clients` and "Клиенты"** (Upload permission): **Найти / Добавить / Все клиенты**.
   - Все клиенты: 20 per page with balance, **← / →** paging.
   - Client card: name, balance, shipped, paid, last sale date, last payment date; **Переименовать**, **Внести оплату** (starts the `/pay` dialog with this client).
   - Добавить: ask name → create (error if it exists).

## Out of scope

Editing payments, bulk payment upload, transfers between clients, merging clients, phone editing (all after MVP).

## Done when

- [ ] A payment entered via `/pay` lowers the client's balance by that amount; the confirmation card shows correct before/after values.
- [ ] Wrong amount (`abc`, `0`) and a future date are rejected with a hint; `/cancel` leaves the dialog at any step.
- [ ] A deleted payment disappears from `/payments` and no longer affects the balance.
- [ ] Clients can be found by part of the name, added, renamed (duplicate names rejected).
- [ ] A View-only user cannot use `/pay`, `/payments` or `/clients`.

## Handoff

Update the Status column and add a handoff note in [AGENTS.md](../../AGENTS.md) (describe how to call `client_picker` from another dialog).
