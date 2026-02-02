from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, ConfigDict
from enum import Enum


class Country(str, Enum):
    IRELAND = "Ireland"
    ENGLAND = "England"
    FRANCE = "France"
    WALES = "Wales"
    SCOTLAND = "Scotland"
    ITALY = "Italy"


class Position(str, Enum):
    PROP = "prop"
    HOOKER = "hooker"
    SECOND_ROW = "second_row"
    BACK_ROW = "back_row"
    SCRUM_HALF = "scrum_half"
    OUT_HALF = "out_half"
    CENTRE = "centre"
    BACK_3 = "back_3"


class League(str, Enum):
    URC = "urc"
    PREMIERSHIP = "premiership"
    TOP_14 = "top_14"


class PlayerBase(BaseModel):
    name: str
    country: Country
    fantasy_position: Position
    is_kicker: bool = False


class PlayerCreate(PlayerBase):
    pass


class PlayerClubInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    club: str
    league: League
    season: str


class PlayerResponse(PlayerBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime


class PlayerSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    country: Country
    fantasy_position: Position
    club: Optional[str] = None
    league: Optional[League] = None
    price: Optional[float] = None
    is_available: bool = False
    is_starting: Optional[bool] = None
    predicted_points: Optional[float] = None
    points_per_star: Optional[float] = None
    value_score: Optional[float] = None
    recent_form: Optional[float] = None
    anytime_try_odds: Optional[float] = None


class StatsHistory(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    match_date: datetime
    opponent: str
    fantasy_points: Optional[float] = None
    tries: int = 0
    tackles_made: int = 0
    metres_carried: int = 0


class PlayerDetail(PlayerSummary):
    model_config = ConfigDict(from_attributes=True)

    is_kicker: bool
    six_nations_stats: List[StatsHistory] = []
    club_stats: List[StatsHistory] = []
    prediction_breakdown: Optional[dict] = None


class PlayerProjection(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    # Identity
    id: int
    name: str
    country: str
    fantasy_position: str

    # Cost / Value
    price: Optional[float] = None
    predicted_points: Optional[float] = None
    points_per_star: Optional[float] = None

    # Predicted Stats (historical averages)
    avg_tries: Optional[float] = None
    avg_tackles: Optional[float] = None
    avg_metres: Optional[float] = None
    avg_turnovers: Optional[float] = None
    avg_defenders_beaten: Optional[float] = None
    avg_offloads: Optional[float] = None

    # Efficiency
    expected_minutes: Optional[float] = None
    start_rate: Optional[float] = None
    points_per_minute: Optional[float] = None

    # Odds / Fixture
    anytime_try_odds: Optional[float] = None
    opponent: Optional[str] = None
    home_away: Optional[str] = None

    # Sample size
    total_games: int = 0


class PlayerValueAnalysis(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    # Identity
    id: Optional[int] = None
    name: str
    country: str
    fantasy_position: str
    is_forward: bool

    # Price & ownership
    price: Optional[float] = None
    ownership_pct: Optional[float] = None

    # Fixture context
    opponent: Optional[str] = None
    is_home: Optional[bool] = None
    is_starting: Optional[bool] = None

    # Try scorer odds & EV
    anytime_try_odds: Optional[float] = None
    implied_try_prob: Optional[float] = None
    try_points: int = 10
    expected_try_points: Optional[float] = None
    try_ev_per_star: Optional[float] = None

    # Historical averages (3 years Six Nations + club)
    avg_fantasy_points: Optional[float] = None
    avg_tries_per_game: Optional[float] = None
    avg_tackles_per_game: Optional[float] = None
    avg_metres_per_game: Optional[float] = None
    avg_defenders_beaten_per_game: Optional[float] = None
    avg_turnovers_per_game: Optional[float] = None
    avg_offloads_per_game: Optional[float] = None
    total_games: Optional[int] = None

    # Combined value scores
    predicted_points: Optional[float] = None
    overall_ev_per_star: Optional[float] = None
