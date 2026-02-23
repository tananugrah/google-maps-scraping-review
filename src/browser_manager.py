import random
from playwright.sync_api import sync_playwright
from fake_useragent import UserAgent
import os
from src.logger_handler import setup_logger

logger = setup_logger()

class BrowserManager:
    def __init__(self, headless=True):
        self.headless = headless
        self.ua = UserAgent()
        self.browser = None
        self.context = None
        self.page = None

    def start_browser(self):
        """Starts a fresh browser instance with anti-detection args."""
        try:
            pw = sync_playwright().start()
            self.browser = pw.chromium.launch(
                headless=self.headless,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-infobars",
                    "--window-position=0,0",
                    "--ignore-certifcate-errors",
                    "--ignore-certifcate-errors-spki-list",
                    "--user-agent=" + self.ua.random
                ]
            )
            
            # Context randomization
            viewport_width = random.randint(1280, 1920)
            viewport_height = random.randint(720, 1080)
            
            self.context = self.browser.new_context(
                viewport={'width': viewport_width, 'height': viewport_height},
                user_agent=self.ua.random
            )
            
            # Initial stealth scripts could be added here if needed
            self.page = self.context.new_page()
            
            # Hide automation traces
            self.page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            logger.info(f"Browser started successfully. Viewport: {viewport_width}x{viewport_height}")
            return self.page
        except Exception as e:
            logger.error(f"Failed to start browser: {e}")
            raise

    def close_browser(self):
        """Closes the browser instance."""
        if self.browser:
            self.browser.close()
            logger.info("Browser closed.")

    def get_new_context(self):
        """Creates a fresh context to clear session data."""
        if self.context:
            self.context.close()
        
        viewport_width = random.randint(1280, 1920)
        viewport_height = random.randint(720, 1080)
        
        self.context = self.browser.new_context(
            viewport={'width': viewport_width, 'height': viewport_height},
            user_agent=self.ua.random
        )
        self.page = self.context.new_page()
        self.page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        logger.info(f"Fresh context created. Viewport: {viewport_width}x{viewport_height}")
        return self.page
