#!/usr/bin/env python3
"""
JP Automation Fixed - Chat Input Detection
==========================================

Fixed version that correctly identifies and interacts with JP's contenteditable chat input.

Key findings from deep debug:
- Chat input is: div#chat-input[contenteditable="plaintext-only"]
- Submit button is: button#chat-submit[aria-label="Submit"]
- Interface uses Fluent UI components, not standard HTML inputs

Usage:
    python jp_automation_fixed.py --input ../input/questions.csv --output ../output/jp_answers.csv --limit 1 --headed
"""

import asyncio
import json
import time
import argparse
import csv
import hashlib
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from playwright.async_api import async_playwright, Browser, BrowserContext, Page

# ASCII-only logging (no Unicode/emojis per coding standards)
def log_info(msg: str) -> None:
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] [INFO] {msg}")

def log_success(msg: str) -> None:
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] [SUCCESS] {msg}")

def log_warning(msg: str) -> None:
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] [WARNING] {msg}")

def log_error(msg: str) -> None:
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] [ERROR] {msg}")

class JPAutomationFixed:
    def __init__(self, input_file: Path, output_file: Path, limit: Optional[int] = None, headed: bool = False):
        self.input_file = input_file
        self.output_file = output_file
        self.limit = limit
        self.headed = headed
        self.results = []
        
        # Progressive timeout constants - 15s, 30s, 45s, 60s = 2:30 total
        self.TIMEOUT_PHASES = [15, 30, 45, 60]  
        self.MAX_RETRIES = 3  # Three strikes rule
        
        # Setup directories
        self.debug_dir = Path("../debug")
        self.debug_dir.mkdir(exist_ok=True)
        
        # Session info
        self.session_id = datetime.now().strftime("jp_session_%Y%m%d_%H%M%S")
        log_info(f"Starting JP Automation Fixed - Session {self.session_id}")

    async def connect_to_edge_debug(self) -> Optional[Browser]:
        """Connect to Edge debug instance on port 9222"""
        try:
            playwright_instance = await async_playwright().start()
            log_info("Connecting to Edge debug instance on port 9222...")
            browser = await playwright_instance.chromium.connect_over_cdp("http://127.0.0.1:9222")
            log_success("Connected to Edge debug instance")
            return browser
        except Exception as e:
            log_error(f"Failed to connect to Edge debug: {e}")
            log_info("Make sure Edge is running with debug port:")
            log_info('& "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe" --remote-debugging-port=9222 --user-data-dir="$env:TEMP\\jp-edge-debug" "https://ei-jp-ui.purplesky-a9615d9b.canadacentral.azurecontainerapps.io"')
            return None

    async def find_jp_page(self, browser: Browser) -> Optional[Page]:
        """Find JP page in browser contexts"""
        try:
            contexts = browser.contexts
            log_info(f"Searching {len(contexts)} browser contexts for JP page...")
            
            for context in contexts:
                pages = context.pages
                for page in pages:
                    url = page.url
                    if "ei-jp-ui.purplesky" in url:
                        title = await page.title()
                        log_success(f"Found JP page: {title}")
                        return page
            
            log_error("JP page not found in any browser context")
            return None
        except Exception as e:
            log_error(f"Error finding JP page: {e}")
            return None

    async def submit_question_to_jp(self, page: Page, question: str, question_id: str) -> bool:
        """Submit question to JP chat interface using correct selectors"""
        try:
            # Wait for page to be ready
            await page.wait_for_load_state('domcontentloaded', timeout=10000)
            
            log_info(f"{question_id}: Looking for JP chat interface elements...")
            
            # Wait for chat interface to be ready - give it time to fully load
            await asyncio.sleep(3)
            
            # Strategy 1: Find the contenteditable chat input (confirmed from debug)
            chat_input_selector = '#chat-input[contenteditable="plaintext-only"]'
            submit_button_selector = '#chat-submit[aria-label="Submit"]'
            
            try:
                # Check for chat input
                chat_input = page.locator(chat_input_selector)
                submit_button = page.locator(submit_button_selector)
                
                # Wait up to 15 seconds for elements to be available and visible
                log_info(f"{question_id}: Waiting for chat input element...")
                await chat_input.wait_for(state='visible', timeout=15000)
                
                log_info(f"{question_id}: Waiting for submit button...")
                await submit_button.wait_for(state='visible', timeout=5000)
                
                log_success(f"{question_id}: Found JP chat interface elements")
                
                # Clear any existing content and add the question
                log_info(f"{question_id}: Submitting question: {question[:50]}...")
                
                # Click on the input to focus it
                await chat_input.click()
                await asyncio.sleep(0.5)
                
                # Clear existing content using JavaScript
                await page.evaluate('''
                    const chatInput = document.querySelector('#chat-input');
                    if (chatInput) {
                        chatInput.textContent = '';
                        chatInput.innerHTML = '';
                    }
                ''')
                await asyncio.sleep(0.5)
                
                # Type the question
                await chat_input.fill(question)
                await asyncio.sleep(1)
                
                # Verify the content was entered
                entered_text = await chat_input.text_content()
                if question not in entered_text:
                    log_warning(f"{question_id}: Question text may not have been entered correctly")
                    log_info(f"{question_id}: Expected: {question[:30]}...")
                    log_info(f"{question_id}: Got: {entered_text[:30]}...")
                
                # Submit via button click
                log_info(f"{question_id}: Clicking submit button...")
                await submit_button.click()
                
                log_success(f"{question_id}: Question submitted successfully")
                await asyncio.sleep(3)  # Wait for submission to process
                return True
                
            except Exception as e:
                log_error(f"{question_id}: Failed to interact with chat interface: {e}")
                
                # Take debug screenshot
                timestamp_str = datetime.now().strftime("%H%M%S")
                debug_path = self.debug_dir / f"jp_{question_id}_submit_failed_{timestamp_str}.png"
                try:
                    await page.screenshot(path=str(debug_path))
                    log_info(f"{question_id}: Debug screenshot saved: {debug_path}")
                except:
                    pass
                
                return False
                
        except Exception as e:
            log_error(f"{question_id}: Question submission failed: {e}")
            return False

    async def wait_for_jp_completion_progressive(self, page: Page, question_id: str, question_text: str) -> str:
        """
        Progressive timeout implementation: 15s, 30s, 45s, 60s phases
        Total: 2 minutes 30 seconds maximum
        Detects completion by looking for case details and stable content
        """
        log_info(f"{question_id}: Starting progressive timeout (15s, 30s, 45s, 60s = 2:30 total)")
        start_time = time.time()
        
        last_content = ""
        stable_count = 0
        required_stable_checks = 3
        
        for phase_idx, phase_timeout in enumerate(self.TIMEOUT_PHASES):
            phase_start = time.time()
            phase_name = ["Initial", "Extended", "Deep", "Final"][phase_idx]
            
            log_info(f"{question_id}: Phase {phase_idx+1} ({phase_name}) - waiting up to {phase_timeout}s")
            
            while time.time() - phase_start < phase_timeout:
                try:
                    # Get current response content
                    current_content = await self.get_response_content(page)
                    
                    # Check for completion indicators
                    completion_indicators = [
                        "Case Details",
                        "Federal Court of Appeals",
                        "Federal Court",
                        "Social Security Tribunal", 
                        "Supreme Court",
                        "Decision:",
                        "Summary:",
                        "No relevant documents found"
                    ]
                    
                    has_completion_indicator = any(indicator in current_content for indicator in completion_indicators)
                    is_substantial = len(current_content) > 200
                    
                    # Check if content is stable (not changing between checks)
                    if current_content == last_content and has_completion_indicator and is_substantial:
                        stable_count += 1
                        log_info(f"{question_id}: Content stable ({stable_count}/{required_stable_checks})")
                        
                        if stable_count >= required_stable_checks:
                            elapsed = time.time() - start_time
                            log_success(f"{question_id}: JP response complete after {elapsed:.1f}s")
                            log_info(f"{question_id}: Final content length: {len(current_content)} chars")
                            return current_content
                    else:
                        if has_completion_indicator:
                            log_info(f"{question_id}: Found completion indicator, checking stability...")
                        stable_count = 0
                    
                    last_content = current_content
                    
                    # Wait before next check
                    await asyncio.sleep(5)
                    
                except Exception as e:
                    log_warning(f"{question_id}: Error during response check: {e}")
                    await asyncio.sleep(5)
            
            elapsed = time.time() - start_time
            log_info(f"{question_id}: Phase {phase_idx+1} complete ({elapsed:.1f}s total)")
        
        # Final timeout - return whatever we have
        final_content = await self.get_response_content(page)
        total_elapsed = time.time() - start_time
        
        if len(final_content) > 100:
            log_warning(f"{question_id}: Timeout reached ({total_elapsed:.1f}s) but got {len(final_content)} chars")
        else:
            log_error(f"{question_id}: Timeout reached ({total_elapsed:.1f}s) with minimal content")
        
        return final_content

    async def get_response_content(self, page: Page) -> str:
        """Extract current JP response content"""
        try:
            # Wait for any content to load
            await page.wait_for_load_state('domcontentloaded', timeout=5000)
            
            # Get the full page text content
            body_text = await page.locator('body').inner_text()
            
            # Look for JP response patterns - focus on meaningful content
            text_lines = body_text.split('\n')
            response_lines = []
            in_response = False
            
            for line in text_lines:
                line = line.strip()
                if not line:
                    continue
                
                # Start collecting when we see case details or legal content
                if any(marker in line for marker in ["Case Details", "Federal Court", "Social Security Tribunal", "Decision:", "Summary:", "Supreme Court"]):
                    in_response = True
                
                if in_response:
                    response_lines.append(line)
                
                # Skip navigation and footer content
                if any(skip in line.lower() for skip in ["type your message", "disclaimer", "provide feedback", "job aid", "toggle theme"]):
                    continue
            
            response_text = '\n'.join(response_lines).strip()
            
            # If we got a good response, return it
            if len(response_text) > 100:
                return response_text
            
            # Fallback: Look for any substantial content that's not navigation
            meaningful_lines = []
            for line in text_lines:
                line = line.strip()
                if (len(line) > 20 and 
                    not any(skip in line.lower() for skip in ["toggle", "button", "menu", "navigation", "header", "footer"]) and
                    not line.startswith("[")):
                    meaningful_lines.append(line)
            
            if meaningful_lines:
                return '\n'.join(meaningful_lines[:20])  # First 20 meaningful lines
            
            # Final fallback
            return body_text.strip()[:1000] if body_text else "[No content found]"
                
        except Exception as e:
            return f"[ERROR] Content extraction failed: {e}"

    async def process_question(self, question: str, question_num: int) -> Dict[str, Any]:
        """Process a single question with three-strike retry"""
        question_id = f"q{question_num:03d}"
        
        for attempt in range(1, self.MAX_RETRIES + 1):
            log_info(f"{question_id}: Attempt {attempt}/{self.MAX_RETRIES}")
            
            browser = None
            try:
                # Connect to Edge debug instance
                browser = await self.connect_to_edge_debug()
                if not browser:
                    log_error(f"{question_id}: Could not connect to browser on attempt {attempt}")
                    if attempt == self.MAX_RETRIES:
                        return {
                            "question_id": question_id,
                            "question": question,
                            "answer": "[ERROR] Could not connect to browser after 3 attempts",
                            "processing_time": 0,
                            "success": False
                        }
                    continue
                
                # Find JP page
                jp_page = await self.find_jp_page(browser)
                if not jp_page:
                    log_error(f"{question_id}: Could not find JP page on attempt {attempt}")
                    await browser.close()
                    if attempt == self.MAX_RETRIES:
                        return {
                            "question_id": question_id,
                            "question": question,
                            "answer": "[ERROR] Could not find JP page after 3 attempts",
                            "processing_time": 0,
                            "success": False
                        }
                    continue
                
                # Submit question
                start_time = time.time()
                submitted = await self.submit_question_to_jp(jp_page, question, question_id)
                if not submitted:
                    log_error(f"{question_id}: Question submission failed on attempt {attempt}")
                    await browser.close()
                    if attempt == self.MAX_RETRIES:
                        return {
                            "question_id": question_id,
                            "question": question,
                            "answer": "[ERROR] Question submission failed after 3 attempts",
                            "processing_time": 0,
                            "success": False
                        }
                    continue
                
                # Wait for response with progressive timeout
                response = await self.wait_for_jp_completion_progressive(jp_page, question_id, question)
                processing_time = time.time() - start_time
                
                await browser.close()
                
                # Validate response
                if response and len(response) > 50 and "[ERROR]" not in response:
                    log_success(f"{question_id}: Successfully processed in {processing_time:.1f}s")
                    return {
                        "question_id": question_id,
                        "question": question,
                        "answer": response,
                        "processing_time": processing_time,
                        "success": True,
                        "attempts": attempt
                    }
                else:
                    log_warning(f"{question_id}: Poor response quality on attempt {attempt}")
                    if attempt == self.MAX_RETRIES:
                        return {
                            "question_id": question_id,
                            "question": question,
                            "answer": response or "[ERROR] No response received",
                            "processing_time": processing_time,
                            "success": False,
                            "attempts": attempt
                        }
                
            except Exception as e:
                log_error(f"{question_id}: Attempt {attempt} failed with error: {e}")
                if browser:
                    try:
                        await browser.close()
                    except:
                        pass
                
                if attempt == self.MAX_RETRIES:
                    return {
                        "question_id": question_id,
                        "question": question,
                        "answer": f"[ERROR] Processing failed: {e}",
                        "processing_time": 0,
                        "success": False,
                        "attempts": attempt
                    }
        
        # Should not reach here
        return {
            "question_id": question_id,
            "question": question,
            "answer": "[ERROR] Unexpected processing failure",
            "processing_time": 0,
            "success": False
        }

    async def run(self):
        """Main processing loop"""
        log_info(f"Loading questions from: {self.input_file}")
        
        # Load questions
        questions = []
        try:
            with open(self.input_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if 'question' in row and row['question'].strip():
                        questions.append(row['question'].strip())
        except Exception as e:
            log_error(f"Failed to load questions: {e}")
            return
        
        if not questions:
            log_error("No questions found in input file")
            return
        
        # Apply limit
        if self.limit:
            questions = questions[:self.limit]
            log_info(f"Processing first {len(questions)} questions (limit applied)")
        else:
            log_info(f"Processing {len(questions)} questions")
        
        # Process each question
        results = []
        for i, question in enumerate(questions, 1):
            log_info(f"\n{'='*60}")
            log_info(f"QUESTION {i}/{len(questions)}")
            log_info(f"{'='*60}")
            
            result = await self.process_question(question, i)
            results.append(result)
            
            # Show progress
            success_count = sum(1 for r in results if r.get('success', False))
            log_info(f"Progress: {i}/{len(questions)} processed, {success_count} successful")
        
        # Save results
        await self.save_results(results)
        
        # Final summary
        log_info(f"\n{'='*60}")
        log_info("FINAL SUMMARY")
        log_info(f"{'='*60}")
        
        successful = [r for r in results if r.get('success', False)]
        failed = [r for r in results if not r.get('success', False)]
        
        log_info(f"Total processed: {len(results)}")
        log_success(f"Successful: {len(successful)}")
        log_error(f"Failed: {len(failed)}")
        
        if successful:
            avg_time = sum(r.get('processing_time', 0) for r in successful) / len(successful)
            log_info(f"Average processing time: {avg_time:.1f}s")
        
        log_info(f"Results saved to: {self.output_file}")

    async def save_results(self, results: List[Dict[str, Any]]):
        """Save results to CSV and JSON"""
        # Save CSV
        try:
            with open(self.output_file, 'w', newline='', encoding='utf-8') as f:
                fieldnames = ['question_id', 'question', 'answer', 'processing_time', 'success', 'attempts']
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                for result in results:
                    writer.writerow({k: result.get(k, '') for k in fieldnames})
            log_success(f"CSV results saved: {self.output_file}")
        except Exception as e:
            log_error(f"Failed to save CSV: {e}")
        
        # Save JSON
        json_file = self.output_file.with_suffix('.json')
        try:
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'session_id': self.session_id,
                    'timestamp': datetime.now().isoformat(),
                    'results': results
                }, f, indent=2, ensure_ascii=False)
            log_success(f"JSON results saved: {json_file}")
        except Exception as e:
            log_error(f"Failed to save JSON: {e}")

async def main():
    parser = argparse.ArgumentParser(description='JP Automation with Fixed Chat Input Detection')
    parser.add_argument('--input', type=Path, required=True, help='Input CSV file with questions')
    parser.add_argument('--output', type=Path, required=True, help='Output CSV file for results')
    parser.add_argument('--limit', type=int, help='Limit number of questions to process')
    parser.add_argument('--headed', action='store_true', help='Run in headed mode (for debugging)')
    
    args = parser.parse_args()
    
    # Validate files
    if not args.input.exists():
        log_error(f"Input file not found: {args.input}")
        return
    
    # Create output directory
    args.output.parent.mkdir(parents=True, exist_ok=True)
    
    # Run automation
    automation = JPAutomationFixed(args.input, args.output, args.limit, args.headed)
    await automation.run()

if __name__ == "__main__":
    asyncio.run(main())