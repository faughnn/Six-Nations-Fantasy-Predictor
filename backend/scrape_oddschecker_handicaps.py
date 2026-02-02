"""
Standalone script to scrape handicap (spread) odds from Oddschecker.

Auto-discovers Six Nations match URLs and scrapes per-bookmaker handicap odds.
Saves raw JSON to backend/data/oddschecker/ and optionally persists averaged
odds to the database.

Usage:
    python scrape_oddschecker_handicaps.py                         # headless, all matches
    python scrape_oddschecker_handicaps.py --headed                # visible browser
    python scrape_oddschecker_handicaps.py --match france-v-ireland
    python scrape_oddschecker_handicaps.py --save-db --season 2026 --round 1
"""

import asyncio
import argparse
import logging
import sys
from datetime import date, datetime
from pathlib import Path

# Add the backend directory to path so `app.*` imports work
sys.path.insert(0, str(Path(__file__).parent))

from app.scrapers.oddschecker import OddscheckerScraper

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def print_summary_table(parsed_data):
    """Print the consensus handicap line to the console."""
    if not parsed_data:
        print("\nNo handicap data found.")
        return

    item = parsed_data[0]
    home_team = item.get("home_team", "?")
    spread = item.get("home_spread", -item.get("line", 0))
    home_odds = item.get("home_odds", 0) or 0
    away_odds = item.get("away_odds", 0) or 0
    num_bk = item.get("num_bookmakers", 0)

    sign = "+" if spread > 0 else ""
    print(
        f"\nConsensus handicap: {home_team} {sign}{spread:.1f}  "
        f"(home: {home_odds:.2f}, away: {away_odds:.2f}, {num_bk} bookmakers)"
    )


async def scrape_match(scraper: OddscheckerScraper, url: str, slug: str):
    """Scrape a single match URL and return (raw_data, parsed_data)."""
    logger.info(f"Scraping handicap odds: {url}")
    raw_data = await scraper.scrape_handicaps(url)
    parsed_data = scraper.parse(raw_data)

    # Save raw JSON (includes per-bookmaker breakdown)
    scraper.save_raw_json(raw_data, f"{slug}_handicaps")

    return raw_data, parsed_data


async def save_to_db(parsed_data, season: int, round_num: int, match_date: date,
                     home_team: str, away_team: str):
    """Persist handicap odds to the database via OddsService."""
    from app.database import async_session
    from app.services.odds_service import OddsService

    async with async_session() as db:
        service = OddsService(db)
        result = await service.save_handicap_odds(
            handicap_data=parsed_data,
            season=season,
            round_num=round_num,
            match_date=match_date,
            home_team=home_team,
            away_team=away_team,
        )
    return result


async def main():
    parser = argparse.ArgumentParser(
        description="Scrape Oddschecker handicap odds for Six Nations matches",
    )
    parser.add_argument(
        "--headed", action="store_true",
        help="Open a visible browser window (useful for debugging)",
    )
    parser.add_argument(
        "--match",
        metavar="SLUG",
        help="Scrape only one match, e.g. --match france-v-ireland",
    )
    parser.add_argument(
        "--save-db", action="store_true",
        help="Also persist odds to the database (requires DB running)",
    )
    parser.add_argument("--season", type=int, default=2026, help="Season year (default: 2026)")
    parser.add_argument("--round", type=int, default=1, help="Round number (default: 1)")
    args = parser.parse_args()

    headless = not args.headed
    scraper = OddscheckerScraper(headless=headless)

    print(f"Mode: {'headed' if args.headed else 'headless'}")
    print(f"Season: {args.season}, Round: {args.round}")
    if args.match:
        print(f"Single match: {args.match}")
    print()

    # -------------------------------------------------------------------
    # Determine which matches to scrape
    # -------------------------------------------------------------------
    if args.match:
        slug = args.match
        base_url = f"https://www.oddschecker.com/rugby-union/six-nations/{slug}/handicaps"
        matches_to_scrape = [{
            "slug": slug,
            "home": slug.split("-v-")[0].replace("-", " ").title() if "-v-" in slug else slug,
            "away": slug.split("-v-")[1].replace("-", " ").title() if "-v-" in slug else "",
            "url": base_url,
        }]
    else:
        print("Discovering Six Nations matches on Oddschecker...")
        browser = await scraper._init_browser()
        try:
            page = await scraper._create_page(browser)
            matches_to_scrape = await scraper.discover_six_nations_matches(page)
        finally:
            await scraper._close_browser()

        if not matches_to_scrape:
            print("No Six Nations matches found on Oddschecker. Check debug/ for snapshots.")
            return

        # Append /handicaps to each discovered URL
        for m in matches_to_scrape:
            base = m["url"].rstrip("/")
            if "/winner" in base or "/anytime" in base or "/handicap" in base:
                base = base.rsplit("/", 1)[0]
            m["url"] = f"{base}/handicaps"

        print(f"Found {len(matches_to_scrape)} matches:")
        for m in matches_to_scrape:
            print(f"  {m['home']} v {m['away']}  ({m['slug']})")
        print()

    # -------------------------------------------------------------------
    # Scrape each match
    # -------------------------------------------------------------------
    all_results = []

    for match in matches_to_scrape:
        slug = match["slug"]
        url = match["url"]
        print(f"\n{'=' * 60}")
        print(f"  {match['home']} v {match['away']}")
        print(f"  {url}")
        print(f"{'=' * 60}")

        try:
            raw_data, parsed_data = await scrape_match(scraper, url, slug)
            print_summary_table(parsed_data)
            all_results.append({
                "match": match,
                "parsed": parsed_data,
                "line_count": len(parsed_data),
                "bookmaker_count": len(raw_data.get("bookmakers", [])),
            })

            # Optionally save to DB
            if args.save_db:
                try:
                    db_result = await save_to_db(
                        parsed_data,
                        season=args.season,
                        round_num=args.round,
                        match_date=date.today(),
                        home_team=match["home"],
                        away_team=match["away"],
                    )
                    print(
                        f"\n  DB: saved={db_result.get('saved')}, "
                        f"updated={db_result.get('updated')}, "
                        f"line={db_result.get('line')}"
                    )
                except Exception as e:
                    logger.error(f"Failed to save to DB: {e}", exc_info=True)
                    print(f"\n  DB save failed: {e}")

        except Exception as e:
            logger.error(f"Failed to scrape {slug}: {e}", exc_info=True)
            print(f"\n  FAILED: {e}")
            print("  Check data/oddschecker/debug/ for screenshots and HTML dumps.")

    # -------------------------------------------------------------------
    # Final summary
    # -------------------------------------------------------------------
    print(f"\n{'=' * 60}")
    print("SUMMARY")
    print(f"{'=' * 60}")
    total_lines = sum(r["line_count"] for r in all_results)
    print(f"Matches scraped: {len(all_results)} / {len(matches_to_scrape)}")
    print(f"Total lines:     {total_lines}")
    print(f"JSON output dir: data/oddschecker/")
    if args.save_db:
        print(f"DB persistence:  enabled (season={args.season}, round={args.round})")
    print()


if __name__ == "__main__":
    asyncio.run(main())
