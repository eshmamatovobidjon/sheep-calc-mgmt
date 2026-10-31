# Phase 11 - Clients and Payments in the Mini App

| | |
|---|---|
| Status | Done |
| Depends on | 10 |
| Unblocks | 12; first useful daily-work milestone |
| Read first | [Roadmap](../mini-app-plan.md), [target architecture](../mini-app-architecture.md) sections 4-6, 9; [original payment phase](phase-05-clients-and-payments.md) |

## Goal

An accountant finds a client, sees the ledger, records a payment and sees the same balance in the bot. Same accounting rules as the bot.

## Tasks

1. `POST /clients` and `PATCH /clients/{id}` (name, optional phone) using the existing client services and name normalization. A duplicate name returns 409 naming the existing client.
2. `GET /clients/{id}/ledger`: shipments and payments in order with running balance, optional date range, reusing the statement data from `reports/data.py`.
3. `POST /payments` (client, whole UZS amount, method, date, optional note) and `GET /payments` (recent, optional client filter), reusing `services/payments.py` and its validation (positive amount, no future date). Overpayment is allowed and shown as credit.
4. `DELETE /payments/{id}`: the existing soft delete, recording who and when.
5. Client screen: balance, ledger, "Внести оплату" and "Изменить" actions for Upload users. View users see the ledger only.
6. Payment form: amount, method, date (default today), note, then a confirmation with before/after balance. The submit button is disabled while saving; the balance refreshes from the server afterwards.
7. Recent payments screen with a delete action and confirmation.
8. Add Payments to the bottom navigation for Upload users.

## Manual Checks

1. Create a client, find it ignoring case/extra spaces; a duplicate is rejected; edit name and phone.
2. Record cash, card and bank payments; the app balance, bot balance and statement agree.
3. Zero, negative, fractional and future-dated payments are rejected.
4. An overpayment shows as credit in list, detail and ledger.
5. Delete a payment: balance goes back up once.
6. A View user gets 403 when calling the write endpoints directly.
7. A payment entered in the bot appears in the app after refresh, and vice versa.

## Out of Scope

Idempotency keys, version checks, cancellation reasons, audit log, payment edits (delete and re-enter instead), client merge or delete.

## Done When

- [x] Client -> payment -> updated ledger works in Telegram. (Verified in the browser against the same build; real-Telegram click-through by the owner still recommended.)
- [x] All manual checks pass.
- [x] Ruff plus frontend lint/typecheck/build pass.

## Handoff

Done 2026-10-31; details in the AGENTS.md Phase 11 note and architecture sections 9a/9b.