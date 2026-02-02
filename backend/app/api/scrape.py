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

from app.database import get_db, async_session
from app.models.odds import MatchOdds, Odds
from app.models.player import Player
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
            )

    return result


async def _run_scraper(
    job_id: str,
    season: int,
    round_num: int,
    markets: List[tuple],
):
    """Background task: discover matches and scrape specified markets."""
    from app.scrapers.oddschecker import OddscheckerScraper

    job = _jobs[job_id]

    try:
        scraper = OddscheckerScraper(headless=True)

        # Discover matches
        job["message"] = "Discovering Six Nations matches..."
        logger.info("Discovering Six Nations matches on Oddschecker")
        matches = await _discover_matches(scraper)

        if not matches:
            job["status"] = "completed"
            job["message"] = "No matches found on Oddschecker"
            job["matches_found"] = 0
            return

        job["matches_found"] = len(matches)
        market_names = [m[1].replace("_", " ") for m in markets]
        job["message"] = f"Found {len(matches)} matches. Scraping: {', '.join(market_names)}..."
        logger.info(f"Found {len(matches)} matches: {[m['slug'] for m in matches]}")

        for i, match in enumerate(matches, 1):
            slug = match["slug"]
            home = match["home"]
            away = match["away"]
            match_result = {"match": slug, "markets": {}}

            for url_suffix, market_type in markets:
                market_label = market_type.replace("_", " ")
                job["message"] = f"Scraping {home} v {away} ({i}/{len(matches)}): {market_label}..."
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
                    logger.info(f"  {market_type} for {slug}: saved successfully")
                except Exception as e:
                    logger.error(f"  {market_type} for {slug} failed: {e}", exc_info=True)
                    match_result["markets"][market_type] = {
                        "status": "error",
                        "error": str(e),
                    }

            job["matches_completed"] = i
            job.setdefault("results", []).append(match_result)

        job["status"] = "completed"
        job["message"] = f"Scraped {len(matches)} matches ({', '.join(market_names)})"
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
async def scrape_all_match_odds(request: AllMatchOddsScrapeRequest):
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
async def scrape_single_market(request: MarketScrapeRequest):
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
):
    """Auto-detect which markets are missing and scrape only those."""
    season = request.season
    round_num = request.round

    # Check what exists in DB
    result = await db.execute(
        select(MatchOdds)
        .where(MatchOdds.season == season, MatchOdds.round == round_num)
    )
    matches = result.scalars().all()

    missing = set()

    if not matches:
        # No data at all — scrape everything
        missing = {"handicaps", "totals", "try_scorer"}
    else:
        if not all(m.handicap_line is not None for m in matches):
            missing.add("handicaps")
        if not all(m.over_under_line is not None for m in matches):
            missing.add("totals")

        # Check try scorer odds
        for match in matches:
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
                missing.add("try_scorer")
                break

    if not missing:
        return OddsScrapeResponse(
            status="completed",
            job_id="",
            message="All markets already scraped for this round",
        )

    markets = []
    for m in missing:
        markets.append((MARKET_URL_MAP[m], MARKET_TYPE_MAP[m]))

    missing_label = ", ".join(sorted(missing))
    job_id = _create_job(f"missing ({missing_label})")
    asyncio.create_task(_run_scraper(job_id, season, round_num, markets))
    return OddsScrapeResponse(
        status="in_progress",
        job_id=job_id,
        message=f"Scraping missing markets: {missing_label}",
    )


@router.get("/status/{job_id}")
async def get_scrape_status(job_id: str):
    """Get the status of a scrape job."""
    job = _jobs.get(job_id)
    if not job:
        return {"status": "not_found", "message": "Job not found"}
    return job
