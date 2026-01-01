from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import Player, FantasyPrice, TeamSelection, Prediction, Odds, PlayerClub
from app.schemas.player import (
    PlayerCreate,
    PlayerResponse,
    PlayerSummary,
    PlayerDetail,
    Country,
    Position,
    StatsHistory,
)

router = APIRouter()


@router.get("", response_model=List[PlayerSummary])
async def get_players(
    country: Optional[Country] = None,
    position: Optional[Position] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    is_available: Optional[bool] = None,
    season: int = 2025,
    game_round: int = 1,
    db: AsyncSession = Depends(get_db),
):
    """Get list of players with optional filters"""
    query = select(Player).options(
        selectinload(Player.prices),
        selectinload(Player.predictions),
        selectinload(Player.odds),
        selectinload(Player.team_selections),
        selectinload(Player.clubs),
    )

    if country:
        query = query.where(Player.country == country.value)

    if position:
        query = query.where(Player.fantasy_position == position.value)

    result = await db.execute(query)
    players = result.scalars().all()

    summaries = []
    for player in players:
        # Get current price
        price_record = next(
            (p for p in player.prices if p.season == season and p.round == game_round),
            None
        )
        price = float(price_record.price) if price_record else None

        # Apply price filters
        if min_price is not None and (price is None or price < min_price):
            continue
        if max_price is not None and (price is None or price > max_price):
            continue

        # Get team selection
        selection = next(
            (s for s in player.team_selections if s.season == season and s.round == game_round),
            None
        )
        available = selection is not None
        starting = selection.is_starting if selection else None

        if is_available is not None and available != is_available:
            continue

        # Get prediction
        prediction = next(
            (p for p in player.predictions if p.season == season and p.round == game_round),
            None
        )
        predicted_points = float(prediction.predicted_points) if prediction else None

        # Get odds
        odds_record = next(
            (o for o in player.odds if o.season == season and o.round == game_round),
            None
        )
        anytime_try_odds = float(odds_record.anytime_try_scorer) if odds_record and odds_record.anytime_try_scorer else None

        # Get club
        club_record = next(iter(player.clubs), None)

        # Calculate value metrics
        points_per_star = predicted_points / price if predicted_points and price else None
        value_score = points_per_star  # Simplified for now

        summaries.append(PlayerSummary(
            id=player.id,
            name=player.name,
            country=Country(player.country),
            fantasy_position=Position(player.fantasy_position),
            club=club_record.club if club_record else None,
            league=club_record.league if club_record else None,
            price=price,
            is_available=available,
            is_starting=starting,
            predicted_points=predicted_points,
            points_per_star=round(points_per_star, 2) if points_per_star else None,
            value_score=round(value_score, 2) if value_score else None,
            recent_form=None,  # TODO: Calculate from recent stats
            anytime_try_odds=anytime_try_odds,
        ))

    return summaries


@router.get("/{player_id}", response_model=PlayerDetail)
async def get_player(
    player_id: int,
    season: int = 2025,
    game_round: int = 1,
    db: AsyncSession = Depends(get_db),
):
    """Get detailed player information"""
    query = select(Player).options(
        selectinload(Player.prices),
        selectinload(Player.predictions),
        selectinload(Player.odds),
        selectinload(Player.team_selections),
        selectinload(Player.clubs),
        selectinload(Player.six_nations_stats),
        selectinload(Player.club_stats),
    ).where(Player.id == player_id)

    result = await db.execute(query)
    player = result.scalar_one_or_none()

    if not player:
        raise HTTPException(status_code=404, detail="Player not found")

    # Get current price
    price_record = next(
        (p for p in player.prices if p.season == season and p.round == game_round),
        None
    )
    price = float(price_record.price) if price_record else None

    # Get team selection
    selection = next(
        (s for s in player.team_selections if s.season == season and s.round == game_round),
        None
    )

    # Get prediction
    prediction = next(
        (p for p in player.predictions if p.season == season and p.round == game_round),
        None
    )

    # Get odds
    odds_record = next(
        (o for o in player.odds if o.season == season and o.round == game_round),
        None
    )

    # Get club
    club_record = next(iter(player.clubs), None)

    # Build stats history
    six_nations_history = [
        StatsHistory(
            match_date=s.match_date,
            opponent=s.opponent,
            fantasy_points=float(s.fantasy_points) if s.fantasy_points else None,
            tries=s.tries,
            tackles_made=s.tackles_made,
            metres_carried=s.metres_carried,
        )
        for s in player.six_nations_stats
    ]

    club_history = [
        StatsHistory(
            match_date=s.match_date,
            opponent=s.opponent,
            fantasy_points=None,  # Club stats don't have fantasy points
            tries=s.tries,
            tackles_made=s.tackles_made,
            metres_carried=s.metres_carried,
        )
        for s in player.club_stats
    ]

    predicted_points = float(prediction.predicted_points) if prediction else None
    points_per_star = predicted_points / price if predicted_points and price else None

    return PlayerDetail(
        id=player.id,
        name=player.name,
        country=Country(player.country),
        fantasy_position=Position(player.fantasy_position),
        is_kicker=player.is_kicker,
        club=club_record.club if club_record else None,
        league=club_record.league if club_record else None,
        price=price,
        is_available=selection is not None,
        is_starting=selection.is_starting if selection else None,
        predicted_points=predicted_points,
        points_per_star=round(points_per_star, 2) if points_per_star else None,
        value_score=round(points_per_star, 2) if points_per_star else None,
        anytime_try_odds=float(odds_record.anytime_try_scorer) if odds_record and odds_record.anytime_try_scorer else None,
        six_nations_stats=six_nations_history,
        club_stats=club_history,
    )


@router.post("", response_model=PlayerResponse)
async def create_player(
    player: PlayerCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new player"""
    db_player = Player(
        name=player.name,
        country=player.country.value,
        fantasy_position=player.fantasy_position.value,
        is_kicker=player.is_kicker,
    )
    db.add(db_player)
    await db.commit()
    await db.refresh(db_player)
    return db_player


@router.get("/compare", response_model=List[PlayerSummary])
async def compare_players(
    game_round: int,
    position: Optional[Position] = None,
    db: AsyncSession = Depends(get_db),
):
    """Get all available players for comparison"""
    return await get_players(
        position=position,
        is_available=True,
        game_round=game_round,
        db=db,
    )
