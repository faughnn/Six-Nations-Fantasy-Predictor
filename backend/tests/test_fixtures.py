from datetime import datetime, timezone
from unittest.mock import patch
from app.fixtures import is_match_played, get_upcoming_matches, SIX_NATIONS_2026


def test_schedule_has_15_matches():
    assert len(SIX_NATIONS_2026) == 15


def test_schedule_has_all_5_rounds():
    rounds = {key[1] for key in SIX_NATIONS_2026}
    assert rounds == {1, 2, 3, 4, 5}


def test_is_match_played_after_kickoff_plus_2h():
    # France v Ireland kicks off 2026-02-05 20:10 UTC
    # At 22:11 UTC it should be played (kickoff + 2h + 1min)
    with patch("app.fixtures._utcnow") as mock_now:
        mock_now.return_value = datetime(2026, 2, 5, 22, 11, tzinfo=timezone.utc)
        assert is_match_played(2026, 1, "France", "Ireland") is True


def test_is_match_not_played_before_kickoff_plus_2h():
    # At 22:09 UTC it should NOT be played (kickoff + 1h59m)
    with patch("app.fixtures._utcnow") as mock_now:
        mock_now.return_value = datetime(2026, 2, 5, 22, 9, tzinfo=timezone.utc)
        assert is_match_played(2026, 1, "France", "Ireland") is False


def test_is_match_played_unknown_match_returns_false():
    assert is_match_played(2026, 1, "Argentina", "Japan") is False


def test_get_upcoming_matches_filters_played():
    # 2026-02-07 18:41 UTC: after England v Wales (16:40 + 2h) and Italy v Scotland (14:10 + 2h)
    # but France v Ireland (Feb 5) is also played
    # so all 3 round 1 matches are played
    with patch("app.fixtures._utcnow") as mock_now:
        mock_now.return_value = datetime(2026, 2, 7, 18, 41, tzinfo=timezone.utc)
        upcoming = get_upcoming_matches(2026, 1)
        assert len(upcoming) == 0


def test_get_upcoming_matches_partial_round():
    # 2026-02-21 16:11 UTC: after England v Ireland (14:10 + 2h)
    # but Wales v Scotland (16:40) hasn't finished yet and France v Italy (Feb 22) hasn't started
    with patch("app.fixtures._utcnow") as mock_now:
        mock_now.return_value = datetime(2026, 2, 21, 16, 11, tzinfo=timezone.utc)
        upcoming = get_upcoming_matches(2026, 3)
        teams = [(m[2], m[3]) for m in upcoming]
        assert ("England", "Ireland") not in teams
        assert ("Wales", "Scotland") in teams
        assert ("France", "Italy") in teams


def test_case_insensitive_lookup():
    with patch("app.fixtures._utcnow") as mock_now:
        mock_now.return_value = datetime(2026, 3, 15, 0, 0, tzinfo=timezone.utc)
        assert is_match_played(2026, 1, "france", "ireland") is True
        assert is_match_played(2026, 1, "FRANCE", "IRELAND") is True
