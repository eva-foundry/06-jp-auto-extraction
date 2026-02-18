#!/usr/bin/env python3
"""
JP Authentication Helper Script
Handles Microsoft authentication for the JP UI system
"""

import logging
from pathlib import Path
from playwright.sync_api import sync_playwright
import time
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

def authenticate_jp_ui(headless: bool = False):
    """
    Handles Microsoft authentication for JP UI
    Returns True if authentication successful, False otherwise
    """
    JP_UI_URL = "https://ei-jp-ui.purplesky-a9615d9b.canadacentral.azurecontainerapps.io/"
    
    logger.info("Starting JP UI authentication helper")
    logger.info(f"JP UI URL: {JP_UI_URL}")
    logger.info(f"Headless mode: {headless}")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context()
        page = context.new_page()
        
        try:
            logger.info("Navigating to JP UI...")
            page.goto(JP_UI_URL)
            page.wait_for_load_state('networkidle', timeout=30000)
            
            # Check if we're on the login page
            if page.locator("text=Login to access the app").count() > 0:
                logger.info("Login page detected")
                
                if headless:
                    logger.error("Authentication required but running in headless mode")
                    logger.error("Please run with --headed flag to authenticate manually")
                    return False
                
                # Look for Microsoft login button
                ms_button = page.locator("button:has-text('Continue with Microsoft')")
                if ms_button.count() > 0:
                    logger.info("Microsoft login button found")
                    logger.info("MANUAL ACTION REQUIRED:")
                    logger.info("1. Click 'Continue with Microsoft' button")
                    logger.info("2. Complete Microsoft authentication in the browser")
                    logger.info("3. Wait until you reach the JP chat interface")
                    logger.info("4. Press ENTER in this terminal when authentication is complete")
                    
                    # Wait for user input
                    input("Press ENTER when you have completed authentication...")
                    
                    # Check if we're now on the main page
                    logger.info("Checking authentication status...")
                    time.sleep(2)
                    
                    # Look for chat interface elements
                    if (page.locator("text=Login to access the app").count() == 0 and 
                        (page.locator("textarea").count() > 0 or 
                         page.locator("input[type='text']").count() > 0)):
                        logger.info("PASS Authentication successful!")
                        logger.info("You can now run the JP automation script")
                        return True
                    else:
                        logger.error("FAIL Authentication appears incomplete")
                        logger.error("Please try the authentication process again")
                        return False
                else:
                    logger.error("Microsoft login button not found")
                    return False
            else:
                logger.info("PASS Already authenticated or no login required")
                return True
                
        except Exception as e:
            logger.error(f"Authentication error: {str(e)}")
            return False
            
        finally:
            if not headless:
                logger.info("Keeping browser open for manual verification...")
                logger.info("Close the browser window when done")
                try:
                    # Keep browser open until user closes it
                    while not page.is_closed():
                        time.sleep(1)
                except:
                    pass
            browser.close()

def main():
    import argparse
    parser = argparse.ArgumentParser(description="JP UI Authentication Helper")
    parser.add_argument("--headed", action="store_true", 
                       help="Run in headed mode (required for manual auth)")
    args = parser.parse_args()
    
    if not args.headed:
        logger.warning("Running in headless mode - authentication will likely fail")
        logger.warning("Use --headed flag for manual authentication")
    
    success = authenticate_jp_ui(headless=not args.headed)
    
    if success:
        logger.info("Authentication helper completed successfully")
        logger.info("You can now run: python run_jp_batch.py --in input/questions.csv --out output/jp_answers.csv --headed")
        sys.exit(0)
    else:
        logger.error("Authentication helper failed")
        sys.exit(1)

if __name__ == "__main__":
    main()