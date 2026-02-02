from typing import Optional, List
from datetime import date
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


class RoundScrapeStatusResponse(BaseModel):
    season: int
    round: int
    matches: List[MatchScrapeStatus]
    missing_markets: List[str]
