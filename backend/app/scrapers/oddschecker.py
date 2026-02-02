"""
Oddschecker scraper for rugby odds using Playwright browser automation.

Handles three market types:
1. Anytime Try Scorer - Player odds for scoring a try
2. Match Points Totals - Over/Under odds for total points scored
3. Handicaps - Spread betting odds (e.g. "France -5.5")
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path
import logging
import asyncio
import json
import re

from playwright.async_api import async_playwright, Page, Browser, TimeoutError as PlaywrightTimeout
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.scrapers.base import BaseScraper

logger = logging.getLogger(__name__)

# Base data directory for saving scrape output
DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "oddschecker"
DEBUG_DIR = DATA_DIR / "debug"


class OddscheckerScraper(BaseScraper):
    """Scraper for Oddschecker odds using Playwright browser automation."""

    # Timeouts
    DEFAULT_TIMEOUT = 60000  # 60 seconds
    PAGE_LOAD_WAIT = 3  # Additional seconds to wait for JS content

    # Six Nations landing page
    SIX_NATIONS_URL = "https://www.oddschecker.com/rugby-union/six-nations"

    # Selectors for odds table (may need adjustment based on actual page structure)
    ODDS_TABLE_SELECTOR = "table.eventTable, table[data-testid='odds-table'], .odds-table"
    PLAYER_ROW_SELECTOR = "tr.diff-row, tr[data-testid='outcome-row'], .outcome-row"
    PLAYER_NAME_SELECTOR = "span.selTxt, .outcome-name, td.sel"
    ODDS_CELL_SELECTOR = "td.bc, td[data-odig], .odds-cell"
    BOOKMAKER_HEADER_SELECTOR = "a.bk-logo-click, .bookmaker-logo, th[data-bk]"

    # Non-player selections to filter out
    NON_PLAYER_NAMES = {"no try scorer", "no tryscorer"}

    # Common cookie consent selectors
    COOKIE_CONSENT_SELECTORS = [
        "button#onetrust-accept-btn-handler",
        "button[data-testid='accept-cookies']",
        "button.js-accept-cookies",
        "button[aria-label='Accept cookies']",
        "button:has-text('Accept')",
        "button:has-text('Accept All')",
        "button:has-text('I Accept')",
        "button:has-text('Got it')",
        "#CybotCookiebotDialogBodyLevelButtonLevelOptinAllowAll",
    ]

    def __init__(self, headless: bool = True):
        self._browser: Optional[Browser] = None
        self._playwright = None
        self._headless = headless

    async def _init_browser(self) -> Browser:
        """Initialize Playwright browser with stealth settings."""
        self._playwright = await async_playwright().start()
        browser = await self._playwright.chromium.launch(
            headless=self._headless,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
            ]
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

    async def _create_page(self, browser: Browser) -> Page:
        """Create a new page with anti-detection settings."""
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/131.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1920, "height": 1080},
            java_script_enabled=True,
            locale="en-GB",
            timezone_id="Europe/London",
        )
        page = await context.new_page()
        return page

    async def _dismiss_cookie_consent(self, page: Page):
        """Try to dismiss cookie consent banners."""
        for selector in self.COOKIE_CONSENT_SELECTORS:
            try:
                btn = page.locator(selector).first
                if await btn.is_visible(timeout=1000):
                    await btn.click()
                    logger.info(f"Dismissed cookie consent with selector: {selector}")
                    await asyncio.sleep(0.5)
                    return
            except Exception:
                continue
        logger.debug("No cookie consent banner found (or already dismissed)")

    async def _save_debug_snapshot(self, page: Page, label: str):
        """Save a screenshot and HTML dump for debugging."""
        DEBUG_DIR.mkdir(parents=True, exist_ok=True)
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        safe_label = re.sub(r'[^\w\-]', '_', label)

        screenshot_path = DEBUG_DIR / f"{ts}_{safe_label}.png"
        html_path = DEBUG_DIR / f"{ts}_{safe_label}.html"

        try:
            await page.screenshot(path=str(screenshot_path), full_page=True)
            logger.info(f"Debug screenshot saved: {screenshot_path}")
        except Exception as e:
            logger.warning(f"Failed to save screenshot: {e}")

        try:
            html = await page.content()
            html_path.write_text(html, encoding="utf-8")
            logger.info(f"Debug HTML saved: {html_path}")
        except Exception as e:
            logger.warning(f"Failed to save HTML: {e}")

    def save_raw_json(self, data: Dict[str, Any], match_slug: str) -> Path:
        """
        Save raw scrape results to a timestamped JSON file.

        Args:
            data: The raw scrape result dict
            match_slug: Match identifier (e.g. "france-v-ireland")

        Returns:
            Path to the saved file
        """
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        safe_slug = re.sub(r'[^\w\-]', '_', match_slug)
        out_path = DATA_DIR / f"{safe_slug}_{ts}.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)
        logger.info(f"Raw JSON saved: {out_path}")
        return out_path

    async def discover_six_nations_matches(self, page: Page) -> List[Dict]:
        """
        Navigate to the Six Nations landing page and discover match URLs.

        Args:
            page: An active Playwright page

        Returns:
            List of dicts: {"slug", "home", "away", "url"}
        """
        logger.info(f"Navigating to {self.SIX_NATIONS_URL}")
        await page.goto(self.SIX_NATIONS_URL, wait_until="domcontentloaded", timeout=self.DEFAULT_TIMEOUT)
        await asyncio.sleep(self.PAGE_LOAD_WAIT)

        await self._dismiss_cookie_consent(page)

        # Find all links that match the Six Nations match pattern
        links = await page.query_selector_all("a[href*='/rugby-union/six-nations/']")
        seen_slugs = set()
        matches = []

        for link in links:
            href = await link.get_attribute("href")
            if not href:
                continue

            # Match pattern: /rugby-union/six-nations/{team-v-team}/...
            m = re.search(r'/rugby-union/six-nations/([a-z]+-v-[a-z]+)', href)
            if not m:
                continue

            slug = m.group(1)
            if slug in seen_slugs:
                continue
            seen_slugs.add(slug)

            # Parse team names from slug
            parts = slug.split("-v-")
            if len(parts) == 2:
                home = parts[0].replace("-", " ").title()
                away = parts[1].replace("-", " ").title()
            else:
                home = slug
                away = ""

            # Build the full URL (ensure absolute)
            if href.startswith("/"):
                url = f"https://www.oddschecker.com{href}"
            else:
                url = href

            matches.append({
                "slug": slug,
                "home": home,
                "away": away,
                "url": url,
            })

        logger.info(f"Discovered {len(matches)} Six Nations matches: {[m['slug'] for m in matches]}")
        return matches

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=60),
        retry=retry_if_exception_type((PlaywrightTimeout, ConnectionError)),
        reraise=True,
    )
    async def scrape(self, url: str, **kwargs) -> Dict[str, Any]:
        """
        Generic scrape method - detects market type and calls appropriate method.

        Args:
            url: Full Oddschecker URL
            market_type: Optional hint for market type ("try_scorer" or "match_totals")

        Returns:
            Dict containing scraped data and metadata
        """
        market_type = kwargs.get("market_type", self._detect_market_type(url))

        if market_type == "handicaps":
            return await self.scrape_handicaps(url)
        elif market_type == "match_totals":
            return await self.scrape_match_totals(url)
        else:
            return await self.scrape_try_scorer(url)

    def _detect_market_type(self, url: str) -> str:
        """Detect market type from URL."""
        url_lower = url.lower()
        if "handicap" in url_lower or "spread" in url_lower:
            return "handicaps"
        if "total" in url_lower or "over-under" in url_lower or "points" in url_lower:
            return "match_totals"
        return "try_scorer"

    async def scrape_try_scorer(self, url: str) -> Dict[str, Any]:
        """
        Scrape anytime try scorer odds from Oddschecker.

        Args:
            url: Full Oddschecker URL for anytime try scorer market

        Returns:
            Dict with player odds data
        """
        browser = await self._init_browser()

        try:
            page = await self._create_page(browser)
            logger.info(f"Navigating to {url}")

            await page.goto(url, wait_until="domcontentloaded", timeout=self.DEFAULT_TIMEOUT)

            # Dismiss cookie consent
            await self._dismiss_cookie_consent(page)

            # Wait for odds table to load
            await self._wait_for_odds_table(page)

            # Additional wait for JavaScript content
            await asyncio.sleep(self.PAGE_LOAD_WAIT)

            # Extract bookmaker headers
            bookmakers = await self._extract_bookmakers(page)
            logger.info(f"Found {len(bookmakers)} bookmakers")

            # Extract player odds data
            odds_data = await self._extract_player_odds(page, bookmakers)
            logger.info(f"Extracted odds for {len(odds_data)} players")

            return {
                "market_type": "try_scorer",
                "url": url,
                "scraped_at": datetime.utcnow().isoformat(),
                "bookmakers": bookmakers,
                "odds_data": odds_data,
            }

        except PlaywrightTimeout as e:
            logger.error(f"Timeout scraping {url}: {e}")
            await self._save_debug_snapshot(page, "timeout_tryscorer")
            raise
        except Exception as e:
            logger.error(f"Error scraping {url}: {e}")
            try:
                await self._save_debug_snapshot(page, "error_tryscorer")
            except Exception:
                pass
            raise
        finally:
            await self._close_browser()

    async def scrape_match_totals(self, url: str) -> Dict[str, Any]:
        """
        Scrape match points totals (over/under) odds from Oddschecker.

        Args:
            url: Full Oddschecker URL for match totals market

        Returns:
            Dict with over/under odds data
        """
        browser = await self._init_browser()

        try:
            page = await self._create_page(browser)
            logger.info(f"Navigating to {url}")

            await page.goto(url, wait_until="domcontentloaded", timeout=self.DEFAULT_TIMEOUT)

            # Dismiss cookie consent
            await self._dismiss_cookie_consent(page)

            # Wait for odds table to load
            await self._wait_for_odds_table(page)

            # Additional wait for JavaScript content
            await asyncio.sleep(self.PAGE_LOAD_WAIT)

            # Extract bookmaker headers
            bookmakers = await self._extract_bookmakers(page)
            logger.info(f"Found {len(bookmakers)} bookmakers")

            # Extract over/under odds
            totals_data = await self._extract_totals_odds(page, bookmakers)
            logger.info(f"Extracted {len(totals_data)} totals lines")

            return {
                "market_type": "match_totals",
                "url": url,
                "scraped_at": datetime.utcnow().isoformat(),
                "bookmakers": bookmakers,
                "totals_data": totals_data,
            }

        except PlaywrightTimeout as e:
            logger.error(f"Timeout scraping {url}: {e}")
            await self._save_debug_snapshot(page, "timeout_totals")
            raise
        except Exception as e:
            logger.error(f"Error scraping {url}: {e}")
            try:
                await self._save_debug_snapshot(page, "error_totals")
            except Exception:
                pass
            raise
        finally:
            await self._close_browser()

    async def _wait_for_odds_table(self, page: Page):
        """Wait for odds table to appear on page."""
        selectors = self.ODDS_TABLE_SELECTOR.split(", ")
        for selector in selectors:
            try:
                await page.wait_for_selector(selector, timeout=5000)
                logger.info(f"Matched odds table selector: {selector}")
                return
            except PlaywrightTimeout:
                logger.debug(f"Selector not found: {selector}")
                continue
        # If no specific selector worked, wait for any table
        logger.info("Falling back to generic 'table' selector")
        await page.wait_for_selector("table", timeout=self.DEFAULT_TIMEOUT)

    async def _extract_bookmakers(self, page: Page) -> List[str]:
        """Extract bookmaker names from table headers."""
        bookmakers = []

        # Try different selector patterns
        selectors = self.BOOKMAKER_HEADER_SELECTOR.split(", ")
        for selector in selectors:
            elements = await page.query_selector_all(selector)
            if elements:
                logger.info(f"Matched bookmaker header selector: {selector} ({len(elements)} elements)")
                for elem in elements:
                    name = await elem.get_attribute("data-bk")
                    if not name:
                        name = await elem.get_attribute("title")
                    if not name:
                        name = await elem.inner_text()
                    if name and name.strip():
                        bookmakers.append(name.strip())
                break

        # Fallback: try to get from header cells
        if not bookmakers:
            header_cells = await page.query_selector_all("thead th, tr.eventTableHeader td")
            if header_cells:
                logger.info(f"Matched fallback header selector ({len(header_cells)} cells)")
            for cell in header_cells:
                text = await cell.inner_text()
                if text and text.strip() and text.strip() not in ["", "Selection"]:
                    bookmakers.append(text.strip())

        # If the list is an exact repeat (sticky header duplication), take the first half
        if len(bookmakers) > 1 and len(bookmakers) % 2 == 0:
            half = len(bookmakers) // 2
            if bookmakers[:half] == bookmakers[half:]:
                logger.info(f"Detected duplicate bookmaker headers, deduplicating {len(bookmakers)} -> {half}")
                bookmakers = bookmakers[:half]

        return bookmakers

    async def _extract_player_odds(self, page: Page, bookmakers: List[str]) -> List[Dict]:
        """Extract player names and odds from each row."""
        odds_data = []

        # Try different row selectors
        rows = []
        selectors = self.PLAYER_ROW_SELECTOR.split(", ")
        for selector in selectors:
            rows = await page.query_selector_all(selector)
            if rows:
                logger.info(f"Matched player row selector: {selector} ({len(rows)} rows)")
                break

        # Fallback to tbody tr
        if not rows:
            rows = await page.query_selector_all("tbody tr")
            if rows:
                logger.info(f"Matched fallback 'tbody tr' selector ({len(rows)} rows)")

        for row in rows:
            try:
                # Extract player name
                player_name = await self._extract_player_name(row)
                if not player_name:
                    continue

                if player_name.lower() in self.NON_PLAYER_NAMES:
                    continue

                # Extract odds for each bookmaker
                odds_cells = await row.query_selector_all(self.ODDS_CELL_SELECTOR.split(", ")[0])
                if not odds_cells:
                    odds_cells = await row.query_selector_all("td")

                player_odds = {}
                for i, cell in enumerate(odds_cells):
                    if i >= len(bookmakers):
                        break

                    odds_value = await self._extract_odds_value(cell)
                    if odds_value is not None:
                        player_odds[bookmakers[i]] = odds_value

                if player_odds:
                    odds_data.append({
                        "player_name": player_name,
                        "odds_by_bookmaker": player_odds,
                    })

            except Exception as e:
                logger.warning(f"Error extracting row: {e}")
                continue

        return odds_data

    async def _extract_player_name(self, row) -> Optional[str]:
        """Extract player name from a row element."""
        # Try different selectors
        selectors = self.PLAYER_NAME_SELECTOR.split(", ")
        for selector in selectors:
            elem = await row.query_selector(selector)
            if elem:
                text = await elem.inner_text()
                if text:
                    return self._normalize_player_name(text.strip())

        # Fallback: first td
        first_td = await row.query_selector("td:first-child")
        if first_td:
            text = await first_td.inner_text()
            if text:
                return self._normalize_player_name(text.strip())

        return None

    def _normalize_player_name(self, name: str) -> str:
        """Normalize player name by removing team suffixes and extra whitespace."""
        # Remove team suffix in parentheses: "Marcus Smith (England)" -> "Marcus Smith"
        name = re.sub(r'\s*\([^)]+\)\s*$', '', name)
        # Remove extra whitespace
        name = ' '.join(name.split())
        return name

    async def _extract_odds_value(self, cell) -> Optional[float]:
        """Extract decimal odds value from a cell.  Returns None for missing/zero odds."""
        value = None

        # Try data-odig attribute first (Oddschecker's decimal odds)
        odds_str = await cell.get_attribute("data-odig")
        if odds_str:
            try:
                value = float(odds_str)
            except ValueError:
                pass

        # Try data-o attribute
        if value is None:
            odds_str = await cell.get_attribute("data-o")
            if odds_str:
                try:
                    value = float(odds_str)
                except ValueError:
                    pass

        # Try inner text and convert fractional to decimal
        if value is None:
            text = await cell.inner_text()
            if text:
                text = text.strip()
                value = self._parse_odds_text(text)

        # A value of 0 means the bookmaker isn't offering this selection
        if value is not None and value <= 0:
            return None

        return value

    def _parse_odds_text(self, text: str) -> Optional[float]:
        """Parse odds text (fractional or decimal) to decimal format."""
        if not text or text in ["-", "N/A", ""]:
            return None

        # Already decimal
        try:
            return float(text)
        except ValueError:
            pass

        # Fractional odds: "5/1" -> 6.0
        if "/" in text:
            try:
                parts = text.split("/")
                numerator = float(parts[0])
                denominator = float(parts[1])
                return (numerator / denominator) + 1
            except (ValueError, ZeroDivisionError):
                pass

        return None

    async def _extract_totals_odds(self, page: Page, bookmakers: List[str]) -> List[Dict]:
        """Extract over/under totals odds."""
        totals_data = []

        rows = await page.query_selector_all("tbody tr")

        for row in rows:
            try:
                # Get the selection text (e.g., "Over 45.5", "Under 45.5")
                name_elem = await row.query_selector("td:first-child, .sel, span.selTxt")
                if not name_elem:
                    continue

                selection_text = await name_elem.inner_text()
                selection_text = selection_text.strip()

                # Parse the line value and direction
                line_info = self._parse_totals_selection(selection_text)
                if not line_info:
                    continue

                # Extract odds for each bookmaker
                odds_cells = await row.query_selector_all("td.bc, td[data-odig]")
                if not odds_cells:
                    odds_cells = await row.query_selector_all("td")[1:]  # Skip first column

                odds_by_bookmaker = {}
                for i, cell in enumerate(odds_cells):
                    if i >= len(bookmakers):
                        break
                    odds_value = await self._extract_odds_value(cell)
                    if odds_value is not None:
                        odds_by_bookmaker[bookmakers[i]] = odds_value

                if odds_by_bookmaker:
                    totals_data.append({
                        "selection": selection_text,
                        "direction": line_info["direction"],
                        "line": line_info["line"],
                        "odds_by_bookmaker": odds_by_bookmaker,
                    })

            except Exception as e:
                logger.warning(f"Error extracting totals row: {e}")
                continue

        return totals_data

    def _parse_totals_selection(self, text: str) -> Optional[Dict]:
        """Parse totals selection text to extract direction and line."""
        text = text.lower().strip()

        # Match patterns like "Over 45.5", "Under 40", "O 45.5", "U 40"
        over_match = re.search(r'over?\s*(\d+\.?\d*)', text)
        if over_match:
            return {
                "direction": "over",
                "line": float(over_match.group(1))
            }

        under_match = re.search(r'under?\s*(\d+\.?\d*)', text)
        if under_match:
            return {
                "direction": "under",
                "line": float(under_match.group(1))
            }

        return None

    def parse(self, raw_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Parse raw scraped data and calculate averaged odds.

        Args:
            raw_data: Output from scrape() method

        Returns:
            List of dicts with averaged odds
        """
        market_type = raw_data.get("market_type", "try_scorer")

        if market_type == "handicaps":
            return self._parse_handicaps(raw_data)
        elif market_type == "match_totals":
            return self._parse_match_totals(raw_data)
        else:
            return self._parse_try_scorer(raw_data)

    def _parse_try_scorer(self, raw_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Parse try scorer odds data."""
        parsed_data = []

        for player_data in raw_data.get("odds_data", []):
            odds_values = list(player_data["odds_by_bookmaker"].values())

            if not odds_values:
                continue

            # Calculate average odds (arithmetic mean)
            average_odds = sum(odds_values) / len(odds_values)

            parsed_data.append({
                "player_name": player_data["player_name"],
                "average_odds": round(average_odds, 2),
                "odds_by_bookmaker": player_data["odds_by_bookmaker"],
                "num_bookmakers": len(odds_values),
                "min_odds": min(odds_values),
                "max_odds": max(odds_values),
            })

        # Sort by average odds (lower odds = more likely to score)
        parsed_data.sort(key=lambda x: x["average_odds"])

        return parsed_data

    def _parse_match_totals(self, raw_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Parse match totals odds data and find the single consensus line.

        For each bookmaker, look at 'over' selections sorted by line value.
        As the line rises the over becomes harder to hit, so over-odds should
        increase monotonically.  The point where they cross 2.0 is that
        bookmaker's main line.  Average across bookmakers for the consensus.
        """
        totals_data = raw_data.get("totals_data", [])
        if not totals_data:
            return []

        # Build per-bookmaker maps
        bk_over: Dict[str, List[tuple]] = {}   # bk -> [(line, odds)]
        bk_all: Dict[str, List[tuple]] = {}    # bk -> [(line, direction, odds)]
        for item in totals_data:
            for bk, odds in item["odds_by_bookmaker"].items():
                bk_all.setdefault(bk, []).append(
                    (item["line"], item["direction"], odds)
                )
                if item["direction"] == "over":
                    bk_over.setdefault(bk, []).append(
                        (item["line"], odds)
                    )

        if not bk_over:
            return []

        # For each bookmaker, find the line where over-odds cross 2.0
        consensus_lines = []
        over_odds_list = []
        under_odds_list = []

        for bk, over_entries in bk_over.items():
            over_entries.sort()  # sort by line ascending
            below = [(ln, o) for ln, o in over_entries if o <= 2.0]
            above = [(ln, o) for ln, o in over_entries if o > 2.0]

            if below and above:
                last_below = max(below, key=lambda x: x[0])
                first_above = min(above, key=lambda x: x[0])
                if first_above[1] != last_below[1]:
                    frac = (2.0 - last_below[1]) / (first_above[1] - last_below[1])
                    main_line = last_below[0] + frac * (first_above[0] - last_below[0])
                else:
                    main_line = (last_below[0] + first_above[0]) / 2
                nearest_line = last_below[0]
            elif below:
                best = max(below, key=lambda x: x[0])
                main_line = best[0]
                nearest_line = best[0]
            else:
                best = min(above, key=lambda x: x[0])
                main_line = best[0]
                nearest_line = best[0]

            consensus_lines.append(main_line)

            # Collect over/under odds at the nearest real line
            for line_val, direction, odds in bk_all.get(bk, []):
                if abs(line_val - nearest_line) < 0.01:
                    if direction == "over":
                        over_odds_list.append(odds)
                    else:
                        under_odds_list.append(odds)

        avg_line = round(sum(consensus_lines) / len(consensus_lines), 1)
        avg_over = round(sum(over_odds_list) / len(over_odds_list), 2) if over_odds_list else None
        avg_under = round(sum(under_odds_list) / len(under_odds_list), 2) if under_odds_list else None

        result: Dict[str, Any] = {
            "line": avg_line,
            "num_bookmakers": len(bk_over),
        }
        if avg_over is not None:
            result["over_odds"] = avg_over
            result["over_num_bookmakers"] = len(over_odds_list)
        if avg_under is not None:
            result["under_odds"] = avg_under
            result["under_num_bookmakers"] = len(under_odds_list)

        return [result]

    # ------------------------------------------------------------------
    # Handicaps market
    # ------------------------------------------------------------------

    async def scrape_handicaps(self, url: str) -> Dict[str, Any]:
        """
        Scrape handicap (spread) odds from Oddschecker.

        Args:
            url: Full Oddschecker URL for handicaps market

        Returns:
            Dict with handicap odds data
        """
        browser = await self._init_browser()

        try:
            page = await self._create_page(browser)
            logger.info(f"Navigating to {url}")

            await page.goto(url, wait_until="domcontentloaded", timeout=self.DEFAULT_TIMEOUT)

            # Dismiss cookie consent
            await self._dismiss_cookie_consent(page)

            # Wait for odds table to load
            await self._wait_for_odds_table(page)

            # Additional wait for JavaScript content
            await asyncio.sleep(self.PAGE_LOAD_WAIT)

            # Extract bookmaker headers
            bookmakers = await self._extract_bookmakers(page)
            logger.info(f"Found {len(bookmakers)} bookmakers")

            # Extract handicap odds
            handicap_data = await self._extract_handicap_odds(page, bookmakers)
            logger.info(f"Extracted {len(handicap_data)} handicap selections")

            return {
                "market_type": "handicaps",
                "url": url,
                "scraped_at": datetime.utcnow().isoformat(),
                "bookmakers": bookmakers,
                "handicap_data": handicap_data,
            }

        except PlaywrightTimeout as e:
            logger.error(f"Timeout scraping {url}: {e}")
            await self._save_debug_snapshot(page, "timeout_handicaps")
            raise
        except Exception as e:
            logger.error(f"Error scraping {url}: {e}")
            try:
                await self._save_debug_snapshot(page, "error_handicaps")
            except Exception:
                pass
            raise
        finally:
            await self._close_browser()

    async def _extract_handicap_odds(self, page: Page, bookmakers: List[str]) -> List[Dict]:
        """Extract handicap selection names and odds from each row."""
        handicap_data = []

        rows = await page.query_selector_all("tbody tr")

        for row in rows:
            try:
                # Get the selection text (e.g., "France -5.5", "Ireland +5.5")
                name_elem = await row.query_selector("td:first-child, .sel, span.selTxt")
                if not name_elem:
                    continue

                selection_text = await name_elem.inner_text()
                selection_text = selection_text.strip()

                # Parse team name and line value
                line_info = self._parse_handicap_selection(selection_text)
                if not line_info:
                    continue

                # Extract odds for each bookmaker
                odds_cells = await row.query_selector_all("td.bc, td[data-odig]")
                if not odds_cells:
                    odds_cells = await row.query_selector_all("td")
                    # Skip the first cell (selection name)
                    odds_cells = odds_cells[1:] if odds_cells else []

                odds_by_bookmaker = {}
                for i, cell in enumerate(odds_cells):
                    if i >= len(bookmakers):
                        break
                    odds_value = await self._extract_odds_value(cell)
                    if odds_value is not None:
                        odds_by_bookmaker[bookmakers[i]] = odds_value

                if odds_by_bookmaker:
                    handicap_data.append({
                        "selection": selection_text,
                        "team": line_info["team"],
                        "line": line_info["line"],
                        "odds_by_bookmaker": odds_by_bookmaker,
                    })

            except Exception as e:
                logger.warning(f"Error extracting handicap row: {e}")
                continue

        return handicap_data

    def _parse_handicap_selection(self, text: str) -> Optional[Dict]:
        """
        Parse handicap selection text to extract team name and signed line.

        Examples:
            "France -5.5" -> {"team": "France", "line": -5.5}
            "Ireland +5.5" -> {"team": "Ireland", "line": 5.5}
        """
        # Match: team name followed by +/- number
        match = re.match(r'^(.+?)\s*([+-]\s*\d+\.?\d*)\s*$', text.strip())
        if match:
            team = match.group(1).strip()
            line = float(match.group(2).replace(" ", ""))
            return {"team": team, "line": line}

        return None

    def _parse_handicaps(self, raw_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Parse handicap odds data and find the single consensus line.

        For each bookmaker, find which selection they price closest to 2.0
        (even money). Normalize all selections to a home-team spread, then
        average across bookmakers to get the market consensus handicap.
        """
        handicap_data = raw_data.get("handicap_data", [])
        if not handicap_data:
            return []

        # Discover the two teams and determine home/away from URL slug
        teams = list({item["team"] for item in handicap_data})
        if len(teams) != 2:
            logger.warning(f"Expected 2 teams in handicaps, found {len(teams)}: {teams}")
            if not teams:
                return []

        # Home team is the first team in the URL slug (e.g. france-v-ireland -> France)
        url = raw_data.get("url", "")
        slug_match = re.search(r'/([a-z]+-v-[a-z]+)', url.lower())
        if slug_match:
            slug_home = slug_match.group(1).split("-v-")[0].replace("-", " ")
            # Match to actual team name (case-insensitive)
            home_team = next(
                (t for t in teams if t.lower().startswith(slug_home)),
                teams[0],
            )
        else:
            home_team = teams[0]

        away_team = next(t for t in teams if t != home_team)

        # Build per-bookmaker map of home-team selections:
        # bk -> sorted list of (abs_spread, odds) for "HomeTeam -X" entries
        bk_home: Dict[str, List[tuple]] = {}
        # Also keep all entries for odds collection later
        bk_all: Dict[str, List[tuple]] = {}
        for item in handicap_data:
            for bk, odds in item["odds_by_bookmaker"].items():
                bk_all.setdefault(bk, []).append(
                    (item["team"], item["line"], odds)
                )
                # Collect home-team negative-line entries (e.g. "France -10")
                if item["team"] == home_team and item["line"] < 0:
                    bk_home.setdefault(bk, []).append(
                        (abs(item["line"]), odds)
                    )

        if not bk_home:
            return []

        # For each bookmaker, find the main line by locating where the
        # home-team odds cross 2.0 as the spread increases.  Larger
        # spreads are easier for the underdog to cover, so odds for the
        # favourite should rise monotonically.  The crossing point is
        # the bookmaker's true main line.
        spread_values = []
        home_odds_list = []
        away_odds_list = []

        for bk, home_entries in bk_home.items():
            home_entries.sort()  # sort by abs_spread ascending
            below = [(sp, o) for sp, o in home_entries if o <= 2.0]
            above = [(sp, o) for sp, o in home_entries if o > 2.0]

            if below and above:
                last_below = max(below, key=lambda x: x[0])
                first_above = min(above, key=lambda x: x[0])
                # Linear interpolation to find the 2.0 crossing
                if first_above[1] != last_below[1]:
                    frac = (2.0 - last_below[1]) / (first_above[1] - last_below[1])
                    main_line = last_below[0] + frac * (first_above[0] - last_below[0])
                else:
                    main_line = (last_below[0] + first_above[0]) / 2
                # Odds straddle the crossing — use the below-side entry
                nearest_abs = last_below[0]
            elif below:
                # All odds <= 2.0; use the largest spread
                best = max(below, key=lambda x: x[0])
                main_line = best[0]
                nearest_abs = best[0]
            else:
                # All odds > 2.0; use the smallest spread
                best = min(above, key=lambda x: x[0])
                main_line = best[0]
                nearest_abs = best[0]

            spread_values.append(-main_line)  # negative = home favourite

            # Collect home/away odds at the nearest real line to the crossing
            for team, line, odds in bk_all.get(bk, []):
                if abs(abs(line) - nearest_abs) < 0.01:
                    if team == home_team and line < 0:
                        home_odds_list.append(odds)
                    elif team == away_team and line > 0:
                        away_odds_list.append(odds)

        avg_spread = round(sum(spread_values) / len(spread_values), 1)
        avg_home_odds = round(sum(home_odds_list) / len(home_odds_list), 2) if home_odds_list else None
        avg_away_odds = round(sum(away_odds_list) / len(away_odds_list), 2) if away_odds_list else None

        return [{
            "line": abs(avg_spread),
            "home_team": home_team,
            "away_team": away_team,
            "home_spread": avg_spread,
            "home_odds": avg_home_odds,
            "away_odds": avg_away_odds,
            "num_bookmakers": len(bk_home),
        }]
