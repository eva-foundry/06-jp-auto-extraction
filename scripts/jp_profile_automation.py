#!/usr/bin/env python3
"""
JP User Profile Automation
==========================

Uses your existing browser profile for authentication, then automates JP.
This should preserve your existing login sessions.
"""

import os
import sys
import asyncio
from pathlib import Path
import logging
from playwright.async_api import async_playwright

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

JP_URL = "https://ei-jp-ui.purplesky-a9615d9b.canadacentral.azurecontainerapps.io"

def find_edge_profile():
    """Find your Edge user profile directory"""
    
    base_path = os.path.expanduser(r"~\AppData\Local\Microsoft\Edge\User Data")
    
    if not os.path.exists(base_path):
        print(f"[ERROR] Edge user data not found at: {base_path}")
        return None
    
    # Try Default profile first
    profiles = ["Default", "Profile 1", "Profile 2"]
    
    for profile in profiles:
        profile_path = os.path.join(base_path, profile)
        if os.path.exists(profile_path):
            print(f"[FOUND] Edge profile: {profile_path}")
            return profile_path
    
    return None

def find_chrome_profile():
    """Find your Chrome user profile directory"""
    
    base_path = os.path.expanduser(r"~\AppData\Local\Google\Chrome\User Data")
    
    if not os.path.exists(base_path):
        print(f"[ERROR] Chrome user data not found at: {base_path}")
        return None
    
    # Try Default profile first
    profiles = ["Default", "Profile 1", "Profile 2"]
    
    for profile in profiles:
        profile_path = os.path.join(base_path, profile)
        if os.path.exists(profile_path):
            print(f"[FOUND] Chrome profile: {profile_path}")
            return profile_path
    
    return None

async def test_with_user_profile():
    """Test JP automation with existing user profile"""
    
    print("=== JP User Profile Automation ===")
    print()
    
    # Try Edge first (since you mentioned it's your default)
    profile_path = find_edge_profile()
    browser_type = "Edge"
    
    if not profile_path:
        profile_path = find_chrome_profile()  
        browser_type = "Chrome"
    
    if not profile_path:
        print("[ERROR] No browser profile found")
        return False
    
    print(f"[INFO] Using {browser_type} profile: {profile_path}")
    
    async with async_playwright() as playwright:
        try:
            # Launch browser with existing user profile
            print(f"[INFO] Launching {browser_type} with your existing profile...")
            
            browser = await playwright.chromium.launch_persistent_context(
                profile_path,
                headless=False,
                args=[
                    "--no-first-run",
                    "--no-default-browser-check",
                ]
            )
            
            print(f"[SUCCESS] {browser_type} launched with your profile!")
            
            # Create or get a page
            pages = browser.pages
            if pages:
                page = pages[0]
            else:
                page = await browser.new_page()
            
            # Navigate to JP
            print(f"[INFO] Navigating to JP: {JP_URL}")
            await page.goto(JP_URL, wait_until='domcontentloaded', timeout=30000)
            
            # Wait a bit for page to load
            await asyncio.sleep(3)
            
            title = await page.title()
            current_url = page.url
            
            print(f"[SUCCESS] JP loaded!")
            print(f"[INFO] Page title: {title}")
            print(f"[INFO] Current URL: {current_url}")
            
            # Take screenshot to verify
            await page.screenshot(path="jp_profile_test.png", full_page=True)
            print("[INFO] Screenshot saved: jp_profile_test.png")
            
            # Check if we're authenticated (look for signs we're logged in)
            authenticated = False
            
            try:
                # Wait for the page to fully load
                await page.wait_for_load_state('networkidle', timeout=10000)
                
                # Look for authentication indicators
                auth_indicators = [
                    "Jurisprudence Assistant",  # Should be visible if logged in
                    "Type your message here",   # Chat input
                    "Employment and Social Development Canada"  # Header
                ]
                
                page_content = await page.content()
                
                for indicator in auth_indicators:
                    if indicator.lower() in page_content.lower():
                        print(f"[FOUND] Authentication indicator: {indicator}")
                        authenticated = True
                        break
                
                # Look for Microsoft login page (indicates not authenticated)
                if "sign in" in page_content.lower() and "microsoft" in page_content.lower():
                    print("[WARNING] Still seeing Microsoft login page")
                    authenticated = False
                
            except Exception as e:
                print(f"[WARNING] Could not check authentication status: {e}")
            
            if authenticated:
                print("[SUCCESS] Appears to be authenticated - no Microsoft login page!")
                
                # Try to find chat input
                chat_selectors = [
                    'input[placeholder*="message"]',
                    'textarea[placeholder*="message"]', 
                    'input[placeholder*="Type your message"]',
                    '.chat-input input',
                    '.chat-input textarea',
                    '[data-testid="chat-input"]'
                ]
                
                chat_found = False
                for selector in chat_selectors:
                    try:
                        element = page.locator(selector)
                        if await element.count() > 0 and await element.first.is_visible():
                            print(f"[FOUND] Chat input element: {selector}")
                            
                            # Test interaction
                            await element.first.fill("Test message - do not send")
                            await asyncio.sleep(1)
                            await element.first.fill("")  # Clear it
                            print("[SUCCESS] Chat input interaction works!")
                            
                            chat_found = True
                            break
                    except:
                        continue
                
                if not chat_found:
                    print("[WARNING] Could not find chat input")
                    
                    # Take debug screenshot
                    await page.screenshot(path="jp_no_chat.png", full_page=True)
                    print("[DEBUG] Full page screenshot: jp_no_chat.png")
                
            else:
                print("[ERROR] Not authenticated - still need to handle login")
            
            print()
            print(f"[INFO] {browser_type} remains open for manual verification")
            input("[MANUAL] Press Enter after checking JP in the browser...")
            
            await browser.close()
            return authenticated
            
        except Exception as e:
            print(f"[ERROR] Profile launch failed: {e}")
            return False

async def main():
    """Main test function"""
    success = await test_with_user_profile()
    
    if success:
        print("\n=== SUCCESS ===")
        print("✅ User profile approach works!")
        print("✅ JP loaded with existing authentication")
        print("✅ Ready to integrate into main automation")
    else:
        print("\n=== NEEDS WORK ===")
        print("❌ Authentication issues remain")
        print("❌ May need to handle Microsoft login flow")

if __name__ == "__main__":
    asyncio.run(main())