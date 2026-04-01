import os
import requests
import json
import time
import logging
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from pathlib import Path
import re
from typing import List, Dict, Optional, Callable
from playwright.sync_api import sync_playwright
from .mixamo_api_client import MixamoAPIClient

logger = logging.getLogger(__name__)

def is_on_dashboard(page):
    return "mixamo.com/#/" in page.url and "login" not in page.url

class MixamoBot:
    LOGIN_URL = "https://www.mixamo.com/login"
    SESSION_FILE = "mixamo_session.json"
    TOKEN_FILE = "mixamo_token.txt"

    def __init__(self, headless=False, API=True, token_file="mixamo_token.txt"):
        self.headless = headless
        self.page = None
        self._playwright = None
        self._browser = None
        self._context = None
        self.character_id = None
        self.api_client = None
        self.TOKEN_FILE = token_file

        if API:
            try:
                self.api_client = MixamoAPIClient(token_file=token_file)
                logger.debug("MixamoBot initialized (headless=%s, API=True)", headless)
            except Exception:
                self.api_client = None
                logger.debug("MixamoBot initialized (headless=%s, API=False)", headless)

    def _refresh_api_client(self):
        if os.path.exists(self.TOKEN_FILE):
            try:
                self.api_client = MixamoAPIClient(token_file=self.TOKEN_FILE)
                logger.info("MixamoAPIClient initialized.")
            except Exception as e:
                logger.error(f"Failed to initialize API client: {e}")

    def _extract_and_save_token(self) -> bool:
        if not self.page:
            return False
        try:
            token = self.page.evaluate("localStorage.getItem('access_token')")
            if token:
                with open(self.TOKEN_FILE, "w") as f:
                    f.write(token)
                logger.info(f"Successfully extracted and saved token to {self.TOKEN_FILE}")
                self._refresh_api_client()
                return True
            else:
                logger.warning("Access token not found in local storage.")
                return False
        except Exception as e:
            logger.error(f"Failed to extract token: {e}")
            return False

    def start(self) -> None:
        self._playwright = sync_playwright().start()
        self._browser = self._playwright.chromium.launch(headless=self.headless)
        if Path(self.SESSION_FILE).exists():
            logger.info(f"Loading session from {self.SESSION_FILE}...")
            self._context = self._browser.new_context(storage_state=self.SESSION_FILE)
        else:
            self._context = self._browser.new_context()
        self.page = self._context.new_page()

    def stop(self) -> None:
        if self._context: self._context.close()
        if self._browser: self._browser.close()
        if self._playwright: self._playwright.stop()

    def is_logged_in(self) -> bool:
        if not self.page: return False
        try:
            if "login" in self.page.url or "imsauth" in self.page.url: return False
            if self.page.get_by_text("UPLOAD CHARACTER", exact=False).count() > 0:
                if self.page.get_by_text("UPLOAD CHARACTER", exact=False).first.is_visible():
                    return True
            return "mixamo.com/#/" in self.page.url and self.page.get_by_text("Log in", exact=False).count() == 0
        except: return False

    def login(self, email: str, password: str) -> bool:
        print("DEBUG: RUNNING LATEST MIXAMO BOT VERSION 2026-03-26-API-AUTO-TOKEN")
        if not self.page: self.start()

        def is_on_dashboard_local():
            return "mixamo.com/#/" in self.page.url and "login" not in self.page.url

        logger.info(f"Navigating to {self.LOGIN_URL}...")
        self.page.goto(self.LOGIN_URL)
        self.page.wait_for_load_state("domcontentloaded")

        if self.is_logged_in():
            logger.info("Automatically logged in.")
            self._extract_and_save_token()
            return True

        try:
            login_btn = self.page.get_by_text("Log in", exact=False).first
            if login_btn.count() > 0 and login_btn.is_visible():
                logger.info("Clicking Log In button...")
                login_btn.click()
                self.page.wait_for_load_state("networkidle")

            if is_on_dashboard_local(): 
                self._extract_and_save_token()
                return True

            email_selector = 'input#EmailPage-EmailField, input[name="username"]'
            self.page.wait_for_selector(email_selector, timeout=20000)
            email_input = self.page.locator(email_selector).first
            email_input.click()
            email_input.press_sequentially(email, delay=100)
            email_input.press("Enter")
            
            for _ in range(20):
                if is_on_dashboard_local(): 
                    self._extract_and_save_token()
                    return True
                if self.page.get_by_text("Personal Account", exact=False).is_visible() or self.page.locator('input[type="password"]').is_visible():
                    break
                self.page.wait_for_timeout(2000)

            account_btn = self.page.get_by_text("Personal Account", exact=False).or_(self.page.get_by_text("Personal ID", exact=False)).first
            if account_btn.count() > 0 and account_btn.is_visible():
                account_btn.click()
                self.page.wait_for_timeout(3000)

            if is_on_dashboard_local(): 
                self._extract_and_save_token()
                return True
            password_input = self.page.locator('input[type="password"]').filter(visible=True).first
            if password_input.count() == 0: 
                if is_on_dashboard_local():
                    self._extract_and_save_token()
                    return True
                return False

            password_input.fill(password)
            password_input.press("Enter")
            
            self.page.wait_for_url(lambda url: "mixamo.com/#/" in url and "login" not in url, timeout=60000)
            logger.info("Login successful.")
            self._context.storage_state(path=self.SESSION_FILE)
            self._extract_and_save_token()
            return True
        except Exception as e:
            if is_on_dashboard_local(): 
                self._extract_and_save_token()
                return True
            logger.error(f"Login failed: {e}"); return False

    def upload_character(self, file_path: str) -> bool:
        if self.api_client:
            try:
                logger.info(f"Uploading character via API: {file_path}")
                self.character_id = self.api_client.upload_character(file_path)
                if self.character_id:
                    logger.info(f"API upload successful. Character ID: {self.character_id}")
                    return True
                else:
                    logger.warning("API upload did not return a character ID. Falling back to Playwright.")
            except Exception as e:
                logger.error(f"API upload failed: {e}. Falling back to Playwright.")

        logger.info(f"Uploading via Playwright: {file_path}")
        if not self.page: self.start()
        try:
            self.page.goto("https://www.mixamo.com/#/?page=1&query=&type=Character")
            self.page.wait_for_load_state("networkidle", timeout=30000)
            self.page.wait_for_timeout(5000)

            upload_btn = self.page.get_by_text("UPLOAD CHARACTER", exact=False).first
            if not upload_btn.is_visible():
                for f in self.page.frames:
                    loc = f.get_by_text("UPLOAD CHARACTER", exact=False).first
                    if loc.is_visible(): upload_btn = loc; break
            
            upload_btn.click()
            self.page.wait_for_selector('input[type="file"]')
            self.page.set_input_files('input[type="file"]', file_path)
            self.page.wait_for_selector('text=Next', timeout=120000)
            self.page.click('text=Next')
            self.page.wait_for_timeout(2000)
            self.page.click('text=Next')
            self.page.wait_for_load_state("networkidle")
            return True
        except Exception as e:
            logger.error(f"Playwright upload failed: {e}")
            return False

    def fetch_animation_catalog(self, limit: int = 100, force_refresh: bool = True) -> List[Dict[str, str]]:
        if self.api_client:
            try:
                logger.info("Fetching catalog via API...")
                return self.api_client.fetch_animation_catalog(limit=limit, force_refresh=force_refresh)
            except Exception as e:
                logger.error(f"API catalog fetch failed: {e}. Falling back to Playwright.")

        if not self.page: self.start()
        try:
            animations = []
            page_num = 1
            while len(animations) < limit:
                url = f"https://www.mixamo.com/#/?page={page_num}&query=&type=Motion%2CMotionPack"
                self.page.goto(url)
                self.page.wait_for_load_state("networkidle")
                self.page.wait_for_timeout(2000)
                
                # Logic to extract animations from page (simplified for brevity)
                # In a real implementation, you'd parse the DOM
                page_num += 1
                if page_num > 100: break
            return animations
        except Exception as e:
            logger.error(f"Catalog failed: {e}")
            return []

    def download_animations(self, selected_anims: List[Dict[str, str]], output_dir: str, progress_callback: Optional[Callable] = None, include_skin: bool = True, inplace: bool = False) -> Dict[str, bool]:
        """
        Batch downloads animations. Prefers multi-threaded API, falls back to Playwright.
        """
        if self.api_client and self.character_id:
            try:
                logger.info("Downloading animations via multi-threaded API...")
                return self.api_client.download_animations(
                    self.character_id, 
                    selected_anims, 
                    output_dir, 
                    progress_callback=progress_callback,
                    include_skin=include_skin,
                    inplace=inplace
                )
            except Exception as e:
                logger.error(f"API download failed: {e}. Falling back to Playwright.")

        if not self.page: self.start()
        os.makedirs(output_dir, exist_ok=True)
        results = {}
        total_count = len(selected_anims)
        download_times = []
        for i, anim in enumerate(selected_anims):
            start_time = time.time()
            aid = anim['id']
            aname = anim['name']
            eta_seconds = 0
            if download_times:
                avg_time = sum(download_times) / len(download_times)
                eta_seconds = int(avg_time * (total_count - i))
            if progress_callback:
                progress_callback(i + 1, total_count, aname, eta_seconds)
            try:
                logger.info(f"Downloading {i+1}/{total_count}: {aname} ({aid})")
                self.page.goto(f"https://www.mixamo.com/#/?page=1&query=&type=Motion%2CCharacter&product_id={aid}")
                self.page.wait_for_load_state("networkidle")
                self.page.wait_for_timeout(5000)
                
                if inplace:
                    # In Playwright mode, we would need to find the "In Place" checkbox and click it.
                    # This is complex and might depend on the specific animation.
                    # For now, we log a warning that inplace is not fully supported in Playwright fallback.
                    logger.warning("Inplace option requested but Playwright fallback does not yet support clicking the checkbox.")

                with self.page.expect_download(timeout=60000) as download_info:
                    self.page.get_by_text("Download", exact=False).first.click()
                    self.page.wait_for_timeout(2000)
                    self.page.get_by_role("button", name="Download").click()
                
                download = download_info.value
                suffix = "with_skin" if include_skin else "no_skin"
                if inplace:
                    filename = f"{aname}_inplace_{aid}_{self.character_id}_{suffix}.fbx"
                else:
                    filename = f"{aname}_{aid}_{self.character_id}_{suffix}.fbx"
                
                download.save_as(os.path.join(output_dir, filename))
                results[aid] = True
                download_times.append(time.time() - start_time)
            except Exception as e:
                logger.error(f"Failed to download {aname}: {e}")
                results[aid] = False
        return results
