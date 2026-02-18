"""
API endpoints for player statistics from Excel data and historical stats from database.
"""
from typing import Optional, List

from fastapi import APIRouter, Query, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import Player
from app.models.stats import SixNationsStats, ClubStats
from app.services.excel_stats import ExcelStatsService
from app.services.fantasy_stats import FantasyStatsService

router = APIRouter()


@router.get("/all")
async def get_all_stats(
    country: Optional[str] = Query(None, description="Filter by country"),
    position: Optional[str] = Query(None, description="Filter by position"),
):
    """
    Get all player stats from the Excel file.
    Optionally filter by country or position.
    """
    service = ExcelStatsService()
    players = service.get_all_players()

    # Apply filters if provided
    if country:
        players = [p for p in players if p.get("country") == country]

    if position:
        players = [p for p in players if p.get("position") == position]

    return players


@router.get("/countries")
async def get_countries():
    """Get list of available countries."""
    return ExcelStatsService.COUNTRIES


@router.get("/positions")
async def get_positions():
    """Get list of unique positions from the data."""
    service = ExcelStatsService()
    players = service.get_all_players()
    positions = sorted(set(p.get("position") for p in players if p.get("position")))
    return positions


@router.get("/historical/six-nations")
async def get_historical_six_nations_stats(
    country: Optional[str] = Query(None, description="Filter by country"),
    position: Optional[str] = Query(None, description="Filter by position"),
    season: Optional[int] = Query(None, description="Filter by season"),
    db: AsyncSession = Depends(get_db),
):
    """
    Get all Six Nations historical stats from database.
    Returns per-match stats for each player.
    """
    query = select(SixNationsStats).options(
        selectinload(SixNationsStats.player)
    ).order_by(SixNationsStats.match_date.desc())

    if season:
        query = query.join(SixNationsStats.player).where(SixNationsStats.season == season)

    result = await db.execute(query)
    stats = result.scalars().all()

    response = []
    for stat in stats:
        player = stat.player

        # Apply filters
        if country and player.country != country:
            continue
        if position and player.fantasy_position != position:
            continue

        response.append({
            "player_id": player.id,
            "player_name": player.name,
            "country": player.country,
            "fantasy_position": player.fantasy_position,
            "season": stat.season,
            "round": stat.round,
            "match_date": stat.match_date.isoformat() if stat.match_date else None,
            "opponent": stat.opponent,
            "home_away": stat.home_away,
            "actual_position": stat.actual_position,
            "started": stat.started,
            "minutes_played": stat.minutes_played,
            "tries": stat.tries,
            "try_assists": stat.try_assists,
            "conversions": stat.conversions,
            "penalties_kicked": stat.penalties_kicked,
            "drop_goals": stat.drop_goals,
            "defenders_beaten": stat.defenders_beaten,
            "metres_carried": stat.metres_carried,
            "clean_breaks": stat.clean_breaks,
            "offloads": stat.offloads,
            "fifty_22_kicks": stat.fifty_22_kicks,
            "tackles_made": stat.tackles_made,
            "tackles_missed": stat.tackles_missed,
            "turnovers_won": stat.turnovers_won,
            "lineout_steals": stat.lineout_steals,
            "scrums_won": stat.scrums_won,
            "penalties_conceded": stat.penalties_conceded,
            "yellow_cards": stat.yellow_cards,
            "red_cards": stat.red_cards,
            "player_of_match": stat.player_of_match,
            "fantasy_points": float(stat.fantasy_points) if stat.fantasy_points else None,
        })

    return response


@router.get("/historical/club")
async def get_historical_club_stats(
    country: Optional[str] = Query(None, description="Filter by country"),
    position: Optional[str] = Query(None, description="Filter by position"),
    league: Optional[str] = Query(None, description="Filter by league"),
    db: AsyncSession = Depends(get_db),
):
    """
    Get all club competition historical stats from database.
    Returns per-match stats for each player.
    """
    query = select(ClubStats).options(
        selectinload(ClubStats.player)
    ).order_by(ClubStats.match_date.desc())

    if league:
        query = query.where(ClubStats.league == league)

    result = await db.execute(query)
    stats = result.scalars().all()

    response = []
    for stat in stats:
        player = stat.player

        # Apply filters
        if country and player.country != country:
            continue
        if position and player.fantasy_position != position:
            continue

        response.append({
            "player_id": player.id,
            "player_name": player.name,
            "country": player.country,
            "fantasy_position": player.fantasy_position,
            "league": stat.league,
            "season": stat.season,
            "match_date": stat.match_date.isoformat() if stat.match_date else None,
            "opponent": stat.opponent,
            "home_away": stat.home_away,
            "started": stat.started,
            "minutes_played": stat.minutes_played,
            "tries": stat.tries,
            "try_assists": stat.try_assists,
            "conversions": stat.conversions,
            "penalties_kicked": stat.penalties_kicked,
            "drop_goals": stat.drop_goals,
            "defenders_beaten": stat.defenders_beaten,
            "metres_carried": stat.metres_carried,
            "clean_breaks": stat.clean_breaks,
            "offloads": stat.offloads,
            "tackles_made": stat.tackles_made,
            "tackles_missed": stat.tackles_missed,
            "turnovers_won": stat.turnovers_won,
            "lineout_steals": stat.lineout_steals,
            "scrums_won": stat.scrums_won,
            "penalties_conceded": stat.penalties_conceded,
            "yellow_cards": stat.yellow_cards,
            "red_cards": stat.red_cards,
        })

    return response


@router.get("/historical/positions")
async def get_historical_positions(db: AsyncSession = Depends(get_db)):
    """Get list of unique fantasy positions from players in historical stats."""
    query = select(Player.fantasy_position).distinct().order_by(Player.fantasy_position)
    result = await db.execute(query)
    positions = [row[0] for row in result.fetchall() if row[0]]
    return positions


@router.get("/historical/leagues")
async def get_historical_leagues(db: AsyncSession = Depends(get_db)):
    """Get list of unique leagues from club stats."""
    query = select(ClubStats.league).distinct().order_by(ClubStats.league)
    result = await db.execute(query)
    leagues = [row[0] for row in result.fetchall()]
    return leagues


@router.get("/historical/seasons")
async def get_historical_seasons(db: AsyncSession = Depends(get_db)):
    """Get list of unique seasons from Six Nations stats."""
    query = select(SixNationsStats.season).distinct().order_by(SixNationsStats.season.desc())
    result = await db.execute(query)
    seasons = [row[0] for row in result.fetchall()]
    return seasons


# ── Fantasy Stats (scraped from fantasy.sixnationsrugby.com) ────────────


@router.get("/fantasy")
async def get_fantasy_stats(
    game_round: Optional[int] = Query(None, description="Filter by round"),
    country: Optional[str] = Query(None, description="Filter by country"),
    position: Optional[str] = Query(None, description="Filter by position"),
    db: AsyncSession = Depends(get_db),
):
    """Get per-round scraped fantasy stats from the 2026 season."""
    service = FantasyStatsService(db)
    return await service.get_players(game_round=game_round, country=country, position=position)


@router.get("/fantasy/metadata")
async def get_fantasy_stats_metadata(db: AsyncSession = Depends(get_db)):
    """Get metadata about the scraped fantasy stats (columns, rounds, etc)."""
    service = FantasyStatsService(db)
    return await service.get_metadata()


@router.get("/fantasy/positions")
async def get_fantasy_stats_positions(db: AsyncSession = Depends(get_db)):
    """Get list of positions available in scraped fantasy stats."""
    service = FantasyStatsService(db)
    return await service.get_positions()


@router.get("/fantasy/countries")
async def get_fantasy_stats_countries(db: AsyncSession = Depends(get_db)):
    """Get list of countries available in scraped fantasy stats."""
    service = FantasyStatsService(db)
    return await service.get_countries()


@router.get("/fantasy/rounds")
async def get_fantasy_stats_rounds(db: AsyncSession = Depends(get_db)):
    """Get list of rounds that have been scraped."""
    service = FantasyStatsService(db)
    return await service.get_rounds()
