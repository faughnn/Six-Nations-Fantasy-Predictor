"""
Hourly scrape orchestrator for GitHub Actions CI.

Auto-detects the current round, runs try scorer odds + fantasy prices scrapers,
and imports fantasy data to the database.

Usage:
    python scrape_hourly.py
    python scrape_hourly.py --round 4          # Override round detection
    python scrape_hourly.py --skip-odds        # Only scrape fantasy prices
    python scrape_hourly.py --skip-fantasy      # Only scrape odds
"""

import asyncio
import argparse
import logging
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.fixtures import get_current_round

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

BACKEND_DIR = Path(__file__).parent
SEASON = 2026


def run_script(description: str, cmd: list[str]) -> bool:
    """Run a subprocess and return True if it succeeded."""
    logger.info(f"Starting: {description}")
    logger.info(f"Command: {' '.join(cmd)}")
    try:
        result = subprocess.run(
            cmd,
            cwd=str(BACKEND_DIR),
            timeout=600,  # 10 minute timeout per scraper
        )
        if result.returncode == 0:
            logger.info(f"Success: {description}")
            return True
        else:
            logger.error(f"Failed: {description} (exit code {result.returncode})")
            return False
    except subprocess.TimeoutExpired:
        logger.error(f"Timeout: {description} (exceeded 10 minutes)")
        return False
    except Exception as e:
        logger.error(f"Error running {description}: {e}")
        return False


async def import_fantasy_json(json_path: str):
    """Import scraped fantasy JSON into the database."""
    from app.database import async_session
    from app.services.import_service import import_scraped_json

    async with async_session() as db:
        result = await import_scraped_json(db, json_path)
    return result


def main():
    parser = argparse.ArgumentParser(description="Hourly scrape orchestrator")
    parser.add_argument("--round", type=int, default=None, help="Override round number")
    parser.add_argument("--skip-odds", action="store_true", help="Skip try scorer odds scrape")
    parser.add_argument("--skip-fantasy", action="store_true", help="Skip fantasy prices scrape")
    args = parser.parse_args()

    round_num = args.round or get_current_round(SEASON)
    logger.info(f"Season {SEASON}, Round {round_num}")

    python = sys.executable
    results = {}

    # 1. Try scorer odds
    if not args.skip_odds:
        results["tryscorer_odds"] = run_script(
            "Try scorer odds scrape",
            [python, "scrape_oddschecker_tryscorer.py",
             "--save-db", "--season", str(SEASON), "--round", str(round_num)],
        )

    # 2. Fantasy prices
    if not args.skip_fantasy:
        json_output = f"data/fantasy_players_r{round_num}.json"
        results["fantasy_prices"] = run_script(
            "Fantasy prices scrape",
            [python, "scrape_fantasy_prices.py",
             "--headless", "--season", str(SEASON), "--round", str(round_num),
             "--output", json_output],
        )

        # 3. Import fantasy JSON to DB
        if results.get("fantasy_prices"):
            json_path = str(BACKEND_DIR / json_output)
            logger.info(f"Importing {json_path} to database...")
            try:
                result = asyncio.run(import_fantasy_json(json_path))
                logger.info(f"Import result: {result}")
                results["fantasy_import"] = True
            except Exception as e:
                logger.error(f"Import failed: {e}")
                results["fantasy_import"] = False

    # Summary
    logger.info("=" * 50)
    logger.info("SCRAPE SUMMARY")
    logger.info("=" * 50)
    for step, success in results.items():
        status = "OK" if success else "FAILED"
        logger.info(f"  {step}: {status}")

    if all(results.values()):
        logger.info("All steps completed successfully.")
        sys.exit(0)
    else:
        logger.error("Some steps failed.")
        sys.exit(1)


if __name__ == "__main__":
    main()
