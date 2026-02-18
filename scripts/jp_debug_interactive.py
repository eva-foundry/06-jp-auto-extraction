#!/usr/bin/env python3
"""
JP Interactive Debug Tool
=========================

Connects to Edge debug instance and provides interactive debugging
for finding JP chat elements.
"""

import asyncio
from playwright.async_api import async_playwright

async def debug_jp_page():
    """Interactive debugging of JP page elements"""
    
    print("=== JP Interactive Debug ===")
    print()
    
    try:
        async with async_playwright() as playwright:
            print("[INFO] Connecting to Edge on port 9222...")
            
            browser = await playwright.chromium.connect_over_cdp("http://127.0.0.1:9222")
            print("[SUCCESS] Connected to Edge!")
            
            # Find JP page
            jp_page = None
            for context in browser.contexts:
                for page in context.pages:
                    url = page.url
                    if "ei-jp-ui.purplesky" in url:
                        jp_page = page
                        break
                if jp_page:
                    break
            
            if not jp_page:
                print("[ERROR] JP page not found")
                await browser.close()
                return
            
            print(f"[FOUND] JP page: {jp_page.url}")
            
            # Wait for page to fully load
            print("[INFO] Waiting for page to load completely...")
            await jp_page.wait_for_load_state('networkidle', timeout=30000)
            
            # Get page info
            title = await jp_page.title()
            print(f"[INFO] Page title: {title}")
            
            # Take a screenshot 
            await jp_page.screenshot(path="jp_full_debug.png", full_page=True)
            print("[INFO] Full screenshot saved: jp_full_debug.png")
            
            # Check for all input elements
            print("\n[DEBUG] Looking for ALL input elements on page...")
            
            all_inputs = await jp_page.query_selector_all('input')
            all_textareas = await jp_page.query_selector_all('textarea')
            all_contenteditable = await jp_page.query_selector_all('[contenteditable="true"]')
            
            print(f"[DEBUG] Found {len(all_inputs)} input elements")
            print(f"[DEBUG] Found {len(all_textareas)} textarea elements")  
            print(f"[DEBUG] Found {len(all_contenteditable)} contenteditable elements")
            
            # Check each input
            for i, input_elem in enumerate(all_inputs):
                try:
                    tag_name = await input_elem.evaluate('el => el.tagName')
                    input_type = await input_elem.get_attribute('type') or 'text'
                    placeholder = await input_elem.get_attribute('placeholder') or 'none'
                    class_name = await input_elem.get_attribute('class') or 'none'
                    is_visible = await input_elem.is_visible()
                    
                    print(f"[DEBUG] Input {i+1}: {tag_name} type='{input_type}' placeholder='{placeholder}' visible={is_visible}")
                    if len(class_name) < 100:  # Don't print huge class strings
                        print(f"         class='{class_name}'")
                    
                    if is_visible and ('message' in placeholder.lower() or 'chat' in class_name.lower()):
                        print(f"[CANDIDATE] Input {i+1} looks like a chat input!")
                        
                        # Test this input
                        try:
                            await input_elem.fill("TEST")
                            await asyncio.sleep(0.5)
                            value = await input_elem.input_value()
                            await input_elem.fill("")  # Clear it
                            
                            if "TEST" in value:
                                print(f"[SUCCESS] Input {i+1} is working! This is likely the chat input.")
                                break
                        except Exception as e:
                            print(f"[DEBUG] Could not test input {i+1}: {e}")
                            
                except Exception as e:
                    print(f"[DEBUG] Error checking input {i+1}: {e}")
            
            # Check textareas
            for i, textarea in enumerate(all_textareas):
                try:
                    placeholder = await textarea.get_attribute('placeholder') or 'none'
                    class_name = await textarea.get_attribute('class') or 'none'
                    is_visible = await textarea.is_visible()
                    
                    print(f"[DEBUG] Textarea {i+1}: placeholder='{placeholder}' visible={is_visible}")
                    if len(class_name) < 100:
                        print(f"         class='{class_name}'")
                    
                    if is_visible:
                        print(f"[CANDIDATE] Textarea {i+1} might be the chat input!")
                        
                        try:
                            await textarea.fill("TEST")
                            await asyncio.sleep(0.5)
                            value = await textarea.input_value()
                            await textarea.fill("")
                            
                            if "TEST" in value:
                                print(f"[SUCCESS] Textarea {i+1} is working!")
                                break
                        except Exception as e:
                            print(f"[DEBUG] Could not test textarea {i+1}: {e}")
                            
                except Exception as e:
                    print(f"[DEBUG] Error checking textarea {i+1}: {e}")
            
            # Check contenteditable
            for i, div in enumerate(all_contenteditable):
                try:
                    class_name = await div.get_attribute('class') or 'none'
                    is_visible = await div.is_visible()
                    
                    print(f"[DEBUG] Contenteditable {i+1}: visible={is_visible}")
                    if len(class_name) < 100:
                        print(f"         class='{class_name}'")
                        
                    if is_visible:
                        print(f"[CANDIDATE] Contenteditable {i+1} might be the chat input!")
                        
                        try:
                            await div.fill("TEST")
                            await asyncio.sleep(0.5)
                            text = await div.text_content()
                            await div.fill("")
                            
                            if "TEST" in text:
                                print(f"[SUCCESS] Contenteditable {i+1} is working!")
                                break
                        except Exception as e:
                            print(f"[DEBUG] Could not test contenteditable {i+1}: {e}")
                            
                except Exception as e:
                    print(f"[DEBUG] Error checking contenteditable {i+1}: {e}")
            
            print("\n[INFO] Debug complete. Check jp_full_debug.png for visual reference.")
            print("[INFO] Look at the manual JP interface to see what the chat input looks like.")
            
            await browser.close()
            
    except Exception as e:
        print(f"[ERROR] Debug failed: {e}")

if __name__ == "__main__":
    asyncio.run(debug_jp_page())