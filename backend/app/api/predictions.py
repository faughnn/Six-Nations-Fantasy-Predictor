from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.auth import require_admin
from app.database import get_db
from app.models import Player, Prediction, FantasyPrice
from app.models.user import User
from app.schemas.prediction import PredictionResponse, PredictionDetail, PredictionBreakdown
from app.schemas.player import Position
from app.services.predictor import Predictor, PlayerFeatures
from app.services.scoring import is_forward

router = APIRouter()
predictor = Predictor()


@router.get("", response_model=List[PredictionResponse])
async def get_predictions(
    round: int,
    position: Optional[Position] = None,
    min_predicted: Optional[float] = None,
    sort_by: str = Query("points", pattern="^(points|value|price)$"),
    db: AsyncSession = Depends(get_db),
):
    """Get all predictions for a round"""
    query = select(Prediction).options(
        selectinload(Prediction.player)
    ).where(Prediction.round == round)

    result = await db.execute(query)
    predictions = result.scalars().all()

    if position:
        predictions = [
            p for p in predictions
            if p.player.fantasy_position == position.value
        ]

    if min_predicted is not None:
        predictions = [
            p for p in predictions
            if float(p.predicted_points) >= min_predicted
        ]

    # Sort
    if sort_by == "points":
        predictions.sort(key=lambda p: float(p.predicted_points), reverse=True)
    elif sort_by == "price":
        # Would need to join with prices
        predictions.sort(key=lambda p: float(p.predicted_points), reverse=True)

    return predictions


@router.get("/{player_id}", response_model=PredictionDetail)
async def get_prediction_detail(
    player_id: int,
    round: int = 1,
    season: int = 2025,
    db: AsyncSession = Depends(get_db),
):
    """Get detailed prediction for a player"""
    query = select(Player).options(
        selectinload(Player.predictions),
        selectinload(Player.six_nations_stats),
        selectinload(Player.club_stats),
        selectinload(Player.odds),
    ).where(Player.id == player_id)

    result = await db.execute(query)
    player = result.scalar_one_or_none()

    if not player:
        raise HTTPException(status_code=404, detail="Player not found")

    # Get existing prediction or generate one
    prediction = next(
        (p for p in player.predictions if p.season == season and p.round == round),
        None
    )

    # Build features for prediction detail
    forward = is_forward(player.fantasy_position)

    # Calculate rolling averages from recent stats
    all_stats = sorted(
        list(player.six_nations_stats) + list(player.club_stats),
        key=lambda s: s.match_date,
        reverse=True
    )

    last_3 = all_stats[:3]
    last_5 = all_stats[:5]

    tries_last_3 = sum(s.tries for s in last_3) / len(last_3) if last_3 else 0
    tackles_last_3 = sum(s.tackles_made for s in last_3) / len(last_3) if last_3 else 0
    metres_last_3 = sum(s.metres_carried for s in last_3) / len(last_3) if last_3 else 0

    # Get odds
    odds_record = next(
        (o for o in player.odds if o.season == season and o.round == round),
        None
    )
    try_odds = float(odds_record.anytime_try_scorer) if odds_record and odds_record.anytime_try_scorer else None
    try_prob = 1.0 / try_odds if try_odds and try_odds > 0 else 0.0

    # Generate prediction if not exists
    if prediction:
        predicted_points = float(prediction.predicted_points)
        confidence_lower = float(prediction.confidence_lower) if prediction.confidence_lower else predicted_points - 5
        confidence_upper = float(prediction.confidence_upper) if prediction.confidence_upper else predicted_points + 5
    else:
        features = PlayerFeatures(
            tries_last_3=tries_last_3,
            tackles_last_3=tackles_last_3,
            metres_last_3=metres_last_3,
            is_forward=forward,
            is_kicker=player.is_kicker,
        )
        pred_result = predictor.predict(features)
        predicted_points = pred_result["predicted_points"]
        confidence_lower = pred_result["confidence_lower"]
        confidence_upper = pred_result["confidence_upper"]

    # Build breakdown
    breakdown = PredictionBreakdown(
        predicted_tries=tries_last_3,
        predicted_try_prob=try_prob,
        predicted_tackles=tackles_last_3,
        predicted_metres=metres_last_3,
        predicted_turnovers=0.5,  # Estimate
        predicted_conversions=2.0 if player.is_kicker else 0.0,
        predicted_penalties=1.5 if player.is_kicker else 0.0,
    )

    # Key factors
    key_factors = []
    if tries_last_3 > 0.5:
        key_factors.append("Strong try-scoring form")
    if tackles_last_3 > 15:
        key_factors.append("High tackle count expected")
    if player.is_kicker:
        key_factors.append("Kicking duties add value")
    if forward and tries_last_3 > 0:
        key_factors.append("Forward try bonus (15 pts)")
    if not key_factors:
        key_factors.append("Consistent performer")

    return PredictionDetail(
        player_id=player.id,
        player_name=player.name,
        predicted_points=predicted_points,
        confidence_interval=(confidence_lower, confidence_upper),
        breakdown=breakdown,
        key_factors=key_factors,
    )


@router.post("/generate")
async def generate_predictions(
    round: int,
    season: int = 2025,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    """Generate predictions for all available players in a round"""
    query = select(Player).options(
        selectinload(Player.team_selections),
        selectinload(Player.six_nations_stats),
        selectinload(Player.club_stats),
        selectinload(Player.odds),
    )

    result = await db.execute(query)
    players = result.scalars().all()

    generated = 0
    for player in players:
        # Check if player is available
        selection = next(
            (s for s in player.team_selections if s.season == season and s.round == round),
            None
        )

        if not selection:
            continue

        # Calculate features
        all_stats = sorted(
            list(player.six_nations_stats) + list(player.club_stats),
            key=lambda s: s.match_date,
            reverse=True
        )

        last_3 = all_stats[:3]
        last_5 = all_stats[:5]

        features = PlayerFeatures(
            tries_last_3=sum(s.tries for s in last_3) / len(last_3) if last_3 else 0,
            tries_last_5=sum(s.tries for s in last_5) / len(last_5) if last_5 else 0,
            tackles_last_3=sum(s.tackles_made for s in last_3) / len(last_3) if last_3 else 0,
            tackles_last_5=sum(s.tackles_made for s in last_5) / len(last_5) if last_5 else 0,
            metres_last_3=sum(s.metres_carried for s in last_3) / len(last_3) if last_3 else 0,
            metres_last_5=sum(s.metres_carried for s in last_5) / len(last_5) if last_5 else 0,
            is_forward=is_forward(player.fantasy_position),
            is_kicker=player.is_kicker,
            is_starting=selection.is_starting or False,
        )

        # Get odds
        odds_record = next(
            (o for o in player.odds if o.season == season and o.round == round),
            None
        )
        if odds_record and odds_record.anytime_try_scorer:
            features.anytime_try_odds = float(odds_record.anytime_try_scorer)

        # Generate prediction
        pred_result = predictor.predict(features)

        # Save prediction
        prediction = Prediction(
            player_id=player.id,
            season=season,
            round=round,
            predicted_points=pred_result["predicted_points"],
            confidence_lower=pred_result["confidence_lower"],
            confidence_upper=pred_result["confidence_upper"],
            model_version="heuristic_v1",
        )
        db.add(prediction)
        generated += 1

    await db.commit()

    return {"status": "success", "predictions_generated": generated}
