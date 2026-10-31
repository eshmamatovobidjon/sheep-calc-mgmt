# Phase 13 - Trip Entry Form

| | |
|---|---|
| Status | Not started |
| Depends on | 12 |
| Unblocks | 14 |
| Read first | [Roadmap](../mini-app-plan.md), [target architecture](../mini-app-architecture.md) sections 5, 8, 9; [original trip upload phase](phase-04-trip-upload.md) |

## Goal

An accountant enters a whole trip in the Mini App without Excel, checks the preview and saves it. The result is identical to uploading the same data as Excel.

## Tasks

1. Define the trip input schema (header, purchases, expenses, sales) with the same fields and units as the Excel template, including sale price in thousand UZS per kg. Money/kg/rates arrive as strings.
2. Build a `ParsedTrip` from that input and validate it with the same `template_spec` rules as `excel/parser.py` (required fields, bounds, choices, heads required for animal products). Share the checks with the parser rather than copying them. Errors are keyed by row, e.g. `sales[3].gross_kg`.
3. Alembic revision: `trip.upload_id` nullable. `save_trip` accepts `upload=None`.
4. `POST /trips/preview`: validation errors, or `compute_trip` totals plus whether the trip number exists (replace warning) and which client names are new.
5. `PUT /trips/{number}`: validate again and call `save_trip` (replaces an existing trip with that number, creates new clients, leaves payments alone), then commit.
6. Trip form: header fields, then Purchases, Expenses and Sales tabs with add/remove row, then Review showing the server preview and "ЗАМЕНИТ рейс N" when applicable. Save is enabled only after a preview without errors. Client field suggests existing clients as you type.
7. A new sale row copies the previous row's day, date and product; an expense with no quantity counts as 1.
8. The form lives in memory only. Leaving with unsaved rows asks for confirmation.

## Manual Checks

- Enter demo trip 101 by hand; preview and saved totals equal the Excel upload (Phase 03 table).
- Errors point to the right row and field: missing heads for an animal sale, negative net kg, bad date.
- Saving an existing number shows the warning and replaces the trip; client payments remain.
- New client names are created once; existing names match regardless of case/extra spaces.
- A View user gets 403 on preview/save.
- The bot's Excel upload still works.

## Out of Scope

Drafts, autosave, versions, revision history, editing an existing trip in the form (Phase 14), Excel upload in the app (Phase 14).

## Done When

- [ ] A full trip can be entered and saved in the app, and totals match the Excel path exactly.
- [ ] Manual checks pass on a phone and on desktop.
- [ ] Ruff plus frontend lint/typecheck/build pass.

## Handoff

Record the trip input shape, how validation is shared with the parser, and the totals comparison with the Excel path.