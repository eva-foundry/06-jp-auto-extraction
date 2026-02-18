#!/usr/bin/env python3
"""
JP Automation - Professional Naming System
==========================================

Centralized filename and path management with consistent timestamping.
All files follow: {purpose}_{YYYYMMDD_HHMMSS}.{extension} format.

Author: JP Automation System
Version: 1.0
Date: 2026-01-23
"""

import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

# Set UTF-8 encoding for Windows compatibility
os.environ.setdefault('PYTHONIOENCODING', 'utf-8')

# Standard filename prefixes
JP_ANSWERS_PREFIX = "jp_answers"
JP_RUN_LOG_PREFIX = "jp_run_log"
JP_EVIDENCE_REPORT_PREFIX = "jp_evidence_report"
JP_VALIDATION_RESULTS_PREFIX = "jp_validation_results"
JP_DEBUG_SCREENSHOT_PREFIX = "jp_debug_screenshot"
JP_DEBUG_HTML_PREFIX = "jp_debug_html"
JP_INPUT_BACKUP_PREFIX = "jp_input_backup"
JP_CONFIG_BACKUP_PREFIX = "jp_config_backup"

# Standard timestamp format
TIMESTAMP_FORMAT = "%Y%m%d_%H%M%S"


def get_timestamp() -> str:
    """Generate standardized timestamp string
    
    Returns:
        Timestamp in YYYYMMDD_HHMMSS format (filesystem safe)
    """
    return datetime.now().strftime(TIMESTAMP_FORMAT)


def get_timestamped_filename(purpose: str, extension: str) -> str:
    """Generate standardized timestamped filename
    
    Args:
        purpose: Descriptive purpose (e.g., 'jp_answers', 'jp_run_log')
        extension: File extension without dot (e.g., 'csv', 'log', 'json')
        
    Returns:
        Formatted filename: jp_answers_20260123_143052.csv
        
    Example:
        filename = get_timestamped_filename("jp_answers", "csv")
        # Returns: "jp_answers_20260123_143052.csv"
    """
    timestamp = get_timestamp()
    return f"{purpose}_{timestamp}.{extension}"


def get_question_debug_filename(question_id: str, file_type: str, extension: str) -> str:
    """Generate debug filename for specific question
    
    Args:
        question_id: Question identifier (e.g., 'q001')
        file_type: Debug file type ('screenshot', 'html')
        extension: File extension without dot
        
    Returns:
        Debug filename with question context
        
    Example:
        filename = get_question_debug_filename("q001", "screenshot", "png")
        # Returns: "jp_debug_screenshot_q001_20260123_143052.png"
    """
    timestamp = get_timestamp()
    return f"jp_debug_{file_type}_{question_id}_{timestamp}.{extension}"


class JPFileManager:
    """Professional file path management for JP automation system
    
    Centralizes all file path generation and ensures consistent
    naming conventions across the entire system.
    
    Attributes:
        base_dir: Project root directory
        timestamp: Shared timestamp for related files
        
    Example:
        file_mgr = JPFileManager(Path("./"))
        output_csv = file_mgr.get_output_csv_path()
        log_file = file_mgr.get_log_file_path()
    """
    
    def __init__(self, base_dir: Path, shared_timestamp: Optional[str] = None):
        """Initialize file manager with base directory
        
        Args:
            base_dir: Project root directory path
            shared_timestamp: Optional shared timestamp for related files
        """
        self.base_dir = Path(base_dir)
        self.timestamp = shared_timestamp or get_timestamp()
        
        # Standard directories
        self.input_dir = self.base_dir / "input"
        self.output_dir = self.base_dir / "output"
        self.evidence_dir = self.base_dir / "evidence"
        self.debug_dir = self.base_dir / "debug"
        self.logs_dir = self.base_dir / "logs"
        
        # Ensure directories exist
        for directory in [self.output_dir, self.evidence_dir, self.debug_dir, self.logs_dir]:
            directory.mkdir(parents=True, exist_ok=True)
    
    def get_output_csv_path(self, custom_prefix: Optional[str] = None) -> Path:
        """Get timestamped output CSV path"""
        prefix = custom_prefix or JP_ANSWERS_PREFIX
        filename = f"{prefix}_{self.timestamp}.csv"
        return self.output_dir / filename
    
    def get_log_file_path(self, custom_prefix: Optional[str] = None) -> Path:
        """Get timestamped log file path"""
        prefix = custom_prefix or JP_RUN_LOG_PREFIX
        filename = f"{prefix}_{self.timestamp}.log"
        return self.logs_dir / filename
    
    def get_evidence_report_path(self) -> Path:
        """Get timestamped evidence report path"""
        filename = f"{JP_EVIDENCE_REPORT_PREFIX}_{self.timestamp}.json"
        return self.evidence_dir / filename
    
    def get_validation_results_path(self) -> Path:
        """Get timestamped validation results path"""
        filename = f"{JP_VALIDATION_RESULTS_PREFIX}_{self.timestamp}.json"
        return self.evidence_dir / filename
    
    def get_debug_screenshot_path(self, question_id: str) -> Path:
        """Get debug screenshot path for specific question"""
        filename = get_question_debug_filename(question_id, "screenshot", "png")
        return self.debug_dir / filename
    
    def get_debug_html_path(self, question_id: str) -> Path:
        """Get debug HTML path for specific question"""
        filename = get_question_debug_filename(question_id, "html", "html")
        return self.debug_dir / filename
    
    def get_input_backup_path(self) -> Path:
        """Get input backup path with timestamp"""
        filename = f"{JP_INPUT_BACKUP_PREFIX}_{self.timestamp}.csv"
        return self.output_dir / filename
    
    def get_all_paths(self) -> Dict[str, Path]:
        """Get dictionary of all standard paths for this session
        
        Returns:
            Dictionary mapping path types to Path objects
        """
        return {
            "output_csv": self.get_output_csv_path(),
            "log_file": self.get_log_file_path(),
            "evidence_report": self.get_evidence_report_path(),
            "validation_results": self.get_validation_results_path(),
            "input_backup": self.get_input_backup_path()
        }
    
    def __str__(self) -> str:
        return f"JPFileManager(base_dir={self.base_dir}, timestamp={self.timestamp})"
    
    def __repr__(self) -> str:
        return self.__str__()


# Utility functions for backward compatibility
def create_file_manager(base_dir: Path) -> JPFileManager:
    """Create file manager with current timestamp
    
    Args:
        base_dir: Project root directory
        
    Returns:
        Configured JPFileManager instance
    """
    return JPFileManager(base_dir)


def get_standard_paths(base_dir: Path) -> Dict[str, Path]:
    """Get all standard file paths for current session
    
    Args:
        base_dir: Project root directory
        
    Returns:
        Dictionary of standard file paths with shared timestamp
    """
    file_mgr = create_file_manager(base_dir)
    return file_mgr.get_all_paths()
