"""
Scrape Fantasy Six Nations per-round stats using Playwright.

Uses the same session state as scrape_fantasy_prices.py so you
don't need to log in again (run that first if you haven't).

Usage:
    python scrape_fantasy_stats.py [--rounds 1,2]

Iterates through each round using the Round dropdown filter,
scrapes all pages, and produces per-player-per-round records.
"""

import asyncio
import argparse
import json
import logging
import sys
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).parent))

from playwright.async_api import async_playwright, Page, Browser, BrowserContext

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

STATS_URL = "https://fantasy.sixnationsrugby.com/m6n/#/game/stats"
SESSION_PATH = Path(__file__).parent / "data" / "session_state.json"
DATA_DIR = Path(__file__).parent / "data"

# Column headers in table order for PER-ROUND view
# (All-rounds: MP / AP, Per-round: Min / Pts)
STAT_COLUMNS = [
    "minutes_played",       # Min (per-round) / MP (all-rounds)
    "player_of_match",      # POTM
    "tries",                # T
    "try_assists",          # As
    "conversions",          # C
    "penalties_kicked",     # Pen
    "drop_goals",           # DG
    "tackles_made",         # Ta
    "metres_carried",       # MC
    "defenders_beaten",     # DB
    "offloads",             # OF
    "fifty_22_kicks",       # 50-22
    "lineout_steals",       # LS
    "breakdown_steals",     # BS
    "kick_returns",         # KR
    "scrums_won",           # SW
    "penalties_conceded",   # CPen
    "yellow_cards",         # YC
    "red_cards",            # RC
    "fantasy_points",       # Pts (per-round) / AP (all-rounds)
]

STAT_DISPLAY = {
    "minutes_played": "Min",
    "player_of_match": "POTM",
    "tries": "T",
    "try_assists": "As",
    "conversions": "C",
    "penalties_kicked": "Pen",
    "drop_goals": "DG",
    "tackles_made": "Ta",
    "metres_carried": "MC",
    "defenders_beaten": "DB",
    "offloads": "OF",
    "fifty_22_kicks": "50-22",
    "lineout_steals": "LS",
    "breakdown_steals": "BS",
    "kick_returns": "KR",
    "scrums_won": "SW",
    "penalties_conceded": "CPen",
    "yellow_cards": "YC",
    "red_cards": "RC",
    "fantasy_points": "Pts",
}

COUNTRY_FROM_IMAGE = {
    "france": "France",
    "ireland": "Ireland",
    "england": "England",
    "wales": "Wales",
    "scotland": "Scotland",
    "italy": "Italy",
}


async def create_browser_context(browser: Browser) -> BrowserContext:
    kwargs = dict(
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/122.0.0.0 Safari/537.36"
        ),
        viewport={"width": 1920, "height": 1080},
        java_script_enabled=True,
        no_viewport=True,
    )
    if SESSION_PATH.exists() and SESSION_PATH.stat().st_size > 0:
        kwargs["storage_state"] = str(SESSION_PATH)
        print("Restoring saved session...")
    else:
        print("No saved session found. Run scrape_fantasy_prices.py first to log in.")
        sys.exit(1)
    return await browser.new_context(**kwargs)


async def dismiss_overlays(page: Page):
    await asyncio.sleep(2)
    for selector in [
        'button:has-text("Accept")',
        'button:has-text("Accept All")',
        '#onetrust-accept-btn-handler',
    ]:
        try:
            elem = await page.query_selector(selector)
            if elem and await elem.is_visible():
                await elem.click()
                await asyncio.sleep(1)
                return
        except Exception:
            continue


async def wait_for_table(page: Page, timeout: int = 60) -> bool:
    print("Waiting for stats table to load...")
    for i in range(timeout):
        await asyncio.sleep(1)
        try:
            rows = await page.query_selector_all("table.fs-table tbody tr")
            if len(rows) > 0:
                print(f"Stats table loaded with {len(rows)} rows.")
                await asyncio.sleep(2)
                return True
        except Exception:
            pass
        if i > 0 and i % 10 == 0:
            print(f"  Still waiting... ({i}s)")
    print("WARNING: Timed out waiting for stats table!")
    return False


async def select_round(page: Page, round_num: int) -> bool:
    """Select a specific round from the Round dropdown."""
    print(f"\n--- Selecting Round {round_num} ---")

    # Click the Round mat-select to open the dropdown
    # The Round dropdown is the 3rd mat-form-field (Nation, Position, Round)
    form_fields = await page.query_selector_all("mat-form-field")
    round_field = None
    for ff in form_fields:
        label = await ff.query_selector("mat-label")
        if label:
            text = (await label.inner_text()).strip()
            if text.lower() == "round":
                round_field = ff
                break

    if not round_field:
        print("  Could not find Round dropdown")
        return False

    # Click the mat-select inside it
    select_el = await round_field.query_selector("mat-select")
    if not select_el:
        print("  Could not find mat-select in Round field")
        return False

    await select_el.click()
    await asyncio.sleep(1)

    # Find and click the option for this round number
    # Options text looks like "Round 1", "Round 2", etc.
    options = await page.query_selector_all("mat-option")
    clicked = False
    for opt in options:
        text = (await opt.inner_text()).strip()
        if text.lower() == f"round {round_num}":
            await opt.click()
            clicked = True
            print(f"  Selected '{text}'")
            break

    if not clicked:
        print(f"  Could not find option for Round {round_num}")
        await page.keyboard.press("Escape")
        return False

    # Wait for table to reload
    await asyncio.sleep(2)
    return True


async def scrape_current_page(page: Page) -> list:
    """Scrape all player rows from the current table page."""
    return await page.evaluate("""
        () => {
            const rows = document.querySelectorAll('table.fs-table tbody tr');
            const results = [];

            rows.forEach(row => {
                const cells = row.querySelectorAll('td');
                if (cells.length < 2) return;

                const firstCell = cells[0];
                const nameEl = firstCell.querySelector('a.link');
                const name = nameEl ? nameEl.innerText.trim() : '';
                if (!name) return;

                // Country from image URL
                const img = firstCell.querySelector('img');
                const imgSrc = img ? img.getAttribute('src') || '' : '';
                let country = '';
                const countryMap = {
                    'france': 'France', 'ireland': 'Ireland', 'england': 'England',
                    'wales': 'Wales', 'scotland': 'Scotland', 'italy': 'Italy'
                };
                for (const [key, val] of Object.entries(countryMap)) {
                    if (imgSrc.toLowerCase().includes(key)) {
                        country = val;
                        break;
                    }
                }

                // Stat cells
                const stats = [];
                for (let i = 1; i < cells.length; i++) {
                    const span = cells[i].querySelector('span');
                    stats.push(span ? span.innerText.trim() : '');
                }

                results.push({ name, country, stats });
            });

            return results;
        }
    """)


async def go_to_next_page(page: Page) -> bool:
    btn = await page.query_selector('button.mat-mdc-paginator-navigation-next')
    if not btn:
        return False
    aria_disabled = await btn.get_attribute("aria-disabled")
    if aria_disabled == "true":
        return False
    classes = (await btn.get_attribute("class") or "").split()
    if "mat-mdc-button-disabled" in classes:
        return False
    await btn.click()
    return True


async def get_pagination_info(page: Page) -> str:
    label = await page.query_selector('.mat-mdc-paginator-range-label')
    return (await label.inner_text()).strip() if label else ""


async def scrape_all_pages(page: Page) -> list:
    """Scrape all pages for the currently selected round."""
    all_players = []
    page_num = 1

    while True:
        page_players = await scrape_current_page(page)
        all_players.extend(page_players)

        pagination = await get_pagination_info(page)
        print(f"  Page {page_num}: {len(page_players)} players (total: {len(all_players)}) [{pagination}]")

        has_next = await go_to_next_page(page)
        if not has_next:
            break

        page_num += 1
        await asyncio.sleep(1)

        if page_num > 100:
            break

    return all_players


def parse_players(raw_players: list, round_num: int) -> list:
    """Convert raw scraped data into structured per-round records."""
    parsed = []
    for p in raw_players:
        record = {
            "name": p["name"],
            "country": p["country"],
            "round": round_num,
        }

        stats = p.get("stats", [])
        for i, col_name in enumerate(STAT_COLUMNS):
            if i < len(stats):
                val = stats[i]
                if val == "" or val is None:
                    record[col_name] = 0
                else:
                    try:
                        record[col_name] = float(val) if "." in str(val) else int(val)
                    except (ValueError, TypeError):
                        record[col_name] = 0
            else:
                record[col_name] = 0

        # Skip players with 0 minutes (they didn't play this round)
        if record.get("minutes_played", 0) == 0:
            continue

        parsed.append(record)

    return parsed


async def detect_available_rounds(page: Page) -> list[int]:
    """Open the Round dropdown and see which options are available."""
    form_fields = await page.query_selector_all("mat-form-field")
    for ff in form_fields:
        label = await ff.query_selector("mat-label")
        if label and (await label.inner_text()).strip().lower() == "round":
            select_el = await ff.query_selector("mat-select")
            if select_el:
                await select_el.click()
                await asyncio.sleep(1)
                options = await page.query_selector_all("mat-option")
                rounds = []
                for opt in options:
                    text = (await opt.inner_text()).strip().lower()
                    if text.startswith("round "):
                        try:
                            rounds.append(int(text.split()[-1]))
                        except ValueError:
                            pass
                await page.keyboard.press("Escape")
                await asyncio.sleep(0.5)
                return sorted(rounds)
    return []


POSITION_MAP = {
    "BACK THREE": "back_3",
    "CENTRE": "centre",
    "FLY-HALF": "out_half",
    "SCRUM-HALF": "scrum_half",
    "BACK-ROW": "back_row",
    "SECOND-ROW": "second_row",
    "PROP": "prop",
    "HOOKER": "hooker",
}


async def select_filter(page: Page, label_text: str, option_text: str) -> bool:
    """Select an option from a named mat-select dropdown."""
    form_fields = await page.query_selector_all("mat-form-field")
    for ff in form_fields:
        label = await ff.query_selector("mat-label")
        if label and (await label.inner_text()).strip().lower() == label_text.lower():
            select_el = await ff.query_selector("mat-select")
            if not select_el:
                return False
            await select_el.click()
            await asyncio.sleep(1)
            options = await page.query_selector_all("mat-option")
            for opt in options:
                text = (await opt.inner_text()).strip()
                if text.lower() == option_text.lower():
                    await opt.click()
                    await asyncio.sleep(2)
                    return True
            await page.keyboard.press("Escape")
            await asyncio.sleep(0.5)
            return False
    return False


async def clear_filter(page: Page, label_text: str) -> bool:
    """Clear a filter by selecting the blank/default option."""
    form_fields = await page.query_selector_all("mat-form-field")
    for ff in form_fields:
        label = await ff.query_selector("mat-label")
        if label and (await label.inner_text()).strip().lower() == label_text.lower():
            select_el = await ff.query_selector("mat-select")
            if not select_el:
                return False
            await select_el.click()
            await asyncio.sleep(1)
            options = await page.query_selector_all("mat-option")
            if options:
                # First option is always the blank/default
                await options[0].click()
                await asyncio.sleep(2)
                return True
            await page.keyboard.press("Escape")
            return False
    return False


async def build_position_map(page: Page) -> dict[str, str]:
    """Build a player name → position map by cycling through position filters."""
    name_to_pos: dict[str, str] = {}

    for display_name, pos_key in POSITION_MAP.items():
        print(f"  Scanning position: {display_name}...")
        if not await select_filter(page, "Position", display_name):
            print(f"    Could not select {display_name}, skipping")
            continue

        # Just read the first page — enough to get most names
        # Actually, read all pages for this position to be thorough
        page_num = 1
        while True:
            players = await scrape_current_page(page)
            for p in players:
                if p["name"] and p["name"] not in name_to_pos:
                    name_to_pos[p["name"]] = pos_key
            has_next = await go_to_next_page(page)
            if not has_next:
                break
            page_num += 1
            await asyncio.sleep(0.5)
            if page_num > 50:
                break

        print(f"    Found {sum(1 for v in name_to_pos.values() if v == pos_key)} players")

    # Clear the position filter
    await clear_filter(page, "Position")

    print(f"  Total position-mapped players: {len(name_to_pos)}")
    return name_to_pos


async def save_to_db(records: list[dict], season: int):
    """Save scraped fantasy stats records to the database."""
    import os
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
    from sqlalchemy import select
    from app.models.stats import FantasyRoundStats
    from app.models.player import Player
    from app.services.import_service import _build_player_cache, _fuzzy_find

    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        print("ERROR: DATABASE_URL not set. Cannot save to database.")
        return

    engine = create_async_engine(database_url, echo=False)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as db:
        cache = await _build_player_cache(db)

        saved = 0
        skipped = 0

        for rec in records:
            player = _fuzzy_find(rec["name"], cache)
            if not player:
                print(f"  SKIP (no match): {rec['name']}")
                skipped += 1
                continue

            # Check if record already exists (upsert)
            existing_q = select(FantasyRoundStats).where(
                FantasyRoundStats.player_id == player.id,
                FantasyRoundStats.season == season,
                FantasyRoundStats.round == rec["round"],
            )
            result = await db.execute(existing_q)
            existing = result.scalar_one_or_none()

            stat_fields = {
                "tries": rec.get("tries", 0),
                "try_assists": rec.get("try_assists", 0),
                "conversions": rec.get("conversions", 0),
                "penalties_kicked": rec.get("penalties_kicked", 0),
                "drop_goals": rec.get("drop_goals", 0),
                "defenders_beaten": rec.get("defenders_beaten", 0),
                "metres_carried": rec.get("metres_carried", 0),
                "clean_breaks": rec.get("clean_breaks", 0),
                "offloads": rec.get("offloads", 0),
                "fifty_22_kicks": rec.get("fifty_22_kicks", 0),
                "tackles_made": rec.get("tackles_made", 0),
                "lineout_steals": rec.get("lineout_steals", 0),
                "breakdown_steals": rec.get("breakdown_steals", 0),
                "kick_returns": rec.get("kick_returns", 0),
                "scrums_won": rec.get("scrums_won", 0),
                "penalties_conceded": rec.get("penalties_conceded", 0),
                "yellow_cards": rec.get("yellow_cards", 0),
                "red_cards": rec.get("red_cards", 0),
                "minutes_played": rec.get("minutes_played", 0),
                "player_of_match": bool(rec.get("player_of_match", 0)),
                "fantasy_points": rec.get("fantasy_points"),
                "scraped_at": datetime.now(timezone.utc),
            }

            if existing:
                for k, v in stat_fields.items():
                    setattr(existing, k, v)
            else:
                new_stat = FantasyRoundStats(
                    player_id=player.id,
                    season=season,
                    round=rec["round"],
                    **stat_fields,
                )
                db.add(new_stat)

            saved += 1

        await db.commit()
        print(f"\nDatabase: {saved} records saved, {skipped} skipped (no player match)")

    await engine.dispose()


async def main():
    parser = argparse.ArgumentParser(description="Scrape Fantasy Six Nations per-round stats")
    parser.add_argument(
        "--rounds", "-r",
        default=None,
        help="Comma-separated round numbers to scrape (e.g. '1,2'). Default: auto-detect all.",
    )
    parser.add_argument(
        "--output", "-o",
        default=str(DATA_DIR / "fantasy_stats_2026.json"),
        help="Output JSON file path",
    )
    parser.add_argument(
        "--skip-positions",
        action="store_true",
        help="Skip the position-mapping pass (faster, no position data)",
    )
    parser.add_argument(
        "--save-db",
        action="store_true",
        help="Also save scraped stats to the Postgres database",
    )
    parser.add_argument(
        "--from-json",
        default=None,
        help="Skip scraping; load this JSON file and save to DB directly",
    )
    parser.add_argument(
        "--season",
        type=int,
        default=2026,
        help="Season year (default: 2026)",
    )
    args = parser.parse_args()

    # --from-json mode: load existing JSON and save to DB, no browser needed
    if args.from_json:
        json_path = Path(args.from_json)
        if not json_path.exists():
            print(f"ERROR: JSON file not found: {json_path}")
            return
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        all_records = data.get("players", [])
        print(f"Loaded {len(all_records)} records from {json_path}")
        await save_to_db(all_records, args.season)
        return

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    pw = await async_playwright().start()
    browser = await pw.chromium.launch(
        headless=False,
        args=["--disable-blink-features=AutomationControlled", "--no-sandbox", "--start-maximized"],
    )

    try:
        context = await create_browser_context(browser)
        page = await context.new_page()

        print(f"\nNavigating to {STATS_URL}")
        await page.goto(STATS_URL, wait_until="domcontentloaded", timeout=60000)
        await dismiss_overlays(page)

        if not await wait_for_table(page):
            print("Could not load stats table. Exiting.")
            return

        # Determine which rounds to scrape
        if args.rounds:
            rounds = [int(r.strip()) for r in args.rounds.split(",")]
        else:
            rounds = await detect_available_rounds(page)
            print(f"Detected available rounds: {rounds}")
            if not rounds:
                rounds = [1, 2]
                print(f"Could not detect rounds, defaulting to {rounds}")

        # Build position map (unless skipped)
        position_map: dict[str, str] = {}
        if not args.skip_positions:
            print("\n--- Building position map ---")
            position_map = await build_position_map(page)
        else:
            print("\nSkipping position mapping (--skip-positions)")

        all_records = []

        for round_num in rounds:
            if not await select_round(page, round_num):
                print(f"Skipping round {round_num} (could not select)")
                continue

            # Wait for table to refresh
            await asyncio.sleep(2)

            raw = await scrape_all_pages(page)
            records = parse_players(raw, round_num)

            # Merge position data
            if position_map:
                for rec in records:
                    rec["position"] = position_map.get(rec["name"], "")

            all_records.extend(records)
            print(f"  Round {round_num}: {len(records)} players with stats")

        # Build output
        output = {
            "source": "fantasy_sixnations_stats",
            "scraped_at": datetime.now(timezone.utc).isoformat(),
            "season": 2026,
            "rounds_scraped": rounds,
            "stat_columns": [c for c in STAT_COLUMNS if c != "matches_played"],
            "stat_display": {k: v for k, v in STAT_DISPLAY.items() if k != "matches_played"},
            "total_records": len(all_records),
            "players": all_records,
        }

        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        print(f"\nSaved {len(all_records)} per-round records to {args.output}")

        if args.save_db:
            print("\n--- Saving to database ---")
            await save_to_db(all_records, args.season)

        # Summary
        print(f"\n{'=' * 60}")
        for rnd in rounds:
            rnd_players = [p for p in all_records if p["round"] == rnd]
            print(f"Round {rnd}: {len(rnd_players)} players")
            top = sorted(rnd_players, key=lambda x: -(x.get("fantasy_points") or 0))[:5]
            for i, p in enumerate(top, 1):
                print(f"  {i}. {p['name']:<25} {p['country']:<10} {p['fantasy_points']:5.1f} pts")
        print(f"{'=' * 60}")

    finally:
        print("\nClosing browser...")
        await browser.close()
        await pw.stop()


if __name__ == "__main__":
    asyncio.run(main())
