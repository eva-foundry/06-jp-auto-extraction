# EVA DA Wrapper Backlog (Future Enhancement)

## Purpose

This backlog captures the future direction for a **reusable EVA DA API wrapper**. It is **not part of the current Project 06 run**, which remains UI-driven via Playwright. This backlog is evidence-first and contract-aware.

---

## Why an API wrapper is preferred

- **API-first reliability**: reduces UI selector brittleness and timing variability
- **Deterministic contracts**: explicit request/response schemas validated with evidence
- **Operational efficiency**: faster batch runs without browser overhead
- **Auditability**: easier to log and replay API interactions

---

## Phase 0 — Contract documentation (evidence pack)

**Goal**: Capture and document the EVA DA API contract using the evidence folder.

- Collect HAR files, samples, and screenshots for all core flows
- Redact sensitive headers and payload fields
- Update the API inventory with confirmed fields and evidence filenames

**Acceptance ideas**:
- Each endpoint has at least one HAR and sample payload
- All redactions documented
- Inventory fields updated with observed schemas

---

## Phase 1 — Minimal wrapper for /chat + session handling

**Goal**: Implement a minimal client that can submit a chat request and manage session state.

- Support `/chat` with observed request/response fields
- Handle session IDs or conversation handles as observed
- Capture citations structure as returned by the API

**Acceptance ideas**:
- One request/response round-trip validated against evidence samples
- Output fields match observed schema

---

## Phase 2 — CSV batch runner

**Goal**: Run a questions.csv-style batch via the API wrapper.

- Input: `input/questions.csv`
- Output: `output/jp_answers.csv` + `output/jp_answers.json`
- Preserve Project 06 output schema (question_id, question, answer_text, citations, timestamp, status, error)

**Acceptance ideas**:
- Full batch completes without UI automation
- Citations extracted directly from API response payloads

---

## Phase 3 — Contract tests with saved fixtures

**Goal**: Validate the wrapper against saved evidence samples offline.

- Build tests that run against stored JSON fixtures
- Ensure schema stability and backwards compatibility

**Acceptance ideas**:
- Offline tests pass without network access
- Fixtures map 1:1 to inventory entries

---

## Change summary (2026-01-21)

- Added a future-direction backlog for an EVA DA API wrapper.
- Kept scope explicitly separate from current Playwright-based automation.
