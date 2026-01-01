from typing import Union
from dataclasses import dataclass


@dataclass
class PlayerStats:
    tries: int = 0
    try_assists: int = 0
    conversions: int = 0
    penalties_kicked: int = 0
    drop_goals: int = 0
    defenders_beaten: int = 0
    metres_carried: int = 0
    offloads: int = 0
    fifty_22_kicks: int = 0
    scrums_won: int = 0
    tackles_made: int = 0
    turnovers_won: int = 0
    lineout_steals: int = 0
    player_of_match: bool = False
    penalties_conceded: int = 0
    yellow_cards: int = 0
    red_cards: int = 0
    is_forward: bool = False


FORWARD_POSITIONS = ["prop", "hooker", "second_row", "back_row"]


def is_forward(fantasy_position: str) -> bool:
    """Check if a position is a forward position."""
    return fantasy_position.lower() in FORWARD_POSITIONS


def calculate_fantasy_points(stats: Union[PlayerStats, dict]) -> float:
    """Calculate fantasy points from player stats according to the scoring system."""
    if isinstance(stats, dict):
        stats = PlayerStats(**stats)

    points = 0.0

    # Tries (forward vs back)
    if stats.is_forward:
        points += stats.tries * 15
    else:
        points += stats.tries * 10

    # Other attacking
    points += stats.try_assists * 4
    points += stats.conversions * 2
    points += stats.penalties_kicked * 3
    points += stats.drop_goals * 5
    points += stats.defenders_beaten * 2
    points += stats.metres_carried // 10  # 1 per 10m
    points += stats.offloads * 2
    points += stats.fifty_22_kicks * 7

    # Scrums (forwards only)
    if stats.is_forward:
        points += stats.scrums_won * 1

    # Defensive
    points += stats.tackles_made * 1
    points += stats.turnovers_won * 5
    points += stats.lineout_steals * 7

    # Awards
    if stats.player_of_match:
        points += 15

    # Discipline (negative)
    points -= stats.penalties_conceded * 1
    points -= stats.yellow_cards * 5
    points -= stats.red_cards * 8

    return float(points)
