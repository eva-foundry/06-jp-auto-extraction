#!/usr/bin/env python3
"""
JP Deep Debug Tool - Enhanced Element Analysis
=============================================

Advanced debugging to find JP chat interface components
when standard input/textarea elements are not present.
"""

import asyncio
import json
from playwright.async_api import async_playwright

async def deep_debug_jp_page():
    """Deep analysis of JP page to find chat interface"""
    
    print("=== JP Deep Debug Tool ===")
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
            
            # Wait for page to fully load and all resources
            print("[INFO] Waiting for page to load completely...")
            await jp_page.wait_for_load_state('networkidle', timeout=30000)
            
            # Give extra time for React/Angular components to render
            print("[INFO] Waiting additional 5 seconds for dynamic components...")
            await asyncio.sleep(5)
            
            title = await jp_page.title()
            print(f"[INFO] Page title: {title}")
            
            # Take full screenshot
            await jp_page.screenshot(path="jp_deep_debug_full.png", full_page=True)
            print("[INFO] Full screenshot: jp_deep_debug_full.png")
            
            print("\n" + "="*60)
            print("COMPREHENSIVE ELEMENT ANALYSIS")
            print("="*60)
            
            # 1. Check for ANY elements that might be chat-related
            print("\n[1] SEARCHING FOR CHAT-RELATED ELEMENTS...")
            
            # Look for elements with chat-related text content
            chat_text_elements = await jp_page.query_selector_all('*:has-text("Type your message"), *:has-text("message"), *:has-text("chat"), *:has-text("ask"), *:has-text("question")')
            print(f"[DEBUG] Found {len(chat_text_elements)} elements with chat-related text")
            
            for i, elem in enumerate(chat_text_elements[:5]):  # First 5 only
                try:
                    tag_name = await elem.evaluate('el => el.tagName')
                    text_content = await elem.text_content()
                    if text_content and len(text_content.strip()) > 0:
                        print(f"[DEBUG] Chat text element {i+1}: {tag_name} - '{text_content[:50]}...'")
                except:
                    pass
            
            # 2. Check for clickable elements
            print("\n[2] SEARCHING FOR CLICKABLE/INTERACTIVE ELEMENTS...")
            
            clickable_elements = await jp_page.query_selector_all('button, [role="button"], [role="textbox"], [tabindex], [onclick]')
            print(f"[DEBUG] Found {len(clickable_elements)} clickable/interactive elements")
            
            for i, elem in enumerate(clickable_elements[:10]):  # First 10 only
                try:
                    tag_name = await elem.evaluate('el => el.tagName')
                    role = await elem.get_attribute('role') or 'none'
                    aria_label = await elem.get_attribute('aria-label') or 'none'
                    class_name = await elem.get_attribute('class') or 'none'
                    text_content = await elem.text_content()
                    is_visible = await elem.is_visible()
                    
                    # Truncate long class names
                    if len(class_name) > 50:
                        class_name = class_name[:47] + "..."
                    
                    print(f"[DEBUG] Interactive {i+1}: {tag_name} role='{role}' visible={is_visible}")
                    print(f"         aria-label='{aria_label}' class='{class_name}'")
                    if text_content and len(text_content.strip()) > 0:
                        print(f"         text='{text_content[:30]}...'")
                    
                    # Check if this looks like a chat input
                    if (role == 'textbox' or 'text' in aria_label.lower() or 
                        'message' in aria_label.lower() or 'input' in class_name.lower()):
                        print(f"[CANDIDATE] Element {i+1} might be chat input!")
                        
                        # Try to interact with it
                        try:
                            if is_visible:
                                await elem.click()
                                await asyncio.sleep(0.5)
                                
                                # Check if a proper input appeared after clicking
                                new_inputs = await jp_page.query_selector_all('input, textarea, [contenteditable="true"]')
                                if len(new_inputs) > 0:
                                    print(f"[BREAKTHROUGH] Clicking element {i+1} revealed {len(new_inputs)} input elements!")
                                    
                                    for j, new_input in enumerate(new_inputs):
                                        try:
                                            new_tag = await new_input.evaluate('el => el.tagName')
                                            new_visible = await new_input.is_visible()
                                            print(f"[DEBUG] New input {j+1}: {new_tag} visible={new_visible}")
                                            
                                            if new_visible:
                                                # Test typing
                                                await new_input.fill("TEST MESSAGE")
                                                await asyncio.sleep(0.5)
                                                value = await new_input.input_value() if new_tag.lower() != 'div' else await new_input.text_content()
                                                await new_input.fill("") if new_tag.lower() != 'div' else await new_input.evaluate('el => el.textContent = ""')
                                                
                                                if "TEST MESSAGE" in (value or ""):
                                                    print(f"[SUCCESS] Found working chat input! Element {j+1}")
                                                    print(f"[SOLUTION] Click element {i+1}, then type in new input {j+1}")
                                                    return  # Found it!
                                        except Exception as e:
                                            print(f"[DEBUG] Could not test new input {j+1}: {e}")
                        except Exception as e:
                            print(f"[DEBUG] Could not interact with element {i+1}: {e}")
                    
                except Exception as e:
                    print(f"[DEBUG] Error checking interactive element {i+1}: {e}")
            
            # 3. Check DOM structure for common patterns
            print(f"\n[3] DOM STRUCTURE ANALYSIS...")
            
            # Look for Microsoft Fluent UI components (common in enterprise apps)
            fluent_elements = await jp_page.query_selector_all('[class*="ms-"], [class*="fluent"], [class*="Fluent"]')
            print(f"[DEBUG] Found {len(fluent_elements)} Fluent UI elements")
            
            # Look for React components
            react_elements = await jp_page.query_selector_all('[data-reactroot], [class*="react"], [class*="React"]')
            print(f"[DEBUG] Found {len(react_elements)} React-related elements") 
            
            # Look for chat/conversation patterns
            chat_containers = await jp_page.query_selector_all('[class*="chat"], [class*="conversation"], [class*="message"], [id*="chat"], [id*="input"]')
            print(f"[DEBUG] Found {len(chat_containers)} chat/message container elements")
            
            # 4. Get page HTML for manual inspection
            print(f"\n[4] SAVING PAGE SOURCE...")
            html_content = await jp_page.content()
            with open("jp_deep_debug.html", "w", encoding="utf-8") as f:
                f.write(html_content)
            print("[INFO] Page HTML saved: jp_deep_debug.html")
            
            # 5. Check JavaScript console for errors
            print(f"\n[5] JAVASCRIPT CONSOLE CHECK...")
            try:
                console_messages = []
                
                def handle_console(msg):
                    console_messages.append(f"{msg.type}: {msg.text}")
                
                jp_page.on('console', handle_console)
                
                # Trigger a page interaction to see console messages
                await jp_page.evaluate('console.log("JP Debug: Page analysis complete")')
                await asyncio.sleep(1)
                
                print(f"[DEBUG] Recent console messages: {len(console_messages)}")
                for msg in console_messages[-5:]:  # Last 5 messages
                    print(f"[CONSOLE] {msg}")
                    
            except Exception as e:
                print(f"[DEBUG] Console check failed: {e}")
            
            print(f"\n" + "="*60)
            print("ANALYSIS COMPLETE")
            print("="*60)
            print("[INFO] Check these files for detailed analysis:")
            print("  - jp_deep_debug_full.png (visual screenshot)")
            print("  - jp_deep_debug.html (full page source)")
            print()
            print("[NEXT] Manual inspection needed:")
            print("  1. Open jp_deep_debug_full.png to see the visual interface")
            print("  2. Look for where you would normally type in the JP interface")
            print("  3. Open jp_deep_debug.html and search for 'input', 'textarea', or 'textbox'")
            print("  4. Check if the chat interface loads after page interaction")
            
            await browser.close()
            
    except Exception as e:
        print(f"[ERROR] Deep debug failed: {e}")

if __name__ == "__main__":
    asyncio.run(deep_debug_jp_page())