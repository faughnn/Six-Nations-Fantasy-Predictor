from typing import Optional, List, Dict, Any
from datetime import date
from pydantic import BaseModel, HttpUrl
from enum import Enum


class MarketType(str, Enum):
    TRY_SCORER = "try_scorer"
    MATCH_TOTALS = "match_totals"
    HANDICAPS = "handicaps"
    TOTAL_POINTS = "total_points"


class OddsScrapeRequest(BaseModel):
    """Request model for odds scraping endpoints."""
    url: HttpUrl
    season: int = 2025
    round: int
    match_date: date
    home_team: str
    away_team: str


class AllMatchOddsScrapeRequest(BaseModel):
    """Request model for scraping all match odds (auto-discovers matches)."""
    season: int = 2026
    round: int = 1


class OddsScrapeResponse(BaseModel):
    """Response model for odds scraping endpoints."""
    status: str
    job_id: str
    message: Optional[str] = None


class PlayerOddsResult(BaseModel):
    """Individual player odds result."""
    player_name: str
    average_odds: float
    num_bookmakers: int
    min_odds: float
    max_odds: float
    matched_player_id: Optional[int] = None
    match_confidence: Optional[float] = None


class MatchTotalsResult(BaseModel):
    """Match totals odds result."""
    line: float
    average_over_odds: float
    average_under_odds: float
    num_bookmakers: int


class OddsScrapeResult(BaseModel):
    """Result of a completed try scorer scrape job."""
    job_id: str
    status: str  # "completed", "failed", "in_progress"
    saved: int = 0
    updated: int = 0
    not_found: List[str] = []
    low_confidence_matches: List[Dict[str, Any]] = []
    error: Optional[str] = None


class MatchTotalsScrapeResult(BaseModel):
    """Result of a completed match totals scrape job."""
    job_id: str
    status: str
    saved: bool = False
    line: Optional[float] = None
    over_odds: Optional[float] = None
    under_odds: Optional[float] = None
    error: Optional[str] = None


class HandicapScrapeResult(BaseModel):
    """Result of a completed handicaps scrape job."""
    job_id: str
    status: str
    saved: bool = False
    line: Optional[float] = None
    home_handicap_odds: Optional[float] = None
    away_handicap_odds: Optional[float] = None
    error: Optional[str] = None
