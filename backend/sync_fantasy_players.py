"""
Targeted sync: fetch historical stats only for players in the fantasy players JSON.
"""
import json
import asyncio
import logging
import re
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session, engine
from app.models import Player
from app.models.stats import SixNationsStats, ClubStats
from app.services.rugbypy_sync import (
    RugbypySync, parse_date, get_fantasy_position, is_kicker_position,
    TEAM_TO_COUNTRY, COMPETITION_TO_LEAGUE,
)

from rugbypy.player import fetch_all_players, fetch_player_stats
import pandas as pd

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def safe_int(val, default=0):
    """Safely convert a value to int, handling NaN/None."""
    if val is None:
        return default
    try:
        import math
        if isinstance(val, float) and math.isnan(val):
            return default
        return int(val)
    except (ValueError, TypeError):
        return default

# Load fantasy players
with open("data/fantasy_players_20260201_233409.json") as f:
    fantasy_data = json.load(f)

fantasy_players = fantasy_data["players"]
logger.info(f"Loaded {len(fantasy_players)} fantasy players")


def normalize_name(name: str) -> str:
    """Normalize name for comparison: lowercase, strip accents roughly, remove punctuation."""
    name = name.lower().strip()
    # Remove periods and extra spaces
    name = name.replace(".", "").replace("'", "'")
    name = re.sub(r"\s+", " ", name)
    return name


def expand_initial(fantasy_name: str) -> tuple:
    """
    Parse fantasy name like 'D. SHEEHAN' into (initial, surname).
    Returns (first_letter, surname_lower).
    """
    fantasy_name = normalize_name(fantasy_name)
    parts = fantasy_name.split()
    if len(parts) >= 2:
        initial = parts[0][0]  # first letter
        surname = " ".join(parts[1:])
        return initial, surname
    return None, fantasy_name


def match_fantasy_to_rugbypy(fantasy_name: str, fantasy_country: str, rugbypy_players_df) -> list:
    """
    Try to match a fantasy player (e.g. 'D. SHEEHAN', 'Ireland') to rugbypy players.
    Returns list of matching (player_id, player_name) tuples.
    """
    initial, surname = expand_initial(fantasy_name)
    if initial is None:
        return []

    matches = []
    for _, row in rugbypy_players_df.iterrows():
        rp_name = normalize_name(row["player_name"])
        rp_parts = rp_name.split()

        if len(rp_parts) < 2:
            continue

        rp_first = rp_parts[0]
        rp_surname = " ".join(rp_parts[1:])

        # Check surname match and first initial match
        if rp_surname == surname and rp_first[0] == initial:
            matches.append((str(row["player_id"]), row["player_name"]))

    return matches


async def sync_player(db: AsyncSession, external_id: str, player_name: str,
                      country: str, fantasy_position: str):
    """Sync a single player and their stats."""
    try:
        stats_df = fetch_player_stats(external_id)
        if stats_df.empty:
            return 0, 0

        # Check they actually played Six Nations
        sn_stats = stats_df[stats_df["competition"].str.contains("Six Nations", na=False)]

        # Get or create player
        query = select(Player).where(Player.external_id == external_id)
        result = await db.execute(query)
        player = result.scalars().first()

        if not player:
            # Try by name and country
            query = select(Player).where(Player.name == player_name, Player.country == country)
            result = await db.execute(query)
            player = result.scalars().first()

        if not player:
            position = stats_df.iloc[-1].get("position", "") if not stats_df.empty else ""
            player = Player(
                external_id=external_id,
                name=player_name,
                country=country,
                fantasy_position=fantasy_position,
                is_kicker=is_kicker_position(position),
            )
            db.add(player)
            await db.flush()
        else:
            if not player.external_id:
                player.external_id = external_id

        # Sync Six Nations stats
        sn_added = 0
        club_added = 0

        for _, row in stats_df.iterrows():
            competition = row.get("competition", "")
            try:
                match_date = parse_date(row["game_date"])
            except Exception:
                continue

            if "Six Nations" in competition:
                query = select(SixNationsStats).where(
                    SixNationsStats.player_id == player.id,
                    SixNationsStats.match_date == match_date,
                )
                result = await db.execute(query)
                if result.scalars().first():
                    continue

                year = match_date.year
                season = year if match_date.month >= 6 else year

                stat = SixNationsStats(
                    player_id=player.id,
                    season=season,
                    round=1,
                    match_date=match_date,
                    opponent=row.get("team_vs", "Unknown"),
                    home_away="home",
                    started=True,
                    tries=safe_int(row.get("tries", 0)),
                    try_assists=safe_int(row.get("try_assists", 0)),
                    conversions=safe_int(row.get("conversion_goals", 0)),
                    penalties_kicked=safe_int(row.get("penalty_goals", 0)),
                    drop_goals=safe_int(row.get("drop_goals_converted", 0)),
                    defenders_beaten=safe_int(row.get("defenders_beaten", 0)),
                    metres_carried=safe_int(row.get("meters_run", 0)),
                    clean_breaks=safe_int(row.get("clean_breaks", 0)),
                    offloads=safe_int(row.get("offload", 0)),
                    tackles_made=safe_int(row.get("tackles", 0)),
                    tackles_missed=safe_int(row.get("missed_tackles", 0)),
                    turnovers_won=0,
                    penalties_conceded=safe_int(row.get("penalties_conceded", 0)),
                    yellow_cards=safe_int(row.get("yellow_cards", 0)),
                    red_cards=safe_int(row.get("red_cards", 0)),
                )
                db.add(stat)
                sn_added += 1

            else:
                league = COMPETITION_TO_LEAGUE.get(competition, competition)
                query = select(ClubStats).where(
                    ClubStats.player_id == player.id,
                    ClubStats.match_date == match_date,
                )
                result = await db.execute(query)
                if result.scalars().first():
                    continue

                stat = ClubStats(
                    player_id=player.id,
                    league=league,
                    season=str(match_date.year),
                    match_date=match_date,
                    opponent=row.get("team_vs", "Unknown"),
                    home_away="home",
                    started=True,
                    tries=safe_int(row.get("tries", 0)),
                    try_assists=safe_int(row.get("try_assists", 0)),
                    conversions=safe_int(row.get("conversion_goals", 0)),
                    penalties_kicked=safe_int(row.get("penalty_goals", 0)),
                    drop_goals=safe_int(row.get("drop_goals_converted", 0)),
                    defenders_beaten=safe_int(row.get("defenders_beaten", 0)),
                    metres_carried=safe_int(row.get("meters_run", 0)),
                    clean_breaks=safe_int(row.get("clean_breaks", 0)),
                    offloads=safe_int(row.get("offload", 0)),
                    tackles_made=safe_int(row.get("tackles", 0)),
                    tackles_missed=safe_int(row.get("missed_tackles", 0)),
                    penalties_conceded=safe_int(row.get("penalties_conceded", 0)),
                    yellow_cards=safe_int(row.get("yellow_cards", 0)),
                    red_cards=safe_int(row.get("red_cards", 0)),
                )
                db.add(stat)
                club_added += 1

        return sn_added, club_added

    except Exception as e:
        logger.warning(f"Error syncing {player_name}: {e}")
        return 0, 0


async def main():
    logger.info("Fetching all players from rugbypy...")
    all_rugbypy = fetch_all_players()
    logger.info(f"Found {len(all_rugbypy)} players in rugbypy")

    total_sn = 0
    total_club = 0
    matched = 0
    unmatched = []

    async with async_session() as db:
        for i, fp in enumerate(fantasy_players):
            name = fp["name"]
            country = fp["country"]
            position = fp["fantasy_position"]

            matches = match_fantasy_to_rugbypy(name, country, all_rugbypy)

            if not matches:
                unmatched.append(name)
                continue

            # Use first match (could refine with country check later)
            ext_id, rp_name = matches[0]
            matched += 1

            sn, club = await sync_player(db, ext_id, rp_name, country, position)
            total_sn += sn
            total_club += club

            if (i + 1) % 20 == 0:
                logger.info(f"Progress: {i+1}/{len(fantasy_players)} players processed")
                await db.commit()

        await db.commit()

    logger.info(f"\n=== SYNC COMPLETE ===")
    logger.info(f"Matched: {matched}/{len(fantasy_players)}")
    logger.info(f"Unmatched: {len(unmatched)}")
    logger.info(f"Six Nations stats added: {total_sn}")
    logger.info(f"Club stats added: {total_club}")
    if unmatched:
        logger.info(f"Unmatched players: {unmatched[:30]}")


if __name__ == "__main__":
    asyncio.run(main())
