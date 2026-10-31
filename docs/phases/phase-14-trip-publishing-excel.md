# Phase 14 - Trip Editing and Excel in the Mini App

| | |
|---|---|
| Status | Not started |
| Depends on | 13 |
| Unblocks | 15; Release B |
| Read first | [Roadmap](../mini-app-plan.md), [target architecture](../mini-app-architecture.md) section 8; [Phase 13](phase-13-trip-workspace.md) |

## Goal

An existing trip can be opened in the form, corrected and saved again, and an Excel file can be loaded into the form from the app. Saving still replaces the trip by number, as today.

## Tasks

1. `GET /trips/{number}/input`: the stored trip converted back into the Phase 13 input shape (sale price back to thousand UZS per kg, original row order).
2. "Изменить" on the trip screen opens the form pre-filled; saving goes through the same preview and `PUT /trips/{number}`. Changing the trip number in the form is treated as a new trip (with the usual replace warning if that number exists).
3. `POST /uploads/parse`: accept an `.xlsx` (same size limit as the bot), store it as the bot does, parse it in a worker thread and return either the input shape or the parser's row errors. The form opens pre-filled from the file for review, and saving links the trip to that upload.
4. Show in Review, for an existing trip, the old and new totals (revenue, cost, profit) so the user sees what changes.
5. Keep the bot's Excel upload and Save/Cancel unchanged.

## Manual Checks

- Open demo trip 101, change one sale's client and weight, save: the old client's balance goes down, the new one's goes up by the exact amount, payments are unchanged, totals update everywhere.
- Open and save a trip without changes: totals are identical.
- Load `demo_trip_102.xlsx` in the app: the form matches the file and saved totals match the bot upload.
- A broken Excel file shows the same row errors as the bot.
- By-products, KZT/USD expenses and the thousand-UZS sale price survive a load -> save round trip.

## Out of Scope

Drafts, version conflicts, revision history, trip deletion, approval workflow.

## Done When

- [ ] Trips can be edited in the app and loaded from Excel in the app.
- [ ] Manual checks pass; bot and app results agree.
- [ ] Ruff plus frontend lint/typecheck/build pass.

## Handoff

Record the edit and Excel-in-app flows, any rounding found in the load -> save round trip, and remaining limitations.