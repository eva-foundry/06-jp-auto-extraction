# Execution Plan — JP Automated Extraction

## Overview

This document outlines the technical approach, implementation phases, and key design decisions for automating the extraction of jurisprudence citations from the JP UI.

## Problem Statement

The JP UI provides a chat interface for legal questions but:

- Has no stable public API for batch automation
- Requires manual interaction for each query
- Does not provide structured export of answers and citations

**Goal**: Automate the UI interaction to enable repeatable, deterministic extraction of answers and citations.

---

## Environment & Dependency Strategy

### Workstation constraint summary

On ESDC workstations, pip installs may fail due to enterprise controls:
- `global.no-index=true` and `global.find-links=https://aar-raa.prv/repos/pip`
- SSL certificate verification failures when attempting to reach `pypi.org`

**Implication**: Installation from public PyPI is not reliable on the workstation.

### Baseline execution environment

**DevBox (recommended)**: Use an ESDC DevBox or equivalent environment where package and browser installs are supported and auditable.

### Alternate execution paths (documented only)

- **Internal pip mirror**: If `playwright` and `pandas` wheels are mirrored in the approved repository, use that path.
- **Offline wheelhouse**: Use vetted offline wheels + Playwright browser binaries (if approved).

---

## Phase 1 — Input Preparation & Validation

### Objectives
- Ensure input data is well-formed and ready for automation
- Validate question quality and structure

### Tasks

#### 1.1 Input CSV Schema Validation
- **Required columns**: `question_id`, `question`
- **Validation checks**:
  - No duplicate `question_id` values
  - No empty `question` fields
  - Questions are within reasonable length limits (e.g., <500 chars)

#### 1.2 Question Stability
- All 37 questions have been **human-validated** by legal analysts
- Questions are curated for QA, regression, and accuracy testing
- Input CSV is **read-only** and treated as ground truth

### Deliverables
- ✅ `input/questions.csv` with 37 validated questions
- ✅ Input validation logic in `run_jp_batch.py`

---

## Phase 2 — Browser Automation Implementation

### Objectives
- Automate UI interaction using Playwright
- Implement robust response detection and extraction
- Handle edge cases and errors gracefully

### Architecture Decisions

#### 2.1 Browser Automation Framework
**Choice**: Playwright (Python sync API)

**Rationale**:
- Modern, well-maintained automation framework
- Excellent selector support and stability
- Built-in wait utilities and error handling
- Cross-browser support (though we use Chromium)

#### 2.2 Session Management
**Choice**: Single browser session for all questions

**Rationale**:
- Faster execution (no repeated browser launches)
- Lower resource usage
- Preserves any session state if needed
- Simplifies error recovery

#### 2.3 Response Detection Strategy
**Critical Challenge**: How to know when the assistant has finished responding?

**Rejected Approaches**:
- ❌ `networkidle`: Unreliable with WebSockets/streaming responses
- ❌ Fixed timeout: Too slow (over-waits) or too fast (misses content)
- ❌ Presence of elements: Doesn't indicate completion

**Chosen Approach**: **Stabilized Text Polling**

```python
def wait_for_stabilized_text(page, selector, timeout_seconds):
    """
    Poll innerText every 200ms.
    Return when text is unchanged for ≥800ms.
    """
    last_text = ""
    stable_count = 0
    required_stable_polls = int(800 / 200)  # 4 consecutive polls
    
    while time_left > 0:
        current_text = page.locator(selector).inner_text()
        
        if current_text == last_text:
            stable_count += 1
            if stable_count >= required_stable_polls:
                return current_text  # Text has stabilized
        else:
            stable_count = 0  # Reset counter on change
            last_text = current_text
        
        time.sleep(0.2)  # 200ms poll interval
```

**Why this works**:
- Streaming responses update incrementally → text keeps changing
- When assistant is done → text stops changing
- 800ms stability window ensures we're not catching mid-stream pauses

#### 2.4 Element Selectors
**Challenge**: JP UI may not have stable, semantic selectors.

**Strategy**: Multi-selector fallback approach

```python
# Try multiple possible selectors in order of preference
ASSISTANT_MESSAGE_SELECTORS = [
    '.assistant-message',           # Ideal: semantic class
    '.message.assistant',           # Common pattern
    '[data-role="assistant"]',      # Data attribute
    '.chat-message:last-child'      # Fallback: last message
]

for selector in ASSISTANT_MESSAGE_SELECTORS:
    try:
        element = page.locator(selector).last
        if element.is_visible():
            return element
    except:
        continue
```

### Tasks

#### 2.1 Page Navigation
1. Launch Chromium browser
2. Navigate to JP UI URL
3. Wait for chat interface to fully load
4. Validate presence of input field and send button

#### 2.2 Question Submission
For each question:
1. Locate chat input field (by placeholder text)
2. Clear any existing text
3. Type question with 50ms delay (simulate human typing)
4. Click send button
5. Wait for request to be sent

#### 2.3 Response Detection
1. Wait 2s for response to start appearing
2. Detect "Thinking..." indicator disappears (optional)
3. Locate assistant message container
4. Poll text content every 200ms
5. Return when stable for ≥800ms

#### 2.4 Content Extraction
1. Capture full `innerText` of stabilized response
2. Parse citations using regex patterns
3. Deduplicate citations while preserving order

### Deliverables
- ✅ `run_jp_batch.py` with full automation logic
- ✅ Stabilized text detection algorithm
- ✅ Multi-selector fallback for robust element location
- ✅ Citation extraction function

---

## Operational procedure for first run

1. **Run in headed mode** to validate selectors and UI stability:
    - `python scripts/run_jp_batch.py --in input/questions.csv --out output/jp_answers.csv --headed`
2. **Validate selectors**: Confirm the assistant response is captured and stabilized.
3. **Spot-check outputs**: Compare citations for a small sample against the UI.
4. **Run headless for batch** once validated:
    - `python scripts/run_jp_batch.py --in input/questions.csv --out output/jp_answers.csv`

---

## Phase 3 — Citation Parsing

### Objectives
- Extract all cited cases from assistant responses
- Support multiple citation formats
- Ensure accuracy and completeness

### Citation Formats

#### 3.1 Neutral Citations
**Pattern**: `YYYY SST NNNN` (e.g., "2023 SST 2068")

**Regex**: `r'\b\d{4}\s+SST\s+\d+\b'`

**Example**:
```
In the case of 2023 SST 2068, the tribunal found...
```

#### 3.2 PDF Filenames
**Pattern**: Any string ending in `.pdf` (case-insensitive)

**Regex**: `r'[\w\-]+\.pdf'`

**Example**:
```
See case_12345.pdf for details.
```

#### 3.3 Link References
**Pattern**: Lines containing "Link:"

**Example**:
```
Link: https://example.com/cases/12345
```

### Parsing Algorithm

```python
def extract_citations(text: str) -> List[str]:
    citations = []
    
    for line in text.split('\n'):
        # Check for "Link:" lines
        if "Link:" in line:
            citations.append(line.strip())
        
        # Extract .pdf filenames
        pdf_matches = re.findall(r'[\w\-]+\.pdf', line, re.IGNORECASE)
        citations.extend(pdf_matches)
        
        # Extract neutral citations
        neutral_matches = re.findall(r'\b\d{4}\s+SST\s+\d+\b', line)
        citations.extend(neutral_matches)
    
    # Deduplicate while preserving order
    return list(dict.fromkeys(citations))
```

### Deliverables
- ✅ `extract_citations()` function in `run_jp_batch.py`
- ✅ Support for all three citation formats
- ✅ Deduplication logic

---

## Phase 4 — Output & Traceability

### Objectives
- Persist results in structured, machine-readable formats
- Ensure full traceability and auditability
- Support downstream processing

### Output Formats

#### 4.1 Primary: CSV (`output/jp_answers.csv`)
**Schema**:
- `question_id`: Unique identifier
- `question`: Original question text
- `answer_text`: Full assistant response
- `citations`: Pipe-separated list of citations
- `timestamp`: ISO 8601 timestamp
- `status`: "success" | "timeout" | "error"
- `error`: Error message (empty if success)

**Rationale**:
- CSV is widely supported
- Easy to import into Excel, pandas, databases
- Human-readable for spot-checking

#### 4.2 Secondary: JSON (`output/jp_answers.json`)
**Format**: JSON array of objects

**Rationale**:
- Easier programmatic access
- Preserves data types
- Better for downstream APIs

#### 4.3 Debug Artifacts
When a question fails:
- **Screenshot**: Full-page PNG of browser state
- **HTML snapshot**: Complete DOM at time of failure

**Naming**: `{question_id}_{timestamp}.{ext}`

**Location**:
- `debug/screenshots/`
- `debug/html/`

### Logging Strategy

#### Log Levels
- `INFO`: Progress updates, summaries
- `DEBUG`: Detailed step-by-step execution
- `ERROR`: Failures, exceptions

#### Outputs
- **Console**: `INFO` and `ERROR` levels
- **Log file**: All levels (`logs/run.log`)

### Deliverables
- ✅ CSV writer with header row
- ✅ JSON export function
- ✅ Debug artifact capture on failure
- ✅ Comprehensive logging

---

## Evidence capture & run artifacts

To support audit and troubleshooting, each run should bundle the following artifacts:

- `logs/run.log`
- `output/jp_answers.csv`
- `output/jp_answers.json`
- `debug/screenshots/` and `debug/html/` (only if failures occurred)

**Operational note**: Archive these artifacts per run (e.g., by date/time) to preserve traceability.

---

## Phase 5 — Error Handling & Resilience

### Objectives
- Ensure batch continues on individual failures
- Capture enough debug info to diagnose issues
- Minimize manual intervention

### Error Scenarios

#### 5.1 Timeout
**Cause**: Response doesn't stabilize within `MAX_WAIT_SECONDS` (120s)

**Handling**:
1. Log error with question ID
2. Save screenshot and HTML snapshot
3. Write row with `status="timeout"`
4. Continue to next question

#### 5.2 Element Not Found
**Cause**: UI structure changed, selector no longer valid

**Handling**:
1. Try fallback selectors
2. If all fail, log error
3. Save debug artifacts
4. Write row with `status="error"`
5. Continue to next question

#### 5.3 Network Issues
**Cause**: JP UI unreachable or slow

**Handling**:
- Playwright has built-in retries
- If fatal, entire batch fails (user must re-run)

#### 5.4 Malformed Input
**Cause**: Missing columns, corrupt CSV

**Handling**:
- Validate input on startup
- Fail fast with clear error message
- Do not start browser

### Resilience Features

#### Immediate Output Flushing
```python
writer.writerow(result)
output_file.flush()  # Write immediately, don't buffer
```

**Rationale**: If batch is interrupted, partial results are saved.

#### Restartability
- Output CSV includes `question_id` from input
- User can filter out completed questions and re-run remaining
- (Future enhancement: auto-resume from last success)

#### Throttling
```python
time.sleep(THROTTLE_SECONDS)  # 2s between questions
```

**Rationale**:
- Reduces UI load
- Avoids rate limiting
- Gives UI time to recover between queries

### Deliverables
- ✅ Try-except blocks around question processing
- ✅ Debug artifact capture on failure
- ✅ Batch continues on individual failures
- ✅ Output flushing for partial results

---

## Phase 6 — Validation & Quality Assurance

### Objectives
- Verify automation accuracy
- Ensure results match manual UI queries
- Identify and fix edge cases

### Validation Strategy

#### 6.1 Spot-Checking
**Method**: Manually query 10% of questions in UI, compare results

**Checks**:
- Answer text matches exactly (modulo whitespace)
- All citations present in output
- No hallucinated citations

#### 6.2 Citation Completeness
**Method**: Review debug screenshots for failed/timeout cases

**Checks**:
- Are citations visible in screenshot but missing from output?
- If yes, update `extract_citations()` patterns

#### 6.3 Regression Testing
**Method**: Re-run batch with same inputs, compare outputs

**Checks**:
- Same questions → same answers (or document differences)
- Outputs are deterministic (modulo timestamps)

### Success Criteria
- ≥90% success rate on batch runs
- Cited cases match manual verification
- No false positive citations

### Deliverables
- ✅ Validation checklist
- ✅ Spot-check results documentation
- ✅ Regression test baseline

---

## Technical Specifications

### Dependencies
```txt
playwright>=1.40.0
pandas>=2.0.0
```

### System Requirements
- Python 3.10+
- 2GB RAM
- 500MB disk space (for browser binaries)
- Network access to JP UI

### Performance Expectations
- **Processing rate**: ~2-3 questions/minute (with 2s throttle)
- **Total runtime**: ~15-20 minutes for 37 questions
- **Success rate**: ≥90% on stable UI

### Maintenance Considerations
- **Selector updates**: If UI changes, update selector constants
- **Citation patterns**: If citation format changes, update regex
- **Timeout tuning**: Adjust `MAX_WAIT_SECONDS` if responses are slower

---

## Risk Assessment

### High Risk
❌ **JP UI structure changes**
- **Mitigation**: Multi-selector fallback, clear error messages
- **Contingency**: Update selectors and re-run

### Medium Risk
⚠️ **Slow/inconsistent responses**
- **Mitigation**: Stabilization algorithm, generous timeout (120s)
- **Contingency**: Increase `MAX_WAIT_SECONDS`, review debug artifacts

### Low Risk
✅ **Input data quality**
- **Mitigation**: Questions are pre-validated by legal analysts
- **Contingency**: N/A (inputs are stable)

---

## Future Enhancements

### Phase 7+ (Not Included)
1. **Auto-resume**: Skip already-processed questions based on output CSV
2. **Parallel execution**: Run multiple browser contexts simultaneously
3. **API integration**: If JP exposes an API, switch to direct API calls
4. **Answer comparison**: Track answer changes over time (regression detection)
5. **Citation validation**: Cross-check citations against source documents

---

## Summary

This plan provides a **deterministic, auditable, and maintainable** approach to automating JP UI queries. Key design principles:

- **Robustness**: Multi-selector fallback, stabilization algorithm
- **Traceability**: Full logging, debug artifacts, timestamped outputs
- **Resilience**: Continue on failure, immediate output flushing
- **Simplicity**: Single script, minimal dependencies, clear structure

The implementation is ready for production use and can be extended as requirements evolve.

---

## Change summary (2026-01-21)

- Documented workstation installation constraints and approved execution options.
- Added first-run operational procedure for headed validation and spot-checking.
- Added evidence capture guidance for audit-ready run artifacts.
