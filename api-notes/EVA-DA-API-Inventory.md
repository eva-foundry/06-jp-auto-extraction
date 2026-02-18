# EVA DA API Inventory (Observed Endpoints)

## Purpose

This document catalogs EVA DA endpoints **observed** in DevTools Network traces. Entries remain **UNCONFIRMED** until a corresponding HAR/sample is saved under `api-notes/evidence/`.

**Rule**: Only confirm an endpoint when evidence artifacts exist.

---

## Inventory table

| Endpoint | Method | Purpose | Request fields (observed) | Response fields (observed) | Notes | Evidence artifact filename |
|---|---|---|---|---|---|---|
| /chat | UNCONFIRMED | UNCONFIRMED | UNCONFIRMED | UNCONFIRMED | UNCONFIRMED until evidence captured | (pending) |
| /history | UNCONFIRMED | UNCONFIRMED | UNCONFIRMED | UNCONFIRMED | UNCONFIRMED until evidence captured | (pending) |
| /sessions | UNCONFIRMED | UNCONFIRMED | UNCONFIRMED | UNCONFIRMED | UNCONFIRMED until evidence captured | (pending) |
| /getfolders | UNCONFIRMED | UNCONFIRMED | UNCONFIRMED | UNCONFIRMED | UNCONFIRMED until evidence captured | (pending) |
| /gettags | UNCONFIRMED | UNCONFIRMED | UNCONFIRMED | UNCONFIRMED | UNCONFIRMED until evidence captured | (pending) |
| /env | UNCONFIRMED | UNCONFIRMED | UNCONFIRMED | UNCONFIRMED | UNCONFIRMED until evidence captured | (pending) |
| /file | UNCONFIRMED | UNCONFIRMED | UNCONFIRMED | UNCONFIRMED | UNCONFIRMED until evidence captured | (pending) |
| /customExamples | UNCONFIRMED | UNCONFIRMED | UNCONFIRMED | UNCONFIRMED | UNCONFIRMED until evidence captured | (pending) |
| /logstatus | UNCONFIRMED | UNCONFIRMED | UNCONFIRMED | UNCONFIRMED | UNCONFIRMED until evidence captured | (pending) |

---

## Confirmation workflow

1. Capture evidence using the network trace guide.
2. Save artifacts in:
   - `api-notes/evidence/har/`
   - `api-notes/evidence/samples/`
   - `api-notes/evidence/screenshots/`
3. Update the row:
   - Replace **UNCONFIRMED** with observed details.
   - Reference the exact evidence filename(s).

---

## Change summary (2026-01-21)

- Seeded an evidence-first inventory with placeholders for known UI endpoints.
- Added confirmation workflow tied to evidence artifacts.
