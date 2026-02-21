# Streamline Scraping — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the manual CLI-based scraping workflow with a UI-driven system featuring one-click scraping, automated validation, data freshness tracking, and scrape history.

**Architecture:** Adds a `scrape_runs` table for history tracking and a validation service that generates warnings. The existing status API is enriched with per-market timestamps and warnings. The admin page becomes the sole scraping control point. Public pages get lightweight freshness indicators.

**Tech Stack:** Python/FastAPI/SQLAlchemy (backend), React/TypeScript/TailwindCSS (frontend), PostgreSQL

**Design doc:** `docs/plans/2026-02-21-streamline-scraping-design.md`

---

## Phase 1: Backend Data Layer

### Task 1: Create ScrapeRun model

**Files:**
- Create: `backend/app/models/scrape_run.py`
- Modify: `backend/app/models/__init__.py`
- Modify: `backend/app/database.py` (add table creation to `init_db()`)

**Step 1: Create the ScrapeRun model**

```python
# backend/app/models/scrape_run.py
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Float, Text
from sqlalchemy.dialects.postgresql import JSON
from app.database import Base


class ScrapeRun(Base):
    __tablename__ = "scrape_runs"

    id = Column(Integer, primary_key=True)
    season = Column(Integer, nullable=False)
    round = Column(Integer, nullable=False)
    market_type = Column(String(20), nullable=False)  # handicaps, totals, try_scorer, fantasy_prices, fantasy_stats
    match_slug = Column(String(100), nullable=True)  # null for fantasy_prices/stats
    status = Column(String(20), nullable=False, default="in_progress")  # in_progress, completed, failed, cancelled
    started_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    duration_seconds = Column(Float, nullable=True)
    result_summary = Column(JSON, nullable=True)  # {"players_found": 142, "matches_found": 3}
    warnings = Column(JSON, nullable=True)  # [{"type": "...", "message": "..."}]
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)
```

**Step 2: Register in models/__init__.py**

Add `from app.models.scrape_run import ScrapeRun` to `backend/app/models/__init__.py` alongside existing imports.

**Step 3: Add table creation to init_db()**

In `backend/app/database.py`, the `init_db()` function (line 25) uses `Base.metadata.create_all()`. Since ScrapeRun inherits from Base, importing the model is sufficient — the table will be created automatically. Verify the import is loaded before `create_all` runs by checking that `__init__.py` imports it.

**Step 4: Verify table creation**

Run: `cd backend && docker-compose up --build`
Then check: `docker-compose exec db psql -U postgres -d railway -c "\d scrape_runs"`
Expected: Table with all columns listed above.

**Step 5: Commit**

```bash
git add app/models/scrape_run.py app/models/__init__.py
git commit -m "feat: add ScrapeRun model for scrape history tracking"
```

---

### Task 2: Create validation service

**Files:**
- Create: `backend/app/services/validation_service.py`
- Test: `backend/tests/test_validation.py`

**Step 1: Write failing tests for validation rules**

```python
# backend/tests/test_validation.py
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
        "unknown_availability": 15,  # high unknown = pre-squad
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
        "players_with_odds": 18,  # only 18 of 23 have odds
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
```

**Step 2: Run tests to verify they fail**

Run: `cd backend && python -m pytest tests/test_validation.py -v`
Expected: FAIL — `validate_round_data` not defined

**Step 3: Implement the validation service**

```python
# backend/app/services/validation_service.py
from datetime import datetime, timedelta, timezone
from typing import Any

STALE_THRESHOLD_HOURS = 24
MIN_TRY_SCORER_PLAYERS = 20
EXPECTED_SQUAD_SIZE = 23
HIGH_UNKNOWN_THRESHOLD = 10  # if > 10 players unknown, consider pre-squad


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

        # Rule 1: Squad completeness
        squad_count = match.get("squad_count", 0)
        if has_prices and squad_count < EXPECTED_SQUAD_SIZE:
            warnings.append({
                "type": "incomplete_squad",
                "match": match_label,
                "team": f"{home}/{away}",
                "count": squad_count,
                "expected": EXPECTED_SQUAD_SIZE,
                "message": f"{match_label} squad incomplete: {squad_count}/{EXPECTED_SQUAD_SIZE}",
                "action": "re_scrape_prices",
            })

        # Rule 3: Stale odds (per market)
        for market, key in [("handicaps", "handicap_scraped_at"), ("totals", "totals_scraped_at"), ("try scorers", "try_scorer_scraped_at")]:
            scraped_at = match.get(key)
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
        ts_scraped = match.get("try_scorer_scraped_at")
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

        # Rule 7: Missing player odds (squad known but player lacks try scorer odds)
        players_with_odds = match.get("players_with_odds", 0)
        if squad_count >= EXPECTED_SQUAD_SIZE and unknown == 0 and players_with_odds < squad_count:
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
```

**Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_validation.py -v`
Expected: All PASS

**Step 5: Commit**

```bash
git add app/services/validation_service.py tests/test_validation.py
git commit -m "feat: add validation service with 7 scraping data rules"
```

---

## Phase 2: Backend API Enhancements

### Task 3: Update match schemas for enriched status response

**Files:**
- Modify: `backend/app/schemas/match.py` (currently 68 lines)

**Step 1: Add new Pydantic models for the enriched status**

Add these new schemas after the existing `MatchScrapeStatus` (line 42) and before `RoundScrapeStatusResponse` (line 45). Then update `RoundScrapeStatusResponse` to use the new types.

New schemas to add:

```python
from datetime import datetime
from pydantic import BaseModel
from typing import Optional

class MarketStatus(BaseModel):
    status: str  # "complete", "missing", "warning"
    scraped_at: Optional[datetime] = None
    warning: Optional[str] = None

class SquadStatus(BaseModel):
    total: int
    expected: int = 23
    unknown_availability: int

class EnrichedMatchScrapeStatus(BaseModel):
    home_team: str
    away_team: str
    match_date: Optional[date] = None
    handicaps: MarketStatus
    totals: MarketStatus
    try_scorer: MarketStatus
    squad_status: SquadStatus
    try_scorer_count: int

class DatasetStatus(BaseModel):
    status: str  # "complete", "missing", "not_applicable"
    scraped_at: Optional[datetime] = None
    player_count: Optional[int] = None
    note: Optional[str] = None

class ValidationWarning(BaseModel):
    type: str
    message: str
    match: Optional[str] = None
    market: Optional[str] = None
    action: Optional[str] = None
    action_params: Optional[dict] = None

class ScrapeRunSummary(BaseModel):
    id: int
    market_type: str
    match_slug: Optional[str] = None
    status: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    warnings: Optional[list] = None
    result_summary: Optional[dict] = None
```

Update `RoundScrapeStatusResponse` (line 45) to:

```python
class RoundScrapeStatusResponse(BaseModel):
    season: int
    round: int
    # Keep old fields for backward compat
    matches: list[MatchScrapeStatus]
    missing_markets: list[str]
    has_prices: bool
    price_count: int
    availability_known: int
    availability_unknown: int
    # New enriched fields
    enriched_matches: list[EnrichedMatchScrapeStatus] = []
    fantasy_prices: Optional[DatasetStatus] = None
    fantasy_stats: Optional[DatasetStatus] = None
    warnings: list[ValidationWarning] = []
    last_scrape_run: Optional[ScrapeRunSummary] = None
    scrape_history: list[ScrapeRunSummary] = []
```

**Step 2: Verify backend starts**

Run: `cd backend && python -c "from app.schemas.match import RoundScrapeStatusResponse; print('OK')"`
Expected: `OK`

**Step 3: Commit**

```bash
git add app/schemas/match.py
git commit -m "feat: add enriched status schemas with timestamps and validation warnings"
```

---

### Task 4: Enhance the status endpoint to return timestamps and warnings

**Files:**
- Modify: `backend/app/api/matches.py` (currently 298 lines, status endpoint at lines 70-162)

**Step 1: Update the status endpoint**

The current endpoint at `GET /status` (line 70) queries `MatchOdds` and `Odds` but doesn't return `scraped_at` timestamps. Modify it to:

1. Include `MatchOdds.scraped_at` in the query (it's already selected but not returned)
2. For each match, query the per-team squad count and unknown availability from `FantasyPrice`
3. Count players_with_odds per match (players in the match teams who have try scorer odds)
4. Get the latest `FantasyPrice.created_at` as price_scraped_at
5. Get the latest `FantasyRoundStats.scraped_at` as stats_scraped_at
6. Call `validate_round_data()` with the enriched data
7. Query recent `ScrapeRun` records for history
8. Build the enriched response fields

Key imports to add at top of file:
```python
from app.services.validation_service import validate_round_data
from app.models.scrape_run import ScrapeRun
from app.models.stats import FantasyRoundStats
from app.schemas.match import (
    MarketStatus, SquadStatus, EnrichedMatchScrapeStatus,
    DatasetStatus, ValidationWarning, ScrapeRunSummary,
)
```

For each match in the existing loop, add queries for:
- `MatchOdds.scraped_at` — already available from the existing query result
- Squad count per match: `SELECT COUNT(*) FROM fantasy_prices WHERE season=X AND round=Y AND availability IN ('starting', 'substitute') AND player_id IN (SELECT id FROM players WHERE country IN (home_country, away_country))`
- Unknown availability: `SELECT COUNT(*) FROM fantasy_prices WHERE season=X AND round=Y AND availability IS NULL AND player_id IN (...)`
- Players with odds per match: `SELECT COUNT(DISTINCT o.player_id) FROM odds o JOIN players p ON o.player_id = p.id WHERE o.season=X AND o.round=Y AND o.anytime_try_scorer IS NOT NULL AND p.country IN (home_country, away_country)`

After the loop, query:
- `SELECT MAX(created_at) FROM fantasy_prices WHERE season=X AND round=Y` for price_scraped_at
- `SELECT MAX(scraped_at) FROM fantasy_round_stats WHERE season=X AND round=Y` for stats_scraped_at
- `SELECT * FROM scrape_runs WHERE season=X AND round=Y ORDER BY started_at DESC LIMIT 20` for history

Build `enriched_matches` list with `MarketStatus` objects using the `scraped_at` timestamps.
Call `validate_round_data()` and map results to `ValidationWarning` objects.
Set `last_scrape_run` to the most recent completed `ScrapeRun`.

**Important:** Keep the existing response fields (`matches`, `missing_markets`, etc.) intact for backward compatibility. The new `enriched_matches`, `warnings`, `scrape_history` fields are additive.

**Step 2: Verify the endpoint works**

Run the docker-compose stack and hit: `curl http://localhost:8000/api/matches/status?season=2026&game_round=3`
Expected: Response includes both old fields and new `enriched_matches`, `warnings`, `scrape_history` fields.

**Step 3: Commit**

```bash
git add app/api/matches.py
git commit -m "feat: enrich status endpoint with per-market timestamps and validation warnings"
```

---

### Task 5: Record scrape runs in the scraping API

**Files:**
- Modify: `backend/app/api/scrape.py` (currently 528 lines)

**Step 1: Add ScrapeRun recording to the scrape pipeline**

Import at top:
```python
from app.models.scrape_run import ScrapeRun
from datetime import datetime, timezone
```

Create a helper function near the top of the file (after the existing helpers):

```python
async def _record_scrape_run(
    season: int, round_num: int, market_type: str, match_slug: str | None,
    status: str, started_at: datetime, result_summary: dict | None = None,
    warnings: list | None = None, error_message: str | None = None,
):
    """Record a scrape run to the database."""
    completed_at = datetime.now(timezone.utc)
    duration = (completed_at - started_at).total_seconds()
    async with async_session() as db:
        run = ScrapeRun(
            season=season, round=round_num, market_type=market_type,
            match_slug=match_slug, status=status, started_at=started_at,
            completed_at=completed_at, duration_seconds=duration,
            result_summary=result_summary, warnings=warnings,
            error_message=error_message,
        )
        db.add(run)
        await db.commit()
```

**Step 2: Instrument `_scrape_market_for_match()`**

In `_scrape_market_for_match()` (line 67), wrap the existing logic to capture timing and record a ScrapeRun after each market-match scrape completes. Add `started_at = datetime.now(timezone.utc)` at the start. After the save call succeeds, call `_record_scrape_run(...)` with status="completed". In the except block, call it with status="failed".

**Step 3: Instrument `_run_fantasy_import()`**

In `_run_fantasy_import()` (line 394), similarly add timing and record a ScrapeRun with market_type="fantasy_prices".

**Step 4: Verify recording works**

Run a scrape via the admin UI or curl. Then check: `docker-compose exec db psql -U postgres -d railway -c "SELECT * FROM scrape_runs ORDER BY id DESC LIMIT 5"`
Expected: Recent scrape runs with status, timestamps, and duration.

**Step 5: Commit**

```bash
git add app/api/scrape.py
git commit -m "feat: record scrape runs to scrape_runs table for history tracking"
```

---

### Task 6: Add "Scrape All" orchestration endpoint

**Files:**
- Modify: `backend/app/api/scrape.py`

**Step 1: Add the orchestration endpoint**

Add a new endpoint `POST /all` that runs all scrapers in sequence:

```python
@router.post("/all")
async def scrape_all(
    request: AllMatchOddsScrapeRequest,
    db: AsyncSession = Depends(get_db),
    _user=Depends(require_admin),
):
    """Scrape everything: handicaps, totals, try scorers, then import fantasy prices."""
    job = _create_job(f"Scrape all markets for round {request.round}")
    job["total_steps"] = 4
    job["current_step"] = 0
    job["step_label"] = "Starting..."

    async def run_all():
        try:
            browser = None
            scraper = OddscheckerScraper(headless=True)
            browser = await scraper._init_browser()
            page = await scraper._create_page(browser)

            # Discover matches
            job["message"] = "Discovering matches..."
            matches = await scraper.discover_six_nations_matches(page)
            job["matches_found"] = len(matches)

            if not matches:
                job["status"] = "failed"
                job["message"] = "No matches found"
                return

            # Step 1: Handicaps
            job["current_step"] = 1
            job["step_label"] = "Scraping handicaps"
            for i, (slug, url) in enumerate(matches):
                job["message"] = f"Step 1/4: Handicaps — {slug} ({i+1}/{len(matches)})"
                job["current_match"] = slug
                await _scrape_market_for_match(
                    scraper, page, slug, url, "/handicaps", "handicaps",
                    request.season, request.round, db
                )

            # Step 2: Totals
            job["current_step"] = 2
            job["step_label"] = "Scraping totals"
            for i, (slug, url) in enumerate(matches):
                job["message"] = f"Step 2/4: Totals — {slug} ({i+1}/{len(matches)})"
                job["current_match"] = slug
                await _scrape_market_for_match(
                    scraper, page, slug, url, "/total-points", "totals",
                    request.season, request.round, db
                )

            # Step 3: Try scorers
            job["current_step"] = 3
            job["step_label"] = "Scraping try scorers"
            for i, (slug, url) in enumerate(matches):
                job["message"] = f"Step 3/4: Try scorers — {slug} ({i+1}/{len(matches)})"
                job["current_match"] = slug
                await _scrape_market_for_match(
                    scraper, page, slug, url, "/anytime-tryscorer", "try_scorer",
                    request.season, request.round, db
                )

            await scraper._close_browser()

            # Step 4: Fantasy prices
            job["current_step"] = 4
            job["step_label"] = "Importing fantasy prices"
            job["message"] = "Step 4/4: Importing fantasy prices..."
            # Trigger the fantasy import using existing logic
            await _run_fantasy_import_inline(db, request.season, request.round, job)

            job["status"] = "completed"
            job["message"] = f"All done — {len(matches)} matches scraped + prices imported"
        except Exception as e:
            job["status"] = "failed"
            job["message"] = str(e)

    task = asyncio.create_task(run_all())
    _tasks[job["job_id"]] = task

    return OddsScrapeResponse(
        status="in_progress",
        job_id=job["job_id"],
        message=f"Scraping all markets for round {request.round}",
    )
```

**Note:** The exact implementation will need to adapt to the existing `_run_scraper()` and `_run_fantasy_import()` patterns in `scrape.py`. The above is a guide — use the existing helper functions where possible rather than duplicating logic. The key addition is the step tracking (`current_step`, `step_label`, `total_steps`) in the job dict.

**Step 2: Verify**

Trigger via curl: `curl -X POST http://localhost:8000/api/scrape/all -H "Content-Type: application/json" -d '{"season": 2026, "round": 3}'`
Then poll: `curl http://localhost:8000/api/scrape/active`
Expected: Job progresses through steps 1-4.

**Step 3: Commit**

```bash
git add app/api/scrape.py
git commit -m "feat: add POST /api/scrape/all endpoint for one-click full scrape"
```

---

### Task 7: Add fantasy stats scrape endpoint

**Files:**
- Modify: `backend/app/api/scrape.py`

**Step 1: Add the endpoint**

```python
@router.post("/fantasy-stats")
async def scrape_fantasy_stats(
    request: AllMatchOddsScrapeRequest,
    _user=Depends(require_admin),
):
    """Trigger fantasy stats scraper for specified round(s)."""
    job = _create_job(f"Scraping fantasy stats for round {request.round}")

    async def run_stats():
        try:
            started_at = datetime.now(timezone.utc)
            job["message"] = "Starting fantasy stats scrape..."

            # Import and call the stats scraper logic
            # Reuse the save_to_db and scraping logic from scrape_fantasy_stats.py
            from scrape_fantasy_stats import main as run_stats_scraper
            # Call with appropriate args - this needs adaptation based on
            # how scrape_fantasy_stats.py's main() works (it uses argparse internally)
            # Better approach: extract the core logic into a callable function

            job["status"] = "completed"
            job["message"] = "Fantasy stats scraped successfully"
            await _record_scrape_run(
                request.season, request.round, "fantasy_stats", None,
                "completed", started_at, {"round": request.round}
            )
        except Exception as e:
            job["status"] = "failed"
            job["message"] = str(e)

    task = asyncio.create_task(run_stats())
    _tasks[job["job_id"]] = task

    return OddsScrapeResponse(
        status="in_progress",
        job_id=job["job_id"],
        message=f"Scraping fantasy stats for round {request.round}",
    )
```

**Note:** The `scrape_fantasy_stats.py` main() function uses argparse and is designed as a CLI tool. You'll need to extract the core scraping logic into a callable async function (similar to how `_run_fantasy_import` works for prices). The key functions to reuse are `create_browser_context()`, `detect_available_rounds()`, `scrape_all_pages()`, `parse_players()`, and `save_to_db()` from `scrape_fantasy_stats.py`.

**Step 2: Commit**

```bash
git add app/api/scrape.py
git commit -m "feat: add POST /api/scrape/fantasy-stats endpoint"
```

---

### Task 8: Add scrape history endpoint

**Files:**
- Modify: `backend/app/api/scrape.py`

**Step 1: Add a GET endpoint for scrape history**

```python
@router.get("/history")
async def get_scrape_history(
    season: int = 2026,
    game_round: int = 1,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    _user=Depends(require_admin),
):
    """Get scrape run history for a round."""
    result = await db.execute(
        select(ScrapeRun)
        .where(ScrapeRun.season == season, ScrapeRun.round == game_round)
        .order_by(ScrapeRun.started_at.desc())
        .limit(limit)
    )
    runs = result.scalars().all()
    return [
        {
            "id": r.id,
            "market_type": r.market_type,
            "match_slug": r.match_slug,
            "status": r.status,
            "started_at": r.started_at.isoformat() if r.started_at else None,
            "completed_at": r.completed_at.isoformat() if r.completed_at else None,
            "duration_seconds": r.duration_seconds,
            "result_summary": r.result_summary,
            "warnings": r.warnings,
            "error_message": r.error_message,
        }
        for r in runs
    ]
```

**Step 2: Commit**

```bash
git add app/api/scrape.py
git commit -m "feat: add GET /api/scrape/history endpoint for scrape run history"
```

---

## Phase 3: Frontend Types & API Client

### Task 9: Update TypeScript types and API client

**Files:**
- Modify: `frontend/src/api/client.ts` (currently 289 lines)
- Modify: `frontend/src/types/index.ts` (currently 260 lines)

**Step 1: Add new TypeScript types**

In `frontend/src/types/index.ts`, add at the end:

```typescript
// Enriched scrape status types
export interface MarketStatus {
  status: 'complete' | 'missing' | 'warning';
  scraped_at: string | null;
  warning: string | null;
}

export interface SquadStatus {
  total: number;
  expected: number;
  unknown_availability: number;
}

export interface EnrichedMatchScrapeStatus {
  home_team: string;
  away_team: string;
  match_date: string | null;
  handicaps: MarketStatus;
  totals: MarketStatus;
  try_scorer: MarketStatus;
  squad_status: SquadStatus;
  try_scorer_count: number;
}

export interface DatasetStatus {
  status: 'complete' | 'missing' | 'not_applicable';
  scraped_at: string | null;
  player_count: number | null;
  note: string | null;
}

export interface ValidationWarning {
  type: string;
  message: string;
  match?: string;
  market?: string;
  action?: string;
  action_params?: Record<string, string>;
}

export interface ScrapeRunSummary {
  id: number;
  market_type: string;
  match_slug: string | null;
  status: string;
  started_at: string;
  completed_at: string | null;
  duration_seconds: number | null;
  warnings: any[] | null;
  result_summary: Record<string, any> | null;
}
```

**Step 2: Update RoundScrapeStatus in client.ts**

In `frontend/src/api/client.ts`, update the `RoundScrapeStatus` interface (line 146) to include the new fields:

```typescript
export interface RoundScrapeStatus {
  season: number;
  round: number;
  matches: MatchScrapeStatus[];
  missing_markets: string[];
  has_prices: boolean;
  price_count: number;
  availability_known: number;
  availability_unknown: number;
  // New enriched fields
  enriched_matches: EnrichedMatchScrapeStatus[];
  fantasy_prices: DatasetStatus | null;
  fantasy_stats: DatasetStatus | null;
  warnings: ValidationWarning[];
  last_scrape_run: ScrapeRunSummary | null;
  scrape_history: ScrapeRunSummary[];
}
```

Add the import at the top of client.ts:
```typescript
import type { EnrichedMatchScrapeStatus, DatasetStatus, ValidationWarning, ScrapeRunSummary } from './types';
```

**Step 3: Add new API functions**

In the `scrapeApi` object (line 195), add:

```typescript
scrapeAll: async (season: number, round: number): Promise<ScrapeResponse> => {
  const { data } = await api.post('/api/scrape/all', { season, round });
  return data;
},
scrapeFantasyStats: async (season: number, round: number): Promise<ScrapeResponse> => {
  const { data } = await api.post('/api/scrape/fantasy-stats', { season, round });
  return data;
},
getHistory: async (season: number, round: number): Promise<ScrapeRunSummary[]> => {
  const { data } = await api.get(`/api/scrape/history?season=${season}&game_round=${round}`);
  return data;
},
```

**Step 4: Update ScrapeJobStatus interface**

Update `ScrapeJobStatus` (line 185) to include step tracking:

```typescript
export interface ScrapeJobStatus {
  status: string;
  message: string;
  matches_found: number;
  matches_completed: number;
  current_match: string;
  // New step tracking
  total_steps?: number;
  current_step?: number;
  step_label?: string;
}
```

**Step 5: Commit**

```bash
git add src/types/index.ts src/api/client.ts
git commit -m "feat: add TypeScript types and API client functions for enriched scrape status"
```

---

## Phase 4: Admin Page Redesign

### Task 10: Redesign admin page — Control Panel

**Files:**
- Modify: `frontend/src/pages/AdminScrape.tsx` (currently 491 lines)

**Step 1: Add "Scrape Everything" button**

In the Data Controls section (line 285), add a prominent "Scrape Everything" button at the top that calls `scrapeApi.scrapeAll(season, round)`. This should use the existing `useScrapeJob()` hook's `startJob()` function but with the new endpoint.

Update the `startJob` function (line 146 in useScrapeJob) or add a new variant that accepts a custom API call. The button should be visually distinct (larger, primary color).

**Step 2: Add step progress display**

When a "scrape all" job is running, show step progress: "Step 2/4: Scraping totals — france-v-ireland (1/3)". Use the new `total_steps`, `current_step`, `step_label` fields from the job status. Add a progress bar or step indicator.

**Step 3: Add Fantasy Stats button**

Add a "Fantasy Stats" button alongside the existing individual market buttons. It should call `scrapeApi.scrapeFantasyStats(season, round)`.

**Step 4: Commit**

```bash
git add src/pages/AdminScrape.tsx
git commit -m "feat: add Scrape Everything button and step progress to admin page"
```

---

### Task 11: Redesign admin page — Status Grid

**Files:**
- Modify: `frontend/src/pages/AdminScrape.tsx`

**Step 1: Replace the per-match indicators section**

Replace the existing per-match indicators (lines 380-417) with a table/grid showing per-match, per-market status with timestamps. Use the `enriched_matches` data from the status response.

Create a helper component `StatusCell` that renders:
- **Green dot + "Xh ago"** when `status === "complete"` and `scraped_at` is within 24h
- **Amber dot + "Xd ago (pre-squad)"** when `status === "warning"`
- **Red "missing"** when `status === "missing"`

Create a helper `timeAgo(isoString)` function (extend the existing one at line 211) that returns human-readable relative time.

Each cell should be a clickable button that triggers a re-scrape for that specific market+match when clicked.

Add a row below the match grid for Fantasy Prices and Fantasy Stats using the `fantasy_prices` and `fantasy_stats` dataset status fields.

**Step 2: Add squad status column**

Add a "Squad" column to the grid showing `squad_status.total/squad_status.expected` with color coding:
- Green: 23/23
- Amber: < 23 but > 0
- Red: 0

**Step 3: Commit**

```bash
git add src/pages/AdminScrape.tsx
git commit -m "feat: add per-market status grid with timestamps to admin page"
```

---

### Task 12: Redesign admin page — Warnings Panel

**Files:**
- Modify: `frontend/src/pages/AdminScrape.tsx`

**Step 1: Add warnings panel below the status grid**

Create a `WarningsPanel` component that renders the `warnings` array from the status response. Each warning should show:
- An amber/red icon based on severity
- The warning message text
- A "Re-scrape" button mapped to the warning's `action` field

The button should trigger the appropriate scrape API call based on the `action`:
- `re_scrape_try_scorer` → `scrapeApi.scrapeMarket("try_scorer")`
- `re_scrape_prices` → `scrapeApi.importPrices()`
- `scrape_missing` → `scrapeApi.scrapeMissing()`
- etc.

If no warnings, show a green "All data looks good" message.

**Step 2: Commit**

```bash
git add src/pages/AdminScrape.tsx
git commit -m "feat: add actionable warnings panel with one-click re-scrape"
```

---

### Task 13: Redesign admin page — Scrape History

**Files:**
- Modify: `frontend/src/pages/AdminScrape.tsx`

**Step 1: Add collapsible scrape history section**

Create a `ScrapeHistory` component at the bottom of the admin page. It should:
- Fetch history from `scrapeApi.getHistory(season, round)`
- Display as a timeline/list of recent scrape runs
- Each entry shows: time, market type, status (icon), duration, match slug (if applicable)
- Collapsible by default (show/hide toggle)
- Color-code by status: green for completed, red for failed, gray for cancelled
- Show warnings count if the run had validation warnings

**Step 2: Commit**

```bash
git add src/pages/AdminScrape.tsx
git commit -m "feat: add collapsible scrape history timeline to admin page"
```

---

## Phase 5: Public Page Freshness Indicators

### Task 14: Add freshness indicators to Dashboard

**Files:**
- Modify: `frontend/src/pages/Dashboard.tsx` (currently 160 lines)

**Step 1: Enhance the Data Status section**

The existing Data Status section (lines 57-136) already shows per-match status pills. Enhance it:

1. Use `enriched_matches` instead of `matches` from the status response
2. For each market indicator (H/T/TS), show relative time: "H: 2h ago" instead of just a green dot
3. Add a subtle caveat banner when the `warnings` array contains `pre_squad_odds` type: "Some odds were retrieved before team announcements and may have changed"
4. Show squad count as "20/23" instead of just player count

Keep the existing green/amber status dot logic but make it warning-aware.

**Step 2: Add "last updated" text**

Below the round selector, add a small text showing the most recent scrape time: "Last updated: 14:32 today" using `last_scrape_run` from the status response.

**Step 3: Commit**

```bash
git add src/pages/Dashboard.tsx
git commit -m "feat: add data freshness timestamps and caveat banners to dashboard"
```

---

### Task 15: Add freshness indicator to Try Scorers page

**Files:**
- Modify: `frontend/src/pages/TryScorers.tsx` (currently 329 lines)

**Step 1: Add freshness header**

Add a `useRoundScrapeStatus` query to the TryScorers component. Below the title/edition bar (around line 168), add:

1. A small text: "Odds retrieved: Feb 21, 14:30" using the earliest `try_scorer.scraped_at` from `enriched_matches`
2. If any match has `try_scorer.status === "warning"`, show an amber banner: "Some odds were scraped before squad announcements. Players may have changed."

Keep it unobtrusive — just a line of small gray text and an optional amber banner.

**Step 2: Commit**

```bash
git add src/pages/TryScorers.tsx
git commit -m "feat: add odds freshness indicator to try scorers page"
```

---

## Phase 6: Final Verification

### Task 16: End-to-end verification

**Step 1: Start the full stack**

```bash
cd fantasy-six-nations && docker-compose up --build
```

**Step 2: Verify admin page**

1. Navigate to `http://localhost:3000/admin/scrape`
2. Verify: "Scrape Everything" button is visible and prominent
3. Verify: Individual market buttons (Handicaps, Totals, Try Scorers, Fantasy Prices, Fantasy Stats) are visible
4. Verify: Status grid shows per-match, per-market data with timestamps or "missing"
5. Verify: Warnings panel shows any applicable warnings
6. Click "Scrape Everything" — verify progress display shows step-by-step progress
7. After completion, verify: status grid updates with fresh timestamps
8. Verify: Scrape history section shows the recent run

**Step 3: Verify dashboard**

1. Navigate to `http://localhost:3000/`
2. Verify: Data status section shows relative timestamps ("2h ago")
3. Verify: Any pre-squad warnings appear as a caveat banner
4. Verify: Squad counts show as "X/23"

**Step 4: Verify try scorers page**

1. Navigate to `http://localhost:3000/tryscorers`
2. Verify: Odds freshness text appears below the header
3. If pre-squad data exists, verify amber banner appears

**Step 5: Commit any fixes**

```bash
git add -A && git commit -m "fix: address issues found during end-to-end verification"
```

---

## Summary

| Phase | Tasks | Key Deliverables |
|-------|-------|------------------|
| 1: Data Layer | 1-2 | ScrapeRun model, validation service with tests |
| 2: Backend API | 3-8 | Enriched status, scrape-all, fantasy-stats, history endpoints |
| 3: Frontend Types | 9 | TypeScript types, API client updates |
| 4: Admin Page | 10-13 | Control panel, status grid, warnings, history |
| 5: Public Pages | 14-15 | Dashboard & try scorers freshness indicators |
| 6: Verification | 16 | End-to-end testing |

Total: 16 tasks across 6 phases.
