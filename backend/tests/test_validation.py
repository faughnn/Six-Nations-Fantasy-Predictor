import pytest
from datetime import datetime, timedelta, timezone
from app.services.validation_service import validate_round_data


def _utcnow():
    return datetime.now(timezone.utc)


def test_missing_markets_warning():
    """Matches with incomplete market data should produce warnings."""
    match_data = [{
        "home_team": "France", "away_team": "Ireland",
        "has_handicap": True, "has_totals": False, "has_try_scorer": False,
        "handicap_scraped_at": _utcnow(), "totals_scraped_at": None, "try_scorer_scraped_at": None,
        "try_scorer_count": 0, "squad_count": 23, "unknown_availability": 0,
        "players_with_odds": 0,
    }]
    warnings = validate_round_data(match_data, has_prices=True, price_count=142, price_scraped_at=_utcnow())
    types = [w["type"] for w in warnings]
    assert "missing_markets" in types


def test_squad_completeness_warning():
    """Teams with < 23 players should produce a warning."""
    match_data = [{
        "home_team": "France", "away_team": "Ireland",
        "has_handicap": True, "has_totals": True, "has_try_scorer": True,
        "handicap_scraped_at": _utcnow(), "totals_scraped_at": _utcnow(), "try_scorer_scraped_at": _utcnow(),
        "try_scorer_count": 30, "squad_count": 20, "unknown_availability": 0,
        "players_with_odds": 20,
    }]
    warnings = validate_round_data(match_data, has_prices=True, price_count=142, price_scraped_at=_utcnow())
    types = [w["type"] for w in warnings]
    assert "incomplete_squad" in types


def test_stale_odds_warning():
    """Market data > 24h old should produce a warning."""
    old = _utcnow() - timedelta(hours=30)
    match_data = [{
        "home_team": "France", "away_team": "Ireland",
        "has_handicap": True, "has_totals": True, "has_try_scorer": True,
        "handicap_scraped_at": old, "totals_scraped_at": _utcnow(), "try_scorer_scraped_at": _utcnow(),
        "try_scorer_count": 30, "squad_count": 23, "unknown_availability": 0,
        "players_with_odds": 23,
    }]
    warnings = validate_round_data(match_data, has_prices=True, price_count=142, price_scraped_at=_utcnow())
    types = [w["type"] for w in warnings]
    assert "stale_odds" in types


def test_pre_squad_odds_warning():
    """Try scorer odds scraped before squad data exists should warn."""
    match_data = [{
        "home_team": "France", "away_team": "Ireland",
        "has_handicap": True, "has_totals": True, "has_try_scorer": True,
        "handicap_scraped_at": _utcnow(), "totals_scraped_at": _utcnow(),
        "try_scorer_scraped_at": _utcnow() - timedelta(days=2),
        "try_scorer_count": 30, "squad_count": 23,
        "unknown_availability": 15,
        "players_with_odds": 20,
    }]
    warnings = validate_round_data(match_data, has_prices=True, price_count=142, price_scraped_at=_utcnow())
    types = [w["type"] for w in warnings]
    assert "pre_squad_odds" in types


def test_suspiciously_few_odds_warning():
    """Match with < 20 try scorer players should warn."""
    match_data = [{
        "home_team": "France", "away_team": "Ireland",
        "has_handicap": True, "has_totals": True, "has_try_scorer": True,
        "handicap_scraped_at": _utcnow(), "totals_scraped_at": _utcnow(), "try_scorer_scraped_at": _utcnow(),
        "try_scorer_count": 12, "squad_count": 23, "unknown_availability": 0,
        "players_with_odds": 12,
    }]
    warnings = validate_round_data(match_data, has_prices=True, price_count=142, price_scraped_at=_utcnow())
    types = [w["type"] for w in warnings]
    assert "suspiciously_few_odds" in types


def test_missing_player_odds_warning():
    """Squad known but some players lack try scorer odds should warn."""
    match_data = [{
        "home_team": "France", "away_team": "Ireland",
        "has_handicap": True, "has_totals": True, "has_try_scorer": True,
        "handicap_scraped_at": _utcnow(), "totals_scraped_at": _utcnow(), "try_scorer_scraped_at": _utcnow(),
        "try_scorer_count": 30, "squad_count": 23, "unknown_availability": 0,
        "players_with_odds": 18,
    }]
    warnings = validate_round_data(match_data, has_prices=True, price_count=142, price_scraped_at=_utcnow())
    types = [w["type"] for w in warnings]
    assert "missing_player_odds" in types


def test_no_warnings_when_all_good():
    """Complete, fresh data should produce no warnings."""
    match_data = [{
        "home_team": "France", "away_team": "Ireland",
        "has_handicap": True, "has_totals": True, "has_try_scorer": True,
        "handicap_scraped_at": _utcnow(), "totals_scraped_at": _utcnow(), "try_scorer_scraped_at": _utcnow(),
        "try_scorer_count": 30, "squad_count": 23, "unknown_availability": 0,
        "players_with_odds": 23,
    }]
    warnings = validate_round_data(match_data, has_prices=True, price_count=142, price_scraped_at=_utcnow())
    assert len(warnings) == 0
