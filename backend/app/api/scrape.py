"""
API endpoints for triggering odds scraping.

Supports:
- Scrape all markets for all matches
- Scrape a single market type (handicaps, totals, try_scorer) for all matches
- Scrape only missing markets (auto-detects what's null in DB)
"""

import asyncio
import uuid
import logging
from datetime import date
from typing import Dict, Any, List, Optional

from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import require_admin
from app.database import get_db, async_session
from app.models.odds import MatchOdds, Odds
from app.models.player import Player
from app.models.user import User
from app.schemas.odds import AllMatchOddsScrapeRequest, OddsScrapeResponse

router = APIRouter()
logger = logging.getLogger(__name__)

# In-memory job store (sufficient for single-server use)
_jobs: Dict[str, Dict[str, Any]] = {}

# Market definitions: (url_suffix, market_type)
ALL_MARKETS = [
    ("handicaps", "handicaps"),
    ("total-points", "match_totals"),
    ("anytime-tryscorer", "try_scorer"),
]

MARKET_URL_MAP = {
    "handicaps": "handicaps",
    "totals": "total-points",
    "try_scorer": "anytime-tryscorer",
}

MARKET_TYPE_MAP = {
    "handicaps": "handicaps",
    "totals": "match_totals",
    "try_scorer": "try_scorer",
}


async def _discover_matches(scraper):
    """Discover Six Nations matches from Oddschecker."""
    browser = await scraper._init_browser()
    try:
        page = await scraper._create_page(browser)
        matches = await scraper.discover_six_nations_matches(page)
    finally:
        await scraper._close_browser()
    return matches


async def _scrape_market_for_match(
    scraper, match: Dict, url_suffix: str, market_type: str,
    season: int, round_num: int,
):
    """Scrape a single market for a single match and save to DB."""
    from app.services.odds_service import OddsService

    slug = match["slug"]
    home = match["home"]
    away = match["away"]
    base_url = match["url"].rstrip("/")
    for suffix in ("/winner", "/anytime-tryscorer", "/handicaps", "/total-points"):
        if base_url.endswith(suffix):
            base_url = base_url[: -len(suffix)]
            break

    url = f"{base_url}/{url_suffix}"
    logger.info(f"Scraping {market_type} for {slug}: {url}")

    raw_data = await scraper.scrape(url, market_type=market_type)
    parsed_data = scraper.parse(raw_data)
    scraper.save_raw_json(raw_data, f"{slug}_{market_type}")

    async with async_session() as db:
        service = OddsService(db)
        if market_type == "handicaps":
            result = await service.save_handicap_odds(
                handicap_data=parsed_data,
                season=season,
                round_num=round_num,
                match_date=date.today(),
                home_team=home,
                away_team=away,
            )
        elif market_type == "match_totals":
            result = await service.save_match_totals_odds(
                totals_data=parsed_data,
                season=season,
                round_num=round_num,
                match_date=date.today(),
                home_team=home,
                away_team=away,
            )
        else:  # try_scorer
            result = await service.save_anytime_try_scorer_odds(
                odds_data=parsed_data,
                season=season,
                round_num=round_num,
                match_date=date.today(),
                home_team=home,
                away_team=away,
            )

    return result


async def _run_scraper(
    job_id: str,
    season: int,
    round_num: int,
    markets: List[tuple],
    per_match_missing: Optional[Dict[str, List[tuple]]] = None,
):
    """Background task: discover matches and scrape specified markets.

    Args:
        per_match_missing: Optional dict mapping "home|away" keys to their
            missing market list. When provided, only the missing markets for
            each match are scraped. When None, all ``markets`` are scraped
            for every match (used by "Refresh All" / single-market buttons).
    """
    from app.scrapers.oddschecker import OddscheckerScraper

    job = _jobs[job_id]

    try:
        job["message"] = "Launching browser..."
        scraper = OddscheckerScraper(headless=True)

        # Discover matches
        job["message"] = "Opening Oddschecker — finding matches..."
        logger.info("Discovering Six Nations matches on Oddschecker")
        matches = await _discover_matches(scraper)

        if not matches:
            job["status"] = "completed"
            job["message"] = "No matches found on Oddschecker"
            job["matches_found"] = 0
            return

        # Filter to only matches that need scraping when per_match_missing is set
        if per_match_missing is not None:
            matches = [
                m for m in matches
                if f"{m['home']}|{m['away']}" in per_match_missing
            ]

        if not matches:
            job["status"] = "completed"
            job["message"] = "All markets already scraped"
            job["matches_found"] = 0
            return

        job["matches_found"] = len(matches)
        market_names = [m[1].replace("_", " ") for m in markets]
        match_labels = [f"{m['home']} v {m['away']}" for m in matches]
        job["message"] = f"Found {len(matches)} match(es) to scrape: {', '.join(match_labels)}"
        logger.info(f"Found {len(matches)} matches: {[m['slug'] for m in matches]}")

        for i, match in enumerate(matches, 1):
            slug = match["slug"]
            home = match["home"]
            away = match["away"]
            match_result = {"match": slug, "markets": {}}

            # Use per-match markets if available, otherwise scrape all requested markets
            match_key = f"{home}|{away}"
            match_markets = (
                per_match_missing[match_key]
                if per_match_missing is not None and match_key in per_match_missing
                else markets
            )

            for j, (url_suffix, market_type) in enumerate(match_markets, 1):
                market_label = market_type.replace("_", " ")
                job["message"] = (
                    f"{home} v {away} ({i}/{len(matches)}): "
                    f"loading {market_label} page ({j}/{len(match_markets)})..."
                )
                job["current_match"] = slug

                try:
                    db_result = await _scrape_market_for_match(
                        scraper, match, url_suffix, market_type,
                        season, round_num,
                    )
                    match_result["markets"][market_type] = {
                        "status": "ok",
                        "db_result": db_result,
                    }
                    job["message"] = (
                        f"{home} v {away} ({i}/{len(matches)}): "
                        f"saved {market_label}"
                    )
                    logger.info(f"  {market_type} for {slug}: saved successfully")
                except Exception as e:
                    logger.error(f"  {market_type} for {slug} failed: {e}", exc_info=True)
                    match_result["markets"][market_type] = {
                        "status": "error",
                        "error": str(e),
                    }
                    job["message"] = (
                        f"{home} v {away} ({i}/{len(matches)}): "
                        f"{market_label} failed — {e}"
                    )

            job["matches_completed"] = i
            job.setdefault("results", []).append(match_result)

        job["status"] = "completed"
        total_markets = sum(
            1 for r in job["results"]
            for m in r["markets"].values()
            if m["status"] == "ok"
        )
        job["message"] = f"Done — scraped {total_markets} market(s) across {len(matches)} match(es)"
        logger.info(f"Scrape complete: {len(matches)} matches, markets: {market_names}")

    except Exception as e:
        logger.error(f"Scrape failed: {e}", exc_info=True)
        job["status"] = "failed"
        job["message"] = f"Scrape failed: {e}"


def _create_job(markets_label: str) -> str:
    """Create a new job entry and return the job_id."""
    job_id = str(uuid.uuid4())
    _jobs[job_id] = {
        "status": "in_progress",
        "message": f"Starting {markets_label} scrape...",
        "matches_found": 0,
        "matches_completed": 0,
        "current_match": None,
        "results": [],
    }
    return job_id


@router.post("/all-match-odds", response_model=OddsScrapeResponse)
async def scrape_all_match_odds(
    request: AllMatchOddsScrapeRequest,
    _admin: User = Depends(require_admin),
):
    """Scrape all markets (handicaps, totals, try scorer) for all matches."""
    job_id = _create_job("all markets")
    asyncio.create_task(_run_scraper(job_id, request.season, request.round, ALL_MARKETS))
    return OddsScrapeResponse(
        status="in_progress",
        job_id=job_id,
        message="Scraping all markets — discovering matches...",
    )


class MarketScrapeRequest(AllMatchOddsScrapeRequest):
    """Request model for single-market scraping."""
    market: str  # "handicaps", "totals", or "try_scorer"


@router.post("/market", response_model=OddsScrapeResponse)
async def scrape_single_market(
    request: MarketScrapeRequest,
    _admin: User = Depends(require_admin),
):
    """Scrape a single market type for all matches."""
    market = request.market
    if market not in MARKET_URL_MAP:
        return OddsScrapeResponse(
            status="error",
            job_id="",
            message=f"Invalid market: {market}. Use: handicaps, totals, try_scorer",
        )

    url_suffix = MARKET_URL_MAP[market]
    market_type = MARKET_TYPE_MAP[market]
    markets = [(url_suffix, market_type)]

    job_id = _create_job(market)
    asyncio.create_task(_run_scraper(job_id, request.season, request.round, markets))
    return OddsScrapeResponse(
        status="in_progress",
        job_id=job_id,
        message=f"Scraping {market} — discovering matches...",
    )


@router.post("/missing", response_model=OddsScrapeResponse)
async def scrape_missing_markets(
    request: AllMatchOddsScrapeRequest,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    """Auto-detect which markets are missing per match and scrape only those."""
    season = request.season
    round_num = request.round

    # Check what exists in DB
    result = await db.execute(
        select(MatchOdds)
        .where(MatchOdds.season == season, MatchOdds.round == round_num)
    )
    matches = result.scalars().all()

    # Build per-match missing map: "home|away" -> [(url_suffix, market_type), ...]
    per_match_missing: Dict[str, List[tuple]] = {}
    all_missing_types: set = set()

    if not matches:
        # No data at all — will scrape everything for all discovered matches
        all_missing_types = {"handicaps", "totals", "try_scorer"}
        # Can't build per-match map without DB data, fall back to flat scrape
        markets = [(MARKET_URL_MAP[m], MARKET_TYPE_MAP[m]) for m in all_missing_types]
        missing_label = ", ".join(sorted(all_missing_types))
        job_id = _create_job(f"missing ({missing_label})")
        asyncio.create_task(_run_scraper(job_id, season, round_num, markets))
        return OddsScrapeResponse(
            status="in_progress",
            job_id=job_id,
            message=f"Scraping missing markets: {missing_label}",
        )

    for match in matches:
        key = f"{match.home_team}|{match.away_team}"
        missing_markets = []

        if match.handicap_line is None:
            missing_markets.append((MARKET_URL_MAP["handicaps"], MARKET_TYPE_MAP["handicaps"]))
            all_missing_types.add("handicaps")

        if match.over_under_line is None:
            missing_markets.append((MARKET_URL_MAP["totals"], MARKET_TYPE_MAP["totals"]))
            all_missing_types.add("totals")

        # Check try scorer odds for this specific match
        try_result = await db.execute(
            select(func.count())
            .select_from(Odds)
            .join(Player, Odds.player_id == Player.id)
            .where(
                Odds.season == season,
                Odds.round == round_num,
                Player.country.in_([match.home_team, match.away_team]),
                Odds.anytime_try_scorer.isnot(None),
            )
        )
        if (try_result.scalar() or 0) == 0:
            missing_markets.append((MARKET_URL_MAP["try_scorer"], MARKET_TYPE_MAP["try_scorer"]))
            all_missing_types.add("try_scorer")

        if missing_markets:
            per_match_missing[key] = missing_markets

    if not per_match_missing:
        return OddsScrapeResponse(
            status="completed",
            job_id="",
            message="All markets already scraped for this round",
        )

    # Build a flat list of all market types for job labelling / fallback
    all_markets = [(MARKET_URL_MAP[m], MARKET_TYPE_MAP[m]) for m in all_missing_types]
    match_count = len(per_match_missing)
    missing_label = ", ".join(sorted(all_missing_types))
    job_id = _create_job(f"missing ({missing_label}) for {match_count} match(es)")
    asyncio.create_task(
        _run_scraper(job_id, season, round_num, all_markets, per_match_missing=per_match_missing)
    )
    return OddsScrapeResponse(
        status="in_progress",
        job_id=job_id,
        message=f"Scraping {missing_label} for {match_count} match(es)",
    )


@router.post("/import-prices", response_model=OddsScrapeResponse)
async def import_prices(
    request: AllMatchOddsScrapeRequest,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    """Import fantasy prices from the latest JSON file for the given season/round."""
    import json
    from pathlib import Path
    from app.services.import_service import import_scraped_json

    data_dir = Path(__file__).resolve().parent.parent.parent / "data"

    # Find JSON files matching the round
    candidates = []
    for f in sorted(data_dir.glob("fantasy_players_*.json"), reverse=True):
        try:
            with open(f, "r", encoding="utf-8") as fh:
                header = json.load(fh)
            if header.get("season") == request.season and header.get("round") == request.round:
                candidates.append(f)
        except Exception:
            continue

    if not candidates:
        return OddsScrapeResponse(
            status="completed",
            job_id="",
            message=f"No price JSON found for season {request.season} round {request.round} in data/",
        )

    # Use the most recent file (sorted descending by filename = timestamp)
    chosen = candidates[0]
    result = await import_scraped_json(db, str(chosen))

    return OddsScrapeResponse(
        status="completed",
        job_id="",
        message=(
            f"Imported {result['prices_set']} prices "
            f"({result['matched_existing']} matched, {result['created_new']} new players) "
            f"from {chosen.name}"
        ),
    )


@router.get("/active")
async def get_active_jobs():
    """Return any in-progress jobs and the most recent completed/failed job."""
    active = []
    latest_finished = None
    for jid, job in _jobs.items():
        entry = {"job_id": jid, **job}
        if job["status"] == "in_progress":
            active.append(entry)
        elif latest_finished is None or jid > (latest_finished.get("job_id") or ""):
            latest_finished = entry

    return {"active": active, "latest_finished": latest_finished}


@router.get("/status/{job_id}")
async def get_scrape_status(job_id: str):
    """Get the status of a scrape job."""
    job = _jobs.get(job_id)
    if not job:
        return {"status": "not_found", "message": "Job not found"}
    return job
