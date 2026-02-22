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


def test_no_warnings_for_played_matches():
    """Played matches should produce zero warnings regardless of data state."""
    old = _utcnow() - timedelta(hours=48)
    match_data = [{
        "home_team": "France", "away_team": "Ireland",
        "has_handicap": True, "has_totals": True, "has_try_scorer": True,
        "handicap_scraped_at": old, "totals_scraped_at": old, "try_scorer_scraped_at": old,
        "try_scorer_count": 30, "squad_count": 23, "unknown_availability": 0,
        "players_with_odds": 23,
    }]
    played = {"France v Ireland"}
    warnings = validate_round_data(match_data, has_prices=True, price_count=142,
                                   price_scraped_at=_utcnow(), played_matches=played)
    # Should be no match-level warnings at all
    match_warnings = [w for w in warnings if w.get("match")]
    assert len(match_warnings) == 0


def test_warnings_still_fire_for_upcoming_matches():
    """Upcoming matches should still get warnings even when played_matches is provided."""
    old = _utcnow() - timedelta(hours=48)
    match_data = [
        {
            "home_team": "France", "away_team": "Ireland",
            "has_handicap": True, "has_totals": True, "has_try_scorer": True,
            "handicap_scraped_at": old, "totals_scraped_at": old, "try_scorer_scraped_at": old,
            "try_scorer_count": 30, "squad_count": 23, "unknown_availability": 0,
            "players_with_odds": 23,
        },
        {
            "home_team": "England", "away_team": "Wales",
            "has_handicap": True, "has_totals": True, "has_try_scorer": True,
            "handicap_scraped_at": old, "totals_scraped_at": old, "try_scorer_scraped_at": old,
            "try_scorer_count": 30, "squad_count": 23, "unknown_availability": 0,
            "players_with_odds": 23,
        },
    ]
    played = {"France v Ireland"}
    warnings = validate_round_data(match_data, has_prices=True, price_count=142,
                                   price_scraped_at=_utcnow(), played_matches=played)
    stale = [w for w in warnings if w["type"] == "stale_odds"]
    # Only England v Wales should have stale warnings, not France v Ireland
    assert all("England v Wales" in w["message"] for w in stale)
    assert len(stale) == 3  # handicaps, totals, try scorers
