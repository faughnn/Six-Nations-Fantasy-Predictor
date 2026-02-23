from typing import List, Optional
from datetime import date, datetime

from fastapi import APIRouter, Depends
from sqlalchemy import select, func, case, exists
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.odds import MatchOdds, Odds
from app.models.player import Player
from app.models.prediction import FantasyPrice
from app.models.scrape_run import ScrapeRun
from app.models.stats import FantasyRoundStats
from app.fixtures import is_match_played, get_round_fixtures, get_current_round as fixtures_current_round
from app.services.scoring import is_forward
from app.services.validation_service import validate_round_data
from app.schemas.match import (
    MatchResponse,
    MatchTryScorer,
    CurrentRoundResponse,
    MatchScrapeStatus,
    RoundScrapeStatusResponse,
    TryScorerDetail,
    MarketStatus,
    SquadStatus,
    EnrichedMatchScrapeStatus,
    DatasetStatus,
    ValidationWarning,
    ScrapeRunSummary,
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
    Determine the current active round from the hardcoded schedule.

    Uses fixture kickoff times to find the earliest round with unplayed matches.
    """
    target_season = season or date.today().year
    current = fixtures_current_round(target_season)
    return CurrentRoundResponse(season=target_season, round=current)


@router.get("/status", response_model=RoundScrapeStatusResponse)
async def get_round_scrape_status(
    season: int = 2026,
    game_round: int = 1,
    db: AsyncSession = Depends(get_db),
):
    """
    Report which markets have been scraped for each match in a round.
    Uses hardcoded schedule as the base, enriched with DB data.
    """
    fixtures = get_round_fixtures(season, game_round)

    # Build lookup of DB odds keyed by (home, away)
    result = await db.execute(
        select(MatchOdds)
        .where(MatchOdds.season == season, MatchOdds.round == game_round)
        .order_by(MatchOdds.match_date)
    )
    odds_by_match: dict[tuple[str, str], MatchOdds] = {
        (m.home_team, m.away_team): m for m in result.scalars().all()
    }

    match_statuses = []
    enriched_match_data = []  # Collect per-match data for validation
    for home, away, kickoff in fixtures:
        match = odds_by_match.get((home, away))
        has_handicap = match is not None and match.handicap_line is not None
        has_totals = match is not None and match.over_under_line is not None

        # Check if any try scorer odds exist for players on these teams
        try_scorer_result = await db.execute(
            select(func.count())
            .select_from(Odds)
            .join(Player, Odds.player_id == Player.id)
            .where(
                Odds.season == season,
                Odds.round == game_round,
                Player.country.in_([home, away]),
                Odds.anytime_try_scorer.isnot(None),
            )
        )
        try_scorer_count = try_scorer_result.scalar() or 0

        # --- Enriched data queries ---

        # Try scorer scraped_at: MAX(o.scraped_at) for players on these teams
        ts_scraped_result = await db.execute(
            select(func.max(Odds.scraped_at))
            .join(Player, Odds.player_id == Player.id)
            .where(
                Odds.season == season,
                Odds.round == game_round,
                Player.country.in_([home, away]),
                Odds.anytime_try_scorer.isnot(None),
            )
        )
        try_scorer_scraped_at = ts_scraped_result.scalar()

        # Squad count per match: starting + substitute
        squad_result = await db.execute(
            select(func.count())
            .select_from(FantasyPrice)
            .join(Player, FantasyPrice.player_id == Player.id)
            .where(
                FantasyPrice.season == season,
                FantasyPrice.round == game_round,
                Player.country.in_([home, away]),
                FantasyPrice.availability.in_(["starting", "substitute"]),
            )
        )
        squad_count = squad_result.scalar() or 0

        # Unknown availability per match
        unknown_result = await db.execute(
            select(func.count())
            .select_from(FantasyPrice)
            .join(Player, FantasyPrice.player_id == Player.id)
            .where(
                FantasyPrice.season == season,
                FantasyPrice.round == game_round,
                Player.country.in_([home, away]),
                FantasyPrice.availability.is_(None),
            )
        )
        unknown_availability = unknown_result.scalar() or 0

        # Players with odds per match (distinct player_id)
        pwo_result = await db.execute(
            select(func.count(func.distinct(Odds.player_id)))
            .select_from(Odds)
            .join(Player, Odds.player_id == Player.id)
            .where(
                Odds.season == season,
                Odds.round == game_round,
                Player.country.in_([home, away]),
                Odds.anytime_try_scorer.isnot(None),
            )
        )
        players_with_odds = pwo_result.scalar() or 0

        # MatchOdds.scraped_at applies to both handicaps and totals
        match_odds_scraped_at = match.scraped_at if match and match.scraped_at else None

        match_statuses.append(
            MatchScrapeStatus(
                home_team=home,
                away_team=away,
                match_date=kickoff.date(),
                has_handicap=has_handicap,
                has_totals=has_totals,
                has_try_scorer=try_scorer_count > 0,
                try_scorer_count=try_scorer_count,
            )
        )

        # Collect data for validation and enriched response
        enriched_match_data.append({
            "home_team": home,
            "away_team": away,
            "match_date": kickoff.date(),
            "has_handicap": has_handicap,
            "has_totals": has_totals,
            "has_try_scorer": try_scorer_count > 0,
            "try_scorer_count": try_scorer_count,
            "handicap_scraped_at": match_odds_scraped_at,
            "totals_scraped_at": match_odds_scraped_at,
            "try_scorer_scraped_at": try_scorer_scraped_at,
            "squad_count": squad_count,
            "unknown_availability": unknown_availability,
            "players_with_odds": players_with_odds,
        })

    # Query fantasy prices for this round
    price_result = await db.execute(
        select(func.count()).select_from(FantasyPrice)
        .where(FantasyPrice.season == season, FantasyPrice.round == game_round)
    )
    price_count = price_result.scalar() or 0

    # Count players with/without availability info
    avail_known_result = await db.execute(
        select(func.count()).select_from(FantasyPrice)
        .where(
            FantasyPrice.season == season,
            FantasyPrice.round == game_round,
            FantasyPrice.availability.isnot(None),
        )
    )
    availability_known = avail_known_result.scalar() or 0
    availability_unknown = price_count - availability_known

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

    # --- Enriched data: dataset timestamps ---

    # Fantasy prices: MAX(created_at) for this round
    price_ts_result = await db.execute(
        select(func.max(FantasyPrice.created_at))
        .where(FantasyPrice.season == season, FantasyPrice.round == game_round)
    )
    price_scraped_at = price_ts_result.scalar()

    # Fantasy stats: MAX(scraped_at) for this round
    stats_ts_result = await db.execute(
        select(func.max(FantasyRoundStats.scraped_at))
        .where(FantasyRoundStats.season == season, FantasyRoundStats.round == game_round)
    )
    stats_scraped_at = stats_ts_result.scalar()

    stats_count_result = await db.execute(
        select(func.count()).select_from(FantasyRoundStats)
        .where(FantasyRoundStats.season == season, FantasyRoundStats.round == game_round)
    )
    stats_count = stats_count_result.scalar() or 0

    # --- Scrape history ---
    scrape_runs_result = await db.execute(
        select(ScrapeRun)
        .where(ScrapeRun.season == season, ScrapeRun.round == game_round)
        .order_by(ScrapeRun.started_at.desc())
        .limit(20)
    )
    scrape_runs = scrape_runs_result.scalars().all()

    # --- Determine played matches ---
    played_matches = set()
    for md in enriched_match_data:
        if is_match_played(season, game_round, md["home_team"], md["away_team"]):
            played_matches.add(f"{md['home_team']} v {md['away_team']}")

    # --- Validation warnings ---
    has_prices = price_count > 0
    has_stats = stats_count > 0
    raw_warnings = validate_round_data(
        match_data=enriched_match_data,
        has_prices=has_prices,
        price_count=price_count,
        price_scraped_at=price_scraped_at,
        has_stats=has_stats,
        stats_scraped_at=stats_scraped_at,
        played_matches=played_matches,
    )

    # --- Build enriched match statuses ---
    enriched_matches = []
    for md in enriched_match_data:
        # Handicaps market status
        if md["has_handicap"] and md["handicap_scraped_at"]:
            handicaps_status = MarketStatus(status="complete", scraped_at=md["handicap_scraped_at"])
        elif md["has_handicap"]:
            handicaps_status = MarketStatus(status="complete")
        else:
            handicaps_status = MarketStatus(status="missing")

        # Totals market status
        if md["has_totals"] and md["totals_scraped_at"]:
            totals_status = MarketStatus(status="complete", scraped_at=md["totals_scraped_at"])
        elif md["has_totals"]:
            totals_status = MarketStatus(status="complete")
        else:
            totals_status = MarketStatus(status="missing")

        # Try scorer market status
        if md["has_try_scorer"] and md["try_scorer_scraped_at"]:
            if md["unknown_availability"] >= 10:
                ts_status = MarketStatus(
                    status="warning",
                    scraped_at=md["try_scorer_scraped_at"],
                    warning="Scraped before squad announcement",
                )
            else:
                ts_status = MarketStatus(status="complete", scraped_at=md["try_scorer_scraped_at"])
        elif md["has_try_scorer"]:
            ts_status = MarketStatus(status="complete")
        else:
            ts_status = MarketStatus(status="missing")

        match_label = f"{md['home_team']} v {md['away_team']}"
        enriched_matches.append(
            EnrichedMatchScrapeStatus(
                home_team=md["home_team"],
                away_team=md["away_team"],
                match_date=md["match_date"],
                is_played=match_label in played_matches,
                handicaps=handicaps_status,
                totals=totals_status,
                try_scorer=ts_status,
                squad_status=SquadStatus(
                    total=md["squad_count"],
                    unknown_availability=md["unknown_availability"],
                ),
                try_scorer_count=md["try_scorer_count"],
            )
        )

    # --- Build dataset statuses ---
    fantasy_prices_status = DatasetStatus(
        status="complete" if has_prices else "missing",
        scraped_at=price_scraped_at,
        player_count=price_count if has_prices else None,
    )

    fantasy_stats_status = DatasetStatus(
        status="complete" if has_stats else "missing",
        scraped_at=stats_scraped_at,
        player_count=stats_count if has_stats else None,
    )

    # --- Build validation warnings ---
    validation_warnings = [
        ValidationWarning(
            type=w.get("type", "unknown"),
            message=w.get("message", ""),
            match=w.get("match"),
            market=w.get("market"),
            action=w.get("action"),
            action_params=w.get("action_params"),
        )
        for w in raw_warnings
    ]

    # --- Build scrape history ---
    scrape_history = [
        ScrapeRunSummary(
            id=sr.id,
            market_type=sr.market_type,
            match_slug=sr.match_slug,
            status=sr.status,
            started_at=sr.started_at,
            completed_at=sr.completed_at,
            duration_seconds=sr.duration_seconds,
            warnings=sr.warnings,
            result_summary=sr.result_summary,
        )
        for sr in scrape_runs
    ]

    return RoundScrapeStatusResponse(
        season=season,
        round=game_round,
        matches=match_statuses,
        missing_markets=missing_markets,
        has_prices=has_prices,
        price_count=price_count,
        availability_known=availability_known,
        availability_unknown=availability_unknown,
        enriched_matches=enriched_matches,
        fantasy_prices=fantasy_prices_status,
        fantasy_stats=fantasy_stats_status,
        warnings=validation_warnings,
        last_scrape_run=scrape_history[0] if scrape_history else None,
        scrape_history=scrape_history,
    )


@router.get("/tryscorers", response_model=List[TryScorerDetail])
async def get_tryscorers(
    season: int = 2026,
    game_round: int = 1,
    db: AsyncSession = Depends(get_db),
):
    """Get all players with fantasy prices for a round, enriched with tryscorer odds."""
    # Build country -> match label mapping from hardcoded schedule
    fixtures = get_round_fixtures(season, game_round)
    country_to_match: dict[str, str] = {}
    for home, away, _ in fixtures:
        label = f"{home} v {away}"
        country_to_match[home] = label
        country_to_match[away] = label

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
                ownership_pct=float(fp.ownership_pct) if fp.ownership_pct is not None else None,
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
    """Get match fixtures and odds for a given season/round.

    Always returns fixtures from the hardcoded schedule, enriched with
    odds data from the database when available.
    """
    fixtures = get_round_fixtures(season, game_round)

    # Build lookup of DB odds keyed by (home, away)
    result = await db.execute(
        select(MatchOdds)
        .where(MatchOdds.season == season, MatchOdds.round == game_round)
    )
    odds_by_match: dict[tuple[str, str], MatchOdds] = {
        (m.home_team, m.away_team): m for m in result.scalars().all()
    }

    responses = []
    for home, away, kickoff in fixtures:
        match = odds_by_match.get((home, away))

        # Get top try scorers for players from both teams
        odds_result = await db.execute(
            select(Odds, Player)
            .join(Player, Odds.player_id == Player.id)
            .where(
                Odds.season == season,
                Odds.round == game_round,
                Player.country.in_([home, away]),
                Odds.anytime_try_scorer.isnot(None),
            )
            .order_by(Odds.anytime_try_scorer.asc())
            .limit(10)
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
                home_team=home,
                away_team=away,
                match_date=kickoff.date(),
                home_win=float(match.home_win) if match and match.home_win else None,
                away_win=float(match.away_win) if match and match.away_win else None,
                draw=float(match.draw) if match and match.draw else None,
                handicap_line=float(match.handicap_line) if match and match.handicap_line else None,
                home_handicap_odds=float(match.home_handicap_odds) if match and match.home_handicap_odds else None,
                away_handicap_odds=float(match.away_handicap_odds) if match and match.away_handicap_odds else None,
                over_under_line=float(match.over_under_line) if match and match.over_under_line else None,
                over_odds=float(match.over_odds) if match and match.over_odds else None,
                under_odds=float(match.under_odds) if match and match.under_odds else None,
                top_try_scorers=top_scorers,
            )
        )

    return responses
