# JP Automation Dependency Strategy

## Current Environment Analysis

### ✅ Available in ESDC Enterprise Environment
The following packages are **already installed** and available:

**Core Dependencies**:
- `pandas 2.2.3` - CSV processing and data handling
- `requests 2.32.3` - HTTP requests for API mocking
- `pytest 8.3.4` - Unit testing framework

**Code Quality Tools**:
- `mypy 1.14.1` - Type checking
- `flake8 7.1.1` - Code linting  
- `black 24.10.0` - Code formatting
- `isort 6.0.1` - Import sorting

**Supporting Libraries**:
- `numpy 2.1.3` - Numerical operations
- `urllib3 2.3.0` - HTTP client library
- `json` (built-in) - JSON processing

### ❌ NOT Available in Enterprise Environment
These packages require **DevBox or offline installation**:

**Browser Automation**:
- `playwright` - Browser automation (core requirement)
- `playwright-pytest` - Pytest integration

**Enhanced Testing**:
- `pytest-cov` - Test coverage reporting
- `responses` - HTTP request mocking
- `factory-boy` - Test data generation

## Dependency Installation Strategy

### Phase 1: Enterprise Environment (Current Workstation)
```bash
# Install available core dependencies
pip install -r requirements-core.txt

# Run basic validation without browser automation
python tests/run_validation_suite.py
```

**Capabilities in Enterprise Environment**:
- ✅ Core logic testing (citation extraction, input validation)
- ✅ Unit tests with pytest
- ✅ Code quality checks (mypy, flake8, black)
- ✅ CSV processing and validation
- ❌ Browser automation (requires playwright)
- ❌ Live JP UI testing

### Phase 2: DevBox Environment (Full Capabilities)
```bash
# In DevBox with internet access
pip install playwright pandas pytest pytest-cov

# Install browser binaries
playwright install chromium

# Full functionality available
python scripts/run_jp_batch.py --headed
```

**Full Capabilities in DevBox**:
- ✅ All Phase 1 capabilities
- ✅ Browser automation with playwright  
- ✅ Live JP UI testing
- ✅ Full batch processing (37 questions)
- ✅ Screenshot/HTML debug artifacts
- ✅ Baseline evidence generation

## Alternative Testing Approach (Enterprise-Friendly)

Since playwright is not available, I've implemented a **hybrid testing strategy**:

### 1. Core Logic Testing (No External Dependencies)
```bash
# Tests citation extraction, input validation, deduplication
python tests/test_citation_simple.py
python tests/test_input_validation.py
```

### 2. Mock-Based Integration Testing
```bash
# Uses unittest.mock instead of playwright
python -m pytest tests/unit/ -v
```

### 3. Manual Browser Validation Checklist
When playwright is not available, use this manual validation process:

**Manual Testing Steps**:
1. Open JP UI in browser: `https://ei-jp-ui.purplesky-a9615d9b.canadacentral.azurecontainerapps.io/`
2. Test input field detection: Verify placeholder text matches expectations
3. Test question submission: Submit 1-2 test questions manually
4. Test response extraction: Copy/paste responses to validate citation patterns
5. Compare manual results with automated extraction logic

## Recommended Deployment Path

### Option A: DevBox (Recommended)
```bash
# Complete automation capabilities
1. Access ESDC DevBox with internet connectivity
2. pip install playwright pandas pytest
3. playwright install chromium
4. python scripts/run_jp_batch.py --input input/questions.csv --headed
```

### Option B: Hybrid Approach (Current Workstation)
```bash
# Core validation + manual browser testing
1. pip install -r requirements-core.txt
2. python tests/run_validation_suite.py  # Validate core logic
3. Manual browser testing for UI validation
4. Deploy to DevBox for full automation
```

### Option C: Offline Installation (If Approved)
```bash
# Pre-approved wheelhouse approach
1. Use vetted offline wheels for playwright + dependencies
2. Include browser binaries in approved package
3. Install from offline source
```

## File Updates Made

### Updated Files:
- ✅ `requirements-core.txt` - Enterprise-available packages only
- ✅ `requirements-test.txt` - Documented enterprise constraints
- ✅ Validation test suite - Works without playwright
- ✅ Core logic tests - No external dependencies

### Deployment Commands Updated:

**Current Environment (Workstation)**:
```bash
pip install -r requirements-core.txt
python tests/run_validation_suite.py
```

**DevBox Environment (Full)**:
```bash
pip install playwright pandas pytest
playwright install chromium
python scripts/run_jp_batch.py --input input/questions.csv --count 5 --headed
```

## Success Validation

### ✅ Current Status
- Core dependencies: **AVAILABLE**
- Basic testing: **WORKING**
- Logic validation: **PASSING** (2/2 test suites)
- Input validation: **PASSING** (37 questions validated)

### ⏳ Pending (Requires DevBox)
- Browser automation: **Needs playwright**
- Live UI testing: **Needs network access to JP UI**
- Full batch processing: **Needs complete setup**

## Next Steps

1. **Immediate**: Use current workstation for core logic development and testing
2. **Phase 2**: Move to DevBox for full playwright-based automation
3. **Production**: Deploy to environment with both playwright and JP UI access

The implementation is **core-complete** and ready for DevBox deployment when playwright becomes available.
