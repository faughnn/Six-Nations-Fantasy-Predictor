"""
Standalone script to scrape Fantasy Six Nations player roster and prices.

Usage:
    python scrape_fantasy_prices.py [--output FILE] [--season YEAR] [--round NUM]

Opens a browser window for you to log in, then scrapes all player cards
from the DOM, paginating through every page automatically.
"""

import asyncio
import argparse
import json
import logging
import sys
from pathlib import Path
from datetime import datetime

# Add the backend directory to path
sys.path.insert(0, str(Path(__file__).parent))

from app.scrapers.fantasy_sixnations import FantasySixNationsScraper

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def main():
    parser = argparse.ArgumentParser(description="Scrape Fantasy Six Nations player data")
    parser.add_argument(
        "--output", "-o",
        default=f"data/fantasy_players_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
        help="Output JSON file path (default: data/fantasy_players_YYYYMMDD_HHMMSS.json)",
    )
    parser.add_argument("--season", type=int, default=2026, help="Season year (default: 2026)")
    parser.add_argument("--round", type=int, default=1, help="Round number (default: 1)")
    parser.add_argument(
        "--url",
        default="https://fantasy.sixnationsrugby.com/m6n/#/game/play/me",
        help="Fantasy Six Nations URL to scrape",
    )
    parser.add_argument(
        "--clear-session",
        action="store_true",
        help="Delete saved session and force a fresh login",
    )
    args = parser.parse_args()

    # Ensure output directory exists
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    scraper = FantasySixNationsScraper()

    if args.clear_session and scraper._session_path.exists():
        scraper._session_path.unlink()
        print("Cleared saved session — you will need to log in.")

    print(f"\nSeason: {args.season}, Round: {args.round}")
    print(f"Output: {args.output}\n")

    # Run the scraper
    raw_data = await scraper.scrape(url=args.url)

    # Parse the raw data
    players = scraper.parse(raw_data)

    # Build output
    output = {
        "season": args.season,
        "round": args.round,
        "scraped_at": datetime.utcnow().isoformat(),
        "player_count": len(players),
        "players": players,
    }

    # Save parsed players
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False, default=str)
    print(f"\nSaved {len(players)} players to {output_path}")

    # Print summary
    if players:
        print(f"\n{'=' * 60}")
        print(f"RESULTS: {len(players)} players found")
        print(f"{'=' * 60}")

        # Group by country
        by_country = {}
        for p in players:
            country = p.get("country", "Unknown")
            by_country.setdefault(country, []).append(p)

        for country, country_players in sorted(by_country.items()):
            print(f"\n{country} ({len(country_players)} players):")
            for p in sorted(country_players, key=lambda x: -(x.get("price") or 0)):
                price_str = f"{p['price']:5.1f}*" if p.get("price") else "  ???"
                pos_str = (p.get("fantasy_position") or "?").ljust(12)
                own_str = f"{p['ownership_pct']:2.0f}%" if p.get("ownership_pct") is not None else "  ?"
                avail_str = {"starting": "XV", "substitute": "SUB", "not_playing": " - "}.get(p.get("availability") or "", "  ?")
                print(f"  {price_str}  {pos_str} {p['name']:<30} {own_str:>4}  {avail_str}")
    else:
        print("\nNo players found. Check that the player list was visible in the browser.")


if __name__ == "__main__":
    asyncio.run(main())
