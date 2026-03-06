# Smart Match Filtering Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Automatically skip already-played matches when scraping, suppress stale-odds warnings for finished matches, and visually distinguish played matches in the admin UI.

**Architecture:** A hardcoded 2026 Six Nations fixture schedule with kickoff datetimes lives in a new `app/fixtures.py` module. A match is "played" when `now > kickoff + 2h`. This is consumed by: (1) the scraper runner to filter out played matches, (2) the validation service to suppress warnings, (3) the status API to expose `is_played` per match, and (4) the admin UI to grey out played rows and disable scrape buttons.

**Tech Stack:** Python/FastAPI backend, React/TypeScript frontend, existing test infrastructure (pytest).

---

### Task 1: Create fixtures module with schedule and helpers

**Files:**
- Create: `backend/app/fixtures.py`
- Create: `backend/tests/test_fixtures.py`

**Step 1: Write the failing tests**

```python
# backend/tests/test_fixtures.py
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
```

**Step 2: Run tests to verify they fail**

Run: `cd /g/FantasyML/fantasy-six-nations/backend && python -m pytest tests/test_fixtures.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.fixtures'`

**Step 3: Write the implementation**

```python
# backend/app/fixtures.py
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
```

**Step 4: Run tests to verify they pass**

Run: `cd /g/FantasyML/fantasy-six-nations/backend && python -m pytest tests/test_fixtures.py -v`
Expected: All 8 tests PASS

**Step 5: Commit**

```bash
git add backend/app/fixtures.py backend/tests/test_fixtures.py
git commit -m "feat: add 2026 Six Nations fixture schedule with played-match helpers"
```

---

### Task 2: Filter played matches during bulk scraping

**Files:**
- Modify: `backend/app/api/scrape.py` — `_run_scraper()` and `_run_scrape_all()`

**Step 1: Add played-match filtering to `_run_scraper()`**

In `backend/app/api/scrape.py`, add import at top:

```python
from app.fixtures import is_match_played
```

In `_run_scraper()`, after the existing `match_filter` and `per_match_missing` filtering blocks (around line 207, after `if not matches:` early return), add a new filter block:

```python
        # Filter out already-played matches (skip for explicit single-match requests)
        if match_filter is None:
            before_count = len(matches)
            matches = [
                m for m in matches
                if not is_match_played(season, round_num, m["home"], m["away"])
            ]
            skipped = before_count - len(matches)
            if skipped > 0:
                logger.info(f"Skipped {skipped} already-played match(es)")
                job["skipped_played"] = skipped
```

Insert this block right after the `per_match_missing` filtering (line ~206) and before the `if not matches:` check on line 208. The existing `if not matches:` block handles the case where all matches are played — its message "All markets already scraped" is close enough, but update it:

Replace the message on line 211 from `"All markets already scraped"` to:
```python
job["message"] = "No upcoming matches to scrape" if skipped > 0 else "All markets already scraped"
```

Wait — that variable `skipped` won't be in scope if the `match_filter is None` block didn't run. Simpler: just add the filtering unconditionally for the `match_filter is None` case, and update the empty-matches message:

Actually, let me restructure more carefully. After the existing per_match_missing filter block and before the `if not matches:` check, insert:

```python
        # Filter out already-played matches (only for bulk operations)
        skipped_played = 0
        if match_filter is None:
            before_count = len(matches)
            matches = [
                m for m in matches
                if not is_match_played(season, round_num, m["home"], m["away"])
            ]
            skipped_played = before_count - len(matches)
            if skipped_played > 0:
                logger.info(f"Skipped {skipped_played} already-played match(es)")
                job["skipped_played"] = skipped_played

        if not matches:
            job["status"] = "completed"
            job["message"] = (
                f"All {skipped_played} match(es) already played — nothing to scrape"
                if skipped_played > 0
                else "No matches found on Oddschecker"
                if match_filter is None
                else "All markets already scraped"
            )
            job["matches_found"] = 0
            return
```

This replaces the existing `if not matches:` block (lines 208-212).

**Step 2: Add played-match filtering to `_run_scrape_all()`**

In `_run_scrape_all()` (line ~594), after match discovery and the `if not matches:` check (line ~611), add the same filtering:

```python
        # Filter out already-played matches
        before_count = len(matches)
        matches = [
            m for m in matches
            if not is_match_played(season, round_num, m["home"], m["away"])
        ]
        skipped_played = before_count - len(matches)
        if skipped_played > 0:
            logger.info(f"Scrape-all: skipped {skipped_played} already-played match(es)")

        if not matches:
            # All matches played — still run fantasy prices/stats (step 4)
            logger.info("All matches played, skipping odds scraping")
```

Note: For `_run_scrape_all`, even if all match odds are skipped, we should still proceed to step 4 (fantasy prices). So don't early-return here — just let the odds loop iterate over an empty list, and the fantasy step runs normally. Simply skip the step label updates gracefully.

**Step 3: Run existing tests**

Run: `cd /g/FantasyML/fantasy-six-nations/backend && python -m pytest tests/ -v`
Expected: All existing tests still pass

**Step 4: Commit**

```bash
git add backend/app/api/scrape.py
git commit -m "feat: skip already-played matches in bulk scrape operations"
```

---

### Task 3: Suppress validation warnings for played matches

**Files:**
- Modify: `backend/app/services/validation_service.py`
- Modify: `backend/tests/test_validation.py`

**Step 1: Write the failing test**

Add to `backend/tests/test_validation.py`:

```python
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
```

**Step 2: Run tests to verify they fail**

Run: `cd /g/FantasyML/fantasy-six-nations/backend && python -m pytest tests/test_validation.py::test_no_warnings_for_played_matches tests/test_validation.py::test_warnings_still_fire_for_upcoming_matches -v`
Expected: FAIL — `validate_round_data() got unexpected keyword argument 'played_matches'`

**Step 3: Implement — add `played_matches` parameter**

In `backend/app/services/validation_service.py`, modify the `validate_round_data` signature to accept a new optional parameter:

```python
def validate_round_data(
    match_data: list[dict[str, Any]],
    has_prices: bool = False,
    price_count: int = 0,
    price_scraped_at: datetime | None = None,
    has_stats: bool = False,
    stats_scraped_at: datetime | None = None,
    played_matches: set[str] | None = None,
) -> list[dict[str, Any]]:
```

At the top of the `for match in match_data:` loop, right after `match_label` is computed, add:

```python
        # Skip all warnings for played matches
        if played_matches and match_label in played_matches:
            continue
```

**Step 4: Run all validation tests**

Run: `cd /g/FantasyML/fantasy-six-nations/backend && python -m pytest tests/test_validation.py -v`
Expected: All tests PASS (including existing ones — they don't pass `played_matches` so behavior unchanged)

**Step 5: Commit**

```bash
git add backend/app/services/validation_service.py backend/tests/test_validation.py
git commit -m "feat: suppress validation warnings for played matches"
```

---

### Task 4: Wire fixtures into the status API and add `is_played` to response

**Files:**
- Modify: `backend/app/schemas/match.py` — add `is_played` to `EnrichedMatchScrapeStatus`
- Modify: `backend/app/api/matches.py` — pass `played_matches` to validation, set `is_played`
- Modify: `frontend/src/types/index.ts` — add `is_played` field

**Step 1: Add `is_played` to backend schema**

In `backend/app/schemas/match.py`, add to `EnrichedMatchScrapeStatus`:

```python
class EnrichedMatchScrapeStatus(BaseModel):
    home_team: str
    away_team: str
    match_date: Optional[date] = None
    is_played: bool = False  # <-- new field
    handicaps: MarketStatus
    totals: MarketStatus
    try_scorer: MarketStatus
    squad_status: SquadStatus
    try_scorer_count: int
```

**Step 2: Wire into `get_round_scrape_status` in `backend/app/api/matches.py`**

Add import at top:

```python
from app.fixtures import is_match_played
```

In `get_round_scrape_status()`, before the `validate_round_data()` call (around line 274), build the played_matches set:

```python
    # --- Determine played matches ---
    played_matches = set()
    for md in enriched_match_data:
        if is_match_played(season, game_round, md["home_team"], md["away_team"]):
            played_matches.add(f"{md['home_team']} v {md['away_team']}")
```

Pass it to `validate_round_data`:

```python
    raw_warnings = validate_round_data(
        match_data=enriched_match_data,
        has_prices=has_prices,
        price_count=price_count,
        price_scraped_at=price_scraped_at,
        has_stats=has_stats,
        stats_scraped_at=stats_scraped_at,
        played_matches=played_matches,
    )
```

In the enriched_matches loop (around line 317), set `is_played`:

```python
        match_label = f"{md['home_team']} v {md['away_team']}"
        enriched_matches.append(
            EnrichedMatchScrapeStatus(
                home_team=md["home_team"],
                away_team=md["away_team"],
                match_date=md["match_date"],
                is_played=match_label in played_matches,
                handicaps=handicaps_status,
                ...
            )
        )
```

**Step 3: Add `is_played` to frontend type**

In `frontend/src/types/index.ts`, update `EnrichedMatchScrapeStatus`:

```typescript
export interface EnrichedMatchScrapeStatus {
  home_team: string;
  away_team: string;
  match_date: string | null;
  is_played: boolean;  // <-- new field
  handicaps: MarketStatus;
  totals: MarketStatus;
  try_scorer: MarketStatus;
  squad_status: SquadStatus;
  try_scorer_count: number;
}
```

**Step 4: Run backend tests**

Run: `cd /g/FantasyML/fantasy-six-nations/backend && python -m pytest tests/ -v`
Expected: All tests pass

**Step 5: Commit**

```bash
git add backend/app/schemas/match.py backend/app/api/matches.py frontend/src/types/index.ts
git commit -m "feat: expose is_played flag in round scrape status API"
```

---

### Task 5: Update admin UI to visually distinguish played matches

**Files:**
- Modify: `frontend/src/pages/AdminScrape.tsx`

**Step 1: Grey out played match rows and disable scrape buttons**

In the status grid `<tbody>` (around line 554), update the match row rendering. The `enrichedMatches.map((m) => { ... })` block needs these changes:

1. Add played check at start of map callback:
```tsx
const isPlayed = m.is_played;
```

2. Add a class to the `<tr>` for greyed-out styling:
```tsx
<tr key={`${m.home_team}-${m.away_team}`} className={`border-b border-dotted border-stone-200 ${isPlayed ? 'opacity-40' : ''}`}>
```

3. In the match label `<td>`, add a "Played" badge:
```tsx
<td className="py-1.5 pr-4 font-medium text-stone-700 whitespace-nowrap">
  {m.home_team} v {m.away_team}
  {isPlayed && (
    <span className="ml-2 text-[10px] px-1.5 py-0.5 bg-stone-100 text-stone-400 border border-stone-200 font-semibold uppercase tracking-wider">
      Played
    </span>
  )}
</td>
```

4. Disable the `MarketCell` onClick for played matches by passing `disabled={scrapeJob.isBusy || isPlayed}` for each of the three market cells:
```tsx
<MarketCell
  market={m.handicaps}
  onClick={() => scrapeJob.startJob(() => scrapeApi.scrapeMatchMarket(season, round, 'handicaps', m.home_team, m.away_team))}
  disabled={scrapeJob.isBusy || isPlayed}
/>
```

Same for totals and try_scorer cells.

**Step 2: Verify visually**

Run: `cd /g/FantasyML/fantasy-six-nations && docker-compose up --build`
Check admin page — played matches should appear greyed out with "Played" badge, scrape buttons disabled.

**Step 3: Commit**

```bash
git add frontend/src/pages/AdminScrape.tsx
git commit -m "feat: grey out played matches in admin status grid"
```

---

### Task 6: Final integration test

**Step 1: Verify end-to-end with Docker**

Run: `cd /g/FantasyML/fantasy-six-nations && docker-compose up --build`

Verify on admin page (http://localhost:3000/admin):
1. Round 3 shows England v Ireland and Wales v Scotland as "Played" (greyed out, badge visible)
2. France v Italy shows as normal (upcoming — kickoff Feb 22 15:10 UTC)
3. No stale-odds warnings appear for England v Ireland or Wales v Scotland
4. Warnings still appear for France v Italy if its odds are stale
5. Clicking "Scrape Everything" or "Handicaps" etc. only scrapes France v Italy
6. Individual market cells for played matches are disabled/unclickable

**Step 2: Run all backend tests**

Run: `cd /g/FantasyML/fantasy-six-nations/backend && python -m pytest tests/ -v`
Expected: All tests pass

**Step 3: Final commit (if any cleanup needed)**

```bash
git add -A
git commit -m "chore: smart match filtering integration cleanup"
```
