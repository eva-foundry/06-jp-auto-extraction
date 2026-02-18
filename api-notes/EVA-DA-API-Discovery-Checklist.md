# EVA DA API Discovery Checklist (Evidence-First)

## 1) Scope & intent

- Document **EVA DA APIs exposed to the browser UI**
- **Not part of current JP Playwright automation**
- Goal: enable a **future reusable EVA API wrapper**

## 2) Preconditions

- Access to EVA Domain Assistant UI
- Browser DevTools access
- Ability to export HAR files
- Auth is opaque and must be **redacted** (no bypassing controls)

## 3) Network inspection setup

- Open DevTools → Network
- Enable:
  - Preserve log
  - Disable cache
- Filter to:
  - Fetch/XHR
  - WS/SSE **only if observed**
- Clear Network log before each scenario

## 4) Required discovery scenarios (checkbox style)

For each scenario: perform the UI action → capture a HAR → identify relevant requests → save artifacts under api-notes/evidence/.

☐ Cold application load (no chat yet)
☐ Start a new chat and submit one question
☐ Observe full chat response completion
☐ Open chat history
☐ Switch project/folder (if applicable)
☐ Open supporting content / citations / sources (if available)

## 5) For each observed endpoint, capture (explicit checklist)

☐ HTTP method
☐ URL path
☐ Status code
☐ Request headers (**auth redacted**)
☐ Request body (JSON)
☐ Response body (JSON)
☐ Identify where:
  - answer text appears
  - citations appear
  - sessionId / conversationId appears
☐ Note if streaming is used (**only if observed**)

## 6) Evidence storage rules

Locations (Project 06 structure):
- HAR files → api-notes/evidence/har/
- JSON samples → api-notes/evidence/samples/
- Screenshots → api-notes/evidence/screenshots/

Redaction rules:
- Redact Authorization, cookies, tokens, user identifiers
- Preserve field names, structural IDs (sessionId, messageId, projectId), and response shape
- Never commit secrets

## 7) API inventory update rule

- For every endpoint observed:
  - Add a row to api-notes/EVA-DA-API-Inventory.md
  - Reference the HAR or sample filename
- Endpoints remain **UNCONFIRMED** until evidence exists

## 8) Completion criteria (definition of done)

☐ All discovery scenarios are executed
☐ At least one HAR exists per scenario
☐ All observed endpoints are listed in API inventory
☐ /chat request and response structure is clearly identified
☐ Citations location in response is documented
☐ No undocumented assumptions remain

## 9) Relationship to Project 06 — JP Automated Extraction

- JP UI requires Playwright due to lack of exposed API
- EVA DA exposes API-first contract suitable for wrapper
- This checklist supports a future migration path
- This checklist does not alter current acceptance criteria
