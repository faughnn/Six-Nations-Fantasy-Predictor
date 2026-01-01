from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class PredictionBase(BaseModel):
    player_id: int
    season: int
    round: int
    predicted_points: float


class PredictionCreate(PredictionBase):
    confidence_lower: Optional[float] = None
    confidence_upper: Optional[float] = None
    model_version: Optional[str] = None


class PredictionResponse(PredictionBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    confidence_lower: Optional[float] = None
    confidence_upper: Optional[float] = None
    model_version: Optional[str] = None
    created_at: datetime


class PredictionBreakdown(BaseModel):
    predicted_tries: float
    predicted_try_prob: float
    predicted_tackles: float
    predicted_metres: float
    predicted_turnovers: float
    predicted_conversions: float
    predicted_penalties: float


class PredictionDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    player_id: int
    player_name: str
    predicted_points: float
    confidence_interval: tuple[float, float]
    breakdown: PredictionBreakdown
    key_factors: List[str]
