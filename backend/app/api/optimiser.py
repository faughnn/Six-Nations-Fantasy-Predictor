from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import Player, FantasyPrice, TeamSelection, Prediction
from app.schemas.team import OptimiseRequest, OptimisedTeam
from app.services.optimiser import optimise_team, OptimiserPlayer

router = APIRouter()


@router.post("", response_model=OptimisedTeam)
async def optimise(
    request: OptimiseRequest,
    db: AsyncSession = Depends(get_db),
):
    """Generate optimal team selection"""
    season = 2025  # Current season

    # Get all players with their data
    query = select(Player).options(
        selectinload(Player.prices),
        selectinload(Player.predictions),
        selectinload(Player.team_selections),
    )

    result = await db.execute(query)
    players = result.scalars().all()

    # Build OptimiserPlayer list
    optimiser_players = []
    for player in players:
        # Get price for this round
        price_record = next(
            (p for p in player.prices if p.season == season and p.round == request.round),
            None
        )
        if not price_record:
            continue

        # Get prediction
        prediction = next(
            (p for p in player.predictions if p.season == season and p.round == request.round),
            None
        )
        if not prediction:
            continue

        # Get team selection
        selection = next(
            (s for s in player.team_selections if s.season == season and s.round == request.round),
            None
        )

        optimiser_players.append(OptimiserPlayer(
            id=player.id,
            name=player.name,
            country=player.country,
            fantasy_position=player.fantasy_position,
            price=float(price_record.price),
            predicted_points=float(prediction.predicted_points),
            is_available=selection is not None,
            is_starting=selection.is_starting if selection else None,
        ))

    # Run optimiser
    result = optimise_team(
        players=optimiser_players,
        budget=request.budget,
        max_per_country=request.max_per_country,
        locked_players=request.locked_players,
        excluded_players=request.excluded_players,
        include_bench=request.include_bench,
    )

    return result
