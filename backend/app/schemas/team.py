from typing import Optional, List
from pydantic import BaseModel
from app.schemas.player import PlayerSummary, Position


class OptimiseRequest(BaseModel):
    round: int
    budget: float = 230.0
    max_per_country: int = 4
    locked_players: List[int] = []
    excluded_players: List[int] = []
    min_players: int = 0
    include_bench: bool = True


class TeamSlot(BaseModel):
    position: Position
    player: Optional[PlayerSummary] = None


class StartingXV(BaseModel):
    props: List[PlayerSummary] = []
    hooker: Optional[PlayerSummary] = None
    second_row: List[PlayerSummary] = []
    back_row: List[PlayerSummary] = []
    scrum_half: Optional[PlayerSummary] = None
    out_half: Optional[PlayerSummary] = None
    centres: List[PlayerSummary] = []
    back_3: List[PlayerSummary] = []


class OptimisedTeam(BaseModel):
    starting_xv: StartingXV
    bench: List[PlayerSummary] = []
    captain: Optional[PlayerSummary] = None
    super_sub: Optional[PlayerSummary] = None
    total_cost: float
    total_predicted_points: float
    remaining_budget: float
    empty_slots: List[Position] = []
