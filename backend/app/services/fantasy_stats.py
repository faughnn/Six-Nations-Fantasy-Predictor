"""
Service for reading per-round Fantasy Six Nations stats from the database.
"""
import logging
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.models.player import Player
from app.models.stats import FantasyRoundStats

logger = logging.getLogger(__name__)

# Column metadata (unchanged from scraper constants)
STAT_COLUMNS = [
    "minutes_played", "player_of_match", "tries", "try_assists",
    "conversions", "penalties_kicked", "drop_goals", "tackles_made",
    "metres_carried", "defenders_beaten", "offloads", "fifty_22_kicks",
    "lineout_steals", "breakdown_steals", "kick_returns", "scrums_won",
    "penalties_conceded", "yellow_cards", "red_cards", "fantasy_points",
]

STAT_DISPLAY = {
    "minutes_played": "Min", "player_of_match": "POTM", "tries": "T",
    "try_assists": "As", "conversions": "C", "penalties_kicked": "Pen",
    "drop_goals": "DG", "tackles_made": "Ta", "metres_carried": "MC",
    "defenders_beaten": "DB", "offloads": "OF", "fifty_22_kicks": "50-22",
    "lineout_steals": "LS", "breakdown_steals": "BS", "kick_returns": "KR",
    "scrums_won": "SW", "penalties_conceded": "CPen", "yellow_cards": "YC",
    "red_cards": "RC", "fantasy_points": "Pts",
}


class FantasyStatsService:
    """Service to read per-round fantasy stats from the database."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_players(
        self,
        game_round: Optional[int] = None,
        country: Optional[str] = None,
        position: Optional[str] = None,
    ) -> list[dict]:
        query = select(FantasyRoundStats).options(
            selectinload(FantasyRoundStats.player)
        )

        if game_round is not None:
            query = query.where(FantasyRoundStats.round == game_round)

        result = await self.db.execute(query)
        stats = result.scalars().all()

        players = []
        for s in stats:
            p = s.player

            if country and p.country != country:
                continue
            if position and p.fantasy_position != position:
                continue

            players.append({
                "name": p.name,
                "country": p.country,
                "position": p.fantasy_position,
                "round": s.round,
                "minutes_played": s.minutes_played,
                "player_of_match": s.player_of_match,
                "tries": s.tries,
                "try_assists": s.try_assists,
                "conversions": s.conversions,
                "penalties_kicked": s.penalties_kicked,
                "drop_goals": s.drop_goals,
                "tackles_made": s.tackles_made,
                "metres_carried": s.metres_carried,
                "defenders_beaten": s.defenders_beaten,
                "offloads": s.offloads,
                "fifty_22_kicks": s.fifty_22_kicks,
                "lineout_steals": s.lineout_steals,
                "breakdown_steals": s.breakdown_steals,
                "kick_returns": s.kick_returns,
                "scrums_won": s.scrums_won,
                "penalties_conceded": s.penalties_conceded,
                "yellow_cards": s.yellow_cards,
                "red_cards": s.red_cards,
                "fantasy_points": float(s.fantasy_points) if s.fantasy_points else 0,
            })

        return players

    async def get_metadata(self) -> dict:
        # Get distinct rounds
        rounds_q = select(FantasyRoundStats.round).distinct()
        result = await self.db.execute(rounds_q)
        rounds_scraped = sorted([row[0] for row in result.fetchall()])

        # Get total count
        count_q = select(func.count(FantasyRoundStats.id))
        result = await self.db.execute(count_q)
        total_records = result.scalar() or 0

        # Get latest scraped_at
        latest_q = select(func.max(FantasyRoundStats.scraped_at))
        result = await self.db.execute(latest_q)
        scraped_at = result.scalar()

        return {
            "scraped_at": scraped_at.isoformat() if scraped_at else None,
            "season": 2026,
            "rounds_scraped": rounds_scraped,
            "total_records": total_records,
            "stat_columns": STAT_COLUMNS,
            "stat_display": STAT_DISPLAY,
        }

    async def get_countries(self) -> list[str]:
        query = (
            select(Player.country)
            .join(FantasyRoundStats, FantasyRoundStats.player_id == Player.id)
            .distinct()
            .order_by(Player.country)
        )
        result = await self.db.execute(query)
        return [row[0] for row in result.fetchall() if row[0]]

    async def get_positions(self) -> list[str]:
        query = (
            select(Player.fantasy_position)
            .join(FantasyRoundStats, FantasyRoundStats.player_id == Player.id)
            .distinct()
            .order_by(Player.fantasy_position)
        )
        result = await self.db.execute(query)
        return [row[0] for row in result.fetchall() if row[0]]

    async def get_rounds(self) -> list[int]:
        query = select(FantasyRoundStats.round).distinct().order_by(FantasyRoundStats.round)
        result = await self.db.execute(query)
        return [row[0] for row in result.fetchall()]
