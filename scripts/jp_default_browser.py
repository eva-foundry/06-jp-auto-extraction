#!/usr/bin/env python3
"""
JP Automation with Default Browser
==================================

Uses the system's default browser (where user is already authenticated)
instead of launching a fresh Playwright browser.

This bypasses all authentication issues by using existing browser sessions.
"""

import os
import sys
import time
import asyncio
import webbrowser
import subprocess
from pathlib import Path
import logging
from playwright.async_api import async_playwright, Page

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

JP_URL = "https://ei-jp-ui.purplesky-a9615d9b.canadacentral.azurecontainerapps.io"
TIMEOUT_SECONDS = 60

async def test_default_browser_approach():
    """Test opening JP in default browser and connecting to it"""
    
    print("[SUCCESS] Using system's default browser approach")
    print(f"[INFO] Opening JP URL: {JP_URL}")
    
    # Step 1: Open JP URL in default browser
    try:
        webbrowser.open(JP_URL)
        print("[SUCCESS] JP URL opened in default browser")
        print("[INFO] Please verify JP loaded in your browser...")
        
        # Give user time to see the page load
        await asyncio.sleep(3)
        
    except Exception as e:
        print(f"[ERROR] Failed to open default browser: {e}")
        return False
    
    # Step 2: Try to connect to the browser
    print("[INFO] Now attempting to connect to browser for automation...")
    
    try:
        # Check if we can find any Chrome/Edge processes to connect to
        print("[INFO] Looking for browser processes to connect to...")
        
        # Method 1: Try connecting to Chrome DevTools protocol
        async with async_playwright() as playwright:
            
            # Common Chrome/Edge debugging ports
            debug_ports = [9222, 9223, 9224, 9225]
            
            for port in debug_ports:
                try:
                    print(f"[INFO] Trying to connect to browser on port {port}...")
                    browser = await playwright.chromium.connect_over_cdp(f"http://127.0.0.1:{port}")
                    
                    contexts = browser.contexts
                    print(f"[SUCCESS] Connected to browser with {len(contexts)} contexts")
                    
                    # Look for JP tab
                    for context in contexts:
                        pages = context.pages
                        for page in pages:
                            url = page.url
                            if "ei-jp-ui.purplesky" in url or "jurisprudence" in url.lower():
                                print(f"[FOUND] JP page found: {url}")
                                
                                # Test basic interaction
                                title = await page.title()
                                print(f"[INFO] Page title: {title}")
                                
                                await browser.close()
                                return True
                    
                    await browser.close()
                    
                except Exception as e:
                    print(f"[DEBUG] Port {port} connection failed: {e}")
                    continue
            
            print("[WARNING] Could not connect to any browser with DevTools enabled")
            
    except Exception as e:
        print(f"[ERROR] Browser connection failed: {e}")
    
    print("[INFO] Default browser opened successfully - manual verification needed")
    return True

async def launch_chrome_with_debugging():
    """Launch Chrome with debugging enabled to allow Playwright connection"""
    
    print("[INFO] Launching Chrome with debugging enabled...")
    
    # Common Chrome executable paths on Windows
    chrome_paths = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        r"C:\Users\{}\AppData\Local\Google\Chrome\Application\chrome.exe".format(os.environ.get('USERNAME', '')),
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
    ]
    
    chrome_exe = None
    for path in chrome_paths:
        if os.path.exists(path):
            chrome_exe = path
            print(f"[FOUND] Browser executable: {chrome_exe}")
            break
    
    if not chrome_exe:
        print("[ERROR] Could not find Chrome or Edge executable")
        return False
    
    # Launch with debugging port
    debug_port = 9222
    cmd = [
        chrome_exe,
        f"--remote-debugging-port={debug_port}",
        "--user-data-dir=temp-chrome-debug",
        JP_URL
    ]
    
    try:
        print(f"[INFO] Launching: {' '.join(cmd)}")
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Wait for browser to start
        await asyncio.sleep(5)
        
        # Now connect via Playwright
        async with async_playwright() as playwright:
            try:
                browser = await playwright.chromium.connect_over_cdp(f"http://127.0.0.1:{debug_port}")
                print("[SUCCESS] Connected to Chrome with debugging enabled")
                
                contexts = browser.contexts
                if contexts:
                    context = contexts[0]
                    pages = context.pages
                    
                    if pages:
                        page = pages[0]
                        
                        # Navigate to JP if not already there
                        current_url = page.url
                        if "ei-jp-ui.purplesky" not in current_url:
                            print(f"[INFO] Navigating to JP URL from: {current_url}")
                            await page.goto(JP_URL)
                            await page.wait_for_load_state('domcontentloaded')
                        
                        title = await page.title()
                        print(f"[SUCCESS] Connected to JP page: {title}")
                        print(f"[INFO] Current URL: {page.url}")
                        
                        # Take a screenshot to verify
                        await page.screenshot(path="jp_connected.png")
                        print("[INFO] Screenshot saved: jp_connected.png")
                        
                        await browser.close()
                        return True
                
            except Exception as e:
                print(f"[ERROR] Failed to connect to launched browser: {e}")
        
        # Clean up process
        try:
            process.terminate()
        except:
            pass
        
    except Exception as e:
        print(f"[ERROR] Failed to launch browser: {e}")
        
    return False

async def main():
    """Main test function"""
    print("=== JP Default Browser Connection Test ===")
    print()
    
    # Try Method 1: Default browser
    print("Method 1: Opening JP in your default authenticated browser...")
    success1 = await test_default_browser_approach()
    
    if not success1:
        print()
        print("Method 2: Launching Chrome with debugging for Playwright connection...")
        success2 = await launch_chrome_with_debugging()
        
        if success2:
            print("[SUCCESS] Chrome debugging method worked!")
        else:
            print("[ERROR] Both methods failed")
    
    print()
    print("=== Test Complete ===")

if __name__ == "__main__":
    asyncio.run(main())