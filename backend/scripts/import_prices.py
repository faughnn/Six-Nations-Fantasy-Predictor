"""
Import scraped fantasy player prices from a JSON file.

Usage:
    cd fantasy-six-nations
    docker-compose exec backend python -m scripts.import_prices data/fantasy_players_20260201_233409.json
"""
import asyncio
import sys
import logging

from app.database import async_session
from app.services.import_service import import_scraped_json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main(file_path: str):
    async with async_session() as db:
        result = await import_scraped_json(db, file_path)
        logger.info(
            f"Done: {result['matched_existing']} matched, "
            f"{result['created_new']} created, "
            f"{result['prices_set']} prices set"
        )
        if result["errors"]:
            for err in result["errors"]:
                logger.warning(f"  Error: {err}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m scripts.import_prices <path-to-json>")
        sys.exit(1)
    asyncio.run(main(sys.argv[1]))
