"""
One-time script to backfill fantasy_points for all existing ClubStats records.

Usage:
    cd fantasy-six-nations
    docker-compose exec backend python -m scripts.backfill_club_fantasy_points
"""
import asyncio
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session
from app.models import ClubStats, Player
from app.services.scoring import is_forward
from app.services.derived_stats import compute_fantasy_points_for_club_stat

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def backfill():
    async with async_session() as db:
        # Load all club stats with their player
        result = await db.execute(
            select(ClubStats, Player.fantasy_position)
            .join(Player, ClubStats.player_id == Player.id)
            .where(ClubStats.fantasy_points.is_(None))
        )
        rows = result.all()
        logger.info(f"Found {len(rows)} club stats without fantasy_points")

        updated = 0
        for club_stat, fantasy_position in rows:
            forward = is_forward(fantasy_position)
            fp = compute_fantasy_points_for_club_stat(club_stat, forward)
            club_stat.fantasy_points = fp
            updated += 1

        await db.commit()
        logger.info(f"Updated {updated} club stats with fantasy_points")


if __name__ == "__main__":
    asyncio.run(backfill())
