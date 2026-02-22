from typing import Optional, List
from datetime import date, datetime
from pydantic import BaseModel


class MatchTryScorer(BaseModel):
    player_id: int
    name: str
    country: str
    odds: float
    implied_prob: float


class MatchResponse(BaseModel):
    home_team: str
    away_team: str
    match_date: date
    home_win: Optional[float] = None
    away_win: Optional[float] = None
    draw: Optional[float] = None
    handicap_line: Optional[float] = None
    home_handicap_odds: Optional[float] = None
    away_handicap_odds: Optional[float] = None
    over_under_line: Optional[float] = None
    over_odds: Optional[float] = None
    under_odds: Optional[float] = None
    top_try_scorers: List[MatchTryScorer] = []


class CurrentRoundResponse(BaseModel):
    season: int
    round: int


class MatchScrapeStatus(BaseModel):
    home_team: str
    away_team: str
    match_date: date
    has_handicap: bool
    has_totals: bool
    has_try_scorer: bool
    try_scorer_count: int = 0


class MarketStatus(BaseModel):
    status: str  # "complete", "missing", "warning"
    scraped_at: Optional[datetime] = None
    warning: Optional[str] = None


class SquadStatus(BaseModel):
    total: int
    expected: int = 46  # 23 per team × 2 teams per match
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


class RoundScrapeStatusResponse(BaseModel):
    season: int
    round: int
    # Existing fields (keep as-is)
    matches: List[MatchScrapeStatus]
    missing_markets: List[str]
    has_prices: bool = False
    price_count: int = 0
    availability_known: int = 0
    availability_unknown: int = 0
    # New enriched fields
    enriched_matches: list[EnrichedMatchScrapeStatus] = []
    fantasy_prices: Optional[DatasetStatus] = None
    fantasy_stats: Optional[DatasetStatus] = None
    warnings: list[ValidationWarning] = []
    last_scrape_run: Optional[ScrapeRunSummary] = None
    scrape_history: list[ScrapeRunSummary] = []


class TryScorerDetail(BaseModel):
    player_id: int
    name: str
    country: str
    fantasy_position: str
    match: str
    anytime_try_odds: Optional[float] = None
    implied_prob: Optional[float] = None
    expected_try_points: Optional[float] = None
    price: Optional[float] = None
    ownership_pct: Optional[float] = None
    exp_pts_per_star: Optional[float] = None
    availability: Optional[str] = None
