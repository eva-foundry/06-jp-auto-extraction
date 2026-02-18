#!/usr/bin/env python3
"""
JP Automation with Progressive Timeout
=====================================

Progressive timeout: 15s, 30s, 45s, 60s = 2:30 total
Three strikes rule: Kill session and retry with fresh browser
Edge debug connection for authenticated sessions

Usage:
    python jp_automation_progressive.py --input ../input/questions.csv --output ../output/jp_answers.csv --limit 5 --headed
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

class JPAutomationProgressive:
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
        log_info(f"Starting JP Automation Progressive - Session {self.session_id}")

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

    async def get_response_content(self, page: Page) -> str:
        """Extract current JP response content"""
        try:
            # Wait for any content to load
            await page.wait_for_load_state('domcontentloaded', timeout=5000)
            
            # Get the full page text content
            body_text = await page.locator('body').inner_text()
            
            # Look for JP response patterns
            text_lines = body_text.split('\n')
            response_lines = []
            in_response = False
            
            for line in text_lines:
                line = line.strip()
                if not line:
                    continue
                
                # Start collecting when we see case details or legal content
                if any(marker in line for marker in ["Case Details", "Federal Court", "Social Security Tribunal", "Decision:", "Summary:"]):
                    in_response = True
                
                if in_response:
                    response_lines.append(line)
                
                # Skip navigation and footer content
                if any(skip in line.lower() for skip in ["type your message", "disclaimer", "provide feedback", "job aid"]):
                    continue
            
            response_text = '\n'.join(response_lines).strip()
            
            # If we got a good response, return it
            if len(response_text) > 100:
                return response_text
            
            # Fallback: return body text
            return body_text.strip()
                
        except Exception as e:
            return f"[ERROR] Content extraction failed: {e}"

    async def submit_question_to_jp(self, page: Page, question: str, question_id: str) -> bool:
        """Submit question to JP chat interface"""
        try:
            # Wait for page to be ready
            await page.wait_for_load_state('domcontentloaded', timeout=10000)
            
            # Wait for chat interface to fully load - progressive waiting
            log_info(f"{question_id}: Waiting for chat interface to load...")
            
            chat_input_found = False
            max_wait_time = 30  # seconds
            check_interval = 2   # seconds
            start_time = time.time()
            
            # Strategy 1: Look for input elements with message-related attributes
            chat_selectors = [
                'input[placeholder*="Type your message here"]',
                'textarea[placeholder*="message"]',
                'input[placeholder*="message"]',
                'input[type="text"]',
                'textarea',
                'div[contenteditable="true"]',
                '.chat-input input',
                '.ms-TextField-field'
            ]
            
            # Progressive wait for chat input to appear
            while time.time() - start_time < max_wait_time and not chat_input_found:
                for selector in chat_selectors:
                    try:
                        elements = page.locator(selector)
                        if await elements.count() > 0:
                            first_element = elements.first
                            if await first_element.is_visible():
                                log_success(f"{question_id}: Found chat input with selector: {selector}")
                                
                                # Clear any existing content and type the question
                                await first_element.fill("")
                                await asyncio.sleep(0.5)
                                await first_element.fill(question)
                                await asyncio.sleep(1)
                                
                                chat_input_found = True
                                break
                    except Exception as e:
                        continue
                
                if not chat_input_found:
                    elapsed = time.time() - start_time
                    log_info(f"{question_id}: Still waiting for chat input... ({elapsed:.1f}s)")
                    await asyncio.sleep(check_interval)
            
            if not chat_input_found:
                log_error(f"{question_id}: Chat input not found after {max_wait_time}s wait")
                
                # Take debug screenshot to see what's on the page
                timestamp_str = datetime.now().strftime("%H%M%S")
                debug_path = self.debug_dir / f"jp_{question_id}_no_input_{timestamp_str}.png"
                try:
                    await page.screenshot(path=str(debug_path))
                    log_info(f"{question_id}: Debug screenshot saved: {debug_path}")
                except:
                    pass
                
                return False
            
            # Submit the question
            try:
                # Try pressing Enter first
                await page.keyboard.press('Enter')
                log_info(f"{question_id}: Question submitted via Enter key")
                await asyncio.sleep(3)  # Wait for submission to process
                return True
            except:
                # Try looking for send button
                send_selectors = [
                    'button[aria-label*="Send"]',
                    'button[title*="Send"]',
                    'button:has(svg)',  # Button with icon (likely send)
                    '.send-button',
                    'button[type="submit"]',
                    'button:has-text("Send")'
                ]
                
                for selector in send_selectors:
                    try:
                        send_btn = page.locator(selector)
                        if await send_btn.count() > 0:
                            first_btn = send_btn.first
                            if await first_btn.is_visible():
                                await first_btn.click()
                                log_info(f"{question_id}: Question submitted via send button")
                                await asyncio.sleep(3)
                                return True
                    except:
                        continue
                
                log_error(f"{question_id}: Could not submit question - no send method worked")
                return False
                
        except Exception as e:
            log_error(f"{question_id}: Question submission failed: {e}")
            return False

    async def wait_for_jp_completion_progressive(self, page: Page, question_id: str, question_text: str) -> str:
        """
        Progressive timeout implementation: 15s, 30s, 45s, 60s phases
        Total: 2 minutes 30 seconds maximum
        """
        log_info(f"{question_id}: Starting progressive timeout (15s, 30s, 45s, 60s = 2:30 total)")
        start_time = time.time()
        
        for phase_num, timeout_seconds in enumerate(self.TIMEOUT_PHASES, 1):
            phase_start = time.time()
            log_info(f"{question_id}: Phase {phase_num}/{len(self.TIMEOUT_PHASES)} - waiting up to {timeout_seconds}s")
            
            # Take screenshot at start of phase
            timestamp_str = datetime.now().strftime("%H%M%S")
            screenshot_path = self.debug_dir / f"jp_{question_id}_phase_{phase_num}_start_{timestamp_str}.png"
            try:
                await page.screenshot(path=str(screenshot_path))
                log_info(f"{question_id}: Screenshot saved - phase {phase_num} start")
            except Exception as e:
                log_warning(f"{question_id}: Screenshot failed: {e}")
            
            # Wait for this phase with periodic checks every 5 seconds
            while time.time() - phase_start < timeout_seconds:
                await asyncio.sleep(5)
                
                try:
                    # Get current page content
                    content = await self.get_response_content(page)
                    
                    # Strong completion indicators - must have substantial legal content
                    completion_indicators = ["Case Details", "Federal Court", "Social Security Tribunal", "Decision:", "Summary:"]
                    working_indicators = ["Thinking", "Summary Agent", "Analyzing documents", "Search Agent", "please wait"]
                    
                    has_completion = any(indicator in content for indicator in completion_indicators)
                    has_working = any(indicator in content for indicator in working_indicators)
                    
                    if has_completion and len(content) > 200 and not has_working:
                        elapsed = time.time() - start_time
                        log_success(f"{question_id}: Response complete after {elapsed:.1f}s in phase {phase_num}")
                        
                        # Take final success screenshot
                        timestamp_str = datetime.now().strftime("%H%M%S")
                        final_path = self.debug_dir / f"jp_{question_id}_final_success_{timestamp_str}.png"
                        try:
                            await page.screenshot(path=str(final_path))
                        except:
                            pass
                        
                        return content
                    
                    # JP working indicators - continue waiting
                    if has_working:
                        elapsed = time.time() - phase_start
                        log_info(f"{question_id}: JP processing... ({elapsed:.1f}s in phase {phase_num})")
                        continue
                    
                    # Check for other substantial content
                    if len(content) > 100:
                        log_info(f"{question_id}: Got {len(content)} chars, checking quality...")
                
                except Exception as e:
                    log_warning(f"{question_id}: Content check failed: {e}")
            
            # End of phase - take screenshot
            timestamp_str = datetime.now().strftime("%H%M%S")
            end_path = self.debug_dir / f"jp_{question_id}_phase_{phase_num}_end_{timestamp_str}.png"
            try:
                await page.screenshot(path=str(end_path))
                log_info(f"{question_id}: Screenshot saved - phase {phase_num} end")
            except:
                pass
        
        # All phases exhausted - final attempt
        elapsed_total = time.time() - start_time
        log_warning(f"{question_id}: All phases exhausted after {elapsed_total:.1f}s")
        
        try:
            final_content = await self.get_response_content(page)
            timestamp_str = datetime.now().strftime("%H%M%S")
            final_timeout_path = self.debug_dir / f"jp_{question_id}_final_timeout_{timestamp_str}.png"
            await page.screenshot(path=str(final_timeout_path))
            log_info(f"{question_id}: Final content captured: {len(final_content)} chars")
            return final_content
        except Exception as e:
            log_error(f"{question_id}: Final content capture failed: {e}")
            return f"[TIMEOUT] Progressive timeout exceeded 2:30 after phases: {self.TIMEOUT_PHASES}"

    async def process_single_question(self, question_id: str, question_text: str, attempt: int) -> Dict[str, Any]:
        """Process single question with progressive timeout"""
        log_info(f"Processing {question_id} (attempt {attempt}/{self.MAX_RETRIES})")
        
        browser = await self.connect_to_edge_debug()
        if not browser:
            return {
                'question_id': question_id,
                'question': question_text,
                'answer_text': '[ERROR] Could not connect to Edge debug instance',
                'status': 'error',
                'attempt': attempt,
                'timestamp': datetime.now().isoformat()
            }
        
        try:
            jp_page = await self.find_jp_page(browser)
            if not jp_page:
                await browser.close()
                return {
                    'question_id': question_id,
                    'question': question_text,
                    'answer_text': '[ERROR] JP page not found in browser',
                    'status': 'error',
                    'attempt': attempt,
                    'timestamp': datetime.now().isoformat()
                }
            
            # Submit question
            if not await self.submit_question_to_jp(jp_page, question_text, question_id):
                await browser.close()
                return {
                    'question_id': question_id,
                    'question': question_text,
                    'answer_text': '[ERROR] Failed to submit question to JP',
                    'status': 'error',
                    'attempt': attempt,
                    'timestamp': datetime.now().isoformat()
                }
            
            # Wait with progressive timeout
            response = await self.wait_for_jp_completion_progressive(jp_page, question_id, question_text)
            
            # Determine status based on response quality
            completion_indicators = ["Case Details", "Federal Court", "Social Security Tribunal", "Decision:", "Summary:"]
            has_completion = any(indicator in response for indicator in completion_indicators)
            
            if has_completion and len(response) > 200 and not "[TIMEOUT]" in response:
                status = 'success'
                log_success(f"{question_id}: Question completed successfully")
            elif "[TIMEOUT]" in response:
                status = 'timeout'
                log_warning(f"{question_id}: Question timed out after 2:30")
            elif len(response) > 100:
                status = 'partial'
                log_warning(f"{question_id}: Question completed with partial response")
            else:
                status = 'error'
                log_error(f"{question_id}: Question failed with minimal response")
            
            await browser.close()
            
            return {
                'question_id': question_id,
                'question': question_text,
                'answer_text': response,
                'status': status,
                'attempt': attempt,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            try:
                await browser.close()
            except:
                pass
            log_error(f"{question_id}: Processing failed: {e}")
            return {
                'question_id': question_id,
                'question': question_text,
                'answer_text': f'[ERROR] Processing failed: {e}',
                'status': 'error',
                'attempt': attempt,
                'timestamp': datetime.now().isoformat()
            }

    async def process_questions_with_retry(self) -> None:
        """Process all questions with three-strike retry logic"""
        # Load questions
        questions = self.load_questions()
        if not questions:
            return
        
        # Process each question with retry
        for i, (question_id, question_text) in enumerate(questions):
            if self.limit and i >= self.limit:
                log_info(f"Reached limit of {self.limit} questions")
                break
            
            log_info(f"Starting question {i+1}/{len(questions)}: {question_id}")
            
            # Three strikes rule
            success = False
            for attempt in range(1, self.MAX_RETRIES + 1):
                result = await self.process_single_question(question_id, question_text, attempt)
                
                if result['status'] == 'success':
                    self.results.append(result)
                    success = True
                    break
                elif result['status'] in ['partial'] and attempt == self.MAX_RETRIES:
                    # Accept partial on final attempt
                    self.results.append(result)
                    success = True
                    log_info(f"{question_id}: Accepting partial result on final attempt")
                    break
                elif result['status'] == 'timeout' and attempt == self.MAX_RETRIES:
                    # Accept timeout on final attempt
                    self.results.append(result)
                    success = True
                    log_info(f"{question_id}: Accepting timeout result on final attempt")
                    break
                else:
                    log_warning(f"{question_id}: Attempt {attempt} failed ({result['status']})")
                    if attempt < self.MAX_RETRIES:
                        log_info(f"{question_id}: Retrying with fresh browser session...")
                        await asyncio.sleep(2)  # Brief pause between attempts
            
            if not success:
                # All attempts failed
                self.results.append({
                    'question_id': question_id,
                    'question': question_text,
                    'answer_text': '[ERROR] All 3 attempts failed',
                    'status': 'failed',
                    'attempts': self.MAX_RETRIES,
                    'timestamp': datetime.now().isoformat()
                })
        
        # Save results
        await self.save_results()

    def load_questions(self) -> List[tuple]:
        """Load questions from CSV file"""
        try:
            questions = []
            with open(self.input_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    question_id = row.get('question_id', '').strip()
                    question = row.get('question', '').strip()
                    
                    if question_id and question:
                        questions.append((question_id, question))
            
            log_info(f"Loaded {len(questions)} questions from {self.input_file}")
            return questions
            
        except Exception as e:
            log_error(f"Failed to load questions: {e}")
            return []

    async def save_results(self) -> None:
        """Save results to CSV and JSON files"""
        try:
            # Ensure output directory exists
            self.output_file.parent.mkdir(exist_ok=True)
            
            # Save CSV
            with open(self.output_file, 'w', newline='', encoding='utf-8') as f:
                if self.results:
                    fieldnames = list(self.results[0].keys())
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(self.results)
            
            # Save JSON
            json_file = self.output_file.with_suffix('.json')
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(self.results, f, indent=2, ensure_ascii=False)
            
            log_success(f"Results saved to {self.output_file}")
            log_success(f"JSON saved to {json_file}")
            
            # Summary
            total = len(self.results)
            success_count = len([r for r in self.results if r['status'] == 'success'])
            partial_count = len([r for r in self.results if r['status'] == 'partial'])
            timeout_count = len([r for r in self.results if r['status'] == 'timeout'])
            error_count = len([r for r in self.results if r['status'] in ['error', 'failed']])
            
            log_info("=== SESSION SUMMARY ===")
            log_info(f"Total Questions: {total}")
            log_info(f"Successful: {success_count}")
            log_info(f"Partial: {partial_count}")
            log_info(f"Timeouts: {timeout_count}")
            log_info(f"Errors: {error_count}")
            if total > 0:
                success_rate = (success_count + partial_count) / total * 100
                log_info(f"Success Rate: {success_rate:.1f}%")
            else:
                log_info("Success Rate: 0%")
            
        except Exception as e:
            log_error(f"Failed to save results: {e}")

async def main():
    parser = argparse.ArgumentParser(description='JP Automation with Progressive Timeout')
    parser.add_argument('--input', required=True, help='Input CSV file with questions')
    parser.add_argument('--output', required=True, help='Output CSV file for results')
    parser.add_argument('--limit', type=int, help='Limit number of questions to process')
    parser.add_argument('--headed', action='store_true', help='Run in headed mode (not used with debug connection)')
    
    args = parser.parse_args()
    
    input_path = Path(args.input)
    output_path = Path(args.output)
    
    if not input_path.exists():
        log_error(f"Input file not found: {input_path}")
        return
    
    automation = JPAutomationProgressive(input_path, output_path, args.limit, args.headed)
    await automation.process_questions_with_retry()

if __name__ == "__main__":
    asyncio.run(main())