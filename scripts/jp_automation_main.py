#!/usr/bin/env python3
"""
JP Automation - Professional Main Script
========================================

Enterprise-grade browser automation for legal question processing.
Follows professional coding standards with comprehensive error handling.

Author: JP Automation System
Version: 2.0 (Professional Refactor)  
Date: 2026-01-23

Usage:
    python jp_automation_main.py --input input/questions.csv --output output/jp_answers.csv
    python jp_automation_main.py --input input/questions.csv --output output/jp_answers.csv --headed
    python jp_automation_main.py --input input/questions.csv --output output/jp_answers.csv --connect --limit 5
"""

import os
import sys
import argparse
import asyncio
import logging
import re
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
import pandas as pd
from contextlib import asynccontextmanager

# Set UTF-8 encoding for Windows compatibility
os.environ.setdefault('PYTHONIOENCODING', 'utf-8')

# Import professional modules
from jp_naming_system import JPFileManager, get_timestamp
from jp_exceptions import (
    JPConfigurationError, JPAuthenticationError, JPBrowserError,
    JPQuestionProcessingError, JPResponseError, JPValidationError,
    JPTimeoutError, JPDataError, JPSystemError, JPCriticalError,
    handle_exception_gracefully
)
from jp_acceptance_tester import run_acceptance_tests
from jp_evidence_collector import collect_comprehensive_evidence
from jp_session_manager import EnhancedJPBrowserManager

# Import browser automation components
try:
    from playwright.async_api import async_playwright, Page, TimeoutError as PlaywrightTimeout, Browser, BrowserContext
    import psutil
except ImportError as e:
    raise JPConfigurationError(
        "Required dependencies not installed",
        context={"missing_dependency": str(e), "install_command": "pip install playwright psutil"}
    )

# Configuration constants  
JP_UI_URL = "https://ei-jp-ui.purplesky-a9615d9b.canadacentral.azurecontainerapps.io/"
INITIAL_TIMEOUT_SECONDS = 10   # First check after 10 seconds (user expectation)
EXTENDED_TIMEOUT_SECONDS = 5   # Additional 5 seconds if no response
HARD_TIMEOUT_SECONDS = 15      # 15 seconds absolute maximum (10+5)
POLL_INTERVAL_SECONDS = 2      # Check response every 2 seconds
RESPONSE_STABILITY_CHECKS = 2  # Require 2 consecutive stable checks
MIN_RESPONSE_LENGTH = 50       # Minimum characters for substantial response

# Phase-aware timeout configuration for enhanced detection
PHASE_TIMEOUTS = {
    "thinking": 10,      # Initial thinking phase - users expect 5-10 seconds
    "search": 10,        # Search agent should be fast
    "analysis": 15,      # Document analysis maximum 15 seconds
    "summary": 15,       # Summary generation maximum 15 seconds
    "unknown": 15        # Default maximum 15 seconds
}

# Enhanced citation patterns for quality validation
CITATION_PATTERNS = [
    r'\b20\d{2}\s+(FC|SST|FCA)\s+\d+\b',  # 2024 FC 679, 2021 SST 188
    r'\b\d{4}\s+CanLII\s+\d+\b',          # 1234 CanLII 5678
    r'\bA-\d+-\d+\b',                      # A-123-45 (Federal Court)
    r'\bGE-\d+-\d+\b',                     # GE-12-345 (SST)
]

# Quality indicators for legal responses
QUALITY_INDICATORS = [
    "decision:", "appeal", "tribunal", "court held",
    "ruling", "precedent", "case law", "judgment"
]

# Retry configuration
MAX_RETRIES = 3
BASE_BACKOFF = 2.0  # Base seconds for exponential backoff
MAX_BACKOFF = 30.0  # Maximum backoff time
MAX_RETRIES = 2               # Maximum retry attempts per question
THROTTLE_SECONDS = 3          # Delay between questions

# UI Element selectors
CHAT_INPUT_PLACEHOLDER_VARIANTS = [
    "Type your message here...",
    "Type your message here",
    "Type a message"
]
SEND_BUTTON_SELECTOR = '#chat-submit, button[aria-label="Send message"], button:has-text("Send")'
CHAT_CONTAINER_SELECTOR = '.chat-messages, [role="log"], .message-list'
ASSISTANT_MESSAGE_SELECTOR = '.assistant-message, .bot-message, [data-role="assistant"]'


class JPBrowserManager:
    """Professional browser management with lifecycle control
    
    Manages Playwright browser instances with proper cleanup,
    error handling, and connection management.
    
    Attributes:
        headless: Whether to run browser in headless mode
        persistent: Whether to use persistent browser context
        connect_url: Optional URL for connecting to existing browser
        browser: Current browser instance
        context: Current browser context
        page: Current page instance
        session_id: Unique session identifier
    """
    
    def __init__(self, headless: bool = True, persistent: bool = False, 
                 connect_url: Optional[str] = None, session_id: Optional[str] = None):
        """Initialize browser manager
        
        Args:
            headless: Run browser without UI
            persistent: Use persistent context to maintain state
            connect_url: URL to connect to existing browser instance
            session_id: Unique session identifier for logging
        """
        self.headless = headless
        self.persistent = persistent  
        self.connect_url = connect_url
        self.session_id = session_id or f"session_{get_timestamp()}"
        
        # Browser components
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        
        # Lifecycle tracking
        self.browser_pid: Optional[int] = None
        self.start_time: Optional[datetime] = None
    
    @asynccontextmanager
    async def browser_session(self):
        """Async context manager for browser session lifecycle
        
        Ensures proper cleanup even if exceptions occur.
        
        Yields:
            Page instance ready for automation
            
        Raises:
            JPBrowserError: If browser initialization fails
        """
        try:
            page = await self.start_browser_session()
            self.start_time = datetime.now()
            yield page
        except Exception as e:
            raise JPBrowserError(
                "Browser session initialization failed",
                context={"error": str(e), "session_id": self.session_id}
            )
        finally:
            await self.cleanup_browser_session()
    
    async def start_browser_session(self) -> Page:
        """Start fresh browser session with proper configuration
        
        Returns:
            Page instance ready for automation
            
        Raises:
            JPBrowserError: If browser startup fails
        """
        try:
            # Clean up any existing session
            await self.cleanup_browser_session()
            
            # Initialize Playwright
            self.playwright = await async_playwright().start()
            
            if self.connect_url:
                await self._connect_to_existing_browser()
            else:
                await self._launch_new_browser()
            
            # Navigate to JP UI
            await self.page.goto(JP_UI_URL, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(3)  # Allow UI initialization
            
            return self.page
            
        except Exception as e:
            await self.cleanup_browser_session()
            raise JPBrowserError(
                "Failed to start browser session",
                context={
                    "error": str(e),
                    "connect_url": self.connect_url,
                    "headless": self.headless,
                    "session_id": self.session_id
                }
            )
    
    async def _connect_to_existing_browser(self):
        """Connect to existing browser via CDP"""
        try:
            self.browser = await self.playwright.chromium.connect_over_cdp(self.connect_url)
            contexts = self.browser.contexts
            
            if contexts:
                self.context = contexts[0]
                pages = self.context.pages
                self.page = pages[0] if pages else await self.context.new_page()
            else:
                self.context = await self.browser.new_context(
                    viewport={'width': 1920, 'height': 1080},
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                )
                self.page = await self.context.new_page()
                
        except Exception as e:
            # Fallback to new browser if connection fails
            self.connect_url = None
            await self._launch_new_browser()
    
    async def _launch_new_browser(self):
        """Launch new browser instance"""
        if self.persistent:
            user_data_dir = str(Path.home() / ".jp_automation_browser")
            self.context = await self.playwright.chromium.launch_persistent_context(
                user_data_dir=user_data_dir,
                headless=self.headless,
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                args=['--disable-blink-features=AutomationControlled']
            )
            self.page = await self.context.new_page()
            self.browser = self.context
        else:
            self.browser = await self.playwright.chromium.launch(
                headless=self.headless,
                args=['--disable-blink-features=AutomationControlled']
            )
            self.context = await self.browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            )
            self.page = await self.context.new_page()
    
    async def cleanup_browser_session(self):
        """Clean up browser resources"""
        try:
            if self.page:
                await self.page.close()
                self.page = None
                
            if self.context and not self.persistent:
                await self.context.close()
                self.context = None
                
            if self.browser:
                await self.browser.close()
                self.browser = None
                
            if self.playwright:
                await self.playwright.stop()
                self.playwright = None
                
        except Exception as e:
            # Log cleanup errors but don't raise
            logging.warning(f"Browser cleanup error: {e}")


class JPQuestionProcessor:
    """Professional question processing with JP response handling
    
    Handles the complete question-answer workflow including response
    completion detection, citation extraction, and error recovery.
    
    Attributes:
        browser_manager: Browser management instance
        file_manager: File management instance
        logger: Logging instance
        session_stats: Session statistics tracking
    """
    
    def __init__(self, browser_manager: JPBrowserManager, file_manager: JPFileManager, logger):
        """Initialize question processor
        
        Args:
            browser_manager: Configured browser manager instance
            file_manager: File management instance for paths
            logger: Logging instance for detailed output
        """
        self.browser_manager = browser_manager
        self.file_manager = file_manager
        self.logger = logger
        
        # Session statistics
        self.session_stats = {
            "questions_processed": 0,
            "successful_responses": 0,
            "failed_responses": 0,
            "timeout_responses": 0,
            "total_processing_time": 0.0,
            "start_time": datetime.now()
        }
    
    async def process_questions_batch(self, questions: List[Dict[str, str]], 
                                    limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Process batch of questions with comprehensive error handling
        
        Args:
            questions: List of question dictionaries with 'question_id' and 'question'
            limit: Optional limit on number of questions to process
            
        Returns:
            List of result dictionaries with answers, citations, and metadata
            
        Raises:
            JPCriticalError: If batch processing cannot continue
        """
        results = []
        questions_to_process = questions[:limit] if limit else questions
        
        self.logger.info(f"Starting batch processing: {len(questions_to_process)} questions")
        
        async with self.browser_manager as manager:
            page = manager.page
            for i, question_data in enumerate(questions_to_process, 1):
                try:
                    self.logger.info(f"Processing question {i}/{len(questions_to_process)}: {question_data.get('question_id', 'unknown')}")
                    
                    result = await self.process_single_question(page, question_data, i)
                    results.append(result)
                    
                    # Update statistics
                    self.session_stats["questions_processed"] += 1
                    if result["status"] == "success":
                        self.session_stats["successful_responses"] += 1
                    elif result["status"] == "timeout":
                        self.session_stats["timeout_responses"] += 1
                    else:
                        self.session_stats["failed_responses"] += 1
                    
                    # Throttle between questions
                    if i < len(questions_to_process):
                        await asyncio.sleep(THROTTLE_SECONDS)
                        
                except JPCriticalError:
                    # Critical errors stop batch processing
                    raise
                except Exception as e:
                    # Non-critical errors are logged and processing continues
                    error_result = self._create_error_result(question_data, e)
                    results.append(error_result)
                    self.session_stats["failed_responses"] += 1
                    
                    self.logger.error(f"Question processing failed: {question_data.get('question_id', 'unknown')} - {e}")
        
        self._log_session_summary()
        return results
    
    async def process_single_question(self, page: Page, question_data: Dict[str, str], 
                                    question_number: int) -> Dict[str, Any]:
        """Process single question with retry logic
        
        Args:
            page: Browser page instance
            question_data: Question dictionary with 'question_id' and 'question'
            question_number: Current question number for context
            
        Returns:
            Result dictionary with answer, citations, and metadata
            
        Raises:
            JPQuestionProcessingError: If question processing fails after retries
        """
        question_id = question_data.get("question_id", f"q{question_number:03d}")
        question_text = question_data.get("question", "")
        
        if not question_text.strip():
            raise JPValidationError(
                "Empty question text provided",
                context={"question_id": question_id, "question_number": question_number}
            )
        
        # Attempt processing with enhanced retry logic and exponential backoff
        last_exception = None
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                self.logger.info(f"Processing {question_id} (attempt {attempt}/{MAX_RETRIES})")
                
                # Submit question and wait for response
                await self._submit_question(page, question_text, question_id)
                response_data = await self._wait_for_response_completion(page, question_id)
                
                # Create successful result with enhanced data
                result = {
                    "question_id": question_id,
                    "question": question_text,
                    "answer_text": response_data["answer_text"],
                    "citations": response_data["citations"],
                    "extracted_citations": response_data.get("extracted_citations", []),
                    "timestamp": datetime.now().isoformat(),
                    "status": "success",
                    "error": "",
                    "processing_time_seconds": response_data["processing_time"],
                    "attempt_number": attempt,
                    "quality_score": response_data.get("quality_score", 0),
                    "citations_count": response_data.get("citations_count", 0),
                    "has_decision": response_data.get("has_decision", False),
                    "content_length": response_data.get("content_length", 0)
                }
                
                self.logger.info(f"Successfully processed {question_id} on attempt {attempt}, "
                               f"citations: {result['citations_count']}, quality_score: {result['quality_score']}")
                return result
                
            except JPTimeoutError as e:
                last_exception = e
                await self._save_debug_artifacts(page, question_id, f"timeout_attempt_{attempt}")
                
                if attempt == MAX_RETRIES:
                    return self._create_timeout_result(question_data, e, attempt)
                else:
                    # Exponential backoff with jitter
                    backoff_time = min(BASE_BACKOFF * (2 ** (attempt - 1)), MAX_BACKOFF)
                    jitter = backoff_time * 0.1 * (0.5 - (datetime.now().timestamp() % 1))
                    total_backoff = backoff_time + jitter
                    
                    self.logger.warning(f"Question {question_id} timed out on attempt {attempt}, "
                                      f"retrying in {total_backoff:.1f}s...")
                    await asyncio.sleep(total_backoff)
                    
            except JPResponseError as e:
                last_exception = e
                await self._save_debug_artifacts(page, question_id, f"jp_error_attempt_{attempt}")
                
                # Handle JP glitch specifically - retry immediately
                if "jp_glitch" in str(e).lower():
                    if attempt == MAX_RETRIES:
                        self.logger.error(f"JP glitch persisted after {MAX_RETRIES} attempts for {question_id}")
                        return self._create_error_result(question_data, e, attempt)
                    else:
                        self.logger.warning(f"JP glitch detected for {question_id} on attempt {attempt}, retrying immediately...")
                        await asyncio.sleep(2)  # Brief pause before retry
                        continue
                
                # Handle other response errors
                if attempt == MAX_RETRIES:
                    return self._create_error_result(question_data, e, attempt)
                else:
                    backoff_time = min(BASE_BACKOFF * (2 ** (attempt - 1)), MAX_BACKOFF)
                    self.logger.warning(f"Response error for {question_id} on attempt {attempt}: {e}, "
                                      f"retrying in {backoff_time:.1f}s...")
                    await asyncio.sleep(backoff_time)
                    
            except Exception as e:
                last_exception = e
                await self._save_debug_artifacts(page, question_id, f"error_attempt_{attempt}")
                
                if attempt == MAX_RETRIES:
                    return self._create_error_result(question_data, e, attempt)
                else:
                    # Exponential backoff for general errors too
                    backoff_time = min(BASE_BACKOFF * (2 ** (attempt - 1)), MAX_BACKOFF)
                    self.logger.warning(f"Question {question_id} failed on attempt {attempt}: {e}, "
                                      f"retrying in {backoff_time:.1f}s...")
                    await asyncio.sleep(backoff_time)
        
        # This should not be reached, but handle gracefully
        return self._create_error_result(question_data, last_exception or Exception("Max retries exceeded"))
    
    async def _submit_question(self, page: Page, question_text: str, question_id: str):
        """Submit question to JP interface with screenshot validation
        
        Args:
            page: Browser page instance
            question_text: Question to submit
            question_id: Question identifier for context
            
        Raises:
            JPQuestionProcessingError: If question submission fails
        """
        try:
            # Step 1: Take screenshot before submission to verify chat is ready
            await self._save_debug_artifacts(page, question_id, "before_submission")
            
            # Find and click input field
            input_found = False
            for placeholder in CHAT_INPUT_PLACEHOLDER_VARIANTS:
                try:
                    input_selector = f'input[placeholder="{placeholder}"], textarea[placeholder="{placeholder}"]'
                    await page.wait_for_selector(input_selector, timeout=10000)
                    await page.click(input_selector)
                    await page.fill(input_selector, question_text)
                    input_found = True
                    break
                except PlaywrightTimeout:
                    continue
            
            if not input_found:
                # Fallback: try any visible input/textarea
                await page.wait_for_selector('input:visible, textarea:visible', timeout=10000)
                await page.click('input:visible, textarea:visible')
                await page.fill('input:visible, textarea:visible', question_text)
            
            # Submit question
            await page.click(SEND_BUTTON_SELECTOR)
            await asyncio.sleep(1)  # Allow submission to process
            
        except PlaywrightTimeout:
            raise JPQuestionProcessingError(
                "Unable to find question input field or send button",
                context={"question_id": question_id, "url": page.url}
            )
        except Exception as e:
            raise JPQuestionProcessingError(
                "Question submission failed",
                context={"question_id": question_id, "error": str(e)}
            )
    
    async def _wait_for_response_completion(self, page: Page, question_id: str) -> Dict[str, Any]:
        """Enhanced wait for JP response with phase-aware timeouts and quality validation
        
        Args:
            page: Browser page instance
            question_id: Question identifier for context
            
        Returns:
            Dictionary with answer_text, citations, and processing_time
            
        Raises:
            JPTimeoutError: If response doesn't complete within timeout
        """
        start_time = datetime.now()
        last_content = ""
        stable_count = 0
        current_phase = "unknown"
        phase_start_time = start_time
        
        # Enhanced JP response phases to detect
        phase_indicators = {
            "thinking": ["Thinking...", "⏳ Thinking..."],
            "search": ["Search Agent Federal Court of Appeals", "Search Agent"], 
            "analysis": ["Document analysis, this may take additional time", "Document analysis"],
            "summary": ["Summary Agent", "Analyzing documents found", "Analyzing documents"]
        }
        
        self.logger.info(f"Starting enhanced response detection for question {question_id}")
        
        try:
            while (datetime.now() - start_time).total_seconds() < HARD_TIMEOUT_SECONDS:
                # Get current response content
                try:
                    # Look for assistant messages
                    messages = await page.query_selector_all(ASSISTANT_MESSAGE_SELECTOR)
                    if messages:
                        # Get the latest message content
                        latest_message = messages[-1]
                        current_content = await latest_message.inner_text()
                    else:
                        # Fallback: get all chat content
                        chat_container = await page.query_selector(CHAT_CONTAINER_SELECTOR)
                        current_content = await chat_container.inner_text() if chat_container else ""
                    
                    if not current_content:
                        await asyncio.sleep(POLL_INTERVAL_SECONDS)
                        continue
                    
                    # Detect phase changes
                    detected_phase = self._detect_current_phase(current_content, phase_indicators)
                    if detected_phase != current_phase:
                        self.logger.info(f"Phase transition: {current_phase} -> {detected_phase}")
                        current_phase = detected_phase
                        phase_start_time = datetime.now()
                    
                    # Check phase-specific timeout
                    phase_elapsed = (datetime.now() - phase_start_time).total_seconds()
                    phase_timeout = PHASE_TIMEOUTS.get(current_phase, PHASE_TIMEOUTS["unknown"])
                    
                    if phase_elapsed > phase_timeout:
                        self.logger.warning(f"Phase timeout exceeded for {current_phase} phase ({phase_timeout}s)")
                        # For analysis phase, extend timeout as it can take very long
                        if current_phase == "analysis" and phase_elapsed < 600:  # 10 minutes max for analysis
                            self.logger.info("Extending timeout for document analysis phase")
                            phase_start_time = datetime.now()  # Reset timer
                    
                    # Enhanced completion detection
                    is_complete, completion_details = self._is_response_complete_enhanced(current_content, last_content)
                    
                    if is_complete:
                        # Content appears complete, check for stability
                        if current_content == last_content:
                            stable_count += 1
                            if stable_count >= RESPONSE_STABILITY_CHECKS:
                                # Response is stable and complete
                                processing_time = (datetime.now() - start_time).total_seconds()
                                self.logger.info(f"Response complete after {stable_count} stable checks, "
                                               f"citations: {completion_details.get('citations_found', 0)}")
                                return self._extract_response_data_enhanced(current_content, processing_time, completion_details)
                        else:
                            stable_count = 0  # Reset stability counter
                        
                        last_content = current_content
                    else:
                        # Still processing, reset stability
                        stable_count = 0
                        last_content = current_content
                    
                    # Log progress every 30 seconds
                    total_elapsed = (datetime.now() - start_time).total_seconds()
                    if total_elapsed % 30 < POLL_INTERVAL_SECONDS:
                        self.logger.info(f"Waiting for completion: {total_elapsed:.0f}s elapsed, "
                                       f"phase={current_phase}, citations={completion_details.get('citations_found', 0)}")
                    
                    await asyncio.sleep(POLL_INTERVAL_SECONDS)
                    
                except Exception as e:
                    self.logger.warning(f"Error checking response content: {e}")
                    await asyncio.sleep(POLL_INTERVAL_SECONDS)
            
            # Timeout reached
            processing_time = (datetime.now() - start_time).total_seconds()
            self.logger.warning(f"Hard timeout ({HARD_TIMEOUT_SECONDS}s) reached for question {question_id}")
            
            # Return partial results if available
            if last_content and len(last_content) > MIN_RESPONSE_LENGTH:
                self.logger.info("Returning partial response due to timeout")
                _, completion_details = self._is_response_complete_enhanced(last_content, "")
                return self._extract_response_data_enhanced(last_content, processing_time, completion_details)
            
            raise JPTimeoutError(
                "Response completion timeout exceeded",
                context={
                    "question_id": question_id,
                    "timeout_seconds": HARD_TIMEOUT_SECONDS,
                    "processing_time": processing_time,
                    "last_content_length": len(last_content),
                    "final_phase": current_phase
                }
            )
            
        except JPTimeoutError:
            raise
        except Exception as e:
            raise JPResponseError(
                "Error waiting for response completion",
                context={"question_id": question_id, "error": str(e)}
            )
    
    def _detect_current_phase(self, content: str, phase_indicators: Dict[str, List[str]]) -> str:
        """Detect which phase JP is currently in
        
        Args:
            content: Current response content
            phase_indicators: Dictionary mapping phases to indicator strings
            
        Returns:
            Current phase name
        """
        content_lower = content.lower()
        
        for phase, indicators in phase_indicators.items():
            for indicator in indicators:
                if indicator.lower() in content_lower:
                    return phase
        
        return "unknown"
    
    def _is_response_complete_enhanced(self, content: str, previous_content: str = "") -> Tuple[bool, Dict[str, Any]]:
        """Enhanced completion detection focusing on 'Case Details' prefix and JP glitch detection
        
        Args:
            content: Current response content
            previous_content: Previous content for comparison
            
        Returns:
            Tuple of (is_complete, completion_details)
        """
        if len(content) < MIN_RESPONSE_LENGTH:
            return False, {"reason": "insufficient_content", "citations_found": 0}
        
        completion_details = {
            "citations_found": 0,
            "has_case_details": False,
            "content_length": len(content),
            "is_jp_glitch": False,
            "stable_content": content == previous_content if previous_content else False
        }
        
        content_lower = content.lower()
        
        # Check for incomplete indicators (still processing)
        incomplete_indicators = [
            "thinking...", "⏳ thinking...", "search agent", "document analysis",
            "this may take additional time", "analyzing documents", "summary agent"
        ]
        
        for indicator in incomplete_indicators:
            if indicator.lower() in content_lower:
                return False, {**completion_details, "reason": "still_processing", "phase": indicator}
        
        # PRIMARY COMPLETION CRITERIA: Look for "Case Details" prefix
        if content.strip().startswith("Case Details"):
            completion_details["has_case_details"] = True
            
            # Citation analysis using regex patterns
            import re
            for pattern in CITATION_PATTERNS:
                matches = re.findall(pattern, content, re.IGNORECASE)
                completion_details["citations_found"] += len(matches)
            
            return True, {**completion_details, "reason": "case_details_found"}
        
        # DETECT JP GLITCH: Generic "no documents found" response
        jp_glitch_indicators = [
            "no documents were found that specifically address",
            "you may want to reformulate your question",
            "provide additional details to refine the search"
        ]
        
        for glitch_indicator in jp_glitch_indicators:
            if glitch_indicator.lower() in content_lower:
                completion_details["is_jp_glitch"] = True
                return True, {**completion_details, "reason": "jp_glitch_detected"}
        
        # Check for explicit completion indicators (fallback)
        completion_indicators = [
            "2024 fc", "2021 sst", "2022 fc", "2023 sst",  # Recent case citations
            "decision: the court", "decision: the tribunal",
            "link: appellant v respondent"
        ]
        
        has_completion_indicator = any(indicator in content_lower for indicator in completion_indicators)
        
        # Fallback completion if no "Case Details" but has strong indicators
        if has_completion_indicator or completion_details["citations_found"] > 0:
            import re
            for pattern in CITATION_PATTERNS:
                matches = re.findall(pattern, content, re.IGNORECASE)
                completion_details["citations_found"] += len(matches)
            
            return True, {**completion_details, "reason": "fallback_completion"}
        
        # Not complete - still waiting
        return False, {**completion_details, "reason": "waiting_for_case_details"}
    
    def _extract_response_data(self, content: str, processing_time: float) -> Dict[str, Any]:
        """Extract answer text and citations from response content
        
        Args:
            content: Complete response content
            processing_time: Processing time in seconds
            
        Returns:
            Dictionary with answer_text, citations, and processing_time
        """
        # Split content into answer and citations
        lines = content.split('\\n')
        
        answer_lines = []
        citation_lines = []
        
        in_citations = False
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Check for citation indicators
            if any(indicator in line for indicator in ["Link:", "2024 FC", "2021 SST", "Citation:", "Source:"]):
                in_citations = True
                citation_lines.append(line)
            elif in_citations:
                citation_lines.append(line)
            else:
                answer_lines.append(line)
        
        answer_text = '\\n'.join(answer_lines).strip()
        citations = '\\n'.join(citation_lines).strip()
        
        return {
            "answer_text": answer_text,
            "citations": citations,
            "processing_time": processing_time
        }
    
    def _extract_response_data_enhanced(self, content: str, processing_time: float, completion_details: Dict[str, Any]) -> Dict[str, Any]:
        """Enhanced extraction with completion details integration
        
        Args:
            content: Complete response content
            processing_time: Processing time in seconds
            completion_details: Details from completion detection
            
        Returns:
            Dictionary with enhanced response data
        """
        # Get basic extraction first
        basic_data = self._extract_response_data(content, processing_time)
        
        # Add enhanced data
        enhanced_data = {
            **basic_data,
            "extracted_citations": [],
            "quality_score": 0,
            "citations_count": completion_details.get("citations_found", 0),
            "has_decision": completion_details.get("has_case_details", False),
            "content_length": len(content),
            "completion_reason": completion_details.get("reason", "unknown")
        }
        
        # Extract individual citations for detailed analysis
        if basic_data["citations"]:
            citation_lines = basic_data["citations"].split('\n')
            enhanced_data["extracted_citations"] = [line.strip() for line in citation_lines if line.strip()]
        
        # Calculate quality score
        if enhanced_data["citations_count"] > 0:
            enhanced_data["quality_score"] += 50
        if enhanced_data["has_decision"]:
            enhanced_data["quality_score"] += 30
        if len(content) > 200:
            enhanced_data["quality_score"] += 20
        
        return enhanced_data
    
    async def _save_debug_artifacts(self, page: Page, question_id: str, context: str):
        """Save debug artifacts for failed questions
        
        Args:
            page: Browser page instance
            question_id: Question identifier
            context: Context for artifact naming
        """
        try:
            debug_dir = self.file_manager.debug_dir
            debug_dir.mkdir(parents=True, exist_ok=True)
            
            # Save screenshot
            screenshot_path = debug_dir / f"jp_debug_screenshot_{question_id}_{context}_{get_timestamp()}.png"
            await page.screenshot(path=str(screenshot_path), full_page=True)
            
            # Save HTML content
            html_path = debug_dir / f"jp_debug_html_{question_id}_{context}_{get_timestamp()}.html"
            html_content = await page.content()
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
                
            self.logger.info(f"Debug artifacts saved for {question_id}: {screenshot_path.name}, {html_path.name}")
            
        except Exception as e:
            self.logger.warning(f"Failed to save debug artifacts for {question_id}: {e}")
    
    def _create_timeout_result(self, question_data: Dict[str, str], 
                             error: Exception, attempt: int) -> Dict[str, Any]:
        """Create result dictionary for timeout case"""
        return {
            "question_id": question_data.get("question_id", "unknown"),
            "question": question_data.get("question", ""),
            "answer_text": "",
            "citations": "",
            "timestamp": datetime.now().isoformat(),
            "status": "timeout",
            "error": f"Response timeout after {DEFAULT_TIMEOUT_SECONDS} seconds (attempt {attempt}): {str(error)}",
            "processing_time_seconds": DEFAULT_TIMEOUT_SECONDS,
            "attempt_number": attempt
        }
    
    def _create_error_result(self, question_data: Dict[str, str], 
                           error: Exception, attempt: int = 1) -> Dict[str, Any]:
        """Create result dictionary for error case"""
        return {
            "question_id": question_data.get("question_id", "unknown"),
            "question": question_data.get("question", ""),
            "answer_text": "",
            "citations": "",
            "timestamp": datetime.now().isoformat(),
            "status": "error",
            "error": f"Processing error (attempt {attempt}): {str(error)}",
            "processing_time_seconds": 0.0,
            "attempt_number": attempt
        }
    
    def _log_session_summary(self):
        """Log comprehensive session summary"""
        total_time = (datetime.now() - self.session_stats["start_time"]).total_seconds()
        success_rate = (self.session_stats["successful_responses"] / 
                       max(self.session_stats["questions_processed"], 1)) * 100
        
        summary = f"""
[SESSION SUMMARY]
Total Questions: {self.session_stats["questions_processed"]}
Successful: {self.session_stats["successful_responses"]}
Failed: {self.session_stats["failed_responses"]}  
Timeouts: {self.session_stats["timeout_responses"]}
Success Rate: {success_rate:.1f}%
Total Time: {total_time:.1f} seconds
Average per Question: {total_time / max(self.session_stats["questions_processed"], 1):.1f} seconds
        """.strip()
        
        self.logger.info(summary)


class JPAutomationMain:
    """Professional main application class
    
    Coordinates the complete JP automation workflow including
    input validation, browser management, question processing,
    output generation, and evidence collection.
    
    Attributes:
        args: Command line arguments
        file_manager: File management instance
        logger: Logging instance
        session_id: Unique session identifier
    """
    
    def __init__(self, args: argparse.Namespace):
        """Initialize main application
        
        Args:
            args: Parsed command line arguments
        """
        self.args = args
        self.session_id = f"jp_session_{get_timestamp()}"
        
        # Initialize professional file management
        project_dir = Path(__file__).parent.parent
        self.file_manager = JPFileManager(project_dir, self.session_id)
        
        # Setup comprehensive logging
        self._setup_logging()
        
        self.logger.info(f"JP Automation Professional v2.0 - Session {self.session_id}")
        self.logger.info(f"Arguments: {vars(args)}")
    
    def _setup_logging(self):
        """Setup comprehensive logging system"""
        log_file = self.file_manager.get_log_file_path("jp_main_log")
        
        # Create logger
        self.logger = logging.getLogger(f"jp_automation_{self.session_id}")
        self.logger.setLevel(logging.INFO)
        
        # Clear any existing handlers
        self.logger.handlers.clear()
        
        # File handler
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_formatter = logging.Formatter(
            '%(asctime)s [%(levelname)s] [%(name)s] %(message)s'
        )
        file_handler.setFormatter(file_formatter)
        self.logger.addHandler(file_handler)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_formatter = logging.Formatter(
            '[%(levelname)s] %(message)s'
        )
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)
    
    async def run(self) -> int:
        """Execute complete JP automation workflow
        
        Returns:
            Exit code (0 for success, non-zero for failure)
        """
        try:
            self.logger.info("Starting JP automation workflow")
            
            # Phase 1: Validate inputs
            questions = await self._load_and_validate_input()
            
            # Phase 2: Process questions
            results = await self._process_questions(questions)
            
            # Phase 3: Save outputs
            output_path = await self._save_results(results)
            
            # Phase 4: Run validation and evidence collection
            if not self.args.skip_validation:
                await self._run_validation_and_evidence_collection(output_path)
            
            self.logger.info("JP automation workflow completed successfully")
            return 0
            
        except JPCriticalError as e:
            self.logger.error(f"Critical error - stopping execution: {e}")
            return 2
        except Exception as e:
            error_report = handle_exception_gracefully(e, self.logger)
            self.logger.error(f"Unexpected error: {error_report}")
            return 1
    
    async def _load_and_validate_input(self) -> List[Dict[str, str]]:
        """Load and validate input questions
        
        Returns:
            List of validated question dictionaries
            
        Raises:
            JPDataError: If input validation fails
        """
        input_path = Path(self.args.input)
        
        if not input_path.exists():
            raise JPDataError(
                "Input file not found",
                context={"input_path": str(input_path)}
            )
        
        try:
            df = pd.read_csv(input_path)
            
            # Validate required columns
            required_columns = ['question_id', 'question']
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            if missing_columns:
                raise JPValidationError(
                    "Input CSV missing required columns",
                    context={
                        "missing_columns": missing_columns,
                        "available_columns": list(df.columns),
                        "input_path": str(input_path)
                    }
                )
            
            # Convert to list of dictionaries
            questions = df.to_dict('records')
            
            # Validate individual questions
            valid_questions = []
            for i, question in enumerate(questions, 1):
                if not question.get('question', '').strip():
                    self.logger.warning(f"Skipping empty question at row {i}")
                    continue
                valid_questions.append(question)
            
            if not valid_questions:
                raise JPValidationError(
                    "No valid questions found in input file",
                    context={"input_path": str(input_path), "total_rows": len(questions)}
                )
            
            self.logger.info(f"Loaded {len(valid_questions)} valid questions from {input_path}")
            return valid_questions
            
        except pd.errors.EmptyDataError:
            raise JPDataError(
                "Input CSV file is empty",
                context={"input_path": str(input_path)}
            )
        except pd.errors.ParserError as e:
            raise JPDataError(
                "Input CSV parsing failed",
                context={"input_path": str(input_path), "parse_error": str(e)}
            )
    
    async def _process_questions(self, questions: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        """Process questions using browser automation with persistent session management
        
        Args:
            questions: List of question dictionaries
            
        Returns:
            List of result dictionaries
            
        Raises:
            JPCriticalError: If processing cannot continue
        """
        # Initialize enhanced browser manager with session persistence
        browser_manager = EnhancedJPBrowserManager(
            headless=not self.args.headed,
            connect_url=self.args.connect_url
        )
        
        # Initialize question processor
        processor = JPQuestionProcessor(browser_manager, self.file_manager, self.logger)
        
        # Process questions
        results = await processor.process_questions_batch(questions, self.args.limit)
        
        return results
    
    async def _save_results(self, results: List[Dict[str, Any]]) -> Path:
        """Save results to CSV output file
        
        Args:
            results: List of result dictionaries
            
        Returns:
            Path to saved output file
            
        Raises:
            JPDataError: If output saving fails
        """
        try:
            # Determine output path
            if hasattr(self.args, 'output') and self.args.output:
                base_output_path = Path(self.args.output)
                if self.args.timestamp_output:
                    output_path = self.file_manager.get_output_csv_path(base_output_path.stem)
                else:
                    output_path = base_output_path
            else:
                output_path = self.file_manager.get_output_csv_path()
            
            # Create output DataFrame
            df = pd.DataFrame(results)
            
            # Ensure output directory exists
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Save to CSV
            df.to_csv(output_path, index=False, encoding='utf-8')
            
            self.logger.info(f"Results saved to: {output_path}")
            self.logger.info(f"Total results: {len(results)}")
            
            # Log summary statistics
            if results:
                status_counts = df['status'].value_counts().to_dict()
                self.logger.info(f"Status distribution: {status_counts}")
            
            return output_path
            
        except Exception as e:
            raise JPDataError(
                "Failed to save results",
                context={"output_path": str(output_path), "error": str(e)}
            )
    
    async def _run_validation_and_evidence_collection(self, output_path: Path):
        """Run acceptance criteria validation and evidence collection
        
        Args:
            output_path: Path to generated output file
        """
        try:
            self.logger.info("Running acceptance criteria validation...")
            
            # Run acceptance tests
            project_dir = self.file_manager.base_dir
            validation_results = run_acceptance_tests(project_dir, self.logger)
            
            # Generate evidence report
            self.logger.info("Generating evidence collection report...")
            evidence_data = collect_comprehensive_evidence(project_dir, self.logger)
            
            # Log validation summary
            validation_summary = validation_results.get("SUMMARY", {})
            self.logger.info(f"Acceptance validation completed:")
            self.logger.info(f"  Total tests: {validation_summary.get('total_tests', 0)}")
            self.logger.info(f"  Pass rate: {validation_summary.get('automated_pass_rate_percent', 0)}%")
            self.logger.info(f"  Ready for production: {validation_summary.get('ready_for_production', False)}")
            
            # Log evidence collection summary
            evidence_summary = evidence_data.get("collection_summary", {})
            self.logger.info(f"Evidence collection completed:")
            self.logger.info(f"  Duration: {evidence_summary.get('total_duration_minutes', 0)} minutes")
            self.logger.info(f"  Categories: {len(evidence_summary.get('evidence_categories_collected', []))}")
            
        except Exception as e:
            self.logger.warning(f"Validation/evidence collection failed: {e}")
            # Don't fail the main process for validation errors


def create_argument_parser() -> argparse.ArgumentParser:
    """Create command line argument parser with comprehensive options
    
    Returns:
        Configured ArgumentParser instance
    """
    parser = argparse.ArgumentParser(
        description="JP Automation Professional v2.0 - Enterprise Legal Question Processing",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python jp_automation_main.py --input input/questions.csv --output output/jp_answers.csv
  python jp_automation_main.py --input input/questions.csv --output output/jp_answers.csv --headed
  python jp_automation_main.py --input input/questions.csv --output output/jp_answers.csv --connect ws://localhost:9222 --limit 5
  python jp_automation_main.py --input input/questions.csv --output output/jp_answers.csv --persistent --timestamp-output

Professional Features:
  - Comprehensive error handling with context-rich messages
  - Automated acceptance criteria validation
  - Evidence collection for compliance reporting
  - Professional file management with timestamped outputs
  - Session-based logging and audit trails
        """
    )
    
    # Input/Output options
    parser.add_argument(
        '--input', '-i', 
        required=True, 
        help='Input CSV file with questions (must contain question_id and question columns)'
    )
    parser.add_argument(
        '--output', '-o', 
        help='Output CSV file path (default: timestamped file in output/ directory)'
    )
    parser.add_argument(
        '--timestamp-output', 
        action='store_true', 
        help='Add timestamp to output filename'
    )
    
    # Browser options
    parser.add_argument(
        '--headed', 
        action='store_true', 
        help='Run browser with UI (default: headless mode)'
    )
    parser.add_argument(
        '--persistent', 
        action='store_true', 
        help='Use persistent browser context to maintain login state'
    )
    parser.add_argument(
        '--connect-url', 
        help='Connect to existing browser via CDP (e.g., ws://localhost:9222)'
    )
    
    # Processing options
    parser.add_argument(
        '--limit', 
        type=int, 
        help='Limit number of questions to process (for testing)'
    )
    parser.add_argument(
        '--skip-validation', 
        action='store_true', 
        help='Skip acceptance criteria validation and evidence collection'
    )
    
    return parser


async def main():
    """Main entry point for JP automation system"""
    parser = create_argument_parser()
    args = parser.parse_args()
    
    try:
        # Initialize and run main application
        app = JPAutomationMain(args)
        exit_code = await app.run()
        sys.exit(exit_code)
        
    except KeyboardInterrupt:
        print("\\n[INFO] Interrupted by user - shutting down gracefully...")
        sys.exit(1)
    except Exception as e:
        print(f"[ERROR] Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())