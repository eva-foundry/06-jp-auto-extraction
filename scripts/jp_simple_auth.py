#!/usr/bin/env python3
"""
Simple JP Authentication Test
Tests whether the JP interface loads automatically for pre-authorized users
"""

import asyncio
import logging
from playwright.async_api import async_playwright

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

JP_URL = "https://ei-jp-ui.purplesky-a9615d9b.canadacentral.azurecontainerapps.io/"

async def test_jp_authentication():
    """Test JP authentication flow"""
    
    logger.info("🚀 Starting JP Authentication Test")
    logger.info(f"Target URL: {JP_URL}")
    
    async with async_playwright() as playwright:
        # Launch browser
        browser = await playwright.chromium.launch(headless=False)
        context = await browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = await context.new_page()
        
        try:
            logger.info("📱 Navigating to JP interface...")
            await page.goto(JP_URL)
            
            # Wait and monitor the authentication flow
            for i in range(60):  # Wait up to 60 seconds
                current_url = page.url
                
                if i == 0 or i % 10 == 0:  # Log every 10 seconds
                    logger.info(f"⏱️  After {i}s - URL: {current_url[:80]}...")
                
                # Check for different page states
                if "login.microsoftonline.com" in current_url:
                    if i == 0:
                        logger.info("🔐 Redirected to Microsoft authentication")
                    
                    # Look for automatic login elements
                    try:
                        # Check if there are account buttons to click
                        account_selectors = [
                            '[data-test-id*="account"]',
                            '.accountButton',
                            'button:has-text("Continue")',
                            'button:has-text("Accept")',
                            '.ms-Button--primary'
                        ]
                        
                        for selector in account_selectors:
                            element = await page.query_selector(selector)
                            if element and await element.is_visible():
                                logger.info(f"🖱️  Clicking: {selector}")
                                await element.click()
                                await asyncio.sleep(3)
                                break
                        
                    except Exception as e:
                        logger.debug(f"Auth interaction error: {e}")
                
                elif "/login" in current_url and "ei-jp-ui.purplesky" in current_url:
                    if i == 0:
                        logger.info("🏠 Back on JP login page")
                    
                    # Look for Continue button
                    try:
                        continue_btn = await page.query_selector('button:has-text("Continue"), a:has-text("Continue")')
                        if continue_btn and await continue_btn.is_visible():
                            logger.info("🖱️  Clicking Continue button")
                            await continue_btn.click()
                            await asyncio.sleep(3)
                    except Exception:
                        pass
                
                else:
                    # Check if we've reached the chat interface
                    chat_selectors = [
                        'textarea[placeholder*="message"]',
                        'textarea[placeholder*="question"]',
                        'input[placeholder*="message"]',
                        'textarea:visible',
                        'button:has-text("Send")'
                    ]
                    
                    for selector in chat_selectors:
                        try:
                            element = await page.query_selector(selector)
                            if element and await element.is_visible():
                                logger.info(f"✅ SUCCESS: Found chat interface element: {selector}")
                                logger.info(f"🎯 Final URL: {current_url}")
                                return True
                        except Exception:
                            continue
                
                await asyncio.sleep(1)
            
            logger.error("❌ TIMEOUT: Authentication did not complete in 60 seconds")
            logger.error(f"Final URL: {page.url}")
            return False
            
        except Exception as e:
            logger.error(f"❌ ERROR: {e}")
            return False
        
        finally:
            await browser.close()

async def main():
    success = await test_jp_authentication()
    if success:
        print("\n✅ JP Authentication works automatically!")
        print("The main automation should work now.")
    else:
        print("\n❌ JP Authentication requires manual intervention")
        print("You may need to complete authentication manually once to save a session.")
    
    return success

if __name__ == "__main__":
    asyncio.run(main())