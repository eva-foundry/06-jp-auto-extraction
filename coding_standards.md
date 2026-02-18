# JP Automation - Professional Coding Standards

**Version**: 1.0  
**Date**: January 23, 2026  
**Scope**: All JP automation system code and documentation

## Core Principles

### 1. ASCII-Only Policy
**Requirement**: No Unicode or emoji characters in code, logging, or output files.

**Rationale**: Enterprise Windows environments use cp1252 encoding which causes UnicodeEncodeError crashes with Unicode characters.

**Implementation**:
```python
# CORRECT - ASCII only
logger.info("[PASS] Question processed successfully")
logger.error("[FAIL] Browser timeout exceeded")  
logger.warning("[RETRY] Attempting browser restart")
logger.debug("[INFO] Processing question q001")

# INCORRECT - Unicode/emojis
logger.info("✅ Question processed successfully")      # FORBIDDEN
logger.error("❌ Browser timeout exceeded")           # FORBIDDEN  
logger.warning("🔄 Attempting browser restart")       # FORBIDDEN
logger.debug("ℹ️ Processing question q001")            # FORBIDDEN
```

**String Standards**:
```python
# Status indicators
STATUS_PASS = "[PASS]"
STATUS_FAIL = "[FAIL]"  
STATUS_RETRY = "[RETRY]"
STATUS_INFO = "[INFO]"
STATUS_WARN = "[WARN]"
STATUS_ERROR = "[ERROR]"

# Progress indicators  
PROGRESS_START = "[START]"
PROGRESS_COMPLETE = "[COMPLETE]"
PROGRESS_TIMEOUT = "[TIMEOUT]"
PROGRESS_BROWSER_RESTART = "[BROWSER_RESTART]"
```

### 2. Timestamped Naming Convention
**Format**: `{purpose}_{YYYYMMDD_HHMMSS}.{extension}`

**Standard Implementation**:
```python
from datetime import datetime
from pathlib import Path

def get_timestamped_filename(purpose: str, extension: str) -> str:
    """Generate standardized timestamped filename
    
    Args:
        purpose: Descriptive purpose (e.g., 'jp_answers', 'jp_run_log')
        extension: File extension without dot (e.g., 'csv', 'log', 'json')
        
    Returns:
        Formatted filename: jp_answers_20260123_143052.csv
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{purpose}_{timestamp}.{extension}"

# Usage examples
output_file = get_timestamped_filename("jp_answers", "csv")
log_file = get_timestamped_filename("jp_run_log", "log")
evidence_file = get_timestamped_filename("jp_evidence_report", "json")
debug_screenshot = get_timestamped_filename(f"jp_debug_screenshot_{question_id}", "png")
```

**Standard Filenames**:
```python
# Primary outputs
JP_ANSWERS_PREFIX = "jp_answers"
JP_RUN_LOG_PREFIX = "jp_run_log"  
JP_EVIDENCE_REPORT_PREFIX = "jp_evidence_report"
JP_VALIDATION_RESULTS_PREFIX = "jp_validation_results"

# Debug artifacts
JP_DEBUG_SCREENSHOT_PREFIX = "jp_debug_screenshot"
JP_DEBUG_HTML_PREFIX = "jp_debug_html"

# Configuration and backup
JP_INPUT_BACKUP_PREFIX = "jp_input_backup"
JP_CONFIG_BACKUP_PREFIX = "jp_config_backup"
```

### 3. Exception Handling Standards
**Requirement**: Specific exception types with context-rich messages.

**Professional Exception Hierarchy**:
```python
class JPAutomationError(Exception):
    """Base exception for JP automation system"""
    
    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.context = context or {}
        self.timestamp = datetime.now().isoformat()

class BrowserTimeoutError(JPAutomationError):
    """Browser operation exceeded timeout threshold"""
    
    def __init__(self, question_id: str, timeout_seconds: int, operation: str = "response"):
        self.question_id = question_id
        self.timeout_seconds = timeout_seconds
        self.operation = operation
        message = f"Question {question_id} {operation} timeout after {timeout_seconds}s"
        context = {
            "question_id": question_id,
            "timeout_seconds": timeout_seconds,
            "operation": operation
        }
        super().__init__(message, context)

class ValidationError(JPAutomationError):
    """Input validation or acceptance criteria validation failed"""
    
    def __init__(self, validation_type: str, errors: List[str]):
        self.validation_type = validation_type
        self.errors = errors
        message = f"{validation_type} validation failed: {'; '.join(errors)}"
        context = {
            "validation_type": validation_type,
            "errors": errors,
            "error_count": len(errors)
        }
        super().__init__(message, context)

class AuthenticationError(JPAutomationError):
    """JP UI authentication required or failed"""
    
    def __init__(self, reason: str, suggestion: str = ""):
        self.reason = reason
        self.suggestion = suggestion
        message = f"Authentication failed: {reason}"
        if suggestion:
            message += f" - {suggestion}"
        context = {
            "reason": reason,
            "suggestion": suggestion
        }
        super().__init__(message, context)

class ConnectivityError(JPAutomationError):
    """Network or JP UI connectivity issues"""
    
    def __init__(self, endpoint: str, error_type: str, details: str = ""):
        self.endpoint = endpoint
        self.error_type = error_type
        self.details = details
        message = f"Connectivity error to {endpoint}: {error_type}"
        if details:
            message += f" - {details}"
        context = {
            "endpoint": endpoint,
            "error_type": error_type,
            "details": details
        }
        super().__init__(message, context)
```

**Exception Usage Standards**:
```python
# CORRECT - Specific exceptions with context
try:
    result = await process_question(question_id, question_text, timeout=15)
except BrowserTimeoutError as e:
    logger.error(f"[BROWSER_TIMEOUT] {e}")
    # Record failure, continue processing
    return create_failure_result(question_id, str(e))
except AuthenticationError as e:
    logger.error(f"[AUTH_ERROR] {e}")
    # Authentication required, exit gracefully
    raise SystemExit(1)
except ValidationError as e:
    logger.error(f"[VALIDATION_ERROR] {e}")
    # Input issues, log and continue
    return create_failure_result(question_id, str(e))
except Exception as e:
    logger.error(f"[UNEXPECTED_ERROR] Question {question_id}: {e}")
    # Unknown error, log and continue
    return create_failure_result(question_id, f"Unexpected error: {e}")

# INCORRECT - Bare exception handling
try:
    result = await process_question(question_id, question_text)
except:  # FORBIDDEN - too broad
    pass  # FORBIDDEN - silent failure
```

### 4. Logging Standards
**Format**: `[LEVEL] [COMPONENT] [CONTEXT] Message`

**Logger Configuration**:
```python
import logging
from pathlib import Path

def setup_professional_logging(log_dir: Path, log_prefix: str = "jp_run_log") -> logging.Logger:
    """Setup standardized logging configuration"""
    
    # Create timestamped log file
    log_file = log_dir / get_timestamped_filename(log_prefix, "log")
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    logger = logging.getLogger("jp_automation")
    logger.info(f"[SYSTEM] [STARTUP] Logging initialized: {log_file}")
    
    return logger

# Usage throughout system
logger = setup_professional_logging(LOG_DIR)
logger.info(f"[BROWSER] [START] Launching browser session")
logger.info(f"[QUESTION] [PROCESS] Processing {question_id}: {question[:50]}...")
logger.warning(f"[TIMEOUT] [RETRY] Question {question_id} timeout, attempt {attempt}/{max_attempts}")
logger.error(f"[VALIDATION] [FAIL] {validation_type}: {error_details}")
```

### 5. Type Hints and Documentation Standards
**Requirement**: All public functions must have type hints and docstrings.

**Function Documentation Standard**:
```python
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path

async def process_question_batch(
    input_file: Path,
    output_file: Path,
    max_retries: int = 3,
    timeout_seconds: int = 15,
    evidence_collection: bool = True
) -> Tuple[int, int, Dict[str, Any]]:
    """Process batch of questions with professional error handling
    
    Args:
        input_file: Path to CSV file containing questions
        output_file: Path for timestamped output CSV
        max_retries: Maximum attempts per question (default: 3)
        timeout_seconds: Browser timeout per attempt (default: 15)
        evidence_collection: Generate acceptance evidence (default: True)
        
    Returns:
        Tuple containing:
            - success_count: Number of successfully processed questions
            - failure_count: Number of failed questions  
            - evidence_report: Dictionary with validation results
            
    Raises:
        ValidationError: Input file validation failed
        ConnectivityError: JP UI not accessible
        AuthenticationError: Manual authentication required
        
    Example:
        success, failures, evidence = await process_question_batch(
            Path("input/jp_questions_validated.csv"),
            Path("output") / get_timestamped_filename("jp_answers", "csv")
        )
    """
    pass  # Implementation follows
```

**Class Documentation Standard**:
```python
class JPAcceptanceTester:
    """Automated validation of JP automation acceptance criteria
    
    This class implements all 12 acceptance criteria tests defined in
    ACCEPTANCE.md, providing automated verification that the system
    meets functional, reliability, and governance requirements.
    
    Attributes:
        input_file: Path to input questions CSV
        output_file: Path to results CSV
        evidence_dir: Directory for evidence artifacts
        timestamp: Execution timestamp for traceability
        
    Example:
        tester = JPAcceptanceTester(input_csv, output_csv, evidence_dir)
        results = await tester.validate_all_criteria()
        
        if results.all_passed:
            logger.info("[ACCEPTANCE] [PASS] All criteria validated")
        else:
            logger.error(f"[ACCEPTANCE] [FAIL] {results.failure_count} criteria failed")
    """
    
    def __init__(
        self, 
        input_file: Path,
        output_file: Path,
        evidence_dir: Path,
        timestamp: Optional[str] = None
    ):
        """Initialize acceptance tester with required paths"""
        pass
```

### 6. Configuration Management Standards
**Requirement**: Centralized configuration with validation.

**Configuration Structure**:
```python
from dataclasses import dataclass
from typing import Optional
import os

@dataclass
class JPAutomationConfig:
    """Professional configuration management for JP automation"""
    
    # Timeout configuration
    hard_timeout_seconds: int = 15
    initial_timeout_seconds: int = 10  
    buffer_timeout_seconds: int = 5
    max_retries: int = 3
    poll_interval_seconds: int = 1
    throttle_seconds: int = 2
    
    # JP UI configuration
    jp_ui_url: str = "https://jp-chatgpt.hccld2.edsc.gc.ca/"
    
    # Browser configuration
    browser_headless: bool = True
    browser_persistent: bool = False
    cdp_port: int = 9222
    
    # File naming configuration
    enable_timestamps: bool = True
    timestamp_format: str = "%Y%m%d_%H%M%S"
    
    # Evidence collection
    collect_evidence: bool = True
    evidence_spot_check_count: int = 5
    
    # Validation configuration
    validate_acceptance_criteria: bool = True
    require_all_criteria_pass: bool = False
    
    @classmethod
    def from_environment(cls) -> 'JPAutomationConfig':
        """Load configuration from environment variables"""
        return cls(
            jp_ui_url=os.getenv("JP_UI_URL", cls.jp_ui_url),
            hard_timeout_seconds=int(os.getenv("JP_TIMEOUT_SECONDS", cls.hard_timeout_seconds)),
            max_retries=int(os.getenv("JP_MAX_RETRIES", cls.max_retries)),
            browser_headless=os.getenv("JP_HEADLESS", "true").lower() == "true",
            collect_evidence=os.getenv("JP_COLLECT_EVIDENCE", "true").lower() == "true"
        )
    
    def validate(self) -> List[str]:
        """Validate configuration values"""
        errors = []
        
        if self.hard_timeout_seconds <= 0:
            errors.append("hard_timeout_seconds must be positive")
        if self.max_retries <= 0:
            errors.append("max_retries must be positive")
        if not self.jp_ui_url.startswith("http"):
            errors.append("jp_ui_url must be valid HTTP/HTTPS URL")
            
        return errors
```

### 7. Testing Standards
**Requirement**: Unit tests for all utility functions, integration tests for workflows.

**Test Structure**:
```python
import pytest
import asyncio
from pathlib import Path
from unittest.mock import Mock, patch

class TestJPNamingSystem:
    """Test suite for timestamped naming system"""
    
    def test_get_timestamped_filename_format(self):
        """Test filename format matches standard"""
        filename = get_timestamped_filename("jp_answers", "csv")
        
        assert filename.startswith("jp_answers_")
        assert filename.endswith(".csv")
        assert len(filename.split("_")) == 3  # jp, answers, timestamp
        
        # Validate timestamp format
        timestamp = filename.split("_")[2].split(".")[0]
        assert len(timestamp) == 15  # YYYYMMDD_HHMMSS
        assert timestamp[8] == "_"  # Underscore separator

class TestJPAcceptanceTester:
    """Test suite for acceptance criteria validation"""
    
    @pytest.mark.asyncio
    async def test_fr1_row_count_validation(self):
        """Test FR-1: Input/output row count validation"""
        
        # Setup test data
        input_csv = create_test_input(question_count=5)
        output_csv = create_test_output(question_count=5)
        
        tester = JPAcceptanceTester(input_csv, output_csv, Path("evidence"))
        result = await tester.test_fr1_all_questions_processed()
        
        assert result.passed is True
        assert result.details["input_rows"] == 5
        assert result.details["output_rows"] == 5
```

## Implementation Checklist

### Code Quality Requirements
- [ ] No Unicode/emoji characters in any code files
- [ ] All logging uses ASCII status indicators
- [ ] Consistent timestamped filename format
- [ ] Professional exception hierarchy implemented  
- [ ] Type hints on all public functions
- [ ] Comprehensive docstrings with examples
- [ ] Centralized configuration management
- [ ] Unit tests for all utilities

### Standards Enforcement
- [ ] Automated pre-commit hooks for Unicode detection
- [ ] Logging format validation
- [ ] Exception handling pattern validation
- [ ] Type hint coverage verification
- [ ] Documentation completeness checks

### Professional Presentation
- [ ] Clean, readable code structure
- [ ] Consistent naming conventions
- [ ] Appropriate abstraction levels
- [ ] Clear separation of concerns
- [ ] Enterprise-ready error messages

---

**Compliance**: All code must adhere to these standards before integration into the main system.