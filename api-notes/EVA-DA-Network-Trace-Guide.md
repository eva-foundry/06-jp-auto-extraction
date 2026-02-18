# EVA DA Network Trace Guide (Evidence-First)

## Purpose

This runbook defines how to inspect EVA Domain Assistant (EVA DA) API behavior using browser DevTools **Network** traces. The goal is to **observe and capture** actual request/response contracts with **redacted** sensitive data. No speculation; only record what is observed.

---

## Evidence standards

Capture **all** of the following for each observed request:

- **Request URL + method**
- **Request headers** (redact auth tokens and cookies)
- **Request payload** (if any)
- **Response payload** (answer + citations structure)
- **Status code**
- **Timings** (TTFB/total if available)
- **Streaming signal** (SSE/WS) **only if observed** in the Network tab

Save evidence artifacts into:

- `api-notes/evidence/har/`
- `api-notes/evidence/screenshots/`
- `api-notes/evidence/samples/`

---

## Redaction policy

Always redact or remove:

- Authorization headers (Bearer tokens, API keys)
- Cookies and session IDs
- User identifiers (email, UPN, GUIDs) unless explicitly required
- Any personal data in request/response payloads

When redacting, replace with **[REDACTED]** and note that a redaction occurred.

---

## Preparation

1. Open EVA DA UI in a modern browser.
2. Open DevTools → **Network** tab.
3. Enable **Preserve log**.
4. Clear existing entries before each scenario.
5. Configure recording to include **Fetch/XHR**, **WS**, and **Other**.

---

## Scenario 1 — Cold load of EVA DA UI

**Goal**: Capture initial configuration and bootstrap requests.

Steps:
1. Clear Network tab.
2. Hard refresh the page (Ctrl+F5).
3. Wait until the UI fully renders.

Capture:
- All bootstrapping endpoints (config/env/session/etc.)
- Response payloads that expose UI or API configuration

Artifacts to save:
- HAR: `api-notes/evidence/har/cold-load.har`
- Screenshot: `api-notes/evidence/screenshots/cold-load.png`
- Sample payloads: `api-notes/evidence/samples/cold-load-*.json`

---

## Scenario 2 — Submit a single question

**Goal**: Capture the primary chat endpoint and response shape.

Steps:
1. Clear Network tab.
2. Submit a single question in the UI.
3. Wait until the response fully renders.

Capture:
- `/chat` request and response
- Any follow-up calls for citations or metadata
- Status codes and timings
- Streaming indicator **only if observed**

Artifacts to save:
- HAR: `api-notes/evidence/har/single-question.har`
- Screenshot: `api-notes/evidence/screenshots/single-question.png`
- Sample payloads: `api-notes/evidence/samples/single-question-*.json`

---

## Scenario 3 — Open chat history

**Goal**: Capture history/session retrieval endpoints.

Steps:
1. Clear Network tab.
2. Open the chat history panel (or equivalent).
3. Select a prior conversation if available.

Capture:
- `/history`, `/sessions`, or similar endpoints
- Response fields that define message structure

Artifacts to save:
- HAR: `api-notes/evidence/har/chat-history.har`
- Screenshot: `api-notes/evidence/screenshots/chat-history.png`
- Sample payloads: `api-notes/evidence/samples/chat-history-*.json`

---

## Scenario 4 — Open supporting content / citations

**Goal**: Capture how citations and supporting content are fetched.

Steps:
1. Clear Network tab.
2. Open a response with citations.
3. Click the citation or supporting content panel (if visible).

Capture:
- `/file`, `/citations`, or similar endpoints
- Payload shape for supporting content

Artifacts to save:
- HAR: `api-notes/evidence/har/supporting-content.har`
- Screenshot: `api-notes/evidence/screenshots/supporting-content.png`
- Sample payloads: `api-notes/evidence/samples/supporting-content-*.json`

---

## Scenario 5 — Switch folder/project (if applicable)

**Goal**: Capture folder/project selection endpoints and related metadata.

Steps:
1. Clear Network tab.
2. Switch folder/project within the UI.
3. Wait for the UI to update.

Capture:
- `/getfolders`, `/gettags`, or similar endpoints
- Response fields used to populate UI state

Artifacts to save:
- HAR: `api-notes/evidence/har/switch-folder.har`
- Screenshot: `api-notes/evidence/screenshots/switch-folder.png`
- Sample payloads: `api-notes/evidence/samples/switch-folder-*.json`

---

## Evidence checklist (per scenario)

- [ ] Request URL + method
- [ ] Request headers (redacted)
- [ ] Request payload (redacted)
- [ ] Response payload (redacted)
- [ ] Status code + timings
- [ ] Streaming indicator **only if observed**
- [ ] HAR saved to evidence folder
- [ ] Screenshot saved to evidence folder
- [ ] Sample JSON saved to evidence folder

---

## Change summary (2026-01-21)

- Added an evidence-first runbook for capturing EVA DA Network traces.
- Defined redaction policy and required artifacts per scenario.
