"""
API endpoints for triggering odds scraping.

Supports:
- Scrape all markets for all matches
- Scrape a single market type (handicaps, totals, try_scorer) for all matches
- Scrape only missing markets (auto-detects what's null in DB)
"""

import asyncio
import json
import uuid
import logging
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional

from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import require_admin
from app.fixtures import is_match_played
from app.database import get_db, async_session
from app.models.odds import MatchOdds, Odds
from app.models.player import Player
from app.models.scrape_run import ScrapeRun
from app.models.user import User
from app.schemas.odds import AllMatchOddsScrapeRequest, OddsScrapeResponse

router = APIRouter()
logger = logging.getLogger(__name__)

# In-memory job store (sufficient for single-server use)
_jobs: Dict[str, Dict[str, Any]] = {}
_tasks: Dict[str, asyncio.Task] = {}

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

    started_at = datetime.now(timezone.utc)
    try:
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

        await _record_scrape_run(
            season, round_num, market_type, slug,
            "completed", started_at, result_summary=result,
        )
        return result

    except Exception as e:
        await _record_scrape_run(
            season, round_num, market_type, slug,
            "failed", started_at, error_message=str(e),
        )
        raise


async def _scrape_handicaps_via_overview(
    season: int,
    round_num: int,
    job: Dict[str, Any],
    match_filter: Optional[tuple] = None,
) -> List[Dict]:
    """Scrape handicaps for all matches at once using the overview page.

    Returns a list of per-match result dicts.
    """
    from app.scrapers.oddschecker import OddscheckerScraper
    from app.services.odds_service import OddsService

    job["message"] = "Scraping handicaps from overview page..."
    scraper = OddscheckerScraper(headless=True)

    started_at = datetime.now(timezone.utc)
    overview_matches = await scraper.scrape_handicaps_overview()

    if not overview_matches:
        job["message"] = "No handicap data found on overview page"
        return []

    results = []
    for m in overview_matches:
        home = m["home"]
        away = m["away"]
        slug = m["slug"]

        # Apply match filter if set
        if match_filter is not None:
            filter_home, filter_away = match_filter
            if home.lower() != filter_home.lower() or away.lower() != filter_away.lower():
                continue

        # Skip already-played matches (unless single-match mode)
        if match_filter is None and is_match_played(season, round_num, home, away):
            continue

        # Build parsed_data in the format save_handicap_odds() expects
        home_line = m["home_line"]
        parsed_data = [{
            "line": abs(home_line),
            "home_team": home,
            "away_team": away,
            "home_spread": home_line,
            "home_odds": m.get("home_odds"),
            "away_odds": m.get("away_odds"),
            "num_bookmakers": 99,  # overview is already a consensus
        }]

        # Save raw JSON
        raw_json = {
            "market_type": "handicaps_overview",
            "scraped_at": datetime.now(timezone.utc).isoformat(),
            **m,
        }
        scraper.save_raw_json(raw_json, f"{slug}_handicaps")

        # Save to DB
        try:
            async with async_session() as db:
                service = OddsService(db)
                db_result = await service.save_handicap_odds(
                    handicap_data=parsed_data,
                    season=season,
                    round_num=round_num,
                    match_date=date.today(),
                    home_team=home,
                    away_team=away,
                )
            results.append({"match": slug, "status": "ok", "db_result": db_result})
            await _record_scrape_run(
                season, round_num, "handicaps", slug,
                "completed", started_at, result_summary=db_result,
            )
            logger.info(f"Handicap saved for {slug}: line={home_line}")
        except Exception as e:
            results.append({"match": slug, "status": "error", "error": str(e)})
            await _record_scrape_run(
                season, round_num, "handicaps", slug,
                "failed", started_at, error_message=str(e),
            )
            logger.error(f"Failed to save handicap for {slug}: {e}")

    return results


async def _run_scraper(
    job_id: str,
    season: int,
    round_num: int,
    markets: List[tuple],
    per_match_missing: Optional[Dict[str, List[tuple]]] = None,
    match_filter: Optional[tuple] = None,  # (home_team, away_team) to scrape one match only
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

        # Filter to a single match when match_filter is set
        if match_filter is not None:
            filter_home, filter_away = match_filter
            matches = [
                m for m in matches
                if m['home'].lower() == filter_home.lower()
                and m['away'].lower() == filter_away.lower()
            ]

        # Filter to only matches that need scraping when per_match_missing is set
        if per_match_missing is not None:
            matches = [
                m for m in matches
                if f"{m['home']}|{m['away']}" in per_match_missing
            ]

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

        job["matches_found"] = len(matches)
        market_names = [m[1].replace("_", " ") for m in markets]
        match_labels = [f"{m['home']} v {m['away']}" for m in matches]
        job["message"] = f"Found {len(matches)} match(es) to scrape: {', '.join(match_labels)}"
        logger.info(f"Found {len(matches)} matches: {[m['slug'] for m in matches]}")

        # ---- Handicaps: scrape via overview page (all matches at once) ----
        has_handicaps = any(mt == "handicaps" for _, mt in markets)
        # Also check per_match_missing for handicaps
        if not has_handicaps and per_match_missing is not None:
            has_handicaps = any(
                mt == "handicaps"
                for missing_list in per_match_missing.values()
                for _, mt in missing_list
            )

        handicap_results = {}
        if has_handicaps:
            job["message"] = "Scraping handicaps from overview page..."
            try:
                hc_results = await _scrape_handicaps_via_overview(
                    season, round_num, job, match_filter=match_filter,
                )
                for r in hc_results:
                    handicap_results[r["match"]] = r
                job["message"] = f"Handicaps done — {len(hc_results)} match(es)"
            except Exception as e:
                logger.error(f"Overview handicaps failed: {e}", exc_info=True)
                job["message"] = f"Handicaps failed: {e}"

        # ---- Other markets: scrape per-match as before ----
        non_handicap_markets = [(s, t) for s, t in markets if t != "handicaps"]

        for i, match in enumerate(matches, 1):
            slug = match["slug"]
            home = match["home"]
            away = match["away"]
            match_result = {"match": slug, "markets": {}}

            # Include handicap result if we scraped it
            if slug in handicap_results:
                hc = handicap_results[slug]
                match_result["markets"]["handicaps"] = {
                    "status": hc["status"],
                    "db_result": hc.get("db_result"),
                    "error": hc.get("error"),
                }

            # Use per-match markets if available, otherwise scrape all requested markets
            match_key = f"{home}|{away}"
            match_markets = (
                per_match_missing[match_key]
                if per_match_missing is not None and match_key in per_match_missing
                else non_handicap_markets
            )
            # Filter out handicaps from per-match list (already handled above)
            match_markets = [(s, t) for s, t in match_markets if t != "handicaps"]

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
            if m.get("status") == "ok"
        )
        job["message"] = f"Done — scraped {total_markets} market(s) across {len(matches)} match(es)"
        logger.info(f"Scrape complete: {len(matches)} matches, markets: {market_names}")

    except asyncio.CancelledError:
        logger.info(f"Scrape job {job_id} was cancelled")
        job["status"] = "cancelled"
        job["message"] = "Scrape cancelled by user"
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
    _tasks[job_id] = asyncio.create_task(_run_scraper(job_id, request.season, request.round, ALL_MARKETS))
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
    _tasks[job_id] = asyncio.create_task(_run_scraper(job_id, request.season, request.round, markets))
    return OddsScrapeResponse(
        status="in_progress",
        job_id=job_id,
        message=f"Scraping {market} — discovering matches...",
    )


class MatchMarketScrapeRequest(AllMatchOddsScrapeRequest):
    """Request model for scraping a specific market for a specific match."""
    market: str  # "handicaps", "totals", or "try_scorer"
    home_team: str
    away_team: str


@router.post("/match-market", response_model=OddsScrapeResponse)
async def scrape_match_market(
    request: MatchMarketScrapeRequest,
    _admin: User = Depends(require_admin),
):
    """Scrape a single market for a single match."""
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
    match_label = f"{request.home_team} v {request.away_team}"

    job_id = _create_job(f"{market} for {match_label}")
    _tasks[job_id] = asyncio.create_task(
        _run_scraper(
            job_id, request.season, request.round, markets,
            match_filter=(request.home_team, request.away_team),
        )
    )
    return OddsScrapeResponse(
        status="in_progress",
        job_id=job_id,
        message=f"Scraping {market} for {match_label}...",
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
        _tasks[job_id] = asyncio.create_task(_run_scraper(job_id, season, round_num, markets))
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
    _tasks[job_id] = asyncio.create_task(
        _run_scraper(job_id, season, round_num, all_markets, per_match_missing=per_match_missing)
    )
    return OddsScrapeResponse(
        status="in_progress",
        job_id=job_id,
        message=f"Scraping {missing_label} for {match_count} match(es)",
    )


async def _run_fantasy_import(
    job_id: str, season: int, round_num: int, headless: bool,
):
    """Background task: scrape fantasy prices and import to DB."""
    from app.scrapers.fantasy_sixnations import FantasySixNationsScraper, SessionExpiredError
    from app.services.import_service import import_scraped_json

    job = _jobs[job_id]
    started_at = datetime.now(timezone.utc)

    try:
        job["message"] = "Launching browser..."
        scraper = FantasySixNationsScraper(headless=headless)

        job["message"] = "Opening Fantasy Six Nations..."
        raw_data = await scraper.scrape()

        job["message"] = "Parsing player data..."
        players = scraper.parse(raw_data)

        if not players:
            job["status"] = "failed"
            job["message"] = "No players found — check the fantasy site"
            await _record_scrape_run(
                season, round_num, "fantasy_prices", None,
                "failed", started_at, error_message="No players found",
            )
            return

        # Save to JSON for record-keeping
        data_dir = Path(__file__).resolve().parent.parent.parent / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        output_path = data_dir / f"fantasy_players_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        output = {
            "season": season,
            "round": round_num,
            "scraped_at": datetime.utcnow().isoformat(),
            "player_count": len(players),
            "players": players,
        }
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2, ensure_ascii=False, default=str)

        job["message"] = f"Importing {len(players)} players..."
        async with async_session() as db:
            result = await import_scraped_json(db, str(output_path))

        job["status"] = "completed"
        parts = [
            f"Imported {result['prices_set']} prices",
            f"({result['matched_existing']} matched, {result['created_new']} new)",
            f"from {len(players)} players",
        ]
        if result.get("marked_not_playing"):
            parts.append(f"— {result['marked_not_playing']} unlisted marked not playing")
        job["message"] = " ".join(parts)

        await _record_scrape_run(
            season, round_num, "fantasy_prices", None,
            "completed", started_at, result_summary=result,
        )

    except SessionExpiredError as e:
        job["status"] = "session_expired"
        job["message"] = str(e)
        await _record_scrape_run(
            season, round_num, "fantasy_prices", None,
            "failed", started_at, error_message=str(e),
        )
    except asyncio.CancelledError:
        job["status"] = "cancelled"
        job["message"] = "Import cancelled by user"
    except Exception as e:
        logger.error(f"Fantasy import failed: {e}", exc_info=True)
        job["status"] = "failed"
        job["message"] = f"Import failed: {e}"
        await _record_scrape_run(
            season, round_num, "fantasy_prices", None,
            "failed", started_at, error_message=str(e),
        )


@router.post("/import-prices", response_model=OddsScrapeResponse)
async def import_prices(
    request: AllMatchOddsScrapeRequest,
    _admin: User = Depends(require_admin),
):
    """Scrape fantasy prices headlessly (using saved session) and import to DB."""
    job_id = _create_job("fantasy prices (headless)")
    _tasks[job_id] = asyncio.create_task(
        _run_fantasy_import(job_id, request.season, request.round, headless=True)
    )
    return OddsScrapeResponse(
        status="in_progress",
        job_id=job_id,
        message="Scraping fantasy prices...",
    )


@router.post("/import-prices-login", response_model=OddsScrapeResponse)
async def import_prices_with_login(
    request: AllMatchOddsScrapeRequest,
    _admin: User = Depends(require_admin),
):
    """Scrape fantasy prices with visible browser for login, then import to DB."""
    job_id = _create_job("fantasy prices (login)")
    _tasks[job_id] = asyncio.create_task(
        _run_fantasy_import(job_id, request.season, request.round, headless=False)
    )
    return OddsScrapeResponse(
        status="in_progress",
        job_id=job_id,
        message="Opening browser for login...",
    )


async def _run_scrape_all(job_id: str, season: int, round_num: int):
    """Background task: scrape all odds markets + fantasy prices in sequence."""
    from app.scrapers.oddschecker import OddscheckerScraper
    from app.scrapers.fantasy_sixnations import FantasySixNationsScraper, SessionExpiredError
    from app.services.import_service import import_scraped_json

    job = _jobs[job_id]

    try:
        # Discover matches
        job["message"] = "Discovering matches..."
        job["step_label"] = "Discovering matches"
        scraper = OddscheckerScraper(headless=True)
        matches = await _discover_matches(scraper)

        if not matches:
            job["status"] = "completed"
            job["message"] = "No matches found on Oddschecker"
            return

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

        match_labels = [f"{m['home']} v {m['away']}" for m in matches]
        logger.info(f"Scrape-all: found {len(matches)} matches: {match_labels}")

        errors = []
        total_ok = 0

        # Step 1: Handicaps via overview page (all matches at once)
        job["current_step"] = 1
        job["step_label"] = "Step 1/4: Handicaps (overview)"
        job["message"] = job["step_label"]

        if matches:
            try:
                hc_results = await _scrape_handicaps_via_overview(
                    season, round_num, job,
                )
                for r in hc_results:
                    if r["status"] == "ok":
                        total_ok += 1
                    else:
                        errors.append(f"Handicaps for {r['match']}: {r.get('error')}")
            except Exception as e:
                err_msg = f"Handicaps overview: {e}"
                logger.error(f"Scrape-all: {err_msg}", exc_info=True)
                errors.append(err_msg)

        # Steps 2-3: Totals and try scorers per-match
        per_match_markets = [
            ("total-points", "match_totals", "Totals"),
            ("anytime-tryscorer", "try_scorer", "Try scorers"),
        ]

        for step_idx, (url_suffix, market_type, market_label) in enumerate(per_match_markets, 2):
            job["current_step"] = step_idx
            for mi, match in enumerate(matches, 1):
                slug = match["slug"]
                job["step_label"] = f"Step {step_idx}/4: {market_label} — {slug} ({mi}/{len(matches)})"
                job["message"] = job["step_label"]

                try:
                    await _scrape_market_for_match(
                        scraper, match, url_suffix, market_type,
                        season, round_num,
                    )
                    total_ok += 1
                except Exception as e:
                    err_msg = f"{market_label} for {slug}: {e}"
                    logger.error(f"Scrape-all: {err_msg}", exc_info=True)
                    errors.append(err_msg)

        # Step 4: Fantasy prices import
        job["current_step"] = 4
        job["step_label"] = "Step 4/4: Fantasy prices"
        job["message"] = "Step 4/4: Fantasy prices — launching browser..."

        started_at = datetime.now(timezone.utc)
        try:
            fantasy_scraper = FantasySixNationsScraper(headless=True)

            job["message"] = "Step 4/4: Fantasy prices — scraping..."
            raw_data = await fantasy_scraper.scrape()

            job["message"] = "Step 4/4: Fantasy prices — parsing..."
            players = fantasy_scraper.parse(raw_data)

            if not players:
                errors.append("Fantasy prices: no players found")
                await _record_scrape_run(
                    season, round_num, "fantasy_prices", None,
                    "failed", started_at, error_message="No players found",
                )
            else:
                # Save to JSON for record-keeping
                data_dir = Path(__file__).resolve().parent.parent.parent / "data"
                data_dir.mkdir(parents=True, exist_ok=True)
                output_path = data_dir / f"fantasy_players_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                output = {
                    "season": season,
                    "round": round_num,
                    "scraped_at": datetime.utcnow().isoformat(),
                    "player_count": len(players),
                    "players": players,
                }
                with open(output_path, "w", encoding="utf-8") as f:
                    json.dump(output, f, indent=2, ensure_ascii=False, default=str)

                job["message"] = f"Step 4/4: Fantasy prices — importing {len(players)} players..."
                async with async_session() as db:
                    result = await import_scraped_json(db, str(output_path))

                total_ok += 1
                await _record_scrape_run(
                    season, round_num, "fantasy_prices", None,
                    "completed", started_at, result_summary=result,
                )

        except SessionExpiredError as e:
            job["status"] = "session_expired"
            job["message"] = str(e)
            await _record_scrape_run(
                season, round_num, "fantasy_prices", None,
                "failed", started_at, error_message=str(e),
            )
            return  # Don't continue — other fantasy scrapers will fail too
        except Exception as e:
            errors.append(f"Fantasy prices: {e}")
            logger.error(f"Scrape-all fantasy import failed: {e}", exc_info=True)
            await _record_scrape_run(
                season, round_num, "fantasy_prices", None,
                "failed", started_at, error_message=str(e),
            )

        # Final status
        if total_ok == 0:
            job["status"] = "failed"
            job["message"] = f"All steps failed: {'; '.join(errors)}"
        else:
            job["status"] = "completed"
            parts = [f"Done — {total_ok} successful"]
            if errors:
                parts.append(f", {len(errors)} error(s): {'; '.join(errors)}")
            job["message"] = "".join(parts)

    except asyncio.CancelledError:
        job["status"] = "cancelled"
        job["message"] = "Scrape-all cancelled by user"
    except Exception as e:
        logger.error(f"Scrape-all failed: {e}", exc_info=True)
        job["status"] = "failed"
        job["message"] = f"Scrape-all failed: {e}"


@router.post("/all", response_model=OddsScrapeResponse)
async def scrape_all(
    request: AllMatchOddsScrapeRequest,
    _admin: User = Depends(require_admin),
):
    """Scrape everything: all odds markets + fantasy prices."""
    job_id = _create_job("all markets + prices")
    _jobs[job_id]["total_steps"] = 4
    _jobs[job_id]["current_step"] = 0
    _jobs[job_id]["step_label"] = "Starting..."
    _tasks[job_id] = asyncio.create_task(
        _run_scrape_all(job_id, request.season, request.round)
    )
    return OddsScrapeResponse(
        status="in_progress",
        job_id=job_id,
        message="Scraping all markets + importing prices...",
    )


async def _run_fantasy_stats(job_id: str, season: int, round_num: int):
    """Background task: scrape fantasy stats for a round."""
    import sys
    from pathlib import Path as _Path
    # Ensure the backend dir is on the path for scrape_fantasy_stats imports
    backend_dir = str(_Path(__file__).resolve().parent.parent.parent)
    if backend_dir not in sys.path:
        sys.path.insert(0, backend_dir)

    from scrape_fantasy_stats import (
        create_browser_context, dismiss_overlays, wait_for_table,
        select_round, scrape_all_pages, parse_players, save_to_db,
        STATS_URL,
    )
    from playwright.async_api import async_playwright

    job = _jobs[job_id]
    started_at = datetime.now(timezone.utc)

    try:
        job["message"] = "Launching browser..."
        pw = await async_playwright().start()
        browser = await pw.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"],
        )

        try:
            context = await create_browser_context(browser)
            page = await context.new_page()

            job["message"] = "Navigating to stats page..."
            await page.goto(STATS_URL, wait_until="domcontentloaded", timeout=60000)
            await dismiss_overlays(page)

            if not await wait_for_table(page):
                # Detect session expiry vs generic load failure
                is_session_expired = '#/welcome' in page.url or '#/login' in page.url
                status = "session_expired" if is_session_expired else "failed"
                msg = "Session expired — run capture_session.py to log in again" if is_session_expired else "Could not load stats table"

                job["status"] = status
                job["message"] = msg
                await _record_scrape_run(
                    season, round_num, "fantasy_stats", None,
                    "failed", started_at, error_message=msg,
                )
                return

            job["message"] = f"Selecting round {round_num}..."
            if not await select_round(page, round_num):
                job["status"] = "failed"
                job["message"] = f"Could not select round {round_num}"
                await _record_scrape_run(
                    season, round_num, "fantasy_stats", None,
                    "failed", started_at,
                    error_message=f"Could not select round {round_num}",
                )
                return

            await asyncio.sleep(2)

            job["message"] = f"Scraping stats for round {round_num}..."
            raw_players = await scrape_all_pages(page)

            job["message"] = "Parsing player stats..."
            records = parse_players(raw_players, round_num)

            if not records:
                job["status"] = "failed"
                job["message"] = "No player stats found"
                await _record_scrape_run(
                    season, round_num, "fantasy_stats", None,
                    "failed", started_at, error_message="No player stats found",
                )
                return

            job["message"] = f"Saving {len(records)} stat records to DB..."
            await save_to_db(records, season)

            job["status"] = "completed"
            job["message"] = f"Imported {len(records)} player stats for round {round_num}"

            await _record_scrape_run(
                season, round_num, "fantasy_stats", None,
                "completed", started_at,
                result_summary={"records_saved": len(records)},
            )

        finally:
            await browser.close()
            await pw.stop()

    except asyncio.CancelledError:
        job["status"] = "cancelled"
        job["message"] = "Fantasy stats scrape cancelled"
    except Exception as e:
        logger.error(f"Fantasy stats scrape failed: {e}", exc_info=True)
        job["status"] = "failed"
        job["message"] = f"Fantasy stats scrape failed: {e}"
        await _record_scrape_run(
            season, round_num, "fantasy_stats", None,
            "failed", started_at, error_message=str(e),
        )


@router.post("/fantasy-stats", response_model=OddsScrapeResponse)
async def scrape_fantasy_stats_endpoint(
    request: AllMatchOddsScrapeRequest,
    _admin: User = Depends(require_admin),
):
    """Trigger fantasy stats scraper for the specified round."""
    job_id = _create_job("fantasy stats")
    _tasks[job_id] = asyncio.create_task(
        _run_fantasy_stats(job_id, request.season, request.round)
    )
    return OddsScrapeResponse(
        status="in_progress",
        job_id=job_id,
        message=f"Scraping fantasy stats for round {request.round}...",
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


@router.post("/kill/{job_id}")
async def kill_scrape_job(
    job_id: str,
    _admin: User = Depends(require_admin),
):
    """Cancel a running scrape job."""
    task = _tasks.get(job_id)
    if not task:
        return {"status": "not_found", "message": "Job not found"}
    if task.done():
        return {"status": "already_finished", "message": "Job already finished"}
    task.cancel()
    return {"status": "cancelling", "message": "Job cancel requested"}


@router.get("/status/{job_id}")
async def get_scrape_status(job_id: str):
    """Get the status of a scrape job."""
    job = _jobs.get(job_id)
    if not job:
        return {"status": "not_found", "message": "Job not found"}
    return job


@router.get("/history")
async def get_scrape_history(
    season: int = 2026,
    game_round: int = 1,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
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
