from datetime import datetime, timedelta, timezone
from typing import Any

STALE_THRESHOLD_HOURS = 24
MIN_TRY_SCORER_PLAYERS = 20
EXPECTED_SQUAD_SIZE = 23
HIGH_UNKNOWN_THRESHOLD = 10


def _ensure_aware(dt: datetime | None) -> datetime | None:
    """Make a naive datetime timezone-aware (assume UTC) for safe comparison."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def validate_round_data(
    match_data: list[dict[str, Any]],
    has_prices: bool = False,
    price_count: int = 0,
    price_scraped_at: datetime | None = None,
    has_stats: bool = False,
    stats_scraped_at: datetime | None = None,
) -> list[dict[str, Any]]:
    """Run all validation rules against round data. Returns list of warning dicts."""
    warnings = []
    now = datetime.now(timezone.utc)

    for match in match_data:
        home = match["home_team"]
        away = match["away_team"]
        match_label = f"{home} v {away}"

        # Rule 4: Missing markets
        missing = []
        if not match.get("has_handicap"):
            missing.append("handicaps")
        if not match.get("has_totals"):
            missing.append("totals")
        if not match.get("has_try_scorer"):
            missing.append("try scorers")
        if missing:
            warnings.append({
                "type": "missing_markets",
                "match": match_label,
                "message": f"{match_label} missing: {', '.join(missing)}",
                "action": "scrape_missing",
                "action_params": {"match": match_label},
            })

        # Rule 1: Squad completeness (both teams combined = 46)
        squad_count = match.get("squad_count", 0)
        expected_match_squad = EXPECTED_SQUAD_SIZE * 2
        if has_prices and squad_count < expected_match_squad:
            warnings.append({
                "type": "incomplete_squad",
                "match": match_label,
                "team": f"{home}/{away}",
                "count": squad_count,
                "expected": EXPECTED_SQUAD_SIZE,
                "message": f"{match_label} squad incomplete: {squad_count}/{expected_match_squad}",
                "action": "re_scrape_prices",
            })

        # Rule 3: Stale odds (per market)
        for market, key in [("handicaps", "handicap_scraped_at"), ("totals", "totals_scraped_at"), ("try scorers", "try_scorer_scraped_at")]:
            scraped_at = _ensure_aware(match.get(key))
            if scraped_at and (now - scraped_at) > timedelta(hours=STALE_THRESHOLD_HOURS):
                hours_old = int((now - scraped_at).total_seconds() / 3600)
                warnings.append({
                    "type": "stale_odds",
                    "match": match_label,
                    "market": market,
                    "hours_old": hours_old,
                    "message": f"{market.title()} odds for {match_label} are {hours_old}h old",
                    "action": f"re_scrape_{market.replace(' ', '_')}",
                    "action_params": {"match": match_label},
                })

        # Rule 2: Pre-squad odds
        unknown = match.get("unknown_availability", 0)
        ts_scraped = _ensure_aware(match.get("try_scorer_scraped_at"))
        if match.get("has_try_scorer") and ts_scraped and unknown >= HIGH_UNKNOWN_THRESHOLD:
            warnings.append({
                "type": "pre_squad_odds",
                "match": match_label,
                "market": "try_scorer",
                "message": f"Try scorer odds for {match_label} may be outdated — scraped before squad release",
                "action": "re_scrape_try_scorer",
                "action_params": {"match": match_label},
            })

        # Rule 8: Suspiciously few odds
        ts_count = match.get("try_scorer_count", 0)
        if match.get("has_try_scorer") and ts_count < MIN_TRY_SCORER_PLAYERS:
            warnings.append({
                "type": "suspiciously_few_odds",
                "match": match_label,
                "count": ts_count,
                "message": f"Only {ts_count} players with try scorer odds for {match_label} — possible partial scrape",
                "action": "re_scrape_try_scorer",
                "action_params": {"match": match_label},
            })

        # Rule 7: Missing player odds
        players_with_odds = match.get("players_with_odds", 0)
        if squad_count >= expected_match_squad and unknown == 0 and players_with_odds < squad_count:
            missing_count = squad_count - players_with_odds
            warnings.append({
                "type": "missing_player_odds",
                "match": match_label,
                "missing_count": missing_count,
                "message": f"{missing_count} players in {match_label} squad missing try scorer odds",
                "action": "re_scrape_try_scorer",
                "action_params": {"match": match_label},
            })

    # Rule 6: Availability unknown (round-level)
    total_unknown = sum(m.get("unknown_availability", 0) for m in match_data)
    if has_prices and total_unknown > 0:
        warnings.append({
            "type": "availability_unknown",
            "count": total_unknown,
            "message": f"{total_unknown} players have unknown availability",
            "action": "re_scrape_prices",
        })

    return warnings
