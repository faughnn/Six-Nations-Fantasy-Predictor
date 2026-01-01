from typing import Optional
from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel

router = APIRouter()

# Store for scraping job status
scrape_jobs = {}


class ScrapeRequest(BaseModel):
    round: Optional[int] = None
    league: Optional[str] = None
    season: Optional[str] = None


class ScrapeStatus(BaseModel):
    job_id: str
    status: str
    message: Optional[str] = None


@router.post("/club-stats")
async def scrape_club_stats(
    request: ScrapeRequest,
    background_tasks: BackgroundTasks,
):
    """Trigger club stats scrape"""
    job_id = f"club_stats_{request.league}_{request.season}"
    scrape_jobs[job_id] = {"status": "started", "message": "Scraping club stats..."}

    # In a real implementation, this would trigger actual scraping
    # background_tasks.add_task(run_club_scraper, request.league, request.season)

    return {"status": "started", "job_id": job_id}


@router.post("/six-nations")
async def scrape_six_nations(
    request: ScrapeRequest,
    background_tasks: BackgroundTasks,
):
    """Trigger Six Nations stats scrape"""
    job_id = f"six_nations_{request.season}"
    scrape_jobs[job_id] = {"status": "started", "message": "Scraping Six Nations stats..."}

    return {"status": "started", "job_id": job_id}


@router.post("/odds")
async def scrape_odds(
    request: ScrapeRequest,
    background_tasks: BackgroundTasks,
):
    """Trigger odds scrape"""
    job_id = f"odds_round_{request.round}"
    scrape_jobs[job_id] = {"status": "started", "message": "Scraping odds..."}

    return {"status": "started", "job_id": job_id}


@router.post("/fantasy-prices")
async def scrape_fantasy_prices(
    request: ScrapeRequest,
    background_tasks: BackgroundTasks,
):
    """Trigger fantasy prices scrape"""
    job_id = f"prices_round_{request.round}"
    scrape_jobs[job_id] = {"status": "started", "message": "Scraping fantasy prices..."}

    return {"status": "started", "job_id": job_id}


@router.get("/status")
async def get_scrape_status():
    """Get status of all scraping jobs"""
    return scrape_jobs
