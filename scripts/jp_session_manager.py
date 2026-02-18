#!/usr/bin/env python3
"""
Enhanced JP Session Management
==============================

Handles authentication state persistence and session reuse for JP automation.
Eliminates the need for repeated authentication by saving browser sessions.

Author: JP Automation System
Version: 1.0
Date: 2026-01-23

Usage:
    Used internally by jp_automation_main.py - no direct usage required
"""

import os
import json
import asyncio
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
import logging

# Configure logging
logger = logging.getLogger(__name__)


class JPSessionManager:
    """Manages JP authentication sessions with persistence"""
    
    def __init__(self, project_root: Path = None):
        if project_root is None:
            project_root = Path(__file__).parent.parent
        
        self.project_root = project_root
        self.session_dir = project_root / "sessions"
        self.session_dir.mkdir(exist_ok=True)
        
        self.session_file = self.session_dir / "jp_browser_session.json"
        self.context_dir = self.session_dir / "browser_context"
        self.storage_state_file = self.context_dir / "storage_state.json"
        
        # Ensure context directory exists
        self.context_dir.mkdir(exist_ok=True)
        
    async def has_valid_session(self) -> bool:
        """Check if we have a valid existing session"""
        
        # Check for session metadata
        if not self.session_file.exists():
            logger.info("No session metadata found")
            return False
        
        try:
            with open(self.session_file, 'r') as f:
                session_data = json.load(f)
            
            # Check session age (expire after 24 hours)
            created = datetime.fromisoformat(session_data.get('created', '1970-01-01'))
            if datetime.now() - created > timedelta(hours=24):
                logger.info("Session expired (older than 24 hours)")
                await self.cleanup_invalid_session()
                return False
            
            # Check if browser context exists
            if not self.storage_state_file.exists():
                logger.info("Browser storage state file missing")
                return False
            
            logger.info(f"Valid session found, created: {created}")
            return True
            
        except Exception as e:
            logger.warning(f"Session validation failed: {e}")
            return False
    
    async def save_session(self, context) -> None:
        """Save browser session state"""
        
        try:
            # Save browser context storage state
            await context.storage_state(path=str(self.storage_state_file))
            
            # Save session metadata
            session_data = {
                "created": datetime.now().isoformat(),
                "jp_url": "https://ei-jp-ui.purplesky-a9615d9b.canadacentral.azurecontainerapps.io/",
                "status": "authenticated",
                "session_type": "microsoft_oauth"
            }
            
            with open(self.session_file, 'w') as f:
                json.dump(session_data, f, indent=2)
            
            logger.info("Session saved successfully")
            
        except Exception as e:
            logger.error(f"Failed to save session: {e}")
    
    async def load_session_context(self, browser):
        """Load existing session into browser context"""
        
        if not await self.has_valid_session():
            return None
        
        try:
            if self.storage_state_file.exists():
                context = await browser.new_context(
                    storage_state=str(self.storage_state_file),
                    viewport={'width': 1920, 'height': 1080}
                )
                logger.info("Browser context restored from session")
                return context
            else:
                logger.warning("Storage state file not found")
                return None
                
        except Exception as e:
            logger.error(f"Failed to load session context: {e}")
            return None
    
    async def verify_session_works(self, page) -> bool:
        """Verify that the session actually works by testing JP access"""
        
        try:
            jp_url = "https://ei-jp-ui.purplesky-a9615d9b.canadacentral.azurecontainerapps.io/"
            
            logger.info("Verifying session by accessing JP interface...")
            await page.goto(jp_url, wait_until="networkidle", timeout=30000)
            
            # Wait a bit for the page to load
            await asyncio.sleep(3)
            
            # Check if we're still on login page
            current_url = page.url
            page_content = await page.content()
            
            if "/login" in current_url or "Login to access the app" in page_content:
                logger.warning("Session verification failed - still on login page")
                return False
            
            # Look for chat interface elements
            try:
                # Try to find the chat input (various possible selectors)
                chat_selectors = [
                    'textarea[placeholder*="Ask me a question"]',
                    'textarea[placeholder*="question"]',
                    'input[placeholder*="Ask"]',
                    '.chat-input',
                    '[data-testid="chat-input"]',
                    'textarea:visible',
                    'input[type="text"]:visible'
                ]
                
                for selector in chat_selectors:
                    try:
                        element = await page.wait_for_selector(selector, timeout=5000)
                        if element:
                            logger.info(f"Chat interface found with selector: {selector}")
                            return True
                    except:
                        continue
                
                logger.warning("No chat interface elements found")
                return False
                
            except Exception as e:
                logger.error(f"Error checking for chat interface: {e}")
                return False
                
        except Exception as e:
            logger.error(f"Session verification error: {e}")
            return False
    
    async def cleanup_invalid_session(self):
        """Clean up invalid session files"""
        
        try:
            if self.session_file.exists():
                self.session_file.unlink()
                logger.info("Session metadata file removed")
            
            if self.context_dir.exists():
                shutil.rmtree(self.context_dir)
                self.context_dir.mkdir(exist_ok=True)
                logger.info("Browser context directory cleaned")
            
        except Exception as e:
            logger.error(f"Session cleanup error: {e}")


class EnhancedJPBrowserManager:
    """Enhanced browser manager with persistent session management"""
    
    def __init__(self, headless: bool = False, connect_url: Optional[str] = None):
        self.headless = headless
        self.connect_url = connect_url
        self.session_manager = JPSessionManager()
        
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        
    async def __aenter__(self):
        from playwright.async_api import async_playwright
        
        self.playwright = await async_playwright().start()
        
        # Handle CDP connection if provided
        if self.connect_url:
            try:
                self.browser = await self.playwright.chromium.connect_over_cdp(self.connect_url)
                logger.info(f"Connected to existing browser via CDP: {self.connect_url}")
            except Exception as e:
                logger.warning(f"CDP connection failed: {e}, launching new browser")
                self.connect_url = None
        
        # Launch new browser if CDP connection failed or not provided
        if not self.browser:
            self.browser = await self.playwright.chromium.launch(
                headless=self.headless,
                args=[
                    '--no-sandbox', 
                    '--disable-web-security',
                    '--disable-blink-features=AutomationControlled'
                ]
            )
            logger.info("New browser launched")
        
        # Try to load existing session
        self.context = await self.session_manager.load_session_context(self.browser)
        
        if self.context:
            logger.info("Using existing browser session")
            self.page = await self.context.new_page()
            
            # Verify session still works
            if await self.session_manager.verify_session_works(self.page):
                logger.info("Session verification successful - ready to process questions")
                return self
            else:
                logger.warning("Session verification failed - cleaning up")
                await self.context.close()
                await self.session_manager.cleanup_invalid_session()
                self.context = None
        
        # Create fresh context if no valid session
        if not self.context:
            logger.info("Creating fresh browser context")
            
            # If headless mode and no session, we have a problem
            if self.headless:
                logger.error("No valid session found and running in headless mode - authentication required")
                raise Exception(
                    "No valid authentication session found. Please run once in non-headless mode "
                    "to complete authentication, or ensure you have a valid saved session."
                )
            
            self.context = await self.browser.new_context(
                viewport={'width': 1920, 'height': 1080}
            )
            self.page = await self.context.new_page()
            
            # Navigate to JP and wait for automatic loading
            jp_url = "https://ei-jp-ui.purplesky-a9615d9b.canadacentral.azurecontainerapps.io/"
            await self.page.goto(jp_url)
            
            logger.info("Navigating to JP interface...")
            logger.info("(Auto-loading for pre-authorized user)")
            
            # Wait for authentication/loading to complete automatically
            await self.wait_for_authentication()
            
            # Save the session for future use
            await self.session_manager.save_session(self.context)
            logger.info("Authentication completed and session saved")
        
        return self
    
    async def wait_for_authentication(self, timeout_minutes: int = 8):
        """Wait for JP interface to load through automatic Microsoft authentication"""
        
        logger.info("Waiting for JP interface to load through automatic authentication...")
        logger.info("(Your email is pre-authorized - authentication should complete automatically)")
        
        max_wait = timeout_minutes * 60  # Convert to seconds
        wait_interval = 3  # Check every 3 seconds
        waited = 0
        last_url = ""
        
        while waited < max_wait:
            try:
                current_url = self.page.url
                
                # Log URL changes
                if current_url != last_url:
                    logger.info(f"Navigation: {current_url[:100]}...")
                    last_url = current_url
                
                # Handle different stages of Microsoft OAuth flow
                if "login.microsoftonline.com" in current_url:
                    logger.info("On Microsoft authentication page...")
                    await self._handle_microsoft_auth_page()
                    await asyncio.sleep(wait_interval)
                    waited += wait_interval
                    continue
                
                elif "/login" in current_url and "ei-jp-ui.purplesky" in current_url:
                    logger.info("On JP login page, looking for redirect...")
                    # Look for automatic redirect or Continue button
                    try:
                        continue_button = await self.page.query_selector('button:has-text("Continue"), a:has-text("Continue"), [class*="continue"], button[class*="login"]')
                        if continue_button and await continue_button.is_visible():
                            logger.info("Clicking continue button...")
                            await continue_button.click()
                            await asyncio.sleep(3)
                    except Exception:
                        pass
                    
                    await asyncio.sleep(wait_interval)
                    waited += wait_interval
                    continue
                
                elif "/auth/" in current_url or "/oauth/" in current_url:
                    logger.info("Processing OAuth callback...")
                    await asyncio.sleep(wait_interval)
                    waited += wait_interval
                    continue
                
                # Check if JP chat interface has loaded
                jp_interface_ready = await self._verify_jp_chat_interface()
                
                if jp_interface_ready:
                    logger.info("✅ JP chat interface loaded successfully!")
                    return
                
                # Log progress every 20 seconds
                if waited % 20 == 0 and waited > 0:
                    logger.info(f"Still waiting for authentication completion... ({waited}s elapsed)")
                
                await asyncio.sleep(wait_interval)
                waited += wait_interval
                
            except Exception as e:
                logger.warning(f"Error during authentication wait: {e}")
                await asyncio.sleep(wait_interval)
                waited += wait_interval
        
        # Timeout reached
        current_url = self.page.url
        raise Exception(f"JP interface failed to load after {timeout_minutes} minutes. Current URL: {current_url}")
    
    async def _handle_microsoft_auth_page(self):
        """Handle Microsoft authentication page for pre-authorized users"""
        try:
            current_url = self.page.url
            logger.debug(f"Handling Microsoft auth page: {current_url[:100]}...")
            
            # Wait a moment for page to fully load
            await asyncio.sleep(3)
            
            # Special handling for account selection page (prompt=select_account)
            if "prompt=select_account" in current_url:
                logger.info("On account selection page...")
                
                # Look for account tiles/buttons
                account_selectors = [
                    # Account tiles in modern Microsoft login
                    '[data-test-id*="account"]',
                    '.accountButton',
                    '.ms-Persona',
                    '.ms-Button--primary',
                    # Generic account selection elements
                    '[role="button"]:has([data-test-id*="name"])',
                    '[role="button"]:has-text("@")',  # Email addresses are often in account buttons
                    # Buttons with Continue or similar text
                    'button:has-text("Continue")',
                    'button:has-text("Accept")',
                    'button:has-text("Sign in")',
                    'button[type="submit"]',
                    'input[type="submit"]',
                    # Any visible primary buttons
                    '.ms-Button--primary:visible',
                    'button.primary:visible',
                    '[role="button"]:visible'
                ]
                
                for selector in account_selectors:
                    try:
                        elements = await self.page.query_selector_all(selector)
                        for element in elements:
                            if await element.is_visible() and await element.is_enabled():
                                # Get element text to see if it looks like an account
                                try:
                                    text_content = await element.text_content()
                                    if text_content:
                                        text_content = text_content.strip()
                                        logger.info(f"Found clickable element '{selector}': {text_content[:50]}...")
                                        
                                        # Click the first viable account/button
                                        await element.click()
                                        logger.info("Clicked account selection element")
                                        await asyncio.sleep(5)  # Wait for redirect
                                        return
                                except Exception as e:
                                    logger.debug(f"Could not get text from element: {e}")
                                    # Try clicking anyway if it's visible and enabled
                                    await element.click()
                                    logger.info(f"Clicked element: {selector}")
                                    await asyncio.sleep(5)
                                    return
                                    
                    except Exception as e:
                        logger.debug(f"Error with selector {selector}: {e}")
                        continue
            
            # Fallback for other auth pages
            else:
                logger.info("Looking for general auth buttons...")
                general_selectors = [
                    'button:has-text("Continue")',
                    'button:has-text("Accept")',
                    'button:has-text("Sign in")',
                    'input[type="submit"]',
                    '.ms-Button--primary:visible'
                ]
                
                for selector in general_selectors:
                    try:
                        element = await self.page.query_selector(selector)
                        if element and await element.is_visible():
                            logger.info(f"Clicking general auth button: {selector}")
                            await element.click()
                            await asyncio.sleep(5)
                            return
                    except Exception:
                        continue
            
            logger.info("No clickable auth elements found, waiting for manual interaction...")
            
        except Exception as e:
            logger.debug(f"Error handling Microsoft auth page: {e}")
    
    async def _verify_jp_chat_interface(self) -> bool:
        """Verify that JP chat interface is loaded and ready (for pre-authorized users)"""
        try:
            current_url = self.page.url
            logger.debug(f"Checking JP interface at: {current_url}")
            
            # Should be on JP UI domain
            if "ei-jp-ui.purplesky" not in current_url:
                logger.debug(f"Not on JP UI domain yet: {current_url}")
                return False
            
            # Should not be on login/auth pages
            if any(keyword in current_url.lower() for keyword in ["/login", "/auth", "/oauth", "microsoft.com"]):
                logger.debug(f"Still on auth/login page: {current_url}")
                return False
            
            # Wait a moment for any dynamic loading
            await asyncio.sleep(1)
            
            # Look for JP chat interface elements with expanded selectors
            chat_selectors = [
                # Text input areas
                'textarea[placeholder*="message"]',
                'textarea[placeholder*="question"]',
                'textarea[placeholder*="Ask"]',
                'textarea[placeholder*="type"]',
                'textarea[placeholder*="chat"]',
                # Input fields
                'input[placeholder*="message"]', 
                'input[placeholder*="question"]',
                'input[placeholder*="Ask"]',
                'input[placeholder*="type"]',
                'input[placeholder*="chat"]',
                # Generic visible inputs
                'textarea:visible',
                'input[type="text"]:visible',
                # Common chat UI classes
                '.chat-input',
                '.message-input',
                '.input-field',
                '[data-testid*="input"]',
                '[data-testid*="chat"]',
                '[role="textbox"]',
                # Send buttons (often appear with chat inputs)
                'button:has-text("Send")',
                'button[type="submit"]:visible'
            ]
            
            for selector in chat_selectors:
                try:
                    element = await self.page.wait_for_selector(selector, timeout=500)
                    if element:
                        is_visible = await element.is_visible()
                        is_enabled = await element.is_enabled()
                        if is_visible and is_enabled:
                            logger.debug(f"✅ Found active JP chat element: {selector}")
                            return True
                except Exception:
                    continue
            
            logger.debug("❌ No active JP chat elements found yet")
            return False
            
        except Exception as e:
            logger.debug(f"Error verifying JP interface: {e}")
            return False
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Clean up browser resources"""
        try:
            if self.context:
                await self.context.close()
            if self.browser and not self.connect_url:  # Don't close CDP-connected browsers
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
        except Exception as e:
            logger.error(f"Error during browser cleanup: {e}")


# Convenience function for backward compatibility
async def create_browser_manager(headless: bool = False, connect_url: Optional[str] = None):
    """Create and return a browser manager with session persistence"""
    return EnhancedJPBrowserManager(headless=headless, connect_url=connect_url)