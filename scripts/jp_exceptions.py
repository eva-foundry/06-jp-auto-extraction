#!/usr/bin/env python3
"""
JP Automation - Professional Exception Hierarchy
===============================================

Comprehensive exception handling for enterprise-grade system.
Provides context-rich error messages without emojis/Unicode.

Author: JP Automation System
Version: 1.0
Date: 2026-01-23
"""

import os
from datetime import datetime
from typing import Optional, Dict, Any

# Set UTF-8 encoding for Windows compatibility
os.environ.setdefault('PYTHONIOENCODING', 'utf-8')


class JPBaseException(Exception):
    """Base exception for all JP automation errors
    
    Provides standardized error reporting with context and timestamps.
    All JP exceptions inherit from this base class.
    
    Attributes:
        message: Human-readable error description
        context: Additional context about the error
        timestamp: When the error occurred
        error_code: Unique error identifier
    """
    
    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None, 
                 error_code: Optional[str] = None):
        """Initialize JP exception with context
        
        Args:
            message: Error description (ASCII only)
            context: Additional error context
            error_code: Unique error identifier
        """
        super().__init__(message)
        self.message = message
        self.context = context or {}
        self.timestamp = datetime.now().isoformat()
        self.error_code = error_code or self.__class__.__name__
        
    def get_error_report(self) -> Dict[str, Any]:
        """Generate structured error report for logging
        
        Returns:
            Dictionary containing full error details
        """
        return {
            "error_type": self.__class__.__name__,
            "error_code": self.error_code,
            "message": self.message,
            "context": self.context,
            "timestamp": self.timestamp
        }
    
    def __str__(self) -> str:
        base_msg = f"[{self.error_code}] {self.message}"
        if self.context:
            context_str = ", ".join(f"{k}: {v}" for k, v in self.context.items())
            base_msg += f" (Context: {context_str})"
        return base_msg


class JPConfigurationError(JPBaseException):
    """Configuration or environment setup errors
    
    Raised when required configuration is missing or invalid.
    
    Example:
        raise JPConfigurationError(
            "Azure credentials not found",
            context={"required_vars": ["AZURE_CLIENT_ID", "AZURE_CLIENT_SECRET"]},
            error_code="CONF_001"
        )
    """
    pass


class JPAuthenticationError(JPBaseException):
    """Authentication and authorization errors
    
    Raised when browser authentication fails or session expires.
    
    Example:
        raise JPAuthenticationError(
            "Failed to authenticate with JP system",
            context={"login_url": url, "attempts": 3}
        )
    """
    pass


class JPBrowserError(JPBaseException):
    """Browser automation and navigation errors
    
    Raised when Playwright operations fail or pages don't load.
    
    Example:
        raise JPBrowserError(
            "Page load timeout exceeded",
            context={"url": target_url, "timeout_ms": 30000}
        )
    """
    pass


class JPQuestionProcessingError(JPBaseException):
    """Question submission and processing errors
    
    Raised when individual questions fail to process correctly.
    
    Example:
        raise JPQuestionProcessingError(
            "Question submission failed",
            context={"question_id": "Q001", "question_text": question}
        )
    """
    pass


class JPResponseError(JPBaseException):
    """Response capture and parsing errors
    
    Raised when JP responses are incomplete or malformed.
    
    Example:
        raise JPResponseError(
            "Incomplete response detected",
            context={"response_length": len(response), "expected_min": 100}
        )
    """
    pass


class JPValidationError(JPBaseException):
    """Data validation and acceptance criteria errors
    
    Raised when outputs don't meet acceptance criteria.
    
    Example:
        raise JPValidationError(
            "Output file validation failed",
            context={"file_path": str(output_path), "missing_columns": ["answer", "source"]}
        )
    """
    pass


class JPTimeoutError(JPBaseException):
    """Timeout and performance-related errors
    
    Raised when operations exceed acceptable time limits.
    
    Example:
        raise JPTimeoutError(
            "Response completion timeout",
            context={"question_id": "Q001", "elapsed_seconds": 300, "max_seconds": 180}
        )
    """
    pass


class JPDataError(JPBaseException):
    """Data processing and file I/O errors
    
    Raised when input/output operations fail or data is corrupted.
    
    Example:
        raise JPDataError(
            "Input CSV format invalid",
            context={"file_path": str(csv_path), "expected_columns": ["question", "id"]}
        )
    """
    pass


class JPSystemError(JPBaseException):
    """System-level and infrastructure errors
    
    Raised when underlying system components fail.
    
    Example:
        raise JPSystemError(
            "Temporary directory creation failed",
            context={"attempted_path": str(temp_dir), "disk_space_mb": disk_free}
        )
    """
    pass


class JPRetryableError(JPBaseException):
    """Errors that may succeed on retry
    
    Used to indicate temporary failures that warrant automatic retry.
    
    Attributes:
        retry_count: How many retries have been attempted
        max_retries: Maximum allowed retry attempts
    """
    
    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None,
                 error_code: Optional[str] = None, retry_count: int = 0,
                 max_retries: int = 3):
        super().__init__(message, context, error_code)
        self.retry_count = retry_count
        self.max_retries = max_retries
    
    def should_retry(self) -> bool:
        """Check if another retry attempt should be made"""
        return self.retry_count < self.max_retries
    
    def increment_retry(self) -> 'JPRetryableError':
        """Create new exception instance with incremented retry count"""
        return self.__class__(
            self.message,
            self.context,
            self.error_code,
            self.retry_count + 1,
            self.max_retries
        )


class JPCriticalError(JPBaseException):
    """Critical errors requiring immediate shutdown
    
    Raised when system integrity is compromised and safe continuation
    is not possible. These errors trigger graceful shutdown.
    
    Example:
        raise JPCriticalError(
            "Browser process terminated unexpectedly",
            context={"exit_code": proc.returncode, "stderr": error_output}
        )
    """
    pass


def create_exception_from_type(error_type: str, message: str, 
                             context: Optional[Dict[str, Any]] = None,
                             error_code: Optional[str] = None) -> JPBaseException:
    """Factory function to create exceptions by type name
    
    Args:
        error_type: Exception class name (e.g., 'JPBrowserError')
        message: Error message
        context: Additional context
        error_code: Unique error code
        
    Returns:
        Appropriate JP exception instance
        
    Raises:
        ValueError: If error_type is not recognized
    """
    exception_map = {
        'JPConfigurationError': JPConfigurationError,
        'JPAuthenticationError': JPAuthenticationError,
        'JPBrowserError': JPBrowserError,
        'JPQuestionProcessingError': JPQuestionProcessingError,
        'JPResponseError': JPResponseError,
        'JPValidationError': JPValidationError,
        'JPTimeoutError': JPTimeoutError,
        'JPDataError': JPDataError,
        'JPSystemError': JPSystemError,
        'JPRetryableError': JPRetryableError,
        'JPCriticalError': JPCriticalError,
    }
    
    exception_class = exception_map.get(error_type)
    if not exception_class:
        raise ValueError(f"Unknown exception type: {error_type}")
    
    return exception_class(message, context, error_code)


def handle_exception_gracefully(exception: Exception, logger=None) -> Dict[str, Any]:
    """Handle any exception gracefully with structured logging
    
    Args:
        exception: Exception to handle
        logger: Optional logger instance
        
    Returns:
        Structured error report
    """
    if isinstance(exception, JPBaseException):
        error_report = exception.get_error_report()
    else:
        # Convert non-JP exceptions to structured format
        error_report = {
            "error_type": type(exception).__name__,
            "error_code": "UNKNOWN",
            "message": str(exception),
            "context": {},
            "timestamp": datetime.now().isoformat()
        }
    
    # Log if logger provided
    if logger:
        logger.error(f"Exception occurred: {error_report}")
    
    return error_report


# Convenience functions for common error patterns
def raise_configuration_error(missing_config: str, required_configs: list = None):
    """Raise configuration error with standard format"""
    context = {"missing_config": missing_config}
    if required_configs:
        context["required_configs"] = required_configs
    
    raise JPConfigurationError(
        f"Missing required configuration: {missing_config}",
        context=context,
        error_code="CONF_001"
    )


def raise_browser_timeout(operation: str, timeout_seconds: int, url: str = None):
    """Raise browser timeout error with standard format"""
    context = {"operation": operation, "timeout_seconds": timeout_seconds}
    if url:
        context["url"] = url
    
    raise JPTimeoutError(
        f"Browser operation timed out: {operation}",
        context=context,
        error_code="TIMEOUT_001"
    )


def raise_validation_failure(validation_type: str, expected_value: Any, 
                           actual_value: Any, file_path: str = None):
    """Raise validation error with standard format"""
    context = {
        "validation_type": validation_type,
        "expected_value": expected_value,
        "actual_value": actual_value
    }
    if file_path:
        context["file_path"] = file_path
    
    raise JPValidationError(
        f"Validation failed: {validation_type}",
        context=context,
        error_code="VALID_001"
    )