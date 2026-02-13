from typing import List, Optional
from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy import select, func, case, exists
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.odds import MatchOdds, Odds
from app.models.player import Player
from app.models.prediction import FantasyPrice
from app.services.scoring import is_forward
from app.schemas.match import (
    MatchResponse,
    MatchTryScorer,
    CurrentRoundResponse,
    MatchScrapeStatus,
    RoundScrapeStatusResponse,
    TryScorerDetail,
)

router = APIRouter()

# Six Nations schedule: rounds are typically weeks apart in Feb-Mar
SIX_NATIONS_ROUNDS = 5


@router.get("/current-round", response_model=CurrentRoundResponse)
async def get_current_round(
    season: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Determine the current active round.

    Logic:
    1. Find the nearest round with match_date >= today (upcoming)
    2. If none, fall back to the most recent round with data
    3. If no data at all, default to season=current year, round=1
    """
    today = date.today()
    current_year = today.year
    target_season = season or current_year

    # Try to find the next upcoming round (match_date >= today)
    result = await db.execute(
        select(MatchOdds.season, MatchOdds.round)
        .where(MatchOdds.match_date >= today)
        .order_by(MatchOdds.match_date.asc())
        .limit(1)
    )
    row = result.first()
    if row:
        return CurrentRoundResponse(season=row[0], round=row[1])

    # Fall back to most recent round with data
    result = await db.execute(
        select(MatchOdds.season, MatchOdds.round)
        .order_by(MatchOdds.match_date.desc())
        .limit(1)
    )
    row = result.first()
    if row:
        return CurrentRoundResponse(season=row[0], round=row[1])

    # No data at all
    return CurrentRoundResponse(season=target_season, round=1)


@router.get("/status", response_model=RoundScrapeStatusResponse)
async def get_round_scrape_status(
    season: int = 2026,
    game_round: int = 1,
    db: AsyncSession = Depends(get_db),
):
    """
    Report which markets have been scraped for each match in a round.
    """
    # Get all matches for this round
    result = await db.execute(
        select(MatchOdds)
        .where(MatchOdds.season == season, MatchOdds.round == game_round)
        .order_by(MatchOdds.match_date)
    )
    matches = result.scalars().all()

    match_statuses = []
    for match in matches:
        has_handicap = match.handicap_line is not None
        has_totals = match.over_under_line is not None

        # Check if any try scorer odds exist for players on these teams
        try_scorer_result = await db.execute(
            select(func.count())
            .select_from(Odds)
            .join(Player, Odds.player_id == Player.id)
            .where(
                Odds.season == season,
                Odds.round == game_round,
                Player.country.in_([match.home_team, match.away_team]),
                Odds.anytime_try_scorer.isnot(None),
            )
        )
        try_scorer_count = try_scorer_result.scalar() or 0

        match_statuses.append(
            MatchScrapeStatus(
                home_team=match.home_team,
                away_team=match.away_team,
                match_date=match.match_date,
                has_handicap=has_handicap,
                has_totals=has_totals,
                has_try_scorer=try_scorer_count > 0,
                try_scorer_count=try_scorer_count,
            )
        )

    # Query fantasy prices for this round
    price_result = await db.execute(
        select(func.count()).select_from(FantasyPrice)
        .where(FantasyPrice.season == season, FantasyPrice.round == game_round)
    )
    price_count = price_result.scalar() or 0

    # Determine which markets are globally missing
    missing_markets = []
    if match_statuses:
        if not all(m.has_handicap for m in match_statuses):
            missing_markets.append("handicaps")
        if not all(m.has_totals for m in match_statuses):
            missing_markets.append("totals")
        if not all(m.has_try_scorer for m in match_statuses):
            missing_markets.append("try_scorer")
    else:
        # No matches at all — everything is missing
        missing_markets = ["handicaps", "totals", "try_scorer"]

    if price_count == 0:
        missing_markets.append("prices")

    return RoundScrapeStatusResponse(
        season=season,
        round=game_round,
        matches=match_statuses,
        missing_markets=missing_markets,
        has_prices=price_count > 0,
        price_count=price_count,
    )


@router.get("/tryscorers", response_model=List[TryScorerDetail])
async def get_tryscorers(
    season: int = 2026,
    game_round: int = 1,
    db: AsyncSession = Depends(get_db),
):
    """Get all players with fantasy prices for a round, enriched with tryscorer odds."""
    # Get matches for this round to map players to matches
    match_result = await db.execute(
        select(MatchOdds)
        .where(MatchOdds.season == season, MatchOdds.round == game_round)
    )
    matches = match_result.scalars().all()

    # Build country -> match label mapping
    country_to_match: dict[str, str] = {}
    for m in matches:
        label = f"{m.home_team} v {m.away_team}"
        country_to_match[m.home_team] = label
        country_to_match[m.away_team] = label

    # Get all players with a fantasy price for this round (the full roster)
    price_result = await db.execute(
        select(FantasyPrice, Player)
        .join(Player, FantasyPrice.player_id == Player.id)
        .where(FantasyPrice.season == season, FantasyPrice.round == game_round)
    )

    # Build player_id -> odds map
    odds_result = await db.execute(
        select(Odds)
        .where(
            Odds.season == season,
            Odds.round == game_round,
            Odds.anytime_try_scorer.isnot(None),
        )
    )
    odds_map: dict[int, float] = {
        o.player_id: float(o.anytime_try_scorer)
        for o in odds_result.scalars().all()
    }

    results = []
    for fp, player in price_result.all():
        try_points = 15 if is_forward(player.fantasy_position or "") else 10
        price_val = float(fp.price)
        odds_val = odds_map.get(player.id)

        implied_prob = round(1 / odds_val, 3) if odds_val and odds_val > 0 else None
        expected_try_points = round(implied_prob * try_points, 2) if implied_prob else None
        exp_pts_per_star = round(expected_try_points / price_val, 2) if expected_try_points and price_val else None

        results.append(
            TryScorerDetail(
                player_id=player.id,
                name=player.name,
                country=player.country,
                fantasy_position=player.fantasy_position or "unknown",
                match=country_to_match.get(player.country, "Unknown"),
                anytime_try_odds=odds_val,
                implied_prob=implied_prob,
                expected_try_points=expected_try_points,
                price=price_val,
                exp_pts_per_star=exp_pts_per_star,
                availability=fp.availability,
            )
        )

    return results


@router.get("", response_model=List[MatchResponse])
async def get_matches(
    season: int = 2026,
    game_round: int = 1,
    db: AsyncSession = Depends(get_db),
):
    """Get match odds and top try scorers for a given season/round."""
    # Fetch match odds
    result = await db.execute(
        select(MatchOdds)
        .where(MatchOdds.season == season, MatchOdds.round == game_round)
        .order_by(MatchOdds.match_date)
    )
    matches = result.scalars().all()

    responses = []
    for match in matches:
        # Get top try scorers for players from both teams
        odds_result = await db.execute(
            select(Odds, Player)
            .join(Player, Odds.player_id == Player.id)
            .where(
                Odds.season == season,
                Odds.round == game_round,
                Player.country.in_([match.home_team, match.away_team]),
                Odds.anytime_try_scorer.isnot(None),
            )
            .order_by(Odds.anytime_try_scorer.asc())
            .limit(6)
        )
        top_scorers = []
        for odds, player in odds_result.all():
            odds_val = float(odds.anytime_try_scorer)
            top_scorers.append(
                MatchTryScorer(
                    player_id=player.id,
                    name=player.name,
                    country=player.country,
                    odds=odds_val,
                    implied_prob=round(1 / odds_val, 3) if odds_val > 0 else 0,
                )
            )

        responses.append(
            MatchResponse(
                home_team=match.home_team,
                away_team=match.away_team,
                match_date=match.match_date,
                home_win=float(match.home_win) if match.home_win else None,
                away_win=float(match.away_win) if match.away_win else None,
                draw=float(match.draw) if match.draw else None,
                handicap_line=float(match.handicap_line) if match.handicap_line else None,
                home_handicap_odds=float(match.home_handicap_odds) if match.home_handicap_odds else None,
                away_handicap_odds=float(match.away_handicap_odds) if match.away_handicap_odds else None,
                over_under_line=float(match.over_under_line) if match.over_under_line else None,
                over_odds=float(match.over_odds) if match.over_odds else None,
                under_odds=float(match.under_odds) if match.under_odds else None,
                top_try_scorers=top_scorers,
            )
        )

    return responses
