from typing import List, Optional
from dataclasses import dataclass
from pulp import LpProblem, LpMaximize, LpVariable, lpSum, LpStatus

from app.schemas.player import PlayerSummary, Position, Country
from app.schemas.team import OptimisedTeam, StartingXV


@dataclass
class OptimiserPlayer:
    id: int
    name: str
    country: str
    fantasy_position: str
    price: float
    predicted_points: float
    is_available: bool = True
    is_starting: Optional[bool] = None


POSITION_LIMITS = {
    Position.PROP: 2,
    Position.HOOKER: 1,
    Position.SECOND_ROW: 2,
    Position.BACK_ROW: 3,
    Position.SCRUM_HALF: 1,
    Position.OUT_HALF: 1,
    Position.CENTRE: 2,
    Position.BACK_3: 3,
}


def optimise_team(
    players: List[OptimiserPlayer],
    budget: float = 230.0,
    max_per_country: int = 4,
    locked_players: List[int] = None,
    excluded_players: List[int] = None,
    include_bench: bool = True,
) -> OptimisedTeam:
    """
    Optimise team selection using linear programming.
    """
    if locked_players is None:
        locked_players = []
    if excluded_players is None:
        excluded_players = []

    # Filter available players
    available_players = [
        p for p in players
        if p.is_available and p.id not in excluded_players
    ]

    if not available_players:
        return OptimisedTeam(
            starting_xv=StartingXV(),
            bench=[],
            captain=None,
            super_sub=None,
            total_cost=0,
            total_predicted_points=0,
            remaining_budget=budget,
            empty_slots=list(Position),
        )

    prob = LpProblem("FantasyRugby", LpMaximize)

    # Decision variables
    x = {p.id: LpVariable(f"start_{p.id}", cat="Binary") for p in available_players}
    b = {p.id: LpVariable(f"bench_{p.id}", cat="Binary") for p in available_players}
    c = {p.id: LpVariable(f"captain_{p.id}", cat="Binary") for p in available_players}
    s = {p.id: LpVariable(f"supersub_{p.id}", cat="Binary") for p in available_players}

    # Objective: Maximize total expected points
    prob += lpSum([
        p.predicted_points * x[p.id] +
        p.predicted_points * 0.5 * b[p.id] +
        p.predicted_points * c[p.id] +  # Captain bonus (+1x, so 2x total)
        p.predicted_points * 2.5 * s[p.id]  # Super sub bonus
        for p in available_players
    ])

    # Budget constraint
    prob += lpSum([
        p.price * (x[p.id] + b[p.id])
        for p in available_players
    ]) <= budget

    # Position limits for starting XV
    for position, limit in POSITION_LIMITS.items():
        position_players = [p for p in available_players if p.fantasy_position == position.value]
        if position_players:
            prob += lpSum([x[p.id] for p in position_players]) <= limit

    # Bench limit
    if include_bench:
        prob += lpSum([b[p.id] for p in available_players]) <= 3
    else:
        for p in available_players:
            prob += b[p.id] == 0

    # Country limit
    for country in Country:
        country_players = [p for p in available_players if p.country == country.value]
        if country_players:
            prob += lpSum([x[p.id] + b[p.id] for p in country_players]) <= max_per_country

    # A player can only be in one slot
    for p in available_players:
        prob += x[p.id] + b[p.id] <= 1

    # Exactly one captain (from selected players)
    prob += lpSum([c[p.id] for p in available_players]) == 1
    for p in available_players:
        prob += c[p.id] <= x[p.id] + b[p.id]

    # Exactly one super sub (from bench only)
    if include_bench:
        prob += lpSum([s[p.id] for p in available_players]) == 1
        for p in available_players:
            prob += s[p.id] <= b[p.id]
    else:
        for p in available_players:
            prob += s[p.id] == 0

    # Locked players must be selected
    for player_id in locked_players:
        if player_id in x:
            prob += x[player_id] + b[player_id] >= 1

    # Solve
    prob.solve()

    if LpStatus[prob.status] != "Optimal":
        # Return empty team if no solution found
        return OptimisedTeam(
            starting_xv=StartingXV(),
            bench=[],
            captain=None,
            super_sub=None,
            total_cost=0,
            total_predicted_points=0,
            remaining_budget=budget,
            empty_slots=list(Position),
        )

    # Extract solution
    starting_players = []
    bench_players = []
    captain_player = None
    super_sub_player = None

    for p in available_players:
        player_summary = PlayerSummary(
            id=p.id,
            name=p.name,
            country=Country(p.country),
            fantasy_position=Position(p.fantasy_position),
            price=p.price,
            predicted_points=p.predicted_points,
            is_available=p.is_available,
            is_starting=p.is_starting,
        )

        if x[p.id].varValue == 1:
            starting_players.append(player_summary)
        if b[p.id].varValue == 1:
            bench_players.append(player_summary)
        if c[p.id].varValue == 1:
            captain_player = player_summary
        if s[p.id].varValue == 1:
            super_sub_player = player_summary

    # Organize starting XV by position
    starting_xv = StartingXV(
        props=[p for p in starting_players if p.fantasy_position == Position.PROP],
        hooker=next((p for p in starting_players if p.fantasy_position == Position.HOOKER), None),
        second_row=[p for p in starting_players if p.fantasy_position == Position.SECOND_ROW],
        back_row=[p for p in starting_players if p.fantasy_position == Position.BACK_ROW],
        scrum_half=next((p for p in starting_players if p.fantasy_position == Position.SCRUM_HALF), None),
        out_half=next((p for p in starting_players if p.fantasy_position == Position.OUT_HALF), None),
        centres=[p for p in starting_players if p.fantasy_position == Position.CENTRE],
        back_3=[p for p in starting_players if p.fantasy_position == Position.BACK_3],
    )

    # Calculate totals
    total_cost = sum(p.price or 0 for p in starting_players + bench_players)

    # Calculate total predicted points including bonuses
    base_points = sum(p.predicted_points or 0 for p in starting_players)
    bench_points = sum((p.predicted_points or 0) * 0.5 for p in bench_players)
    captain_bonus = captain_player.predicted_points if captain_player else 0
    super_sub_bonus = (super_sub_player.predicted_points or 0) * 2.5 if super_sub_player else 0
    total_predicted_points = base_points + bench_points + captain_bonus + super_sub_bonus

    # Find empty slots
    empty_slots = []
    if len(starting_xv.props) < 2:
        empty_slots.append(Position.PROP)
    if starting_xv.hooker is None:
        empty_slots.append(Position.HOOKER)
    if len(starting_xv.second_row) < 2:
        empty_slots.append(Position.SECOND_ROW)
    if len(starting_xv.back_row) < 3:
        empty_slots.append(Position.BACK_ROW)
    if starting_xv.scrum_half is None:
        empty_slots.append(Position.SCRUM_HALF)
    if starting_xv.out_half is None:
        empty_slots.append(Position.OUT_HALF)
    if len(starting_xv.centres) < 2:
        empty_slots.append(Position.CENTRE)
    if len(starting_xv.back_3) < 3:
        empty_slots.append(Position.BACK_3)

    return OptimisedTeam(
        starting_xv=starting_xv,
        bench=bench_players,
        captain=captain_player,
        super_sub=super_sub_player,
        total_cost=total_cost,
        total_predicted_points=total_predicted_points,
        remaining_budget=budget - total_cost,
        empty_slots=empty_slots,
    )
