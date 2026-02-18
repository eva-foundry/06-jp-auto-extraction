#!/usr/bin/env python3
"""
Connect to Running Edge Debug Instance
=====================================

Connects to Edge instance running with --remote-debugging-port=9222
and tests JP automation.

Prerequisites: 
- Edge must be running with debug port 9222
- JP must be authenticated in that Edge instance
"""

import asyncio
from playwright.async_api import async_playwright

JP_URL = "https://ei-jp-ui.purplesky-a9615d9b.canadacentral.azurecontainerapps.io"

async def connect_to_debug_edge():
    """Connect to running Edge debug instance"""
    
    print("=== Connecting to Edge Debug Instance ===")
    print()
    
    try:
        async with async_playwright() as playwright:
            print("[INFO] Connecting to Edge on port 9222...")
            
            # Connect to running Edge instance
            browser = await playwright.chromium.connect_over_cdp("http://127.0.0.1:9222")
            print("[SUCCESS] Connected to Edge debug instance!")
            
            # Find JP page
            contexts = browser.contexts
            jp_page = None
            
            print(f"[INFO] Found {len(contexts)} browser contexts")
            
            for context in contexts:
                pages = context.pages
                print(f"[INFO] Checking {len(pages)} pages in context...")
                
                for page in pages:
                    url = page.url
                    title = await page.title()
                    print(f"[DEBUG] Page: {title} - {url}")
                    
                    if "ei-jp-ui.purplesky" in url:
                        jp_page = page
                        print(f"[FOUND] JP page: {title}")
                        break
                
                if jp_page:
                    break
            
            if not jp_page:
                print("[ERROR] JP page not found in browser")
                print("[HELP] Make sure JP is loaded in the Edge debug instance")
                await browser.close()
                return False
            
            # Test JP page
            print(f"[INFO] Testing JP page: {jp_page.url}")
            
            # Take screenshot
            await jp_page.screenshot(path="jp_debug_connected.png")
            print("[INFO] Screenshot saved: jp_debug_connected.png")
            
            # Look for chat input
            try:
                # Wait for page to be ready
                await jp_page.wait_for_load_state('domcontentloaded', timeout=10000)
                
                # Look for chat input - JP specific selectors
                chat_selectors = [
                    'input[placeholder*="Type your message here"]',
                    'input[placeholder*="message"]',
                    'textarea[placeholder*="message"]', 
                    'input[placeholder*="Type your message"]',
                    '.chat-input input',
                    '.chat-input textarea',
                    'input[type="text"]',
                    'textarea',
                    'div[contenteditable="true"]',  # Sometimes JP uses contenteditable div
                    '.ms-TextField-field',  # Fluent UI text field
                    '.ms-BasePicker-input'  # Microsoft UI input
                ]
                
                chat_input = None
                for selector in chat_selectors:
                    try:
                        elements = jp_page.locator(selector)
                        count = await elements.count()
                        
                        if count > 0:
                            first_element = elements.first
                            if await first_element.is_visible():
                                chat_input = first_element
                                print(f"[FOUND] Chat input: {selector}")
                                break
                    except:
                        continue
                
                if chat_input:
                    # Test typing a message
                    test_message = "Test automation connection"
                    print(f"[INFO] Testing chat input with: {test_message}")
                    
                    await chat_input.fill(test_message)
                    await asyncio.sleep(1)
                    
                    # Check if message was typed
                    typed_value = await chat_input.input_value()
                    if test_message in typed_value:
                        print("[SUCCESS] Chat input works!")
                        
                        # Clear the test message
                        await chat_input.fill("")
                        print("[INFO] Test message cleared")
                        
                        print()
                        print("🎉 [SUCCESS] JP automation connection established!")
                        print("✅ Edge debug instance connected")  
                        print("✅ JP page found and accessible")
                        print("✅ Chat input working")
                        print()
                        print("Ready to run full automation!")
                        
                        await browser.close()
                        return True
                    else:
                        print(f"[ERROR] Chat input not working. Got: {typed_value}")
                else:
                    print("[WARNING] Chat input not found")
                    
                    # Take debug screenshot
                    await jp_page.screenshot(path="jp_no_chat_debug.png")
                    print("[DEBUG] Screenshot saved: jp_no_chat_debug.png")
                    
                    # Print page content for debugging
                    content = await jp_page.content()
                    if "sign in" in content.lower() and "microsoft" in content.lower():
                        print("[ERROR] Still seeing Microsoft login page")
                        print("[HELP] Please complete authentication in the Edge window first")
                    else:
                        print("[INFO] Page seems loaded, but chat input not found")
            
            except Exception as e:
                print(f"[ERROR] Chat input test failed: {e}")
            
            await browser.close()
            return False
            
    except Exception as e:
        print(f"[ERROR] Connection failed: {e}")
        print("[HELP] Make sure Edge is running with:")
        print('       "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe" --remote-debugging-port=9222 --user-data-dir="%TEMP%\\jp-edge-debug"')
        return False

if __name__ == "__main__":
    asyncio.run(connect_to_debug_edge())