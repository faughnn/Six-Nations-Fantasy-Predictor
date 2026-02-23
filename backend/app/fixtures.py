"""Hardcoded 2026 Six Nations fixture schedule."""

from datetime import datetime, timedelta, timezone
from typing import Optional

def _utcnow() -> datetime:
    return datetime.now(timezone.utc)

# Key: (season, round, home_team, away_team) -> kickoff datetime (UTC)
SIX_NATIONS_2026: dict[tuple[int, int, str, str], datetime] = {
    # Round 1
    (2026, 1, "France", "Ireland"):   datetime(2026, 2, 5, 20, 10, tzinfo=timezone.utc),
    (2026, 1, "Italy", "Scotland"):   datetime(2026, 2, 7, 14, 10, tzinfo=timezone.utc),
    (2026, 1, "England", "Wales"):    datetime(2026, 2, 7, 16, 40, tzinfo=timezone.utc),
    # Round 2
    (2026, 2, "Ireland", "Italy"):    datetime(2026, 2, 14, 14, 10, tzinfo=timezone.utc),
    (2026, 2, "Scotland", "England"): datetime(2026, 2, 14, 16, 40, tzinfo=timezone.utc),
    (2026, 2, "Wales", "France"):     datetime(2026, 2, 15, 15, 10, tzinfo=timezone.utc),
    # Round 3
    (2026, 3, "England", "Ireland"):  datetime(2026, 2, 21, 14, 10, tzinfo=timezone.utc),
    (2026, 3, "Wales", "Scotland"):   datetime(2026, 2, 21, 16, 40, tzinfo=timezone.utc),
    (2026, 3, "France", "Italy"):     datetime(2026, 2, 22, 15, 10, tzinfo=timezone.utc),
    # Round 4
    (2026, 4, "Ireland", "Wales"):    datetime(2026, 3, 6, 20, 10, tzinfo=timezone.utc),
    (2026, 4, "Scotland", "France"):  datetime(2026, 3, 7, 14, 10, tzinfo=timezone.utc),
    (2026, 4, "Italy", "England"):    datetime(2026, 3, 7, 16, 40, tzinfo=timezone.utc),
    # Round 5
    (2026, 5, "Ireland", "Scotland"): datetime(2026, 3, 14, 14, 10, tzinfo=timezone.utc),
    (2026, 5, "Wales", "Italy"):      datetime(2026, 3, 14, 16, 40, tzinfo=timezone.utc),
    (2026, 5, "France", "England"):   datetime(2026, 3, 14, 20, 10, tzinfo=timezone.utc),
}

MATCH_PLAYED_BUFFER = timedelta(hours=2)


def _normalize_key(
    season: int, round_num: int, home: str, away: str,
) -> Optional[tuple[int, int, str, str]]:
    """Find the canonical key, case-insensitive on team names."""
    home_l = home.lower()
    away_l = away.lower()
    for key in SIX_NATIONS_2026:
        if (key[0] == season and key[1] == round_num
                and key[2].lower() == home_l and key[3].lower() == away_l):
            return key
    return None


def is_match_played(season: int, round_num: int, home: str, away: str) -> bool:
    """Return True if the match kickoff + 2h is in the past."""
    key = _normalize_key(season, round_num, home, away)
    if key is None:
        return False
    kickoff = SIX_NATIONS_2026[key]
    return _utcnow() > kickoff + MATCH_PLAYED_BUFFER


def get_upcoming_matches(
    season: int, round_num: int,
) -> list[tuple[int, int, str, str]]:
    """Return fixture keys for matches in this round that haven't been played yet."""
    return [
        key for key in SIX_NATIONS_2026
        if key[0] == season and key[1] == round_num
        and not is_match_played(season, round_num, key[2], key[3])
    ]


def get_round_fixtures(
    season: int, round_num: int,
) -> list[tuple[str, str, datetime]]:
    """Return (home, away, kickoff) for all matches in a round, sorted by kickoff."""
    fixtures = [
        (key[2], key[3], SIX_NATIONS_2026[key])
        for key in SIX_NATIONS_2026
        if key[0] == season and key[1] == round_num
    ]
    fixtures.sort(key=lambda f: f[2])
    return fixtures


def get_current_round(season: int = 2026) -> int:
    """Determine current round based on schedule dates.

    Returns the earliest round that still has unplayed matches,
    or the last round if everything has been played.
    """
    now = _utcnow()
    for rnd in range(1, 6):
        fixtures = get_round_fixtures(season, rnd)
        if not fixtures:
            continue
        last_kickoff = max(ko for _, _, ko in fixtures)
        if now < last_kickoff + MATCH_PLAYED_BUFFER:
            return rnd
    return 5
