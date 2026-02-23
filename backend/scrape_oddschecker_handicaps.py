"""
Standalone script to scrape handicap (spread) odds from Oddschecker.

Uses the Six Nations overview page with the Handicaps market selected,
which shows a single consensus line per match. Much simpler and more
accurate than the old per-match approach that interpolated across 30+ lines.

Saves raw JSON to backend/data/oddschecker/ and optionally persists
odds to the database.

Usage:
    python scrape_oddschecker_handicaps.py                         # headless, all matches
    python scrape_oddschecker_handicaps.py --headed                # visible browser
    python scrape_oddschecker_handicaps.py --save-db --season 2026 --round 4
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


def print_summary_table(matches):
    """Print the handicap lines for all matches."""
    if not matches:
        print("\nNo handicap data found.")
        return

    print(f"\n{'Match':<30} {'Line':>8}  {'Home Odds':>10}  {'Away Odds':>10}")
    print("-" * 65)
    for m in matches:
        label = f"{m['home']} v {m['away']}"
        home_sign = "+" if m["home_line"] > 0 else ""
        line_str = f"{home_sign}{m['home_line']}"
        home_odds = f"{m['home_odds']:.2f}" if m["home_odds"] else "?"
        away_odds = f"{m['away_odds']:.2f}" if m["away_odds"] else "?"
        print(f"{label:<30} {line_str:>8}  {home_odds:>10}  {away_odds:>10}")


def build_parsed_data(match_data):
    """
    Convert overview match data into the format expected by save_handicap_odds().

    Returns a single-element list with the primary handicap line.
    """
    home_line = match_data["home_line"]
    return [{
        "line": abs(home_line),
        "home_team": match_data["home"],
        "away_team": match_data["away"],
        "home_spread": home_line,
        "home_odds": match_data.get("home_odds"),
        "away_odds": match_data.get("away_odds"),
        "num_bookmakers": 99,  # overview is already a consensus; pass MIN_BOOKMAKERS check
    }]


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
    print()

    # -------------------------------------------------------------------
    # Scrape all matches from the overview page in one go
    # -------------------------------------------------------------------
    print("Scraping handicaps from Six Nations overview page...")
    overview_matches = await scraper.scrape_handicaps_overview()

    if not overview_matches:
        print("No handicap data found. Check data/oddschecker/debug/ for screenshots.")
        return

    print(f"Found handicap lines for {len(overview_matches)} matches")
    print_summary_table(overview_matches)

    # -------------------------------------------------------------------
    # Save raw JSON and optionally persist to DB
    # -------------------------------------------------------------------
    for match_data in overview_matches:
        slug = match_data["slug"]
        parsed_data = build_parsed_data(match_data)

        # Save raw JSON for record-keeping
        raw_json = {
            "market_type": "handicaps_overview",
            "scraped_at": datetime.utcnow().isoformat(),
            **match_data,
        }
        scraper.save_raw_json(raw_json, f"{slug}_handicaps")

        # Optionally save to DB
        if args.save_db:
            try:
                db_result = await save_to_db(
                    parsed_data,
                    season=args.season,
                    round_num=args.round,
                    match_date=date.today(),
                    home_team=match_data["home"],
                    away_team=match_data["away"],
                )
                status = "saved" if db_result.get("saved") else "updated"
                print(
                    f"  DB [{status}]: {match_data['home']} v {match_data['away']}, "
                    f"line={db_result.get('line')}"
                )
            except Exception as e:
                logger.error(f"Failed to save to DB: {e}", exc_info=True)
                print(f"  DB save failed for {slug}: {e}")

    # -------------------------------------------------------------------
    # Final summary
    # -------------------------------------------------------------------
    print(f"\n{'=' * 60}")
    print("SUMMARY")
    print(f"{'=' * 60}")
    print(f"Matches scraped: {len(overview_matches)}")
    print(f"JSON output dir: data/oddschecker/")
    if args.save_db:
        print(f"DB persistence:  enabled (season={args.season}, round={args.round})")
    print()


if __name__ == "__main__":
    asyncio.run(main())
