"""
Service to sync player data from rugbypy into our database.
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from rugbypy.player import fetch_all_players, fetch_player_stats
from rugbypy.match import fetch_matches

from app.models import Player, PlayerClub, SixNationsStats, ClubStats
from app.services.scoring import is_forward
from app.services.derived_stats import compute_fantasy_points_for_club_stat

logger = logging.getLogger(__name__)

# Six Nations countries
SIX_NATIONS_COUNTRIES = {"Ireland", "England", "France", "Wales", "Scotland", "Italy"}

# Map rugbypy team names to our country names
TEAM_TO_COUNTRY = {
    "Ireland": "Ireland",
    "England": "England",
    "France": "France",
    "Wales": "Wales",
    "Scotland": "Scotland",
    "Italy": "Italy",
}

# Map rugbypy positions to fantasy positions
POSITION_TO_FANTASY = {
    "Loosehead Prop": "prop",
    "Tighthead Prop": "prop",
    "Prop": "prop",
    "Hooker": "hooker",
    "Lock": "second_row",
    "Second Row": "second_row",
    "Blindside Flanker": "back_row",
    "Openside Flanker": "back_row",
    "Flanker": "back_row",
    "Number Eight": "back_row",
    "No. 8": "back_row",
    "Scrum Half": "scrum_half",
    "Scrumhalf": "scrum_half",
    "Fly Half": "out_half",
    "Flyhalf": "out_half",
    "Out Half": "out_half",
    "Outhalf": "out_half",
    "Inside Centre": "centre",
    "Outside Centre": "centre",
    "Centre": "centre",
    "Wing": "back_3",
    "Winger": "back_3",
    "Full Back": "back_3",
    "Fullback": "back_3",
}

# Competition mapping
COMPETITION_TO_LEAGUE = {
    "Six Nations": "Six Nations",
    "Top 14": "Top 14",
    "Premiership Rugby": "Premiership",
    "Gallagher Premiership": "Premiership",
    "United Rugby Championship": "URC",
    "Pro14": "URC",
    "European Rugby Champions Cup": "Champions Cup",
    "Challenge Cup": "Challenge Cup",
    "Rugby World Cup": "World Cup",
}


def parse_date(date_str: str) -> datetime:
    """Parse date string from rugbypy format (YYYYMMDD)."""
    return datetime.strptime(str(date_str), "%Y%m%d").date()


def get_fantasy_position(position: str) -> str:
    """Map rugbypy position to fantasy position."""
    if not position:
        return "back_row"  # Default

    # Try exact match first
    if position in POSITION_TO_FANTASY:
        return POSITION_TO_FANTASY[position]

    # Try case-insensitive partial match
    position_lower = position.lower()
    for key, value in POSITION_TO_FANTASY.items():
        if key.lower() in position_lower or position_lower in key.lower():
            return value

    # Default based on keywords
    if "prop" in position_lower:
        return "prop"
    elif "hook" in position_lower:
        return "hooker"
    elif "lock" in position_lower or "second" in position_lower:
        return "second_row"
    elif "flank" in position_lower or "eight" in position_lower or "back row" in position_lower:
        return "back_row"
    elif "scrum" in position_lower:
        return "scrum_half"
    elif "fly" in position_lower or "out" in position_lower or "10" in position_lower:
        return "out_half"
    elif "centre" in position_lower or "center" in position_lower:
        return "centre"
    elif "wing" in position_lower or "full" in position_lower or "back" in position_lower:
        return "back_3"

    return "back_row"  # Default


def is_kicker_position(position: str) -> bool:
    """Determine if position is typically a kicker."""
    if not position:
        return False
    position_lower = position.lower()
    return "fly" in position_lower or "out" in position_lower or "full" in position_lower


class RugbypySync:
    """Sync data from rugbypy to our database."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_or_create_player(
        self,
        external_id: str,
        name: str,
        country: str,
        position: str,
        height: Optional[int] = None,
        weight: Optional[int] = None,
    ) -> Player:
        """Get existing player or create new one."""
        # Try to find by external_id first
        query = select(Player).where(Player.external_id == external_id)
        result = await self.db.execute(query)
        player = result.scalars().first()

        if player:
            # Update fields if changed
            player.name = name
            player.height = height
            player.weight = weight
            return player

        # Try to find by name and country
        query = select(Player).where(Player.name == name, Player.country == country)
        result = await self.db.execute(query)
        player = result.scalars().first()

        if player:
            player.external_id = external_id
            player.height = height
            player.weight = weight
            return player

        # Create new player
        fantasy_position = get_fantasy_position(position)
        player = Player(
            external_id=external_id,
            name=name,
            country=country,
            fantasy_position=fantasy_position,
            is_kicker=is_kicker_position(position),
            height=height,
            weight=weight,
        )
        self.db.add(player)
        return player

    async def sync_six_nations_players(self) -> Dict[str, Any]:
        """
        Sync all Six Nations players from rugbypy.
        Returns stats about the sync operation.
        """
        logger.info("Fetching all players from rugbypy...")
        all_players_df = fetch_all_players()

        created = 0
        updated = 0
        skipped = 0
        errors = []

        for _, row in all_players_df.iterrows():
            player_id = str(row["player_id"])
            player_name = row["player_name"]

            try:
                # Fetch player stats to get their team/country
                stats_df = fetch_player_stats(player_id)

                if stats_df.empty:
                    skipped += 1
                    continue

                # Check if they've played for a Six Nations team
                six_nations_stats = stats_df[stats_df["competition"].str.contains("Six Nations", na=False)]

                if six_nations_stats.empty:
                    skipped += 1
                    continue

                # Get the team they played for in Six Nations
                team = six_nations_stats.iloc[-1]["team"]  # Most recent

                if team not in TEAM_TO_COUNTRY:
                    skipped += 1
                    continue

                country = TEAM_TO_COUNTRY[team]
                position = stats_df.iloc[-1].get("position", "")
                height = stats_df.iloc[-1].get("height")
                weight = stats_df.iloc[-1].get("weight")

                # Convert height/weight to int if present
                if height and not pd.isna(height):
                    height = int(height)
                else:
                    height = None
                if weight and not pd.isna(weight):
                    weight = int(weight)
                else:
                    weight = None

                # Check if player exists
                query = select(Player).where(Player.external_id == player_id)
                result = await self.db.execute(query)
                existing = result.scalars().first()

                if existing:
                    updated += 1
                else:
                    created += 1

                await self.get_or_create_player(
                    external_id=player_id,
                    name=player_name,
                    country=country,
                    position=position,
                    height=height,
                    weight=weight,
                )

            except Exception as e:
                errors.append(f"{player_name}: {str(e)}")
                logger.warning(f"Error syncing player {player_name}: {e}")

        await self.db.commit()

        return {
            "created": created,
            "updated": updated,
            "skipped": skipped,
            "errors": errors[:10],  # Limit errors returned
            "total_errors": len(errors),
        }

    async def sync_player_stats(self, player_id: int, external_id: str) -> Dict[str, Any]:
        """
        Sync stats for a specific player from rugbypy.
        """
        logger.info(f"Fetching stats for player {external_id}...")
        stats_df = fetch_player_stats(external_id)

        six_nations_added = 0
        club_added = 0

        for _, row in stats_df.iterrows():
            competition = row.get("competition", "")
            match_date = parse_date(row["game_date"])

            if "Six Nations" in competition:
                # Check if stat already exists
                query = select(SixNationsStats).where(
                    SixNationsStats.player_id == player_id,
                    SixNationsStats.match_date == match_date,
                )
                result = await self.db.execute(query)
                existing = result.scalars().first()

                if existing:
                    continue

                # Determine season and round from date
                year = match_date.year
                season = year if match_date.month >= 6 else year

                stat = SixNationsStats(
                    player_id=player_id,
                    season=season,
                    round=1,  # Would need match data to determine
                    match_date=match_date,
                    opponent=row.get("team_vs", "Unknown"),
                    home_away="home",  # Would need match data
                    started=True,  # Assume started
                    tries=int(row.get("tries", 0) or 0),
                    try_assists=int(row.get("try_assists", 0) or 0),
                    conversions=int(row.get("conversion_goals", 0) or 0),
                    penalties_kicked=int(row.get("penalty_goals", 0) or 0),
                    drop_goals=int(row.get("drop_goals_converted", 0) or 0),
                    defenders_beaten=int(row.get("defenders_beaten", 0) or 0),
                    metres_carried=int(row.get("meters_run", 0) or 0),
                    clean_breaks=int(row.get("clean_breaks", 0) or 0),
                    offloads=int(row.get("offload", 0) or 0),
                    tackles_made=int(row.get("tackles", 0) or 0),
                    tackles_missed=int(row.get("missed_tackles", 0) or 0),
                    turnovers_won=0,  # Not directly available
                    penalties_conceded=int(row.get("penalties_conceded", 0) or 0),
                    yellow_cards=int(row.get("yellow_cards", 0) or 0),
                    red_cards=int(row.get("red_cards", 0) or 0),
                )
                self.db.add(stat)
                six_nations_added += 1

            else:
                # Club/other competition stats
                league = COMPETITION_TO_LEAGUE.get(competition, competition)

                query = select(ClubStats).where(
                    ClubStats.player_id == player_id,
                    ClubStats.match_date == match_date,
                )
                result = await self.db.execute(query)
                existing = result.scalars().first()

                if existing:
                    continue

                stat = ClubStats(
                    player_id=player_id,
                    league=league,
                    season=str(match_date.year),
                    match_date=match_date,
                    opponent=row.get("team_vs", "Unknown"),
                    home_away="home",
                    started=True,
                    tries=int(row.get("tries", 0) or 0),
                    try_assists=int(row.get("try_assists", 0) or 0),
                    conversions=int(row.get("conversion_goals", 0) or 0),
                    penalties_kicked=int(row.get("penalty_goals", 0) or 0),
                    drop_goals=int(row.get("drop_goals_converted", 0) or 0),
                    defenders_beaten=int(row.get("defenders_beaten", 0) or 0),
                    metres_carried=int(row.get("meters_run", 0) or 0),
                    clean_breaks=int(row.get("clean_breaks", 0) or 0),
                    offloads=int(row.get("offload", 0) or 0),
                    tackles_made=int(row.get("tackles", 0) or 0),
                    tackles_missed=int(row.get("missed_tackles", 0) or 0),
                    penalties_conceded=int(row.get("penalties_conceded", 0) or 0),
                    yellow_cards=int(row.get("yellow_cards", 0) or 0),
                    red_cards=int(row.get("red_cards", 0) or 0),
                )
                # Auto-calculate fantasy points for club stats
                # Look up the player to get their position
                player_query = select(Player).where(Player.id == player_id)
                player_result = await self.db.execute(player_query)
                player_obj = player_result.scalars().first()
                if player_obj:
                    forward = is_forward(player_obj.fantasy_position)
                    stat.fantasy_points = compute_fantasy_points_for_club_stat(stat, forward)

                self.db.add(stat)
                club_added += 1

        await self.db.commit()

        return {
            "six_nations_stats_added": six_nations_added,
            "club_stats_added": club_added,
        }

    async def sync_all_stats(self) -> Dict[str, Any]:
        """
        Sync stats for all players in the database.
        """
        query = select(Player).where(Player.external_id.isnot(None))
        result = await self.db.execute(query)
        players = result.scalars().all()

        total_six_nations = 0
        total_club = 0
        errors = []

        for player in players:
            try:
                stats = await self.sync_player_stats(player.id, player.external_id)
                total_six_nations += stats["six_nations_stats_added"]
                total_club += stats["club_stats_added"]
            except Exception as e:
                errors.append(f"{player.name}: {str(e)}")
                logger.warning(f"Error syncing stats for {player.name}: {e}")

        return {
            "players_processed": len(players),
            "six_nations_stats_added": total_six_nations,
            "club_stats_added": total_club,
            "errors": errors[:10],
            "total_errors": len(errors),
        }


# Need pandas for NaN checking
import pandas as pd
