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
