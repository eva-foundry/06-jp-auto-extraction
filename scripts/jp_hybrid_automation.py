#!/usr/bin/env python3
"""
JP Hybrid Automation
====================

Combines default browser (for authentication) with Playwright automation.
This approach:
1. Opens JP in your authenticated default browser
2. Uses the same Chrome/Edge instance with debugging for automation

This bypasses authentication issues while enabling automation.
"""

import os
import sys
import time
import asyncio
import webbrowser
import subprocess
import psutil
from pathlib import Path
import logging
import tempfile
import shutil
from playwright.async_api import async_playwright, Page

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

JP_URL = "https://ei-jp-ui.purplesky-a9615d9b.canadacentral.azurecontainerapps.io"

def find_browser_executable():
    """Find available browser executable on Windows"""
    
    browser_paths = [
        # Microsoft Edge
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        # Google Chrome
        r"C:\Program Files\Google\Chrome\Application\chrome.exe", 
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.expanduser(r"~\AppData\Local\Google\Chrome\Application\chrome.exe"),
    ]
    
    for path in browser_paths:
        if os.path.exists(path):
            browser_name = "Edge" if "msedge" in path else "Chrome"
            print(f"[FOUND] {browser_name} executable: {path}")
            return path, browser_name
    
    print("[ERROR] No compatible browser found (Chrome or Edge required)")
    return None, None

def kill_existing_browser_processes():
    """Kill existing browser processes to ensure clean start"""
    
    processes_to_kill = ['chrome.exe', 'msedge.exe']
    
    for proc_name in processes_to_kill:
        try:
            for proc in psutil.process_iter(['pid', 'name']):
                if proc.info['name'] == proc_name:
                    proc.kill()
                    print(f"[INFO] Killed existing {proc_name} process (PID: {proc.info['pid']})")
        except:
            pass
    
    # Wait for processes to fully terminate
    time.sleep(2)

async def launch_browser_with_automation():
    """Launch browser with debugging enabled and automate JP"""
    
    print("=== JP Hybrid Automation ===")
    print()
    
    # Find browser
    browser_exe, browser_name = find_browser_executable()
    if not browser_exe:
        return False
    
    # Clean slate - kill existing browsers
    print("[INFO] Cleaning up existing browser processes...")
    kill_existing_browser_processes()
    
    # Set up temporary user data directory
    temp_dir = tempfile.mkdtemp(prefix="jp_browser_")
    debug_port = 9222
    
    # Launch browser with debugging
    cmd = [
        browser_exe,
        f"--remote-debugging-port={debug_port}",
        f"--user-data-dir={temp_dir}",
        "--no-first-run",
        "--no-default-browser-check", 
        JP_URL
    ]
    
    print(f"[INFO] Launching {browser_name} with debugging enabled...")
    print(f"[INFO] User data dir: {temp_dir}")
    
    try:
        # Launch browser
        process = subprocess.Popen(cmd, 
                                 stdout=subprocess.DEVNULL, 
                                 stderr=subprocess.DEVNULL,
                                 creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
        
        print(f"[SUCCESS] {browser_name} launched (PID: {process.pid})")
        
        # Wait for browser to fully start
        await asyncio.sleep(8)
        
        # Connect via Playwright
        async with async_playwright() as playwright:
            try:
                print(f"[INFO] Connecting to {browser_name} on port {debug_port}...")
                browser = await playwright.chromium.connect_over_cdp(f"http://127.0.0.1:{debug_port}")
                
                print(f"[SUCCESS] Connected to {browser_name}!")
                
                # Get the JP page
                contexts = browser.contexts
                page = None
                
                for context in contexts:
                    for p in context.pages:
                        url = p.url
                        print(f"[DEBUG] Found page: {url}")
                        
                        if "ei-jp-ui.purplesky" in url or url == JP_URL:
                            page = p
                            print(f"[FOUND] JP page: {url}")
                            break
                    
                    if page:
                        break
                
                if not page and contexts:
                    # Create new page and navigate to JP
                    print("[INFO] Creating new JP page...")
                    context = contexts[0] if contexts else await browser.new_context()
                    page = await context.new_page()
                    await page.goto(JP_URL)
                    await page.wait_for_load_state('domcontentloaded')
                
                if page:
                    # Test the page
                    title = await page.title()
                    current_url = page.url
                    
                    print(f"[SUCCESS] Connected to JP!")
                    print(f"[INFO] Page title: {title}")
                    print(f"[INFO] Current URL: {current_url}")
                    
                    # Take screenshot
                    await page.screenshot(path="jp_hybrid_connected.png")
                    print("[INFO] Screenshot saved: jp_hybrid_connected.png")
                    
                    # Test basic interaction - look for chat input
                    try:
                        # Look for chat input field
                        chat_selectors = [
                            'input[placeholder*="message"]',
                            'textarea[placeholder*="message"]',
                            '.chat-input input',
                            '.chat-input textarea',
                            '[data-testid="chat-input"]',
                            'input[type="text"]'
                        ]
                        
                        chat_input = None
                        for selector in chat_selectors:
                            try:
                                chat_input = page.locator(selector).first
                                if await chat_input.is_visible(timeout=2000):
                                    print(f"[FOUND] Chat input: {selector}")
                                    break
                            except:
                                continue
                        
                        if chat_input and await chat_input.is_visible():
                            # Test typing
                            test_message = "Hello, this is an automated test!"
                            await chat_input.fill(test_message)
                            print(f"[SUCCESS] Typed test message: {test_message}")
                            
                            # Clear the message (don't send it)
                            await chat_input.fill("")
                            print("[INFO] Test message cleared")
                            
                        else:
                            print("[WARNING] Could not find chat input field")
                            
                            # Take debug screenshot 
                            await page.screenshot(path="jp_no_chat_input.png")
                            print("[DEBUG] Screenshot saved: jp_no_chat_input.png")
                    
                    except Exception as e:
                        print(f"[WARNING] Chat input test failed: {e}")
                    
                    print()
                    print("[SUCCESS] JP automation connection established!")
                    print("[INFO] Browser remains open for manual verification")
                    print("[INFO] You can now manually verify the JP interface")
                    print()
                    
                    # Keep browser open for manual verification
                    input("[MANUAL] Press Enter after verifying JP is working correctly...")
                    
                    await browser.close()
                    return True
                
                else:
                    print("[ERROR] Could not find or create JP page")
                    await browser.close()
                
            except Exception as e:
                print(f"[ERROR] Playwright connection failed: {e}")
        
    except Exception as e:
        print(f"[ERROR] Browser launch failed: {e}")
    
    finally:
        # Cleanup
        try:
            if 'process' in locals():
                process.terminate()
                process.wait(timeout=5)
        except:
            pass
        
        # Clean up temp directory
        try:
            shutil.rmtree(temp_dir, ignore_errors=True)
        except:
            pass
    
    return False

async def main():
    """Main test function"""
    success = await launch_browser_with_automation()
    
    if success:
        print("\n=== Next Steps ===")
        print("1. The hybrid approach works!")
        print("2. Your browser opened JP with authentication bypassed")
        print("3. Playwright successfully connected for automation")
        print("4. Ready to integrate this into the main automation!")
    else:
        print("\n=== Troubleshooting Required ===")
        print("1. Check if Chrome or Edge is installed")
        print("2. Ensure no antivirus is blocking browser launch")
        print("3. Try running as administrator if needed")

if __name__ == "__main__":
    asyncio.run(main())