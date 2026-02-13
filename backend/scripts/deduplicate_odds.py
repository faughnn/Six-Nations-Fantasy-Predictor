"""
One-time script to deduplicate odds and match_odds records, then add unique constraints.

The dedup bug was caused by including match_date in the lookup key. Scraping on
different days created duplicate rows for the same player/round or match/round.

This script:
1. Deduplicates match_odds by (season, round, home_team, away_team), keeping latest scraped_at
2. Deduplicates odds by (player_id, season, round), keeping latest scraped_at
3. Adds unique constraints to prevent future duplicates

Usage:
    cd fantasy-six-nations
    docker-compose exec backend python -m scripts.deduplicate_odds
"""
import asyncio
import logging

from sqlalchemy import text

from app.database import async_session

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def deduplicate():
    async with async_session() as db:
        # --- Deduplicate match_odds ---
        result = await db.execute(text("""
            DELETE FROM match_odds
            WHERE id NOT IN (
                SELECT DISTINCT ON (season, round, home_team, away_team) id
                FROM match_odds
                ORDER BY season, round, home_team, away_team, scraped_at DESC
            )
        """))
        mo_deleted = result.rowcount
        logger.info(f"Deleted {mo_deleted} duplicate match_odds rows")

        # --- Deduplicate odds ---
        result = await db.execute(text("""
            DELETE FROM odds
            WHERE id NOT IN (
                SELECT DISTINCT ON (player_id, season, round) id
                FROM odds
                ORDER BY player_id, season, round, scraped_at DESC
            )
        """))
        o_deleted = result.rowcount
        logger.info(f"Deleted {o_deleted} duplicate odds rows")

        await db.commit()
        logger.info("Deduplication complete")

        # --- Add unique constraints (idempotent: skip if already exists) ---
        for stmt, name in [
            (
                "ALTER TABLE odds ADD CONSTRAINT uq_odds_player_season_round "
                "UNIQUE (player_id, season, round)",
                "uq_odds_player_season_round",
            ),
            (
                "ALTER TABLE match_odds ADD CONSTRAINT uq_match_odds_season_round_teams "
                "UNIQUE (season, round, home_team, away_team)",
                "uq_match_odds_season_round_teams",
            ),
        ]:
            try:
                await db.execute(text(stmt))
                await db.commit()
                logger.info(f"Added constraint {name}")
            except Exception as e:
                await db.rollback()
                if "already exists" in str(e):
                    logger.info(f"Constraint {name} already exists, skipping")
                else:
                    logger.error(f"Failed to add constraint {name}: {e}")


if __name__ == "__main__":
    asyncio.run(deduplicate())
