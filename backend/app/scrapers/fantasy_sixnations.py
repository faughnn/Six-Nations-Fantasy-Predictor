"""
Fantasy Six Nations scraper for player roster and prices using Playwright.

Opens a visible browser window so the user can log in manually,
then scrapes the rendered DOM to extract the full player roster
with prices, positions, countries, and ownership percentages.

Paginates through all pages of the player list.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
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


class FantasySixNationsScraper(BaseScraper):
    """
    Scraper for Fantasy Six Nations player roster and prices.

    Strategy:
    1. Open headed browser so user can log in
    2. Wait for game page with player list to load
    3. Scrape all sportif-item elements on each page
    4. Paginate through all pages using the next button
    """

    LOGIN_WAIT_TIMEOUT = 300  # 5 minutes max to wait for login

    def __init__(self):
        self._browser: Optional[Browser] = None
        self._playwright = None

    async def _init_browser(self) -> Browser:
        """Initialize Playwright browser in headed mode for manual login."""
        self._playwright = await async_playwright().start()
        browser = await self._playwright.chromium.launch(
            headless=False,
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

    async def _create_context(self, browser: Browser) -> BrowserContext:
        """Create browser context with realistic settings."""
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1920, "height": 1080},
            java_script_enabled=True,
            no_viewport=True,
        )
        return context

    async def scrape(self, url: str = GAME_URL, **kwargs) -> Dict[str, Any]:
        """
        Open browser, wait for login, then scrape all players across all pages.
        """
        self._browser = await self._init_browser()

        try:
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

            # Dismiss cookie consent / overlays
            await self._dismiss_overlays(page)

            # Wait for the user to log in and player list to appear
            await self._wait_for_player_list(page)

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

    async def _wait_for_player_list(self, page: Page):
        """Wait for user to log in and the player list to be visible."""
        print("Waiting for login and player list to load...")

        for i in range(self.LOGIN_WAIT_TIMEOUT):
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
            f"Timed out after {self.LOGIN_WAIT_TIMEOUT}s waiting for player list"
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

            return {
                "name": name,
                "position": position,
                "country": country,
                "price": price,
                "ownership_pct": ownership_pct,
                "opponent": opponent,
                "is_home": is_home,
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
            "raw_position": player.get("position"),
            "raw_country": player.get("country"),
        }
