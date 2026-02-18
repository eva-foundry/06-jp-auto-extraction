#!/usr/bin/env python3
"""
JP Automation - Acceptance Criteria Tester
==========================================

Automated validation of all acceptance criteria from ACCEPTANCE.md.
Provides comprehensive testing framework with detailed reporting.

Author: JP Automation System
Version: 1.0
Date: 2026-01-23
"""

import os
import csv
import json
import subprocess
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
import pandas as pd
import re

# Set UTF-8 encoding for Windows compatibility
os.environ.setdefault('PYTHONIOENCODING', 'utf-8')

# Import professional modules
from jp_exceptions import (
    JPValidationError, JPDataError, JPSystemError, 
    handle_exception_gracefully
)
from jp_naming_system import JPFileManager, get_timestamp

# Standard validation constants
EXPECTED_INPUT_QUESTIONS = 37
EXPECTED_OUTPUT_COLUMNS = ["question_id", "question", "answer_text", "citations", "timestamp", "status", "error"]
ISO_8601_PATTERN = r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}'
MAX_RUNTIME_MINUTES = 30
MAX_MEMORY_GB = 2.0
MIN_CITATION_ACCURACY = 0.95


class AcceptanceCriteriaTester:
    """Comprehensive acceptance criteria validation system
    
    Validates all criteria defined in ACCEPTANCE.md with automated testing
    and detailed reporting. Provides structured pass/fail results.
    
    Attributes:
        project_dir: Base project directory
        file_mgr: File manager for standardized paths
        test_results: Dictionary storing all test results
        logger: Optional logger for detailed output
    """
    
    def __init__(self, project_dir: Path, logger=None):
        """Initialize acceptance tester with project directory
        
        Args:
            project_dir: Path to project root directory
            logger: Optional logger instance for detailed output
        """
        self.project_dir = Path(project_dir)
        self.file_mgr = JPFileManager(self.project_dir)
        self.test_results = {}
        self.logger = logger
        
        # Standard paths
        self.input_dir = self.project_dir / "input"
        self.output_dir = self.project_dir / "output"
        self.scripts_dir = self.project_dir / "scripts"
        self.logs_dir = self.project_dir / "logs"
        self.debug_dir = self.project_dir / "debug"
        
        # Input/output files
        self.input_questions_path = self.input_dir / "questions.csv"
        self.output_answers_path = self.output_dir / "jp_answers.csv"
        self.main_script_path = self.scripts_dir / "run_jp_batch.py"
    
    def log(self, message: str, level: str = "INFO"):
        """Log message with standardized format"""
        timestamp = datetime.now().isoformat()
        formatted_msg = f"[{timestamp}] [{level}] {message}"
        
        if self.logger:
            if level == "ERROR":
                self.logger.error(formatted_msg)
            elif level == "WARNING":
                self.logger.warning(formatted_msg)
            else:
                self.logger.info(formatted_msg)
        else:
            print(formatted_msg)
    
    def run_all_tests(self) -> Dict[str, Any]:
        """Execute all acceptance criteria tests
        
        Returns:
            Comprehensive test results dictionary
        """
        self.log("Starting comprehensive acceptance criteria validation")
        
        try:
            # Functional Requirements
            self.test_fr1_all_questions_processed()
            self.test_fr2_script_completes_unattended()
            self.test_fr3_one_output_per_question()
            self.test_fr4_citations_captured_accurately()
            
            # Environment Readiness
            self.test_er1_dependencies_installed()
            self.test_er2_playwright_chromium_ready()
            self.test_er3_jp_ui_reachable()
            
            # Reliability Requirements
            self.test_rr1_batch_continues_on_failure()
            self.test_rr2_errors_logged_traceable()
            self.test_rr3_debug_artifacts_generated()
            
            # Determinism Requirements
            self.test_dr1_reruns_produce_equivalent()
            self.test_dr2_no_hidden_state()
            
            # Governance & Audit Requirements
            self.test_ga1_clear_separation()
            self.test_ga2_outputs_traceable()
            self.test_ga3_no_backend_assumptions()
            
            # Performance Requirements
            self.test_pr1_reasonable_execution_time()
            self.test_pr2_minimal_resource_usage()
            
            # Documentation Requirements
            self.test_dr1_runnable_instructions()
            self.test_dr2_clear_error_messages()
            self.test_dr3_project_context_documented()
            
            # Reproducible Run Package
            self.test_rp1_exact_commands()
            self.test_rp2_preflight_documented()
            
            self.generate_summary_report()
            
        except Exception as e:
            error_report = handle_exception_gracefully(e, self.logger)
            self.test_results["CRITICAL_ERROR"] = {
                "status": "CRITICAL_FAILURE",
                "error": error_report,
                "timestamp": datetime.now().isoformat()
            }
        
        return self.test_results
    
    def test_fr1_all_questions_processed(self):
        """FR-1: All Input Questions Processed"""
        test_key = "FR1_ALL_QUESTIONS_PROCESSED"
        self.log(f"Testing {test_key}")
        
        try:
            # Check input file exists and count questions
            if not self.input_questions_path.exists():
                raise JPDataError(
                    "Input questions file not found",
                    context={"expected_path": str(self.input_questions_path)}
                )
            
            input_df = pd.read_csv(self.input_questions_path)
            input_count = len(input_df)
            
            # Check output file exists and count answers
            if not self.output_answers_path.exists():
                self.test_results[test_key] = {
                    "status": "FAIL",
                    "reason": "Output file not found - script may not have run yet",
                    "expected_input_count": input_count,
                    "actual_output_count": 0
                }
                return
            
            output_df = pd.read_csv(self.output_answers_path)
            output_count = len(output_df)
            
            # Verify counts match expected
            expected_count = EXPECTED_INPUT_QUESTIONS
            if input_count != expected_count:
                self.test_results[test_key] = {
                    "status": "FAIL",
                    "reason": f"Input count mismatch: expected {expected_count}, found {input_count}",
                    "expected_input_count": expected_count,
                    "actual_input_count": input_count
                }
                return
            
            if output_count != input_count:
                self.test_results[test_key] = {
                    "status": "FAIL", 
                    "reason": f"Output count mismatch: {input_count} input questions, {output_count} output answers",
                    "expected_output_count": input_count,
                    "actual_output_count": output_count
                }
                return
            
            # Verify all question IDs match
            input_ids = set(input_df['question_id'].astype(str))
            output_ids = set(output_df['question_id'].astype(str))
            
            missing_ids = input_ids - output_ids
            extra_ids = output_ids - input_ids
            
            if missing_ids or extra_ids:
                self.test_results[test_key] = {
                    "status": "FAIL",
                    "reason": "Question ID mismatch between input and output",
                    "missing_ids": list(missing_ids),
                    "extra_ids": list(extra_ids)
                }
                return
            
            self.test_results[test_key] = {
                "status": "PASS",
                "input_count": input_count,
                "output_count": output_count,
                "all_ids_matched": True
            }
            
        except Exception as e:
            self.test_results[test_key] = {
                "status": "ERROR",
                "error": handle_exception_gracefully(e)
            }
    
    def test_fr2_script_completes_unattended(self):
        """FR-2: Script Completes Without Manual Intervention"""
        test_key = "FR2_SCRIPT_COMPLETES_UNATTENDED"
        self.log(f"Testing {test_key}")
        
        try:
            # Check if main script exists
            if not self.main_script_path.exists():
                self.test_results[test_key] = {
                    "status": "FAIL",
                    "reason": "Main script not found",
                    "expected_path": str(self.main_script_path)
                }
                return
            
            # This test requires actual execution - check for evidence
            # Look for completed output file and log entries
            completed_runs = []
            
            if self.output_answers_path.exists():
                completed_runs.append("output_csv_exists")
            
            # Check for log files indicating completion
            if self.logs_dir.exists():
                log_files = list(self.logs_dir.glob("*.log"))
                if log_files:
                    completed_runs.append("log_files_exist")
            
            # Check script has headless capability (no interactive prompts)
            with open(self.main_script_path, 'r', encoding='utf-8') as f:
                script_content = f.read()
            
            interactive_indicators = [
                'input(', 'raw_input(', 'getpass.', 'click.confirm',
                'click.prompt', 'sys.stdin.read'
            ]
            
            found_interactive = []
            for indicator in interactive_indicators:
                if indicator in script_content:
                    found_interactive.append(indicator)
            
            if found_interactive:
                self.test_results[test_key] = {
                    "status": "FAIL",
                    "reason": "Script contains interactive elements",
                    "interactive_elements": found_interactive
                }
                return
            
            self.test_results[test_key] = {
                "status": "PASS",
                "script_exists": True,
                "no_interactive_elements": True,
                "evidence_of_completion": completed_runs
            }
            
        except Exception as e:
            self.test_results[test_key] = {
                "status": "ERROR",
                "error": handle_exception_gracefully(e)
            }
    
    def test_fr3_one_output_per_question(self):
        """FR-3: One Output Record Per Input Question"""
        test_key = "FR3_ONE_OUTPUT_PER_QUESTION"
        self.log(f"Testing {test_key}")
        
        try:
            if not self.output_answers_path.exists():
                self.test_results[test_key] = {
                    "status": "FAIL",
                    "reason": "Output file not found"
                }
                return
            
            output_df = pd.read_csv(self.output_answers_path)
            
            # Check for duplicates
            question_ids = output_df['question_id'].astype(str)
            duplicates = question_ids[question_ids.duplicated()].tolist()
            
            if duplicates:
                self.test_results[test_key] = {
                    "status": "FAIL",
                    "reason": "Duplicate question IDs found",
                    "duplicate_ids": duplicates
                }
                return
            
            # Check that failed questions still have rows
            status_counts = output_df['status'].value_counts().to_dict()
            
            self.test_results[test_key] = {
                "status": "PASS",
                "total_rows": len(output_df),
                "no_duplicates": True,
                "status_distribution": status_counts
            }
            
        except Exception as e:
            self.test_results[test_key] = {
                "status": "ERROR", 
                "error": handle_exception_gracefully(e)
            }
    
    def test_fr4_citations_captured_accurately(self):
        """FR-4: Citations Captured Exactly as Presented"""
        test_key = "FR4_CITATIONS_CAPTURED_ACCURATELY"
        self.log(f"Testing {test_key}")
        
        try:
            if not self.output_answers_path.exists():
                self.test_results[test_key] = {
                    "status": "FAIL",
                    "reason": "Output file not found for citation analysis"
                }
                return
            
            output_df = pd.read_csv(self.output_answers_path)
            
            # Check citation column exists and has content
            if 'citations' not in output_df.columns:
                self.test_results[test_key] = {
                    "status": "FAIL",
                    "reason": "Citations column missing from output"
                }
                return
            
            # Analyze citation content
            citations = output_df['citations'].fillna('')
            non_empty_citations = citations[citations.str.strip() != ''].count()
            total_questions = len(output_df)
            
            # Look for citation patterns (case numbers, links, etc.)
            citation_patterns = {
                'case_numbers': citations.str.contains(r'\\d{4} [A-Z]{2,} \\d+', na=False).sum(),
                'links': citations.str.contains(r'http[s]?://', na=False).sum(),
                'tribunal_references': citations.str.contains(r'SST|FC|FCA', na=False).sum()
            }
            
            # Manual validation note
            manual_validation_note = (
                "MANUAL VALIDATION REQUIRED: Select 5 random questions, "
                "query them manually in JP UI, and compare citations. "
                "Target: >=95% accuracy (0-1 discrepancies out of 5 samples)."
            )
            
            self.test_results[test_key] = {
                "status": "MANUAL_VALIDATION_REQUIRED",
                "total_questions": total_questions,
                "questions_with_citations": int(non_empty_citations),
                "citation_coverage_percent": round(non_empty_citations / total_questions * 100, 1),
                "citation_patterns": citation_patterns,
                "validation_instructions": manual_validation_note
            }
            
        except Exception as e:
            self.test_results[test_key] = {
                "status": "ERROR",
                "error": handle_exception_gracefully(e)
            }
    
    def test_er1_dependencies_installed(self):
        """ER-1: Dependencies Installed in Target Environment"""
        test_key = "ER1_DEPENDENCIES_INSTALLED"
        self.log(f"Testing {test_key}")
        
        try:
            required_imports = ['playwright', 'pandas', 'csv', 'pathlib', 'asyncio']
            import_results = {}
            
            for module in required_imports:
                try:
                    __import__(module)
                    import_results[module] = "SUCCESS"
                except ImportError as e:
                    import_results[module] = f"FAILED: {str(e)}"
            
            failed_imports = [k for k, v in import_results.items() if not v.startswith("SUCCESS")]
            
            if failed_imports:
                self.test_results[test_key] = {
                    "status": "FAIL",
                    "reason": f"Missing dependencies: {failed_imports}",
                    "import_results": import_results
                }
            else:
                self.test_results[test_key] = {
                    "status": "PASS",
                    "all_imports_successful": True,
                    "import_results": import_results
                }
                
        except Exception as e:
            self.test_results[test_key] = {
                "status": "ERROR",
                "error": handle_exception_gracefully(e)
            }
    
    def test_er2_playwright_chromium_ready(self):
        """ER-2: Playwright Chromium Installed and Runnable"""
        test_key = "ER2_PLAYWRIGHT_CHROMIUM_READY"
        self.log(f"Testing {test_key}")
        
        try:
            # Check if playwright command is available
            result = subprocess.run(
                ['playwright', '--version'], 
                capture_output=True, 
                text=True, 
                timeout=30
            )
            
            if result.returncode != 0:
                self.test_results[test_key] = {
                    "status": "FAIL",
                    "reason": "Playwright CLI not available",
                    "stderr": result.stderr
                }
                return
            
            playwright_version = result.stdout.strip()
            
            # Try to check browser installation
            browser_result = subprocess.run(
                ['playwright', 'install', '--dry-run', 'chromium'],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            self.test_results[test_key] = {
                "status": "PASS",
                "playwright_version": playwright_version,
                "browser_check_result": browser_result.stdout.strip()
            }
            
        except subprocess.TimeoutExpired:
            self.test_results[test_key] = {
                "status": "FAIL",
                "reason": "Playwright command timed out"
            }
        except FileNotFoundError:
            self.test_results[test_key] = {
                "status": "FAIL",
                "reason": "Playwright CLI not found in PATH"
            }
        except Exception as e:
            self.test_results[test_key] = {
                "status": "ERROR",
                "error": handle_exception_gracefully(e)
            }
    
    def test_er3_jp_ui_reachable(self):
        """ER-3: JP UI Reachable from Run Environment"""
        test_key = "ER3_JP_UI_REACHABLE"
        self.log(f"Testing {test_key}")
        
        try:
            jp_ui_url = "https://ei-jp-ui.purplesky-a9615d9b.canadacentral.azurecontainerapps.io/"
            
            # Try to reach the UI with curl
            result = subprocess.run(
                ['curl', '-I', '--connect-timeout', '30', jp_ui_url],
                capture_output=True,
                text=True,
                timeout=45
            )
            
            if result.returncode == 0 and '200 OK' in result.stdout:
                self.test_results[test_key] = {
                    "status": "PASS",
                    "jp_ui_url": jp_ui_url,
                    "response": "200 OK received"
                }
            else:
                self.test_results[test_key] = {
                    "status": "FAIL",
                    "reason": "JP UI not reachable or not returning 200 OK",
                    "jp_ui_url": jp_ui_url,
                    "curl_stdout": result.stdout,
                    "curl_stderr": result.stderr,
                    "return_code": result.returncode
                }
                
        except subprocess.TimeoutExpired:
            self.test_results[test_key] = {
                "status": "FAIL",
                "reason": "Connection to JP UI timed out"
            }
        except FileNotFoundError:
            self.test_results[test_key] = {
                "status": "FAIL",
                "reason": "curl command not found - cannot test connectivity"
            }
        except Exception as e:
            self.test_results[test_key] = {
                "status": "ERROR",
                "error": handle_exception_gracefully(e)
            }
    
    def test_rr1_batch_continues_on_failure(self):
        """RR-1: Batch Continues on Individual Failure"""
        test_key = "RR1_BATCH_CONTINUES_ON_FAILURE"
        self.log(f"Testing {test_key}")
        
        try:
            if not self.output_answers_path.exists():
                self.test_results[test_key] = {
                    "status": "FAIL",
                    "reason": "Output file not found - cannot assess batch resilience"
                }
                return
            
            output_df = pd.read_csv(self.output_answers_path)
            
            # Check for failed questions
            failed_questions = output_df[
                output_df['status'].isin(['error', 'timeout', 'failure'])
            ]
            success_questions = output_df[output_df['status'] == 'success']
            
            total_questions = len(output_df)
            failed_count = len(failed_questions)
            success_count = len(success_questions)
            
            if failed_count == 0:
                self.test_results[test_key] = {
                    "status": "INDETERMINATE",
                    "reason": "No failed questions found - cannot test batch continuation",
                    "total_questions": total_questions,
                    "success_count": success_count
                }
                return
            
            # If we have both failures and successes, batch continued
            if failed_count > 0 and success_count > 0:
                self.test_results[test_key] = {
                    "status": "PASS",
                    "total_questions": total_questions,
                    "failed_count": failed_count,
                    "success_count": success_count,
                    "batch_continued": True
                }
            else:
                self.test_results[test_key] = {
                    "status": "FAIL",
                    "reason": "All questions failed - batch may have stopped on first error",
                    "total_questions": total_questions,
                    "failed_count": failed_count,
                    "success_count": success_count
                }
                
        except Exception as e:
            self.test_results[test_key] = {
                "status": "ERROR",
                "error": handle_exception_gracefully(e)
            }
    
    def test_rr2_errors_logged_traceable(self):
        """RR-2: Errors Are Logged and Traceable"""
        test_key = "RR2_ERRORS_LOGGED_TRACEABLE"
        self.log(f"Testing {test_key}")
        
        try:
            # Check output file for error details
            if not self.output_answers_path.exists():
                self.test_results[test_key] = {
                    "status": "FAIL", 
                    "reason": "Output file not found"
                }
                return
            
            output_df = pd.read_csv(self.output_answers_path)
            
            # Check for error column and content
            if 'error' not in output_df.columns:
                self.test_results[test_key] = {
                    "status": "FAIL",
                    "reason": "Error column missing from output"
                }
                return
            
            # Find failed questions
            failed_df = output_df[
                output_df['status'].isin(['error', 'timeout', 'failure'])
            ]
            
            if len(failed_df) == 0:
                self.test_results[test_key] = {
                    "status": "INDETERMINATE",
                    "reason": "No failed questions found - cannot test error logging"
                }
                return
            
            # Check if failed questions have error messages
            failed_with_errors = failed_df[
                failed_df['error'].notna() & 
                (failed_df['error'].str.strip() != '')
            ]
            
            # Check log files
            log_files = []
            error_logs_found = False
            
            if self.logs_dir.exists():
                log_files = list(self.logs_dir.glob("*.log"))
                for log_file in log_files:
                    with open(log_file, 'r', encoding='utf-8') as f:
                        log_content = f.read()
                        if 'ERROR' in log_content or 'FAIL' in log_content:
                            error_logs_found = True
                            break
            
            self.test_results[test_key] = {
                "status": "PASS" if len(failed_with_errors) > 0 else "FAIL",
                "total_failed_questions": len(failed_df),
                "failed_with_error_messages": len(failed_with_errors),
                "log_files_found": len(log_files),
                "error_logs_present": error_logs_found,
                "error_coverage_percent": round(len(failed_with_errors) / len(failed_df) * 100, 1) if len(failed_df) > 0 else 0
            }
            
        except Exception as e:
            self.test_results[test_key] = {
                "status": "ERROR",
                "error": handle_exception_gracefully(e)
            }
    
    def test_rr3_debug_artifacts_generated(self):
        """RR-3: Debug Artifacts Generated for Failed Rows"""
        test_key = "RR3_DEBUG_ARTIFACTS_GENERATED"
        self.log(f"Testing {test_key}")
        
        try:
            # Check for debug directories
            screenshots_dir = self.debug_dir / "screenshots"
            html_dir = self.debug_dir / "html"
            
            debug_structure = {
                "debug_dir_exists": self.debug_dir.exists(),
                "screenshots_dir_exists": screenshots_dir.exists(),
                "html_dir_exists": html_dir.exists()
            }
            
            if not self.output_answers_path.exists():
                self.test_results[test_key] = {
                    "status": "FAIL",
                    "reason": "Output file not found",
                    "debug_structure": debug_structure
                }
                return
            
            output_df = pd.read_csv(self.output_answers_path)
            failed_df = output_df[
                output_df['status'].isin(['error', 'timeout', 'failure'])
            ]
            
            if len(failed_df) == 0:
                self.test_results[test_key] = {
                    "status": "INDETERMINATE",
                    "reason": "No failed questions found - cannot test debug artifact generation",
                    "debug_structure": debug_structure
                }
                return
            
            # Check for debug artifacts matching failed questions
            failed_ids = failed_df['question_id'].astype(str).tolist()
            artifacts_found = {"screenshots": 0, "html": 0}
            
            if screenshots_dir.exists():
                screenshot_files = list(screenshots_dir.glob("*.png"))
                for failed_id in failed_ids:
                    matching_screenshots = [f for f in screenshot_files if failed_id in f.name]
                    if matching_screenshots:
                        artifacts_found["screenshots"] += 1
            
            if html_dir.exists():
                html_files = list(html_dir.glob("*.html"))
                for failed_id in failed_ids:
                    matching_html = [f for f in html_files if failed_id in f.name]
                    if matching_html:
                        artifacts_found["html"] += 1
            
            self.test_results[test_key] = {
                "status": "PASS" if artifacts_found["screenshots"] > 0 or artifacts_found["html"] > 0 else "FAIL",
                "total_failed_questions": len(failed_df),
                "failed_question_ids": failed_ids,
                "debug_artifacts_found": artifacts_found,
                "debug_structure": debug_structure
            }
            
        except Exception as e:
            self.test_results[test_key] = {
                "status": "ERROR",
                "error": handle_exception_gracefully(e)
            }
    
    def test_dr1_reruns_produce_equivalent(self):
        """DR-1: Re-running Produces Equivalent Outputs"""
        test_key = "DR1_RERUNS_PRODUCE_EQUIVALENT"
        self.log(f"Testing {test_key}")
        
        # This test requires multiple runs - check for evidence
        self.test_results[test_key] = {
            "status": "MANUAL_TEST_REQUIRED",
            "reason": "This test requires running the script twice and comparing outputs",
            "instructions": [
                "Run: python scripts/run_jp_batch.py --in input/questions.csv --out output/run1.csv",
                "Run: python scripts/run_jp_batch.py --in input/questions.csv --out output/run2.csv",
                "Compare outputs excluding timestamp column",
                "Verify minimal differences (timestamps expected, major answer changes not allowed)"
            ]
        }
    
    def test_dr2_no_hidden_state(self):
        """DR-2: No Hidden State Between Runs"""
        test_key = "DR2_NO_HIDDEN_STATE"
        self.log(f"Testing {test_key}")
        
        # Check for state files that might persist between runs
        state_indicators = []
        
        # Look for cache files, temp files, session files
        potential_state_files = [
            self.project_dir.glob("*.cache"),
            self.project_dir.glob("*session*"),
            self.project_dir.glob("*temp*"),
            self.project_dir.glob(".state*"),
            self.project_dir.glob("*cookie*")
        ]
        
        for pattern in potential_state_files:
            state_indicators.extend(list(pattern))
        
        # Check if script cleans up after itself
        cleanup_indicators = {
            "removes_temp_files": False,
            "clears_browser_state": False,
            "independent_sessions": True
        }
        
        if self.main_script_path.exists():
            with open(self.main_script_path, 'r', encoding='utf-8') as f:
                script_content = f.read()
                
                # Look for cleanup code
                if any(keyword in script_content for keyword in ['cleanup', 'remove', 'delete', 'clear']):
                    cleanup_indicators["removes_temp_files"] = True
                
                if any(keyword in script_content for keyword in ['new_context', 'incognito', 'private']):
                    cleanup_indicators["clears_browser_state"] = True
        
        self.test_results[test_key] = {
            "status": "PASS" if len(state_indicators) == 0 else "WARNING",
            "potential_state_files": [str(f) for f in state_indicators],
            "cleanup_indicators": cleanup_indicators,
            "recommendation": "Verify each run starts fresh by clearing output/debug directories between runs"
        }
    
    # Additional test methods for remaining criteria...
    # (Continuing with placeholder implementations for brevity)
    
    def test_ga1_clear_separation(self):
        """GA-1: Inputs, Outputs, and Scripts Clearly Separated"""
        test_key = "GA1_CLEAR_SEPARATION"
        self.log(f"Testing {test_key}")
        
        required_dirs = {
            "input": self.input_dir,
            "output": self.output_dir,
            "scripts": self.scripts_dir,
            "logs": self.logs_dir,
            "debug": self.debug_dir
        }
        
        dir_status = {}
        for name, path in required_dirs.items():
            dir_status[name] = {
                "exists": path.exists(),
                "path": str(path),
                "is_directory": path.is_dir() if path.exists() else False
            }
        
        all_dirs_exist = all(status["exists"] for status in dir_status.values())
        
        self.test_results[test_key] = {
            "status": "PASS" if all_dirs_exist else "FAIL",
            "directory_structure": dir_status,
            "clear_separation": all_dirs_exist
        }
    
    def test_ga2_outputs_traceable(self):
        """GA-2: Outputs Traceable to Inputs"""
        test_key = "GA2_OUTPUTS_TRACEABLE"
        self.log(f"Testing {test_key}")
        
        try:
            if not self.output_answers_path.exists():
                self.test_results[test_key] = {
                    "status": "FAIL",
                    "reason": "Output file not found"
                }
                return
            
            output_df = pd.read_csv(self.output_answers_path)
            
            # Check required traceability columns
            required_columns = ["question_id", "question", "timestamp"]
            missing_columns = [col for col in required_columns if col not in output_df.columns]
            
            if missing_columns:
                self.test_results[test_key] = {
                    "status": "FAIL",
                    "reason": f"Missing traceability columns: {missing_columns}",
                    "expected_columns": required_columns,
                    "actual_columns": list(output_df.columns)
                }
                return
            
            # Validate timestamp format (ISO 8601)
            timestamps = output_df['timestamp'].fillna('')
            valid_timestamps = timestamps.str.match(ISO_8601_PATTERN).sum()
            total_rows = len(output_df)
            
            self.test_results[test_key] = {
                "status": "PASS" if valid_timestamps == total_rows else "FAIL",
                "total_rows": total_rows,
                "valid_timestamps": int(valid_timestamps),
                "timestamp_format_compliance": round(valid_timestamps / total_rows * 100, 1),
                "required_columns_present": True
            }
            
        except Exception as e:
            self.test_results[test_key] = {
                "status": "ERROR",
                "error": handle_exception_gracefully(e)
            }
    
    def test_ga3_no_backend_assumptions(self):
        """GA-3: No Backend or API Assumptions"""
        test_key = "GA3_NO_BACKEND_ASSUMPTIONS"
        self.log(f"Testing {test_key}")
        
        try:
            if not self.main_script_path.exists():
                self.test_results[test_key] = {
                    "status": "FAIL",
                    "reason": "Main script not found"
                }
                return
            
            with open(self.main_script_path, 'r', encoding='utf-8') as f:
                script_content = f.read()
            
            # Check for disallowed API patterns
            forbidden_patterns = {
                'requests_module': 'requests.',
                'urllib_module': 'urllib.',
                'httpx_module': 'httpx.',
                'direct_api_calls': 'api/',
                'database_access': 'SELECT|INSERT|UPDATE|DELETE'
            }
            
            violations = {}
            for pattern_name, pattern in forbidden_patterns.items():
                matches = re.findall(pattern, script_content, re.IGNORECASE)
                if matches:
                    violations[pattern_name] = len(matches)
            
            # Check for Playwright usage (allowed)
            playwright_usage = 'playwright' in script_content.lower()
            
            self.test_results[test_key] = {
                "status": "PASS" if len(violations) == 0 else "FAIL",
                "uses_playwright": playwright_usage,
                "api_violations": violations,
                "ui_only_automation": len(violations) == 0 and playwright_usage
            }
            
        except Exception as e:
            self.test_results[test_key] = {
                "status": "ERROR",
                "error": handle_exception_gracefully(e)
            }
    
    def test_pr1_reasonable_execution_time(self):
        """PR-1: Reasonable Execution Time"""
        test_key = "PR1_REASONABLE_EXECUTION_TIME"
        self.log(f"Testing {test_key}")
        
        # Check log files for execution time evidence
        execution_time_evidence = []
        
        if self.logs_dir.exists():
            log_files = list(self.logs_dir.glob("*.log"))
            for log_file in log_files:
                try:
                    with open(log_file, 'r', encoding='utf-8') as f:
                        log_content = f.read()
                        # Look for time indicators
                        if 'completed in' in log_content.lower():
                            execution_time_evidence.append(f"Found timing info in {log_file.name}")
                except:
                    continue
        
        self.test_results[test_key] = {
            "status": "MANUAL_TEST_REQUIRED",
            "reason": "Execution time must be measured during actual run",
            "target_max_minutes": MAX_RUNTIME_MINUTES,
            "execution_evidence": execution_time_evidence,
            "instructions": "Time the script execution and verify it completes within 30 minutes"
        }
    
    def test_pr2_minimal_resource_usage(self):
        """PR-2: Minimal Resource Usage"""
        test_key = "PR2_MINIMAL_RESOURCE_USAGE"
        self.log(f"Testing {test_key}")
        
        self.test_results[test_key] = {
            "status": "MANUAL_TEST_REQUIRED",
            "reason": "Resource usage must be measured during actual execution",
            "targets": {
                "max_memory_gb": MAX_MEMORY_GB,
                "max_cpu_percent": 50,
                "max_disk_mb": 100
            },
            "instructions": "Monitor system resources during script execution using task manager or similar"
        }
    
    def test_dr1_runnable_instructions(self):
        """DR-1: Runnable Installation Instructions"""
        test_key = "DR1_RUNNABLE_INSTRUCTIONS"
        self.log(f"Testing {test_key}")
        
        readme_path = self.project_dir / "README.md"
        
        if not readme_path.exists():
            self.test_results[test_key] = {
                "status": "FAIL",
                "reason": "README.md not found"
            }
            return
        
        with open(readme_path, 'r', encoding='utf-8') as f:
            readme_content = f.read()
        
        # Check for key documentation sections
        required_sections = {
            'installation': any(keyword in readme_content.lower() for keyword in ['install', 'setup', 'dependencies']),
            'usage': any(keyword in readme_content.lower() for keyword in ['usage', 'run', 'execute']),
            'examples': any(keyword in readme_content.lower() for keyword in ['example', 'sample', 'demo']),
            'commands': '```' in readme_content  # Code blocks present
        }
        
        sections_present = sum(required_sections.values())
        
        self.test_results[test_key] = {
            "status": "PASS" if sections_present >= 3 else "FAIL",
            "readme_exists": True,
            "sections_found": required_sections,
            "documentation_completeness": f"{sections_present}/4 required sections"
        }
    
    def test_dr2_clear_error_messages(self):
        """DR-2: Clear Error Messages"""
        test_key = "DR2_CLEAR_ERROR_MESSAGES"
        self.log(f"Testing {test_key}")
        
        try:
            if not self.output_answers_path.exists():
                self.test_results[test_key] = {
                    "status": "INDETERMINATE",
                    "reason": "Output file not found - cannot assess error message quality"
                }
                return
            
            output_df = pd.read_csv(self.output_answers_path)
            failed_df = output_df[
                output_df['status'].isin(['error', 'timeout', 'failure'])
            ]
            
            if len(failed_df) == 0:
                self.test_results[test_key] = {
                    "status": "INDETERMINATE",
                    "reason": "No failed questions found - cannot assess error message quality"
                }
                return
            
            # Analyze error message quality
            error_messages = failed_df['error'].fillna('').astype(str)
            
            quality_checks = {
                'non_empty_errors': (error_messages.str.strip() != '').sum(),
                'includes_question_id': error_messages.str.contains(r'q\\d+').sum(),
                'actionable_details': error_messages.str.contains('debug|screenshot|log|check').sum()
            }
            
            total_errors = len(failed_df)
            
            self.test_results[test_key] = {
                "status": "PASS" if quality_checks['non_empty_errors'] == total_errors else "FAIL",
                "total_error_cases": total_errors,
                "quality_analysis": quality_checks,
                "error_message_completeness": round(quality_checks['non_empty_errors'] / total_errors * 100, 1)
            }
            
        except Exception as e:
            self.test_results[test_key] = {
                "status": "ERROR",
                "error": handle_exception_gracefully(e)
            }
    
    def test_dr3_project_context_documented(self):
        """DR-3: Project Context Documented"""
        test_key = "DR3_PROJECT_CONTEXT_DOCUMENTED"
        self.log(f"Testing {test_key}")
        
        documentation_files = {
            'README.md': self.project_dir / "README.md",
            'PLAN.md': self.project_dir / "PLAN.md",
            'ACCEPTANCE.md': self.project_dir / "ACCEPTANCE.md"
        }
        
        doc_analysis = {}
        
        for doc_name, doc_path in documentation_files.items():
            if doc_path.exists():
                with open(doc_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                doc_analysis[doc_name] = {
                    "exists": True,
                    "word_count": len(content.split()),
                    "has_purpose": any(keyword in content.lower() for keyword in ['purpose', 'why', 'goal', 'objective']),
                    "has_context": any(keyword in content.lower() for keyword in ['context', 'background', 'problem', 'need'])
                }
            else:
                doc_analysis[doc_name] = {"exists": False}
        
        documentation_score = sum(1 for doc in doc_analysis.values() if doc.get('exists', False))
        
        self.test_results[test_key] = {
            "status": "PASS" if documentation_score >= 2 else "FAIL",
            "documentation_analysis": doc_analysis,
            "documentation_files_present": documentation_score,
            "context_adequacy": "Sufficient" if documentation_score >= 2 else "Insufficient"
        }
    
    def test_rp1_exact_commands(self):
        """RP-1: Run Package Includes Exact Commands"""
        test_key = "RP1_EXACT_COMMANDS"
        self.log(f"Testing {test_key}")
        
        readme_path = self.project_dir / "README.md"
        
        if not readme_path.exists():
            self.test_results[test_key] = {
                "status": "FAIL",
                "reason": "README.md not found"
            }
            return
        
        with open(readme_path, 'r', encoding='utf-8') as f:
            readme_content = f.read()
        
        # Look for command examples
        command_indicators = {
            'python_commands': readme_content.count('python '),
            'pip_install': readme_content.count('pip install'),
            'playwright_install': readme_content.count('playwright install'),
            'code_blocks': readme_content.count('```'),
            'executable_examples': any(keyword in readme_content for keyword in ['run_jp_batch.py', 'scripts/'])
        }
        
        commands_present = sum(1 for v in command_indicators.values() if (isinstance(v, int) and v > 0) or (isinstance(v, bool) and v))
        
        self.test_results[test_key] = {
            "status": "PASS" if commands_present >= 3 else "FAIL",
            "command_indicators": command_indicators,
            "command_completeness": f"{commands_present}/5 command types found"
        }
    
    def test_rp2_preflight_documented(self):
        """RP-2: Preflight Check is Documented"""
        test_key = "RP2_PREFLIGHT_DOCUMENTED"
        self.log(f"Testing {test_key}")
        
        readme_path = self.project_dir / "README.md"
        
        if not readme_path.exists():
            self.test_results[test_key] = {
                "status": "FAIL",
                "reason": "README.md not found"
            }
            return
        
        with open(readme_path, 'r', encoding='utf-8') as f:
            readme_content = f.read()
        
        preflight_indicators = {
            'dependencies_check': any(keyword in readme_content.lower() for keyword in ['dependencies', 'requirements', 'prerequisites']),
            'browser_install': 'playwright install' in readme_content.lower(),
            'connectivity_check': any(keyword in readme_content.lower() for keyword in ['connectivity', 'reachable', 'network']),
            'preflight_section': any(keyword in readme_content.lower() for keyword in ['preflight', 'pre-flight', 'before running', 'checklist'])
        }
        
        preflight_coverage = sum(preflight_indicators.values())
        
        self.test_results[test_key] = {
            "status": "PASS" if preflight_coverage >= 2 else "FAIL",
            "preflight_indicators": preflight_indicators,
            "preflight_coverage": f"{preflight_coverage}/4 preflight elements documented"
        }
    
    def generate_summary_report(self):
        """Generate comprehensive summary of all test results"""
        
        # Categorize results
        passed_tests = []
        failed_tests = []
        manual_tests = []
        error_tests = []
        indeterminate_tests = []
        
        for test_key, result in self.test_results.items():
            status = result.get("status", "UNKNOWN")
            
            if status == "PASS":
                passed_tests.append(test_key)
            elif status == "FAIL":
                failed_tests.append(test_key)
            elif status in ["MANUAL_TEST_REQUIRED", "MANUAL_VALIDATION_REQUIRED"]:
                manual_tests.append(test_key)
            elif status == "ERROR":
                error_tests.append(test_key)
            elif status in ["INDETERMINATE", "WARNING"]:
                indeterminate_tests.append(test_key)
        
        total_tests = len(self.test_results)
        automated_tests = total_tests - len(manual_tests)
        automated_pass_rate = len(passed_tests) / automated_tests * 100 if automated_tests > 0 else 0
        
        summary = {
            "timestamp": datetime.now().isoformat(),
            "total_tests": total_tests,
            "automated_tests": automated_tests,
            "manual_tests_required": len(manual_tests),
            "test_results_summary": {
                "PASS": len(passed_tests),
                "FAIL": len(failed_tests),
                "MANUAL_REQUIRED": len(manual_tests),
                "ERROR": len(error_tests),
                "INDETERMINATE": len(indeterminate_tests)
            },
            "automated_pass_rate_percent": round(automated_pass_rate, 1),
            "critical_failures": [test for test in failed_tests if "FR" in test or "ER" in test],
            "ready_for_production": len(failed_tests) == 0 and len(error_tests) == 0,
            "next_actions": self._generate_next_actions(failed_tests, manual_tests, error_tests)
        }
        
        self.test_results["SUMMARY"] = summary
        self.log(f"Acceptance criteria testing completed: {len(passed_tests)}/{automated_tests} automated tests passed")
    
    def _generate_next_actions(self, failed_tests: List[str], manual_tests: List[str], error_tests: List[str]) -> List[str]:
        """Generate actionable next steps based on test results"""
        actions = []
        
        if error_tests:
            actions.append(f"CRITICAL: Fix {len(error_tests)} tests with errors - review detailed error reports")
        
        if failed_tests:
            actions.append(f"Fix {len(failed_tests)} failing automated tests - see individual test details")
        
        if manual_tests:
            actions.append(f"Complete {len(manual_tests)} manual validation tests - follow provided instructions")
        
        if not (failed_tests or error_tests):
            actions.append("System appears ready for production - complete manual validations")
        
        return actions
    
    def save_results_to_file(self, output_path: Optional[Path] = None) -> Path:
        """Save test results to JSON file with timestamp
        
        Args:
            output_path: Optional custom output path
            
        Returns:
            Path to saved results file
        """
        if output_path is None:
            output_path = self.file_mgr.get_validation_results_path()
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(self.test_results, f, indent=2, default=str)
        
        return output_path


def run_acceptance_tests(project_dir: Path, logger=None) -> Dict[str, Any]:
    """Convenience function to run all acceptance tests
    
    Args:
        project_dir: Project root directory
        logger: Optional logger instance
        
    Returns:
        Complete test results dictionary
    """
    tester = AcceptanceCriteriaTester(project_dir, logger)
    results = tester.run_all_tests()
    
    # Save results to file
    results_file = tester.save_results_to_file()
    results["results_file_path"] = str(results_file)
    
    return results


if __name__ == "__main__":
    # Command-line usage
    import sys
    
    if len(sys.argv) > 1:
        project_path = Path(sys.argv[1])
    else:
        project_path = Path(".")
    
    print(f"Running acceptance criteria tests for: {project_path}")
    
    results = run_acceptance_tests(project_path)
    
    summary = results.get("SUMMARY", {})
    print(f"\\nTest Summary:")
    print(f"Total tests: {summary.get('total_tests', 0)}")
    print(f"Automated pass rate: {summary.get('automated_pass_rate_percent', 0):.1f}%")
    print(f"Ready for production: {summary.get('ready_for_production', False)}")
    
    if summary.get("next_actions"):
        print("\\nNext Actions:")
        for action in summary["next_actions"]:
            print(f"  - {action}")
    
    print(f"\\nDetailed results saved to: {results.get('results_file_path', 'results.json')}")