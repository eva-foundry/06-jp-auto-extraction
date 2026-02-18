# Acceptance Criteria — JP Automated Extraction

## Purpose

This document defines the **success conditions** for the JP Automated Extraction project. All criteria must be met before the project is considered complete and production-ready.

---

## Functional Requirements

### ✅ FR-1: All Input Questions Processed
**Criteria**: The script must attempt to process every question in `input/questions.csv`.

**Verification**:
- Output CSV has exactly 37 rows (one per input question)
- Each `question_id` from input appears exactly once in output
- No questions are skipped or duplicated

**Test**:
```bash
# Count input rows (excluding header)
wc -l input/questions.csv  # Expected: 38 (37 + header)

# Count output rows (excluding header)
wc -l output/jp_answers.csv  # Expected: 38 (37 + header)

# Verify all IDs match
diff <(tail -n +2 input/questions.csv | cut -d',' -f1 | sort) \
     <(tail -n +2 output/jp_answers.csv | cut -d',' -f1 | sort)
# Expected: no output (files are identical)
```

---

### ✅ FR-2: Script Completes Without Manual Intervention
**Criteria**: The script runs from start to finish without requiring user input or interaction.

**Verification**:
- Script can be run unattended (e.g., via cron job)
- No interactive prompts
- Exits with clear exit code (0 for success, non-zero for fatal errors)

**Test**:
```bash
# Run in headless mode and check exit code
python scripts/run_jp_batch.py --in input/questions.csv --out output/jp_answers.csv
echo $?  # Expected: 0
```

---

### ✅ FR-3: One Output Record Per Input Question
**Criteria**: Each question generates exactly one row in the output CSV, regardless of success or failure.

**Verification**:
- No missing rows
- No duplicate rows for the same `question_id`
- Failed questions still produce a row with `status="error"` or `status="timeout"`

**Test**:
```bash
# Check for duplicates
cut -d',' -f1 output/jp_answers.csv | sort | uniq -d
# Expected: no output (no duplicates)
```

---

### ✅ FR-4: Citations Captured Exactly as Presented
**Criteria**: All citations visible in the UI are captured in the output, with no additions or omissions.

**Verification**:
- Manual spot-check: Query 5 random questions in UI
- Compare UI citations to `citations` column in output
- Citations match exactly (allowing for whitespace differences)

**Spot-Check Procedure**:
1. Select 5 random `question_id` values
2. Manually query each in JP UI
3. Copy citations from UI response
4. Compare to output CSV `citations` column
5. Document any discrepancies

**Success**: ≥95% citation accuracy (0-1 discrepancies allowed out of 5 samples)

---

## Environment Readiness

### ✅ ER-1: Dependencies installed in target run environment
**Criteria**: Required Python dependencies are installed in the execution environment (DevBox or approved mirror).

**Verification**:
- `playwright` and `pandas` installed and importable
- Installation was performed via approved mechanisms (DevBox, internal mirror, or approved wheelhouse)

**Test**:
```bash
python -c "import playwright, pandas; print('ok')"
```

---

### ✅ ER-2: Playwright Chromium installed and runnable
**Criteria**: The Playwright Chromium browser is installed and usable.

**Verification**:
- `playwright install chromium` has completed successfully

**Test**:
```bash
playwright install chromium
```

---

### ✅ ER-3: JP UI reachable from run environment
**Criteria**: The JP UI is reachable from the execution environment.

**Verification**:
- The JP UI loads in a browser from the run environment

**Test**:
```bash
curl -I https://ei-jp-ui.purplesky-a9615d9b.canadacentral.azurecontainerapps.io/
```

---

## Reliability Requirements

### ✅ RR-1: Batch Continues on Individual Failure
**Criteria**: If one question fails (timeout, error), the script continues processing remaining questions.

**Verification**:
- Introduce a deliberately malformed question (e.g., empty string)
- Verify script does not crash
- Verify subsequent questions are still processed

**Test**:
```bash
# Add a test question that will fail
echo "q999,<INVALID>" >> input/test_questions.csv

# Run script
python scripts/run_jp_batch.py --in input/test_questions.csv --out output/test_results.csv

# Check that questions after q999 were still processed
grep -c "success" output/test_results.csv
# Expected: non-zero (other questions succeeded)
```

---

### ✅ RR-2: Errors Are Logged and Traceable
**Criteria**: All errors are captured in the log file and output CSV with sufficient detail for debugging.

**Verification**:
- Failed questions have non-empty `error` column
- Log file (`logs/run.log`) contains error details
- Error messages include `question_id` and timestamp

**Test**:
```bash
# Check for logged errors
grep "ERROR" logs/run.log | grep -o "q[0-9]*"
# Expected: list of failed question IDs

# Verify output CSV has error details
grep "error\|timeout" output/jp_answers.csv | cut -d',' -f1,7
# Expected: question IDs with error messages
```

---

### ✅ RR-3: Debug Artifacts Generated for Failed Rows
**Criteria**: When a question fails, a screenshot and HTML snapshot are automatically saved.

**Verification**:
- Failed questions have corresponding files in `debug/screenshots/` and `debug/html/`
- Files are named with `{question_id}_{timestamp}` format
- Files contain relevant debugging information

**Test**:
```bash
# Find failed question IDs
FAILED_IDS=$(grep "error\|timeout" output/jp_answers.csv | cut -d',' -f1)

# Check for debug artifacts
for id in $FAILED_IDS; do
    ls debug/screenshots/${id}_*.png
    ls debug/html/${id}_*.html
done
# Expected: files exist for each failed question
```

---

## Determinism Requirements

### ✅ DR-1: Re-running Produces Equivalent Outputs
**Criteria**: Running the script twice with the same inputs produces outputs that are identical except for timestamps.

**Verification**:
- Run script twice
- Compare outputs ignoring `timestamp` column
- Answer text and citations should be identical (or document differences)

**Test**:
```bash
# First run
python scripts/run_jp_batch.py --in input/questions.csv --out output/run1.csv

# Second run
python scripts/run_jp_batch.py --in input/questions.csv --out output/run2.csv

# Compare (excluding timestamp column)
diff <(cut -d',' -f1-3,5-7 output/run1.csv) \
     <(cut -d',' -f1-3,5-7 output/run2.csv)
# Expected: minimal differences (JP UI may return slightly different answers)
```

**Allowable Differences**:
- Timestamps (expected to differ)
- Minor wording changes in answers (if JP model is non-deterministic)
- Citation order (if UI presentation changes)

**Not Allowed**:
- Missing citations that were present in first run
- Completely different answers for same question

---

### ✅ DR-2: No Hidden State Between Runs
**Criteria**: Each run is independent; previous runs do not affect current run.

**Verification**:
- Delete output and debug directories
- Re-run script
- Verify same results as initial run

**Test**:
```bash
# Clean outputs
rm -rf output/* debug/screenshots/* debug/html/* logs/*

# Re-run
python scripts/run_jp_batch.py --in input/questions.csv --out output/jp_answers.csv

# Verify output is complete
wc -l output/jp_answers.csv  # Expected: 38 (37 + header)
```

---

## Governance & Audit Requirements

### ✅ GA-1: Inputs, Outputs, and Scripts Clearly Separated
**Criteria**: Project structure maintains clear separation of concerns.

**Verification**:
- Inputs in `input/` directory (read-only)
- Outputs in `output/` directory (regenerable)
- Scripts in `scripts/` directory (versioned)
- Logs in `logs/` directory (ephemeral)
- Debug artifacts in `debug/` directory (ephemeral)

**Test**:
```bash
# Verify directory structure
ls -ld input/ output/ scripts/ logs/ debug/
# Expected: all directories exist
```

---

### ✅ GA-2: Outputs Traceable to Inputs
**Criteria**: Every output row can be traced back to its source question and execution context.

**Verification**:
- Output CSV includes `question_id` from input
- Output CSV includes `question` text from input
- Output CSV includes ISO 8601 `timestamp`
- Log file includes timestamps and question IDs

**Test**:
```bash
# Verify output has required columns
head -1 output/jp_answers.csv
# Expected: question_id,question,answer_text,citations,timestamp,status,error

# Verify timestamps are valid ISO 8601
cut -d',' -f5 output/jp_answers.csv | tail -n +2 | grep -E '^[0-9]{4}-[0-9]{2}-[0-9]{2}T'
# Expected: all rows match pattern
```

---

### ✅ GA-3: No Backend or API Assumptions
**Criteria**: The automation only interacts with the public UI; no assumptions about internal APIs or backend services.

**Verification**:
- Script only uses Playwright browser automation
- No direct HTTP requests to non-UI endpoints
- No assumptions about database structure or internal APIs

**Code Review**:
```bash
# Verify no direct API calls (except Playwright)
grep -r "requests\." scripts/
grep -r "urllib" scripts/
grep -r "httpx" scripts/
# Expected: no results (only Playwright is used)
```

---

## Performance Requirements

### ✅ PR-1: Reasonable Execution Time
**Criteria**: Batch processing completes within acceptable time frame for 37 questions.

**Target**: ≤30 minutes total runtime

**Verification**:
```bash
# Time the execution
time python scripts/run_jp_batch.py --in input/questions.csv --out output/jp_answers.csv
# Expected: real time <30m
```

---

### ✅ PR-2: Minimal Resource Usage
**Criteria**: Script does not consume excessive system resources.

**Targets**:
- Memory: ≤2GB RAM
- CPU: ≤50% average (on modern CPU)
- Disk: ≤100MB for debug artifacts

**Verification**: Monitor system resources during execution using `htop`, Task Manager, or similar.

---

## Documentation Requirements

### ✅ DR-1: Runnable Installation Instructions
**Criteria**: README.md provides complete, accurate installation and usage instructions.

**Verification**:
- Follow README.md on a clean system
- Verify script runs successfully without additional steps

**Test**: Have a colleague follow README.md and report any issues.

---

### ✅ DR-2: Clear Error Messages
**Criteria**: When script fails, error messages are actionable and point to root cause.

**Verification**:
- Review error messages in output CSV and log file
- Verify errors include:
  - What failed (e.g., "Timeout waiting for response")
  - Which question (e.g., "q015")
  - Where to look for more info (e.g., "See debug/screenshots/")

---

### ✅ DR-3: Project Context Documented
**Criteria**: README.md and PLAN.md explain why this project exists and how it works.

**Verification**:
- README.md has "Why This Exists" section
- PLAN.md has "Problem Statement" section
- New team members can understand purpose without asking

---

## Reproducible Run Package

### ✅ RP-1: Run package includes exact commands
**Criteria**: README includes exact, copy/paste-ready commands for installation and execution.

**Verification**:
- README includes commands for dependencies and Playwright browser installation
- README includes both headed validation and headless batch commands

---

### ✅ RP-2: Preflight check is documented
**Criteria**: A minimal preflight check (manual or scripted) is documented to verify readiness before running.

**Verification**:
- README documents a preflight checklist (dependencies, browser install, UI reachability)
- Acceptance criteria reference this preflight step

---

## Summary Checklist

### Functional
- [ ] All 37 input questions processed
- [ ] Script runs unattended
- [ ] One output row per input question
- [ ] Citations accurately captured

### Reliability
- [ ] Batch continues on individual failures
- [ ] Errors logged and traceable
- [ ] Debug artifacts saved for failures

### Determinism
- [ ] Re-runs produce equivalent outputs
- [ ] No hidden state between runs

### Governance
- [ ] Clear separation of inputs/outputs/scripts
- [ ] Outputs traceable to inputs and execution time
- [ ] No backend/API assumptions

### Performance
- [ ] Completes within 30 minutes
- [ ] Uses ≤2GB RAM

### Documentation
- [ ] README.md is runnable
- [ ] Error messages are actionable
- [ ] Project context is documented
- [ ] Environment readiness is confirmed
- [ ] Preflight checks are documented and verified

---

## Sign-Off

**Acceptance**: All criteria above must be met (or explicitly waived with justification) before project is considered complete.

**Verification Method**:
1. Run automated tests (scripts above)
2. Perform manual spot-checks (5 random questions)
3. Review logs and debug artifacts
4. Confirm documentation is accurate

**Sign-Off Date**: _____________

**Approved By**: _____________

---

## Change summary (2026-01-21)

- Added environment readiness criteria (dependencies, browser install, UI reachability).
- Added reproducible run package criteria and preflight verification requirements.
- Preserved 37-question expectation and output schema references.
