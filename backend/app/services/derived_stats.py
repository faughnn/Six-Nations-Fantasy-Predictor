"""
Service to compute derived/aggregated stats for player projections.
"""
from dataclasses import dataclass
from typing import List, Optional, Union

from app.models.stats import SixNationsStats, ClubStats
from app.services.scoring import PlayerStats, calculate_fantasy_points, is_forward


@dataclass
class DerivedPlayerStats:
    avg_fantasy_points: Optional[float] = None
    predicted_points: Optional[float] = None
    avg_tries: Optional[float] = None
    avg_tackles: Optional[float] = None
    avg_metres: Optional[float] = None
    avg_turnovers: Optional[float] = None
    avg_defenders_beaten: Optional[float] = None
    avg_offloads: Optional[float] = None
    expected_minutes: Optional[float] = None
    start_rate: Optional[float] = None
    points_per_minute: Optional[float] = None
    total_games: int = 0


def compute_fantasy_points_for_club_stat(club_stat: ClubStats, forward: bool) -> float:
    """
    Calculate fantasy points for a club stat record.
    Club stats don't track fifty_22_kicks, kicks_retained, or player_of_match,
    so those default to 0/False.
    """
    stats = PlayerStats(
        tries=club_stat.tries,
        try_assists=club_stat.try_assists,
        conversions=club_stat.conversions,
        penalties_kicked=club_stat.penalties_kicked,
        drop_goals=club_stat.drop_goals,
        defenders_beaten=club_stat.defenders_beaten,
        metres_carried=club_stat.metres_carried,
        offloads=club_stat.offloads,
        fifty_22_kicks=0,
        scrums_won=club_stat.scrums_won,
        tackles_made=club_stat.tackles_made,
        turnovers_won=club_stat.turnovers_won,
        lineout_steals=club_stat.lineout_steals,
        kicks_retained=0,
        player_of_match=False,
        penalties_conceded=club_stat.penalties_conceded,
        yellow_cards=club_stat.yellow_cards,
        red_cards=club_stat.red_cards,
        is_forward=forward,
    )
    return calculate_fantasy_points(stats)


def compute_derived_stats(
    sn_stats: List[SixNationsStats],
    club_stats: List[ClubStats],
    fantasy_position: str,
) -> DerivedPlayerStats:
    """
    Compute derived/aggregated stats across all available data (club + international).
    """
    forward = is_forward(fantasy_position)
    all_stats: List[Union[SixNationsStats, ClubStats]] = list(sn_stats) + list(club_stats)
    total_games = len(all_stats)

    if total_games == 0:
        return DerivedPlayerStats()

    # Collect fantasy points from all games
    fantasy_points_list: List[float] = []
    for s in sn_stats:
        if s.fantasy_points is not None:
            fantasy_points_list.append(float(s.fantasy_points))
    for s in club_stats:
        if s.fantasy_points is not None:
            fantasy_points_list.append(float(s.fantasy_points))
        else:
            # Compute on the fly if not stored
            fantasy_points_list.append(compute_fantasy_points_for_club_stat(s, forward))

    avg_fp = sum(fantasy_points_list) / len(fantasy_points_list) if fantasy_points_list else None

    # Per-stat averages
    total_tries = sum(s.tries for s in all_stats)
    total_tackles = sum(s.tackles_made for s in all_stats)
    total_metres = sum(s.metres_carried for s in all_stats)
    total_turnovers = sum(s.turnovers_won for s in all_stats)
    total_db = sum(s.defenders_beaten for s in all_stats)
    total_offloads = sum(s.offloads for s in all_stats)

    # Minutes and start rate
    minutes_list = [s.minutes_played for s in all_stats if s.minutes_played is not None]
    avg_minutes = sum(minutes_list) / len(minutes_list) if minutes_list else None

    started_count = sum(1 for s in all_stats if s.started)
    start_rate = (started_count / total_games) * 100 if total_games else None

    # Points per minute
    ppm = None
    if avg_fp is not None and avg_minutes and avg_minutes > 0:
        ppm = avg_fp / avg_minutes

    return DerivedPlayerStats(
        avg_fantasy_points=round(avg_fp, 2) if avg_fp is not None else None,
        predicted_points=round(avg_fp, 2) if avg_fp is not None else None,
        avg_tries=round(total_tries / total_games, 3),
        avg_tackles=round(total_tackles / total_games, 2),
        avg_metres=round(total_metres / total_games, 2),
        avg_turnovers=round(total_turnovers / total_games, 3),
        avg_defenders_beaten=round(total_db / total_games, 2),
        avg_offloads=round(total_offloads / total_games, 3),
        expected_minutes=round(avg_minutes, 1) if avg_minutes is not None else None,
        start_rate=round(start_rate, 1) if start_rate is not None else None,
        points_per_minute=round(ppm, 3) if ppm is not None else None,
        total_games=total_games,
    )
