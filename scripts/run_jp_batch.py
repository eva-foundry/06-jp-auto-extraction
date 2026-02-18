#!/usr/bin/env python3
"""
JP Automated Extraction - Batch Query Script

Automates the extraction of jurisprudence answers and citations from the JP UI
by programmatically submitting questions via browser automation (Playwright).

Usage:
    python run_jp_batch.py --in input/questions.csv --out output/jp_answers.csv
"""

# Environment Notes:
# - Requires: playwright + pandas
# - Requires: Playwright browser install step (e.g., `playwright install chromium`)
# - Recommended: Run in an ESDC DevBox (or equivalent) due to workstation pip/SSL constraints

import argparse
import csv
import json
import logging
import re
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Tuple

from playwright.sync_api import sync_playwright, Page, TimeoutError as PlaywrightTimeout, Locator


# Custom exception classes for proper error handling
class StabilizationTimeoutError(Exception):
    """Raised when text stabilization times out"""
    pass


class InputValidationError(Exception):
    """Raised when input CSV validation fails"""
    pass


# Configure logging and project paths
BASE_DIR = Path(__file__).parent.parent
LOG_DIR = BASE_DIR / "logs"
DEBUG_DIR = BASE_DIR / "debug"
DEBUG_SCREENSHOTS_DIR = DEBUG_DIR / "screenshots"
DEBUG_HTML_DIR = DEBUG_DIR / "html"

LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / "run.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


# Constants
JP_UI_URL = "https://ei-jp-ui.purplesky-a9615d9b.canadacentral.azurecontainerapps.io/"
CHAT_INPUT_PLACEHOLDER_VARIANTS = [
    "Type your message here…",  # Unicode ellipsis
    "Type your message here...", # ASCII dots
    "Type your message here",    # No ellipsis
    "Type a message"
]
SEND_BUTTON_SELECTOR = 'button[aria-label="Send message"], button:has-text("Send")'
CHAT_CONTAINER_SELECTOR = '.chat-messages, [role="log"], .message-list'
ASSISTANT_MESSAGE_SELECTOR = '.assistant-message, .bot-message, [data-role="assistant"]'

# Stabilization parameters
POLL_INTERVAL_MS = 200
STABLE_DURATION_MS = 800
MAX_WAIT_SECONDS = 120

# Throttle between questions
THROTTLE_SECONDS = 2


def wait_for_stabilized_text(locator: Locator, timeout_seconds: int = MAX_WAIT_SECONDS) -> str:
    """
    Wait for text content to stabilize (no changes for STABLE_DURATION_MS).
    Returns the stabilized text content.
    
    Raises StabilizationTimeoutError if stabilization doesn't occur within timeout_seconds.
    """
    logger.debug(f"Waiting for text stabilization in locator")
    start_time = time.time()
    last_text = ""
    last_change_time = start_time
    stable_count = 0
    required_stable_polls = int(STABLE_DURATION_MS / POLL_INTERVAL_MS)
    
    while (time.time() - start_time) < timeout_seconds:
        try:
            current_text = locator.inner_text()
            
            if current_text == last_text:
                stable_count += 1
                if stable_count >= required_stable_polls:
                    logger.debug(f"Text stabilized after {time.time() - start_time:.1f}s")
                    return current_text
            else:
                stable_count = 0
                last_text = current_text
                last_change_time = time.time()
            
            time.sleep(POLL_INTERVAL_MS / 1000)
            
        except Exception as e:
            logger.debug(f"Element not ready: {e}")
            time.sleep(POLL_INTERVAL_MS / 1000)
            continue
    
    raise StabilizationTimeoutError(f"Text did not stabilize within {timeout_seconds} seconds")


def validate_input_csv(csv_path: Path) -> List[str]:
    """
    Validate input CSV structure and content.
    Returns list of validation errors (empty if valid).
    """
    errors = []
    
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            # Check required columns exist
            required_columns = ['question_id', 'question']
            missing_columns = [col for col in required_columns if col not in reader.fieldnames]
            if missing_columns:
                errors.append(f"Missing required columns: {', '.join(missing_columns)}")
                return errors  # Can't continue validation without required columns
            
            rows = list(reader)
            
            # Check for duplicate question_ids
            question_ids = [row['question_id'] for row in rows]
            duplicates = [qid for qid in set(question_ids) if question_ids.count(qid) > 1]
            if duplicates:
                errors.append(f"Duplicate question_ids found: {', '.join(duplicates)}")
            
            # Check for empty or invalid questions
            for i, row in enumerate(rows, 2):  # Start at 2 for header row
                qid = row['question_id'].strip()
                question = row['question'].strip()
                
                if not qid:
                    errors.append(f"Row {i}: Empty question_id")
                
                if not question:
                    errors.append(f"Row {i}: Empty question")
                elif len(question) > 1000:  # Reasonable length limit
                    errors.append(f"Row {i}: Question too long ({len(question)} chars, max 1000)")
                
            if not rows:
                errors.append("CSV file contains no data rows")
                
    except UnicodeDecodeError:
        errors.append("File encoding error - ensure CSV is UTF-8 encoded")
    except FileNotFoundError:
        errors.append(f"Input file not found: {csv_path}")
    except Exception as e:
        errors.append(f"Error reading CSV file: {str(e)}")
    
    return errors


def find_chat_input_element(page: Page) -> Locator:
    """
    Find chat input element - JP uses React/Chainlit interface with various input patterns.
    Returns the first matching locator.
    """
    # JP React/Chainlit interface selectors - prioritize most specific first
    primary_selectors = [
        'div[contenteditable="plaintext-only"]',
        'div[contenteditable="true"]',
        'textarea[placeholder*="Type"]',
        'input[type="text"][placeholder*="Type"]',
        'textarea[placeholder*="message"]',
        'div[role="textbox"]',
        'div[contenteditable]'
    ]
    
    for selector in primary_selectors:
        try:
            element = page.locator(selector).first
            if element.is_visible(timeout=1000):
                logger.debug(f"Found chat input with selector: {selector}")
                return element
        except:
            continue
    
    # Legacy fallback selectors for non-JP interfaces
    fallback_selectors = [
        'input[type="text"][class*="chat"]',
        'textarea[class*="chat"]', 
        'input[aria-label*="message"]',
        'textarea[aria-label*="message"]'
    ]
    
    for selector in fallback_selectors:
        try:
            element = page.locator(selector).first
            if element.is_visible(timeout=1000):
                logger.debug(f"Found input with fallback selector: {selector}")
                return element
        except:
            continue
    
    raise Exception("Could not locate chat input element with any selector")


def find_assistant_message_element(page: Page) -> Locator:
    """
    Find the latest assistant message element with fallback selectors.
    Returns the locator object for consistent usage.
    """
    assistant_selectors = [
        # Chainlit-specific response patterns (most likely)
        'div.cl-step',
        'div[data-testid="cl-step"]',
        '.cl-step-content',
        'div.step',
        'div[data-cy="step"]',
        'div[data-cy="message"]',
        '.cl-message-content',
        '.cl-message:not(.cl-user-message)',
        # Standard response patterns  
        'main div[class*="response"]',
        'main div[class*="message"]:not([data-author="user"])',
        '.message-content',
        '.step-content',
        'div[class*="answer"]',
        'div[class*="Message"]:not([data-author="user"])',
        # Broader content selectors
        'main div',
        '[role="main"] div',
        'div[class*="chat"] div',
        # Legacy selectors
        ASSISTANT_MESSAGE_SELECTOR,
        '.message.assistant',
        '[data-message-type="assistant"]',
        '[data-role="assistant"]',
        '.bot-message',
        '.assistant-response', 
    ]
    
    for selector in assistant_selectors:
        try:
            elements = page.locator(selector).all()
            logger.debug(f"Selector '{selector}' found {len(elements)} elements")
            
            # Process elements in reverse order (newest first)
            for i, element in enumerate(reversed(elements)):
                try:
                    # Skip invisible elements
                    if not element.is_visible():
                        continue
                    
                    # Get element attributes to check if it's an input
                    tag_name = element.evaluate('el => el.tagName.toLowerCase()')
                    is_contenteditable = element.evaluate('el => el.contentEditable === "true" || el.contentEditable === "plaintext-only"')
                    has_placeholder = element.evaluate('el => el.hasAttribute("data-placeholder")')
                    
                    # Skip input-type elements
                    if tag_name in ['input', 'textarea'] or is_contenteditable or has_placeholder:
                        continue
                    
                    text_content = element.inner_text().strip()
                    
                    # Skip empty or very short content
                    if len(text_content) < 10:
                        continue
                    
                    # Skip obvious user interface elements
                    if any(ui_text in text_content for ui_text in [
                        "Type your message", "Send message", "Clear chat", "New chat",
                        "Previous 7 days", "Create New Chat", "Search conversations"
                    ]):
                        continue
                    
                    # Skip disclaimer text explicitly
                    if any(disclaimer_text in text_content for disclaimer_text in [
                        "Disclaimer: This AI chatbot provides general information",
                        "should not be considered a substitute for professional advice",
                        "By using this AI chatbot, you agree to these terms"
                    ]):
                        continue
                    
                    # Skip if content matches user's question exactly
                    if ("What is the difference between EI regular benefits" in text_content and 
                        text_content.endswith("?")):
                        continue
                    
                    # Look for JP-specific response indicators first (highest priority)
                    jp_indicators = [
                        "[THINKING]", "Search Agent", "Document analysis", "Summary Agent",
                        "Decision:", "Link:", "2024 FC", "2021 SST", "Employment Insurance",
                        "Federal Court", "Social Security Tribunal", "analyzing", "found",
                        "Task manually stopped", "No relevant documents found"
                    ]
                    
                    if any(indicator in text_content for indicator in jp_indicators):
                        logger.debug(f"Found JP response with indicator, selector: {selector} (element {i}), text: {text_content[:100]}...")
                        return element
                        
                    # For longer content, be more selective - must contain legal/case indicators
                    if (len(text_content) > 200 and 
                        not text_content.endswith("?") and
                        "Find cases related" not in text_content and
                        any(legal_term in text_content.lower() for legal_term in [
                            "court", "tribunal", "decision", "case", "benefit", "regulation", 
                            "employment", "insurance", "appeal", "section"
                        ])):
                        logger.debug(f"Found legal content, selector: {selector} (element {i}), text: {text_content[:100]}...")
                        return element
                        
                except Exception as e:
                    logger.debug(f"Error processing element {i} with selector {selector}: {e}")
                    continue
                    
        except Exception as e:
            logger.debug(f"Selector {selector} failed: {e}")
            continue
    
    # If we couldn't find anything, let's debug the page structure
    logger.debug("Could not find assistant message with any selector. Analyzing page structure...")
    try:
        # Get page text to see what's available
        all_text = page.locator('body').inner_text()[:2000]
        logger.debug(f"Page text sample: {all_text}")
        
        # Look for specific patterns that might indicate responses
        thinking_elements = page.locator('text*="Thinking"').count()
        agent_elements = page.locator('text*="Agent"').count()
        document_elements = page.locator('text*="Document analysis"').count()
        
        logger.debug(f"Debug counts - Thinking: {thinking_elements}, Agent: {agent_elements}, Document: {document_elements}")
        
    except Exception as e:
        logger.debug(f"Debug analysis failed: {e}")
    
    raise Exception("Could not locate assistant message element with any selector")


def extract_citations(text: str) -> List[str]:
    """
    Extract citations from assistant response text.
    
    Captures:
    - Lines containing "Link:"
    - Filenames ending in .pdf
    - Neutral citations like "2023 SST 2068"
    
    Returns deduplicated list preserving order.
    """
    citations = []
    lines = text.split('\n')
    
    # Pattern for neutral citations (e.g., "2023 SST 2068")
    neutral_citation_pattern = r'\b\d{4}\s+SST\s+\d+\b'
    
    for line in lines:
        line = line.strip()
        
        # Capture "Link:" lines
        if "Link:" in line:
            citations.append(line)
            continue
        
        # Capture .pdf filenames
        if '.pdf' in line.lower():
            # Extract just the filename
            pdf_match = re.search(r'[\w\-]+\.pdf', line, re.IGNORECASE)
            if pdf_match:
                citations.append(pdf_match.group())
        
        # Capture neutral citations
        neutral_matches = re.finditer(neutral_citation_pattern, line)
        for match in neutral_matches:
            citations.append(match.group())
    
    # Deduplicate while preserving order
    seen = set()
    deduplicated = []
    for citation in citations:
        if citation not in seen:
            seen.add(citation)
            deduplicated.append(citation)
    
    logger.debug(f"Extracted {len(deduplicated)} unique citations")
    return deduplicated


def save_debug_artifacts(page: Page, question_id: str, error: str):
    """Save screenshot and HTML snapshot for debugging failed queries."""
    DEBUG_SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    DEBUG_HTML_DIR.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Save screenshot
    screenshot_path = DEBUG_SCREENSHOTS_DIR / f"{question_id}_{timestamp}.png"
    try:
        page.screenshot(path=str(screenshot_path), full_page=True)
        logger.info(f"Screenshot saved: {screenshot_path}")
    except Exception as e:
        logger.error(f"Failed to save screenshot: {e}")
    
    # Save HTML
    html_path = DEBUG_HTML_DIR / f"{question_id}_{timestamp}.html"
    try:
        html_content = page.content()
        html_path.write_text(html_content, encoding='utf-8')
        logger.info(f"HTML saved: {html_path}")
    except Exception as e:
        logger.error(f"Failed to save HTML: {e}")


def process_question(page: Page, question_id: str, question: str) -> Tuple[str, List[str], str, str]:
    """
    Submit a question to the JP UI and extract the answer and citations.
    
    Returns: (answer_text, citations_list, status, error_message)
    """
    logger.info(f"Processing {question_id}: {question[:60]}...")
    
    try:
        # Find and clear the input field using robust selector
        input_element = find_chat_input_element(page)
        
        # Clear any existing text and type the question
        # Handle both contenteditable and standard inputs
        input_element.click()
        
        # Try contenteditable clearing first, then fallback to standard input
        try:
            # For contenteditable elements
            page.keyboard.press("Control+a")  # Select all
            page.keyboard.press("Delete")     # Delete selected content
            time.sleep(0.3)                   # Brief pause for UI to update
        except:
            # For standard input elements
            try:
                input_element.clear()
            except:
                pass  # Continue if clearing fails
        
        # Type the question with shorter delay for better responsiveness
        input_element.type(question, delay=30)
        
        logger.debug(f"Typed question: {question}")
        
        # Click send button - React/Chainlit interface patterns
        send_button_selectors = [
            'button[aria-label="Send message"]',
            'button[type="submit"]',
            'button:has-text("Send")',
            'button[class*="send"]',
            'button svg[class*="send"]',
            'button:has(svg)',
            'button[id*="send"]',
            'button[data-testid*="send"]'
        ]
        
        send_button = None
        for selector in send_button_selectors:
            try:
                send_button = page.locator(selector).first
                if send_button.is_visible(timeout=1000):
                    logger.debug(f"Found send button with selector: {selector}")
                    break
            except:
                continue
        
        if not send_button:
            raise Exception("Could not find send button")
            
        send_button.click()
        logger.debug("Send button clicked")
        
        # Wait for response to appear and stabilize using progressive timeout system
        # JP's multi-agent system can take 30s-2min for complex queries
        timeout_phases = [15, 30, 45, 60]  # Progressive timeout: 15s+30s+45s+60s = 2:30 total
        
        for phase_timeout in timeout_phases:
            logger.debug(f"Starting {phase_timeout}s timeout phase")
            
            # Initial wait for response to start
            time.sleep(2)
            
            # Wait for "Thinking..." or agent status to disappear or change
            try:
                thinking_selectors = [
                    'text="[THINKING] Thinking..."',
                    'text*="Search Agent"',
                    'text*="Document analysis"',
                    'text*="Summary Agent"',
                    '[class*="thinking"]',
                    '[class*="agent-status"]',
                    '.loading-indicator'
                ]
                
                for selector in thinking_selectors:
                    try:
                        page.wait_for_selector(selector, state="hidden", timeout=5000)
                        logger.debug(f"'{selector}' indicator hidden")
                    except:
                        pass  # Selector might not exist
                
                # Find the latest assistant message using robust selector
                answer_element = find_assistant_message_element(page)
                
                # Wait for text to stabilize within this phase
                answer_text = wait_for_stabilized_text(answer_element, timeout_seconds=phase_timeout)
                
                # Check if we got a substantial response
                if len(answer_text) > 50 and not any(indicator in answer_text for indicator in ["⏳ Thinking", "Task manually stopped"]):
                    logger.debug(f"Got substantial response in {phase_timeout}s phase")
                    break
                    
            except StabilizationTimeoutError:
                logger.debug(f"Phase {phase_timeout}s timed out, trying next phase")
                continue
        else:
            # All phases exhausted
            raise StabilizationTimeoutError("All progressive timeout phases exhausted")
        
        # Extract citations
        citations = extract_citations(answer_text)
        
        logger.info(f"[SUCCESS] {question_id} completed successfully ({len(citations)} citations)")
        return answer_text, citations, "success", ""
        
    except StabilizationTimeoutError as e:
        error_msg = f"Response stabilization timeout: {str(e)}"
        logger.error(f"[FAIL] {question_id} failed: {error_msg}")
        save_debug_artifacts(page, question_id, error_msg)
        return "", [], "timeout", error_msg
        
    except PlaywrightTimeout as e:
        error_msg = f"Playwright timeout: {str(e)}"
        logger.error(f"[FAIL] {question_id} failed: {error_msg}")
        save_debug_artifacts(page, question_id, error_msg)
        return "", [], "timeout", error_msg
        
    except Exception as e:
        error_msg = f"Error processing question: {str(e)}"
        logger.error(f"[FAIL] {question_id} failed: {error_msg}")
        save_debug_artifacts(page, question_id, error_msg)
        return "", [], "error", error_msg


def run_batch(input_csv: Path, output_csv: Path, headless: bool = True):
    """
    Main batch processing function.
    Reads questions from input CSV and writes results to output CSV.
    """
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    DEBUG_SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    DEBUG_HTML_DIR.mkdir(parents=True, exist_ok=True)
    output_csv.parent.mkdir(parents=True, exist_ok=True)

    # Add timestamp to output filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    stem = output_csv.stem
    suffix = output_csv.suffix
    timestamped_output = output_csv.parent / f"{stem}_{timestamp}{suffix}"

    logger.info("Starting JP batch extraction")
    logger.info(f"JP UI: {JP_UI_URL} | headless={headless} | input={input_csv} | output={timestamped_output}")
    
    # Validate input CSV
    logger.info("Validating input CSV...")
    validation_errors = validate_input_csv(input_csv)
    if validation_errors:
        error_msg = "Input validation failed:\\n" + "\\n".join(validation_errors)
        logger.error(error_msg)
        raise InputValidationError(error_msg)
    logger.info("[PASS] Input validation passed")
    
    # Read input questions
    questions = []
    with open(input_csv, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        questions = list(reader)
    
    logger.info(f"Loaded {len(questions)} questions")
    
    # Initialize output CSV (use timestamped filename)
    output_file = open(timestamped_output, 'w', newline='', encoding='utf-8')
    fieldnames = ['question_id', 'question', 'answer_text', 'citations', 'timestamp', 'status', 'error']
    writer = csv.DictWriter(output_file, fieldnames=fieldnames)
    writer.writeheader()
    
    # Launch browser using Edge debug connection for authenticated session
    with sync_playwright() as p:
        try:
            # Try to connect to Edge debug port (requires Edge running with --remote-debugging-port=9222)
            browser = p.chromium.connect_over_cdp("http://localhost:9222")
            logger.info("Connected to Edge debug session on port 9222")
            
            # Use the default context from the connected browser
            contexts = browser.contexts
            if contexts:
                context = contexts[0]
                logger.info("Using existing Edge context")
            else:
                context = browser.new_context(
                    viewport={'width': 1920, 'height': 1080},
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                )
                logger.info("Created new context in Edge")
                
        except Exception as e:
            # Fallback to launching fresh browser
            logger.warning(f"Could not connect to Edge debug port: {e}")
            logger.info("Launching fresh browser as fallback")
            browser = p.chromium.launch(headless=headless)
            context = browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            )
        
        page = context.new_page()
        
        try:
            # Navigate to JP UI
            logger.info(f"Navigating to {JP_UI_URL}")
            page.goto(JP_UI_URL, wait_until="domcontentloaded")
            time.sleep(3)  # Allow UI to fully initialize
            
            # Process each question
            for i, row in enumerate(questions, 1):
                question_id = row['question_id']
                question = row['question']
                
                logger.info(f"[{i}/{len(questions)}] Processing {question_id}")
                
                # Process the question
                answer_text, citations, status, error = process_question(page, question_id, question)
                
                # Write result
                result = {
                    'question_id': question_id,
                    'question': question,
                    'answer_text': answer_text,
                    'citations': ' | '.join(citations),  # Join citations with separator
                    'timestamp': datetime.now().isoformat(),
                    'status': status,
                    'error': error
                }
                writer.writerow(result)
                output_file.flush()  # Ensure data is written immediately
                
                # Throttle between questions
                if i < len(questions):
                    logger.debug(f"Throttling for {THROTTLE_SECONDS}s")
                    time.sleep(THROTTLE_SECONDS)
            
            logger.info("[SUCCESS] Batch processing completed successfully")
            
        except Exception as e:
            logger.error(f"Fatal error during batch processing: {e}")
            raise
        
        finally:
            browser.close()
            output_file.close()
    
    # Summary statistics
    with open(timestamped_output, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        results = list(reader)
        
    success_count = sum(1 for r in results if r['status'] == 'success')
    error_count = len(results) - success_count
    
    logger.info(f"Summary: {success_count} succeeded, {error_count} failed out of {len(results)} total")
    
    # Also save as JSON
    json_output = timestamped_output.with_suffix('.json')
    with open(json_output, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    logger.info(f"Results also saved to: {json_output}")


def main():
    parser = argparse.ArgumentParser(
        description="JP Automated Extraction - Batch query the JP UI and extract answers and citations"
    )
    parser.add_argument(
        '--in',
        dest='input_csv',
        type=Path,
        required=True,
        help='Input CSV file with questions (question_id, question)'
    )
    parser.add_argument(
        '--out',
        dest='output_csv',
        type=Path,
        required=True,
        help='Output CSV file for results'
    )
    parser.add_argument(
        '--headed',
        action='store_true',
        help='Run in headed mode (show browser window)'
    )
    
    args = parser.parse_args()
    
    if not args.input_csv.exists():
        logger.error(f"Input file does not exist: {args.input_csv}")
        return 1
    
    try:
        run_batch(args.input_csv, args.output_csv, headless=not args.headed)
        return 0
    except Exception as e:
        logger.error(f"Batch processing failed: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
