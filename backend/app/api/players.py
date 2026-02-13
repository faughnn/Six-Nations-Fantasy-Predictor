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
    PlayerValueAnalysis,
    PlayerProjection,
    Country,
    Position,
    StatsHistory,
)
from app.models import SixNationsStats, ClubStats
from app.services.scoring import is_forward as is_forward_position
from app.services.derived_stats import compute_fantasy_points_for_club_stat, compute_derived_stats

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
        if selection:
            available = True
            starting = selection.is_starting
        elif price_record and price_record.availability:
            # Fallback: derive from scraped availability on FantasyPrice
            available = price_record.availability != "not_playing"
            starting = price_record.availability == "starting"
        else:
            available = False
            starting = None

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


FORWARD_POSITIONS = {"prop", "hooker", "second_row", "back_row"}


@router.get("/value-analysis", response_model=List[PlayerValueAnalysis])
async def get_value_analysis(
    season: int = 2026,
    game_round: int = 1,
    country: Optional[Country] = None,
    position: Optional[Position] = None,
    sort_by: str = Query(default="try_ev_per_star"),
    db: AsyncSession = Depends(get_db),
):
    """
    Comprehensive player value analysis combining prices, odds, historical
    stats, and expected value calculations.
    """
    query = select(Player).options(
        selectinload(Player.prices),
        selectinload(Player.odds),
        selectinload(Player.predictions),
        selectinload(Player.team_selections),
        selectinload(Player.six_nations_stats),
        selectinload(Player.club_stats),
    )

    if country:
        query = query.where(Player.country == country.value)
    if position:
        query = query.where(Player.fantasy_position == position.value)

    result = await db.execute(query)
    players = result.scalars().all()

    analyses = []
    for player in players:
        # Price for this season/round
        price_record = next(
            (p for p in player.prices if p.season == season and p.round == game_round),
            None,
        )
        if not price_record:
            continue  # Only include players with a price for this round

        price = float(price_record.price)
        ownership_pct = float(price_record.ownership_pct) if price_record.ownership_pct else None

        is_forward = player.fantasy_position in FORWARD_POSITIONS
        try_points = 15 if is_forward else 10

        # Odds
        odds_record = next(
            (o for o in player.odds if o.season == season and o.round == game_round),
            None,
        )
        anytime_try_odds = (
            float(odds_record.anytime_try_scorer)
            if odds_record and odds_record.anytime_try_scorer
            else None
        )

        implied_try_prob = (1.0 / anytime_try_odds) if anytime_try_odds else None
        expected_try_points = (implied_try_prob * try_points) if implied_try_prob else None
        try_ev_per_star = (expected_try_points / price) if expected_try_points and price else None

        # Team selection (with availability fallback)
        selection = next(
            (s for s in player.team_selections if s.season == season and s.round == game_round),
            None,
        )
        if selection:
            is_starting = selection.is_starting
        elif price_record and price_record.availability:
            is_starting = price_record.availability == "starting"
        else:
            is_starting = None

        # Historical stats aggregation (all Six Nations + club stats)
        sn_stats = player.six_nations_stats or []
        cl_stats = player.club_stats or []
        total_games = len(sn_stats) + len(cl_stats)

        # Aggregate across both stat types
        total_tries = sum(s.tries for s in sn_stats) + sum(s.tries for s in cl_stats)
        total_tackles = sum(s.tackles_made for s in sn_stats) + sum(s.tackles_made for s in cl_stats)
        total_metres = sum(s.metres_carried for s in sn_stats) + sum(s.metres_carried for s in cl_stats)
        total_db = sum(s.defenders_beaten for s in sn_stats) + sum(s.defenders_beaten for s in cl_stats)
        total_to = sum(s.turnovers_won for s in sn_stats) + sum(s.turnovers_won for s in cl_stats)
        total_offloads = sum(s.offloads for s in sn_stats) + sum(s.offloads for s in cl_stats)

        avg_tries = (total_tries / total_games) if total_games else None
        avg_tackles = (total_tackles / total_games) if total_games else None
        avg_metres = (total_metres / total_games) if total_games else None
        avg_db = (total_db / total_games) if total_games else None
        avg_to = (total_to / total_games) if total_games else None
        avg_offloads = (total_offloads / total_games) if total_games else None

        # Fantasy points average (Six Nations only — club stats don't have fantasy_points)
        sn_with_fp = [s for s in sn_stats if s.fantasy_points is not None]
        avg_fantasy_points = (
            float(sum(float(s.fantasy_points) for s in sn_with_fp) / len(sn_with_fp))
            if sn_with_fp
            else None
        )

        # Prediction
        prediction = next(
            (p for p in player.predictions if p.season == season and p.round == game_round),
            None,
        )
        predicted_points = float(prediction.predicted_points) if prediction else None

        # Overall EV: use predicted_points if available, fallback to avg_fantasy_points
        base_points = predicted_points if predicted_points is not None else avg_fantasy_points
        overall_ev_per_star = (base_points / price) if base_points and price else None

        # Fixture context — derive opponent from scraped data or Six Nations stats
        # We don't store opponent on FantasyPrice, so check team_selection or leave None
        opponent = None
        is_home = None

        analyses.append(PlayerValueAnalysis(
            id=player.id,
            name=player.name,
            country=player.country,
            fantasy_position=player.fantasy_position,
            is_forward=is_forward,
            price=price,
            ownership_pct=ownership_pct,
            opponent=opponent,
            is_home=is_home,
            is_starting=is_starting,
            anytime_try_odds=anytime_try_odds,
            implied_try_prob=round(implied_try_prob, 4) if implied_try_prob else None,
            try_points=try_points,
            expected_try_points=round(expected_try_points, 2) if expected_try_points else None,
            try_ev_per_star=round(try_ev_per_star, 4) if try_ev_per_star else None,
            avg_fantasy_points=round(avg_fantasy_points, 2) if avg_fantasy_points else None,
            avg_tries_per_game=round(avg_tries, 3) if avg_tries is not None else None,
            avg_tackles_per_game=round(avg_tackles, 2) if avg_tackles is not None else None,
            avg_metres_per_game=round(avg_metres, 2) if avg_metres is not None else None,
            avg_defenders_beaten_per_game=round(avg_db, 2) if avg_db is not None else None,
            avg_turnovers_per_game=round(avg_to, 3) if avg_to is not None else None,
            avg_offloads_per_game=round(avg_offloads, 3) if avg_offloads is not None else None,
            total_games=total_games if total_games else None,
            predicted_points=predicted_points,
            overall_ev_per_star=round(overall_ev_per_star, 4) if overall_ev_per_star else None,
        ))

    # Sort by requested field (descending — higher is better for EV metrics)
    valid_sort_fields = {
        "try_ev_per_star", "overall_ev_per_star", "price", "ownership_pct",
        "anytime_try_odds", "implied_try_prob", "expected_try_points",
        "avg_fantasy_points", "avg_tries_per_game", "avg_tackles_per_game",
        "avg_metres_per_game", "avg_defenders_beaten_per_game",
        "avg_turnovers_per_game", "avg_offloads_per_game", "total_games",
        "predicted_points", "name",
    }
    if sort_by not in valid_sort_fields:
        sort_by = "try_ev_per_star"

    reverse = sort_by != "name"  # Descending for numeric, ascending for name
    analyses.sort(
        key=lambda a: (getattr(a, sort_by) is not None, getattr(a, sort_by) or 0),
        reverse=reverse,
    )

    return analyses


@router.get("/projections", response_model=List[PlayerProjection])
async def get_projections(
    season: int = 2026,
    game_round: int = 1,
    country: Optional[Country] = None,
    position: Optional[Position] = None,
    sort_by: str = Query(default="predicted_points"),
    db: AsyncSession = Depends(get_db),
):
    """
    Player projections derived from historical stats (club + international),
    combined with price and odds data for team-picking decisions.
    """
    query = select(Player).options(
        selectinload(Player.prices),
        selectinload(Player.odds),
        selectinload(Player.six_nations_stats),
        selectinload(Player.club_stats),
    )

    if country:
        query = query.where(Player.country == country.value)
    if position:
        query = query.where(Player.fantasy_position == position.value)

    result = await db.execute(query)
    players = result.scalars().all()

    projections = []
    for player in players:
        sn_stats = player.six_nations_stats or []
        cl_stats = player.club_stats or []

        derived = compute_derived_stats(sn_stats, cl_stats, player.fantasy_position)

        if derived.total_games == 0:
            continue

        # Price for this season/round
        price_record = next(
            (p for p in player.prices if p.season == season and p.round == game_round),
            None,
        )
        price = float(price_record.price) if price_record else None

        # Points per star
        pps = None
        if derived.predicted_points and price and price > 0:
            pps = round(derived.predicted_points / price, 2)

        # Odds
        odds_record = next(
            (o for o in player.odds if o.season == season and o.round == game_round),
            None,
        )
        anytime_try_odds = (
            float(odds_record.anytime_try_scorer)
            if odds_record and odds_record.anytime_try_scorer
            else None
        )

        projections.append(PlayerProjection(
            id=player.id,
            name=player.name,
            country=player.country,
            fantasy_position=player.fantasy_position,
            price=price,
            predicted_points=derived.predicted_points,
            points_per_star=pps,
            avg_tries=derived.avg_tries,
            avg_tackles=derived.avg_tackles,
            avg_metres=derived.avg_metres,
            avg_turnovers=derived.avg_turnovers,
            avg_defenders_beaten=derived.avg_defenders_beaten,
            avg_offloads=derived.avg_offloads,
            expected_minutes=derived.expected_minutes,
            start_rate=derived.start_rate,
            points_per_minute=derived.points_per_minute,
            anytime_try_odds=anytime_try_odds,
            opponent=None,
            home_away=None,
            total_games=derived.total_games,
        ))

    # Sort
    valid_sort_fields = {
        "predicted_points", "points_per_star", "price", "avg_tries",
        "avg_tackles", "avg_metres", "avg_turnovers", "avg_defenders_beaten",
        "expected_minutes", "start_rate", "points_per_minute",
        "anytime_try_odds", "total_games", "name",
    }
    if sort_by not in valid_sort_fields:
        sort_by = "predicted_points"

    reverse = sort_by != "name"
    projections.sort(
        key=lambda p: (getattr(p, sort_by) is not None, getattr(p, sort_by) or 0),
        reverse=reverse,
    )

    return projections


@router.post("/backfill/club-fantasy-points")
async def backfill_club_fantasy_points(db: AsyncSession = Depends(get_db)):
    """Backfill fantasy_points for all ClubStats that don't have them."""
    result = await db.execute(
        select(ClubStats, Player.fantasy_position)
        .join(Player, ClubStats.player_id == Player.id)
        .where(ClubStats.fantasy_points.is_(None))
    )
    rows = result.all()
    updated = 0
    for club_stat, fantasy_position in rows:
        forward = is_forward_position(fantasy_position)
        fp = compute_fantasy_points_for_club_stat(club_stat, forward)
        club_stat.fantasy_points = fp
        updated += 1
    await db.commit()
    return {"status": "ok", "updated": updated}


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

    # Get team selection (with availability fallback)
    selection = next(
        (s for s in player.team_selections if s.season == season and s.round == game_round),
        None
    )
    if selection:
        detail_available = True
        detail_starting = selection.is_starting
    elif price_record and price_record.availability:
        detail_available = price_record.availability != "not_playing"
        detail_starting = price_record.availability == "starting"
    else:
        detail_available = False
        detail_starting = None

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
        is_available=detail_available,
        is_starting=detail_starting,
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


