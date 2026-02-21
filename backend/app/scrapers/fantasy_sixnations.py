"""
Fantasy Six Nations scraper for player roster and prices using Playwright.

Opens a visible browser window so the user can log in manually,
then scrapes the rendered DOM to extract the full player roster
with prices, positions, countries, and ownership percentages.

Paginates through all pages of the player list.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path
import logging
import asyncio
import re

from playwright.async_api import (
    async_playwright,
    Page,
    Browser,
    BrowserContext,
)

from app.scrapers.base import BaseScraper

logger = logging.getLogger(__name__)

# Position mapping from fantasy site labels to our DB positions
POSITION_MAP = {
    # Forwards
    "loosehead prop": "prop",
    "tighthead prop": "prop",
    "prop": "prop",
    "hooker": "hooker",
    "lock": "second_row",
    "second row": "second_row",
    "2nd row": "second_row",
    "blindside flanker": "back_row",
    "openside flanker": "back_row",
    "flanker": "back_row",
    "number 8": "back_row",
    "no. 8": "back_row",
    "back row": "back_row",
    "back-row": "back_row",
    # Backs
    "scrum-half": "scrum_half",
    "scrum half": "scrum_half",
    "fly-half": "out_half",
    "fly half": "out_half",
    "out-half": "out_half",
    "out half": "out_half",
    "centre": "centre",
    "inside centre": "centre",
    "outside centre": "centre",
    "wing": "back_3",
    "winger": "back_3",
    "full-back": "back_3",
    "fullback": "back_3",
    "full back": "back_3",
    "back three": "back_3",
    "back 3": "back_3",
}

COUNTRY_MAP = {
    "ire": "Ireland",
    "ireland": "Ireland",
    "eng": "England",
    "england": "England",
    "fra": "France",
    "france": "France",
    "wal": "Wales",
    "wales": "Wales",
    "sco": "Scotland",
    "scotland": "Scotland",
    "ita": "Italy",
    "italy": "Italy",
}

# Also extract country from team image URLs
COUNTRY_FROM_IMAGE = {
    "ireland": "Ireland",
    "england": "England",
    "france": "France",
    "wales": "Wales",
    "scotland": "Scotland",
    "italy": "Italy",
}

BASE_URL = "https://fantasy.sixnationsrugby.com"
GAME_URL = f"{BASE_URL}/m6n/#/game/play/me"


class SessionExpiredError(Exception):
    """Raised when headless scrape fails because no valid session exists."""
    pass

# Default path for persisted browser session (cookies + localStorage)
DEFAULT_SESSION_PATH = Path(__file__).parent.parent.parent / "data" / "session_state.json"

# Availability CSS class suffix → raw label
# The site uses French: T=Titulaire (starting), R=Remplaçant (sub)
FORME_CLASS_MAP = {
    "T": "starting",
    "R": "substitute",
    "N": "not_playing",   # unconfirmed letter — will log unknowns
    "X": "not_playing",
}


class FantasySixNationsScraper(BaseScraper):
    """
    Scraper for Fantasy Six Nations player roster and prices.

    Strategy:
    1. Open headed browser so user can log in
    2. Wait for game page with player list to load
    3. Scrape all sportif-item elements on each page
    4. Paginate through all pages using the next button

    Session persistence:
    - After a successful login the browser storage state (cookies +
      localStorage) is saved to ``session_path``.
    - On the next run the saved state is restored so login is automatic.
    - If the saved session is stale the scraper falls back to manual login.
    """

    LOGIN_WAIT_TIMEOUT = 300  # 5 minutes max to wait for login
    SESSION_CHECK_TIMEOUT = 30  # seconds to wait before declaring session stale

    def __init__(self, headless: bool = False, session_path: Optional[Path] = None):
        self._browser: Optional[Browser] = None
        self._playwright = None
        self._headless = headless
        self._session_path = session_path or DEFAULT_SESSION_PATH

    async def _init_browser(self) -> Browser:
        """Initialize Playwright browser."""
        self._playwright = await async_playwright().start()
        browser = await self._playwright.chromium.launch(
            headless=self._headless,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--start-maximized",
            ],
        )
        return browser

    async def _close_browser(self):
        """Clean up browser resources."""
        if self._browser:
            await self._browser.close()
            self._browser = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None

    async def _create_context(
        self, browser: Browser, storage_state: Optional[str] = None,
    ) -> BrowserContext:
        """Create browser context with realistic settings, optionally restoring session."""
        kwargs: Dict[str, Any] = dict(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1920, "height": 1080},
            java_script_enabled=True,
            no_viewport=True,
        )
        if storage_state:
            kwargs["storage_state"] = storage_state
        context = await browser.new_context(**kwargs)
        return context

    async def _save_session(self, context: BrowserContext):
        """Persist browser storage state (cookies + localStorage) to disk."""
        try:
            self._session_path.parent.mkdir(parents=True, exist_ok=True)
            await context.storage_state(path=str(self._session_path))
            logger.info(f"Session saved to {self._session_path}")
            print(f"Session saved to {self._session_path}")
        except Exception as e:
            logger.warning(f"Failed to save session: {e}")

    def _has_saved_session(self) -> bool:
        return self._session_path.exists() and self._session_path.stat().st_size > 0

    async def scrape(self, url: str = GAME_URL, **kwargs) -> Dict[str, Any]:
        """
        Open browser, wait for login, then scrape all players across all pages.

        If a saved session exists it is restored first.  When the session is
        stale the browser context is recreated without the old state so the
        user can log in manually.
        """
        # Fail fast in headless mode if there's no saved session to restore
        if self._headless and not self._has_saved_session():
            raise SessionExpiredError(
                "No saved session — run scrape_fantasy_prices.py to log in first"
            )

        self._browser = await self._init_browser()

        try:
            # --- try restoring a saved session first ---
            context: Optional[BrowserContext] = None
            page: Optional[Page] = None
            logged_in = False

            if self._has_saved_session():
                print("\nRestoring saved session...")
                logger.info("Restoring saved session")
                context = await self._create_context(
                    self._browser, storage_state=str(self._session_path),
                )
                page = await context.new_page()
                await page.goto(url, wait_until="domcontentloaded", timeout=60000)
                await self._dismiss_overlays(page)

                # Quick check: does the player list appear within a short timeout?
                try:
                    await self._wait_for_player_list(
                        page, timeout=self.SESSION_CHECK_TIMEOUT,
                    )
                    logged_in = True
                    print("Saved session is valid — skipping login.")
                except TimeoutError:
                    print("Saved session expired — falling back to manual login.")
                    logger.info("Saved session stale, will prompt for manual login")
                    await page.close()
                    await context.close()
                    context = None
                    page = None

            # --- fresh context (manual login) ---
            if not logged_in:
                if self._headless:
                    raise SessionExpiredError(
                        "Saved session expired — run scrape_fantasy_prices.py to log in again"
                    )
                context = await self._create_context(self._browser)
                page = await context.new_page()

                logger.info(f"Navigating to {url}")
                print("\n" + "=" * 60)
                print("FANTASY SIX NATIONS SCRAPER")
                print("=" * 60)
                print(f"\nNavigating to: {url}")
                print("\nPlease log in to your Fantasy Six Nations account.")
                print("The scraper will start once the player list is visible.")
                print("=" * 60 + "\n")

                await page.goto(url, wait_until="domcontentloaded", timeout=60000)
                await self._dismiss_overlays(page)
                await self._wait_for_player_list(page)

            # Save session for next time (after successful login / session restore)
            await self._save_session(context)

            # Dismiss overlays again (OAuth redirect can bring them back)
            await self._dismiss_overlays(page)

            # Scrape all pages
            all_players = await self._scrape_all_pages(page)

            logger.info(f"Scraped {len(all_players)} total players")

            result = {
                "source": "fantasy_sixnations",
                "url": url,
                "scraped_at": datetime.utcnow().isoformat(),
                "dom_players": all_players,
            }

        except Exception as e:
            logger.error(f"Error during scrape: {e}", exc_info=True)
            raise
        finally:
            print("\nScraping complete. Closing browser...")
            try:
                await asyncio.wait_for(self._close_browser(), timeout=10)
            except Exception:
                logger.warning("Browser cleanup timed out, forcing close")
                self._browser = None
                self._playwright = None

        return result

    async def _dismiss_overlays(self, page: Page):
        """Dismiss cookie consent banners and other overlays."""
        await asyncio.sleep(2)

        overlay_selectors = [
            'button:has-text("Accept")',
            'button:has-text("Accept All")',
            'button:has-text("Accept all")',
            'button:has-text("OK")',
            'button:has-text("Got it")',
            '#onetrust-accept-btn-handler',
            '.cc-btn.cc-allow',
            '#didomi-notice-agree-button',
        ]

        for selector in overlay_selectors:
            try:
                elem = await page.query_selector(selector)
                if elem and await elem.is_visible():
                    await elem.click()
                    logger.info(f"Dismissed overlay: {selector}")
                    print(f"Dismissed overlay: {selector}")
                    await asyncio.sleep(1)
                    return
            except Exception:
                continue

        # Try iframes
        try:
            for frame in page.frames:
                if frame == page.main_frame:
                    continue
                for selector in overlay_selectors:
                    try:
                        elem = await frame.query_selector(selector)
                        if elem and await elem.is_visible():
                            await elem.click()
                            logger.info(f"Dismissed overlay in iframe: {selector}")
                            await asyncio.sleep(1)
                            return
                    except Exception:
                        continue
        except Exception:
            pass

    async def _wait_for_player_list(self, page: Page, timeout: Optional[int] = None):
        """Wait for user to log in and the player list to be visible."""
        wait_seconds = timeout or self.LOGIN_WAIT_TIMEOUT
        print("Waiting for login and player list to load...")

        for i in range(wait_seconds):
            await asyncio.sleep(1)

            try:
                # Check if sportif-item elements are present (the player cards)
                items = await page.query_selector_all("sportif-item")
                if len(items) > 0:
                    logger.info(f"Player list detected with {len(items)} items on first page")
                    print(f"Player list loaded! Found {len(items)} players on current page.")
                    await asyncio.sleep(2)  # Let it fully render
                    return

                # Also check for the player list container
                container = await page.query_selector(".ctr-list-sportifs")
                if container:
                    await asyncio.sleep(2)
                    items = await page.query_selector_all("sportif-item")
                    if len(items) > 0:
                        logger.info(f"Player list detected with {len(items)} items")
                        print(f"Player list loaded! Found {len(items)} players on current page.")
                        return
            except Exception:
                # Page navigation (e.g. OAuth redirect) destroys the execution context.
                # This is expected during login - just keep waiting.
                pass

            # Periodically try to dismiss overlays that reappear after login redirect
            if i > 0 and i % 5 == 0:
                try:
                    for sel in ['button:has-text("Accept")', 'button:has-text("Accept All")', '#onetrust-accept-btn-handler']:
                        elem = await page.query_selector(sel)
                        if elem and await elem.is_visible():
                            await elem.click()
                            print(f"Dismissed overlay: {sel}")
                            await asyncio.sleep(1)
                            break
                except Exception:
                    pass

            if i > 0 and i % 30 == 0:
                print(f"Still waiting for login/player list... ({i}s elapsed)")

        raise TimeoutError(
            f"Timed out after {wait_seconds}s waiting for player list"
        )

    async def _scrape_all_pages(self, page: Page) -> List[Dict[str, Any]]:
        """Scrape player data from all pages by clicking the next button."""
        all_players = []
        page_num = 1
        previous_first_name = None

        while True:
            # Scrape current page
            page_players = await self._scrape_current_page(page)
            all_players.extend(page_players)

            current_first_name = page_players[0]["name"] if page_players else None
            print(f"  Page {page_num}: scraped {len(page_players)} players (total: {len(all_players)})")

            # Try to go to next page
            has_next = await self._go_to_next_page(page)
            if not has_next:
                print(f"Reached last page ({page_num}).")
                break

            page_num += 1

            # Wait for the new page to render
            await asyncio.sleep(1.5)

            # Check if the page actually changed (same first player = stuck)
            try:
                new_items = await page.query_selector_all("sportif-item")
                if new_items:
                    name_elem = await new_items[0].query_selector(".nom-sportif")
                    if name_elem:
                        new_first_name = (await name_elem.inner_text()).strip()
                        if new_first_name == current_first_name:
                            print(f"Page content unchanged - reached end at page {page_num - 1}.")
                            break
            except Exception:
                pass

            # Safety limit
            if page_num > 300:
                logger.warning("Hit page limit of 300, stopping pagination")
                break

        return all_players

    async def _scrape_current_page(self, page: Page) -> List[Dict[str, Any]]:
        """Scrape all sportif-item elements on the current page."""
        players = []

        items = await page.query_selector_all("sportif-item")
        for item in items:
            player = await self._extract_player(item)
            if player:
                players.append(player)

        return players

    async def _extract_player(self, elem) -> Optional[Dict[str, Any]]:
        """Extract player data from a sportif-item element."""
        try:
            # Name: .nom-sportif
            name = None
            name_elem = await elem.query_selector(".nom-sportif")
            if name_elem:
                name = (await name_elem.inner_text()).strip()

            if not name:
                return None

            # Position: .position
            position = None
            pos_elem = await elem.query_selector(".position")
            if pos_elem:
                position = (await pos_elem.inner_text()).strip()

            # Country: .info-match-club.club-sportif
            country = None
            country_elem = await elem.query_selector(".info-match-club.club-sportif")
            if country_elem:
                country = (await country_elem.inner_text()).strip()

            # If country not found from text, try from image URL
            if not country:
                img_elem = await elem.query_selector("img.image-sportif")
                if img_elem:
                    src = await img_elem.get_attribute("src") or ""
                    for key, val in COUNTRY_FROM_IMAGE.items():
                        if key in src.lower():
                            country = val
                            break

            # Price: .valeur-sportif-nb
            price = None
            price_elem = await elem.query_selector(".valeur-sportif-nb")
            if price_elem:
                price_text = (await price_elem.inner_text()).strip()
                try:
                    price = float(price_text)
                except ValueError:
                    price_match = re.search(r'[\d.]+', price_text)
                    if price_match:
                        price = float(price_match.group())

            # Ownership %: .sportif-data-value-pourcentage
            ownership_pct = None
            pct_elem = await elem.query_selector(".sportif-data-value-pourcentage")
            if pct_elem:
                pct_text = (await pct_elem.inner_text()).strip()
                try:
                    ownership_pct = float(pct_text)
                except ValueError:
                    pct_match = re.search(r'[\d.]+', pct_text)
                    if pct_match:
                        ownership_pct = float(pct_match.group())

            # Opponent info
            opponent = None
            opp_elem = await elem.query_selector(".info-match-club.club-adversaire span")
            if opp_elem:
                opponent = (await opp_elem.inner_text()).strip()

            # Home/away: check for flight_takeoff (away) or home icon
            is_home = None
            icon_elem = await elem.query_selector(".info-match-club.club-adversaire mat-icon")
            if icon_elem:
                icon_text = (await icon_elem.inner_text()).strip()
                if "home" in icon_text:
                    is_home = True
                elif "flight_takeoff" in icon_text:
                    is_home = False

            # Availability indicator: CSS class "forme forme-X" on the
            # indicator div inside sportif-infos-forme.
            # X = T (Titulaire/starting), R (Remplaçant/sub), etc.
            availability = None
            forme_elem = await elem.query_selector("sportif-infos-forme .forme")
            if forme_elem:
                forme_classes = (await forme_elem.get_attribute("class") or "").split()
                for cls in forme_classes:
                    if cls.startswith("forme-") and cls != "forme":
                        suffix = cls.split("-", 1)[1]
                        availability = FORME_CLASS_MAP.get(suffix)
                        if availability is None:
                            logger.warning(f"Unknown forme class suffix: {suffix!r}")
                        break

            return {
                "name": name,
                "position": position,
                "country": country,
                "price": price,
                "ownership_pct": ownership_pct,
                "opponent": opponent,
                "is_home": is_home,
                "availability": availability,
            }

        except Exception as e:
            logger.debug(f"Error extracting player: {e}")
            return None

    async def _go_to_next_page(self, page: Page) -> bool:
        """Click the next page button. Returns False if on last page."""
        # The Fantasy Six Nations site uses Angular Material paginator.
        # Next button: class="mat-mdc-paginator-navigation-next", aria-label="Next"
        # Disabled state: class includes "mat-mdc-button-disabled-interactive"
        btn = await page.query_selector('button.mat-mdc-paginator-navigation-next, button[aria-label="Next"]')
        if not btn:
            return False

        # Check aria-disabled (set to "true" on last page)
        aria_disabled = await btn.get_attribute("aria-disabled")
        if aria_disabled == "true":
            return False

        # Check for the specific disabled class (NOT "disabled-interactive" which is always present)
        class_attr = await btn.get_attribute("class") or ""
        # Split into individual classes and check for exact "mat-mdc-button-disabled"
        classes = class_attr.split()
        if "mat-mdc-button-disabled" in classes:
            return False

        # Check HTML disabled attribute
        disabled = await btn.get_attribute("disabled")
        if disabled is not None:
            return False

        await btn.click()
        return True

    def parse(self, raw_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Parse raw scraped data into structured player records."""
        players = []
        seen_names = set()

        for dom_player in raw_data.get("dom_players", []):
            name = dom_player.get("name")
            if name and name not in seen_names:
                players.append(self._normalize_player(dom_player))
                seen_names.add(name)

        logger.info(f"Parsed {len(players)} unique players")
        return players

    def _normalize_player(self, player: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize player fields to match our DB schema."""
        # Normalize position
        position = (player.get("position") or "").strip().lower()
        fantasy_position = POSITION_MAP.get(position, position)

        # Normalize country
        country_raw = (player.get("country") or "").strip()
        country_lower = country_raw.lower()
        normalized_country = COUNTRY_MAP.get(country_lower, country_raw)

        return {
            "name": player["name"].strip(),
            "price": player.get("price"),
            "fantasy_position": fantasy_position,
            "country": normalized_country,
            "ownership_pct": player.get("ownership_pct"),
            "opponent": player.get("opponent"),
            "is_home": player.get("is_home"),
            "availability": player.get("availability"),  # already normalized by FORME_CLASS_MAP
            "raw_position": player.get("position"),
            "raw_country": player.get("country"),
        }
