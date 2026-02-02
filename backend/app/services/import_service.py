"""
Service for importing scraped fantasy player JSON into the database.
Uses fuzzy matching to link scraped names to existing Player records.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from rapidfuzz import fuzz, process

from app.models import Player, FantasyPrice

logger = logging.getLogger(__name__)

FUZZY_MATCH_THRESHOLD = 80


def _normalize_name(name: str) -> str:
    """Normalize a player name for matching."""
    if not name:
        return ""
    name = name.lower().strip()
    # Remove extra whitespace
    name = " ".join(name.split())
    return name


async def _build_player_cache(db: AsyncSession) -> Dict[str, Player]:
    """Build a lookup of normalized names -> Player objects."""
    result = await db.execute(select(Player))
    players = list(result.scalars().all())
    cache: Dict[str, Player] = {}
    for player in players:
        normalized = _normalize_name(player.name)
        cache[normalized] = player
        cache[player.name.lower()] = player
    return cache


def _fuzzy_find(name: str, cache: Dict[str, Player]) -> Optional[Player]:
    """Find a player by fuzzy name match against the cache."""
    normalized = _normalize_name(name)

    # Exact match first
    if normalized in cache:
        return cache[normalized]

    player_names = list(cache.keys())
    if not player_names:
        return None

    # token_sort_ratio handles name-order differences
    matches = process.extract(
        normalized, player_names, scorer=fuzz.token_sort_ratio, limit=3
    )
    if matches and matches[0][1] >= FUZZY_MATCH_THRESHOLD:
        return cache[matches[0][0]]

    # partial_ratio for abbreviated names like "D. SHEEHAN"
    matches = process.extract(
        normalized, player_names, scorer=fuzz.partial_ratio, limit=3
    )
    if matches and matches[0][1] >= FUZZY_MATCH_THRESHOLD:
        return cache[matches[0][0]]

    return None


async def import_scraped_json(
    db: AsyncSession, file_path: str
) -> Dict[str, Any]:
    """
    Import scraped fantasy player JSON into Player + FantasyPrice tables.

    For each player in the JSON:
    - Try to find an existing Player by fuzzy name match
    - If not found, create a new Player record
    - Create or update FantasyPrice for the given season/round

    Returns summary dict with counts and errors.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"JSON file not found: {file_path}")

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    season = data["season"]
    round_num = data["round"]
    players_data: List[Dict[str, Any]] = data["players"]

    cache = await _build_player_cache(db)

    created = 0
    matched = 0
    prices_set = 0
    errors: List[str] = []

    for entry in players_data:
        name = entry["name"]
        country = entry["country"]
        fantasy_position = entry["fantasy_position"]
        price = entry["price"]
        ownership_pct = entry.get("ownership_pct")

        # Try to find existing player
        player = _fuzzy_find(name, cache)

        if player:
            matched += 1
            # Update position/country if they were missing or different
            if player.fantasy_position != fantasy_position:
                player.fantasy_position = fantasy_position
            if player.country != country:
                player.country = country
        else:
            # Create new player
            player = Player(
                name=name,
                country=country,
                fantasy_position=fantasy_position,
            )
            db.add(player)
            await db.flush()  # Get the ID assigned
            # Add to cache for subsequent lookups
            cache[_normalize_name(name)] = player
            cache[name.lower()] = player
            created += 1

        # Create or update FantasyPrice
        existing_price_q = select(FantasyPrice).where(
            FantasyPrice.player_id == player.id,
            FantasyPrice.season == season,
            FantasyPrice.round == round_num,
        )
        result = await db.execute(existing_price_q)
        existing_price = result.scalar_one_or_none()

        if existing_price:
            existing_price.price = price
            if ownership_pct is not None:
                existing_price.ownership_pct = ownership_pct
        else:
            new_price = FantasyPrice(
                player_id=player.id,
                season=season,
                round=round_num,
                price=price,
                ownership_pct=ownership_pct,
            )
            db.add(new_price)

        prices_set += 1

    await db.commit()

    logger.info(
        f"Import complete: {matched} matched, {created} created, "
        f"{prices_set} prices set, {len(errors)} errors"
    )

    return {
        "status": "success",
        "season": season,
        "round": round_num,
        "total_players": len(players_data),
        "matched_existing": matched,
        "created_new": created,
        "prices_set": prices_set,
        "errors": errors,
    }
