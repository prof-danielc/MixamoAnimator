import os
import logging
import time
from pathlib import Path
from typing import Optional, List, Dict, Callable
import re
from playwright.sync_api import sync_playwright, Browser, BrowserContext, Page, Error as PlaywrightError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MixamoBot:
    """
    Automates interactions with the Mixamo website using Playwright.
    Handles authentication, character upload, and animation catalog management for the 2026 interface.
    """

    LOGIN_URL = "https://www.mixamo.com/"
    SESSION_FILE = "session.json"

    def __init__(self, headless: bool = False):
        self.headless = headless
        self._playwright = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        print(f"DEBUG: MixamoBot initialized (headless={headless})")

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

    def login(self, email: str, password: str) -> bool:
        print("DEBUG: RUNNING LATEST MIXAMO BOT VERSION 2026-03-23-FINAL-V31")
        if not self.page: self.start()

        def is_on_dashboard():
            return "mixamo.com/#/" in self.page.url and "login" not in self.page.url

        logger.info(f"Navigating to {self.LOGIN_URL}...")
        self.page.goto(self.LOGIN_URL)
        self.page.wait_for_load_state("domcontentloaded")

        if self.is_logged_in():
            logger.info("Automatically logged in.")
            return True

        try:
            login_btn = self.page.get_by_text("Log in", exact=False).first
            if login_btn.count() > 0 and login_btn.is_visible():
                logger.info("Clicking Log In button...")
                login_btn.click()
                self.page.wait_for_load_state("networkidle")

            if is_on_dashboard(): return True

            # Email step
            email_selector = 'input#EmailPage-EmailField, input[name="username"]'
            self.page.wait_for_selector(email_selector, timeout=20000)
            email_input = self.page.locator(email_selector).first
            email_input.click()
            email_input.press_sequentially(email, delay=100)
            email_input.press("Enter")
            
            # Transition
            for _ in range(20):
                if is_on_dashboard(): return True
                if self.page.get_by_text("Personal Account", exact=False).is_visible() or self.page.locator('input[type="password"]').is_visible():
                    break
                self.page.wait_for_timeout(2000)

            # Account select
            account_btn = self.page.get_by_text("Personal Account", exact=False).or_(self.page.get_by_text("Personal ID", exact=False)).first
            if account_btn.count() > 0 and account_btn.is_visible():
                account_btn.click()
                self.page.wait_for_timeout(3000)

            # Password step
            if is_on_dashboard(): return True
            password_input = self.page.locator('input[type="password"]').filter(visible=True).first
            if password_input.count() == 0: return is_on_dashboard()

            password_input.fill(password)
            password_input.press("Enter")
            
            self.page.wait_for_url(lambda url: "mixamo.com/#/" in url and "login" not in url, timeout=60000)
            logger.info("Login successful.")
            self._context.storage_state(path=self.SESSION_FILE)
            return True
        except Exception as e:
            if is_on_dashboard(): return True
            logger.error(f"Login failed: {e}"); return False

    def is_logged_in(self) -> bool:
        if not self.page: return False
        try:
            if "login" in self.page.url or "imsauth" in self.page.url: return False
            # Check for UPLOAD CHARACTER button
            if self.page.get_by_text("UPLOAD CHARACTER", exact=False).count() > 0:
                if self.page.get_by_text("UPLOAD CHARACTER", exact=False).first.is_visible():
                    return True
            return "mixamo.com/#/" in self.page.url and self.page.get_by_text("Log in", exact=False).count() == 0
        except: return False

    def upload_character(self, file_path: str) -> bool:
        if not self.page: self.start()
        try:
            logger.info(f"Uploading: {file_path}")
            self.page.goto("https://www.mixamo.com/#/?page=1&query=&type=Character")
            self.page.wait_for_load_state("networkidle", timeout=30000)
            self.page.wait_for_timeout(5000)

            upload_btn = self.page.get_by_text("UPLOAD CHARACTER", exact=False).first
            if not upload_btn.is_visible():
                for f in self.page.frames:
                    loc = f.get_by_text("UPLOAD CHARACTER", exact=False).first
                    if loc.is_visible(): upload_btn = loc; break
            
            if not (upload_btn and upload_btn.is_visible()): return False

            # Set file logic
            input_found = False
            for attempt in range(15):
                for f in self.page.frames:
                    inp = f.locator('input[type="file"]').first
                    if inp.count() > 0:
                        inp.set_input_files(file_path); input_found = True; break
                if input_found: break
                if attempt == 0 or attempt == 5: upload_btn.click(force=True)
                self.page.wait_for_timeout(3000)
            
            if not input_found: return False

            # Wizard
            def click_next(timeout):
                end = self.page.evaluate("Date.now()") + timeout
                while self.page.evaluate("Date.now()") < end:
                    for f in self.page.frames:
                        for s in ['button:has-text("Next")', 'button:has-text("Finish")', 'text="Next"']:
                            try:
                                l = f.locator(s).first
                                if l.is_visible() and l.is_enabled():
                                    l.click(); return True
                            except: continue
                    self.page.wait_for_timeout(5000)
                return False

            if not click_next(180000): return False
            click_next(45000); self.page.wait_for_timeout(3000); click_next(45000)
            logger.info("Upload complete.")
            return True
        except: return False

    def fetch_animation_catalog(self, limit: int = 50) -> List[Dict]:
        """
        Scrapes the animation catalog by iterating through pages.
        Each page contains ~48 animations.
        """
        if not self.page: self.start()
        try:
            animations = []
            page_num = 1
            
            logger.info(f"Fetching up to {limit} animations via pagination...")
            
            while len(animations) < limit:
                url = f"https://www.mixamo.com/#/?page={page_num}&type=Motion"
                logger.info(f"Navigating to page {page_num}: {url}")
                
                self.page.goto(url)
                self.page.wait_for_load_state("networkidle", timeout=30000)
                self.page.wait_for_timeout(5000) # Let SPA settle
                
                selectors = ['.product', '.animation-card', '[data-product-id]']
                found_on_page = []
                
                for f in self.page.frames:
                    for sel in selectors:
                        try:
                            cards = f.locator(sel).all()
                            for card in cards:
                                # Filter motions only
                                cl = card.get_attribute('class') or ""
                                if 'character' in cl.lower() and 'motion' not in cl.lower(): continue
                                
                                pid = card.get_attribute('data-product-id')
                                if not pid:
                                    img = card.locator('img').first
                                    if img.count() > 0:
                                        src = img.get_attribute('src')
                                        m = re.search(r'motions/(\d+)/', src)
                                        if m: pid = m.group(1)
                                
                                if pid and not any(a['id'] == pid for a in animations):
                                    name = "Unknown"
                                    for ns in ['p', 'h3', 'b']:
                                        el = card.locator(ns).first
                                        if el.count() > 0:
                                            t = el.inner_text().strip()
                                            if t: name = t; break
                                    
                                    animations.append({"id": pid, "name": name})
                                    found_on_page.append(pid)
                                    
                                    if len(animations) >= limit:
                                        break
                                if len(animations) >= limit: break
                            if len(animations) >= limit: break
                        except: continue
                    if len(animations) >= limit: break
                
                logger.info(f"Page {page_num} processed. Total found: {len(animations)}/{limit}")
                
                if not found_on_page:
                    logger.info("No new animations found on this page. Reached end of catalog.")
                    break
                
                page_num += 1
                if page_num > 100: # Safety break
                    break

            logger.info(f"Successfully fetched {len(animations)} animations.")
            return animations
        except Exception as e:
            logger.error(f"Catalog failed: {e}")
            return []

    def download_animations(self, selected_anims: List[Dict[str, str]], output_dir: str, progress_callback: Optional[Callable] = None) -> Dict[str, bool]:
        """
        Batch downloads animations.
        progress_callback: function(current_index, total_count, current_anim_name, eta_seconds)
        """
        if not self.page: self.start()
        os.makedirs(output_dir, exist_ok=True)
        results = {}
        total_count = len(selected_anims)
        download_times = []
        
        for i, anim in enumerate(selected_anims):
            start_time = time.time()
            aid = anim['id']
            aname = anim['name']
            
            # Calculate ETA
            eta_seconds = 0
            if download_times:
                avg_time = sum(download_times) / len(download_times)
                eta_seconds = int(avg_time * (total_count - i))
            
            # Report progress
            if progress_callback:
                progress_callback(i + 1, total_count, aname, eta_seconds)
            
            try:
                logger.info(f"Downloading {i+1}/{total_count}: {aname} ({aid})")
                self.page.goto(f"https://www.mixamo.com/#/?page=1&query=&type=Motion%2CCharacter&product_id={aid}")
                self.page.wait_for_load_state("networkidle", timeout=30000)
                
                # Download button
                dl_btn = self.page.get_by_text("Download", exact=False).first
                if not dl_btn.is_visible():
                    for f in self.page.frames:
                        loc = f.get_by_text("Download", exact=False).first
                        if loc.is_visible(): dl_btn = loc; break
                if not (dl_btn and dl_btn.is_visible()): 
                    logger.error(f"Download button not found for {aname}")
                    results[aid] = False; continue
                
                dl_btn.click()
                
                # Modal Download
                m_btn = None
                for _ in range(10):
                    for f in self.page.frames:
                        try:
                            loc = f.locator('.modal-footer').get_by_text("Download", exact=False).first
                            if loc.count() > 0 and loc.is_visible(): m_btn = loc; break
                        except: continue
                    if m_btn: break
                    self.page.wait_for_timeout(2000)
                
                if not m_btn: 
                    logger.error(f"Modal download button not found for {aname}")
                    results[aid] = False; continue
                
                with self.page.expect_download(timeout=60000) as d_info:
                    m_btn.click()
                
                download = d_info.value
                orig_filename = download.suggested_filename
                base, ext = os.path.splitext(orig_filename)
                
                # Sanitize name
                safe_name = "".join([c for c in aname if c.isalnum() or c in (' ', '_', '-')]).strip().replace(' ', '_')
                
                # Construct unique filename (Collision Fix)
                new_filename = f"{base}_{safe_name}{ext}"
                path = os.path.join(output_dir, new_filename)
                
                counter = 1
                while os.path.exists(path):
                    new_filename = f"{base}_{safe_name}_{counter}{ext}"
                    path = os.path.join(output_dir, new_filename)
                    counter += 1
                
                download.save_as(path)
                logger.info(f"Saved: {path}")
                results[aid] = True
                
                # Record time taken for ETA
                download_times.append(time.time() - start_time)
                
            except Exception as e:
                logger.error(f"Failed {aname}: {e}")
                results[aid] = False
                
        return results

    def __enter__(self): self.start(); return self
    def __exit__(self, x, y, z): self.stop()
