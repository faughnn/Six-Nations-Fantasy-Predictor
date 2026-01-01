from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from app.database import get_db
from app.models import Player, FantasyPrice, TeamSelection

router = APIRouter()


class PriceImport(BaseModel):
    player_name: str
    price: float
    ownership_pct: float = None


class PricesImportRequest(BaseModel):
    round: int
    season: int = 2025
    prices: List[PriceImport]


class TeamSelectionImport(BaseModel):
    player_name: str
    squad_position: int
    actual_position: str = None


class TeamSelectionsImportRequest(BaseModel):
    round: int
    season: int = 2025
    teams: Dict[str, List[TeamSelectionImport]]


@router.post("/prices")
async def import_prices(
    request: PricesImportRequest,
    db: AsyncSession = Depends(get_db),
):
    """Import player prices for a round"""
    imported = 0
    errors = []

    for price_data in request.prices:
        # Find player by name (use first() to handle duplicates gracefully)
        query = select(Player).where(Player.name == price_data.player_name)
        result = await db.execute(query)
        player = result.scalars().first()

        if not player:
            errors.append(f"Player not found: {price_data.player_name}")
            continue

        # Check if price already exists
        existing_query = select(FantasyPrice).where(
            FantasyPrice.player_id == player.id,
            FantasyPrice.season == request.season,
            FantasyPrice.round == request.round,
        )
        existing_result = await db.execute(existing_query)
        existing = existing_result.scalar_one_or_none()

        if existing:
            existing.price = price_data.price
            if price_data.ownership_pct:
                existing.ownership_pct = price_data.ownership_pct
        else:
            new_price = FantasyPrice(
                player_id=player.id,
                season=request.season,
                round=request.round,
                price=price_data.price,
                ownership_pct=price_data.ownership_pct,
            )
            db.add(new_price)

        imported += 1

    await db.commit()

    return {
        "status": "success",
        "imported": imported,
        "errors": errors,
    }


@router.post("/team-selection")
async def import_team_selection(
    request: TeamSelectionsImportRequest,
    db: AsyncSession = Depends(get_db),
):
    """Import team selections for a round"""
    imported = 0
    errors = []

    for country, selections in request.teams.items():
        for selection_data in selections:
            # Find player by name (use first() to handle duplicates gracefully)
            query = select(Player).where(
                Player.name == selection_data.player_name,
                Player.country == country,
            )
            result = await db.execute(query)
            player = result.scalars().first()

            if not player:
                errors.append(f"Player not found: {selection_data.player_name} ({country})")
                continue

            # Check if selection already exists
            existing_query = select(TeamSelection).where(
                TeamSelection.player_id == player.id,
                TeamSelection.season == request.season,
                TeamSelection.round == request.round,
            )
            existing_result = await db.execute(existing_query)
            existing = existing_result.scalar_one_or_none()

            is_starting = selection_data.squad_position <= 15

            if existing:
                existing.squad_position = selection_data.squad_position
                existing.is_starting = is_starting
                existing.actual_position = selection_data.actual_position
            else:
                new_selection = TeamSelection(
                    player_id=player.id,
                    season=request.season,
                    round=request.round,
                    squad_position=selection_data.squad_position,
                    is_starting=is_starting,
                    actual_position=selection_data.actual_position,
                )
                db.add(new_selection)

            imported += 1

    await db.commit()

    return {
        "status": "success",
        "imported": imported,
        "errors": errors,
    }
