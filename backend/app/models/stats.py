from datetime import datetime, date, timezone
from typing import Optional
from decimal import Decimal
from sqlalchemy import String, Boolean, DateTime, Date, Integer, ForeignKey, Numeric, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class SixNationsStats(Base):
    __tablename__ = "six_nations_stats"

    id: Mapped[int] = mapped_column(primary_key=True)
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id"), nullable=False)
    season: Mapped[int] = mapped_column(Integer, nullable=False)
    round: Mapped[int] = mapped_column(Integer, nullable=False)
    match_date: Mapped[date] = mapped_column(Date, nullable=False)
    opponent: Mapped[str] = mapped_column(String(50), nullable=False)
    home_away: Mapped[str] = mapped_column(String(4), nullable=False)
    started: Mapped[bool] = mapped_column(Boolean, nullable=False)
    minutes_played: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    actual_position: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Attacking
    tries: Mapped[int] = mapped_column(Integer, default=0)
    try_assists: Mapped[int] = mapped_column(Integer, default=0)
    conversions: Mapped[int] = mapped_column(Integer, default=0)
    penalties_kicked: Mapped[int] = mapped_column(Integer, default=0)
    drop_goals: Mapped[int] = mapped_column(Integer, default=0)
    defenders_beaten: Mapped[int] = mapped_column(Integer, default=0)
    metres_carried: Mapped[int] = mapped_column(Integer, default=0)
    clean_breaks: Mapped[int] = mapped_column(Integer, default=0)
    offloads: Mapped[int] = mapped_column(Integer, default=0)
    fifty_22_kicks: Mapped[int] = mapped_column(Integer, default=0)

    # Defensive
    tackles_made: Mapped[int] = mapped_column(Integer, default=0)
    tackles_missed: Mapped[int] = mapped_column(Integer, default=0)
    turnovers_won: Mapped[int] = mapped_column(Integer, default=0)
    lineout_steals: Mapped[int] = mapped_column(Integer, default=0)

    # Scrums
    scrums_won: Mapped[int] = mapped_column(Integer, default=0)

    # Discipline
    penalties_conceded: Mapped[int] = mapped_column(Integer, default=0)
    yellow_cards: Mapped[int] = mapped_column(Integer, default=0)
    red_cards: Mapped[int] = mapped_column(Integer, default=0)

    # Awards
    player_of_match: Mapped[bool] = mapped_column(Boolean, default=False)

    # Calculated
    fantasy_points: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 2), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    player: Mapped["Player"] = relationship("Player", back_populates="six_nations_stats")


class ClubStats(Base):
    __tablename__ = "club_stats"

    id: Mapped[int] = mapped_column(primary_key=True)
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id"), nullable=False)
    league: Mapped[str] = mapped_column(String(50), nullable=False)
    season: Mapped[str] = mapped_column(String(10), nullable=False)
    match_date: Mapped[date] = mapped_column(Date, nullable=False)
    opponent: Mapped[str] = mapped_column(String(255), nullable=False)
    home_away: Mapped[str] = mapped_column(String(4), nullable=False)
    started: Mapped[bool] = mapped_column(Boolean, nullable=False)
    minutes_played: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Attacking
    tries: Mapped[int] = mapped_column(Integer, default=0)
    try_assists: Mapped[int] = mapped_column(Integer, default=0)
    conversions: Mapped[int] = mapped_column(Integer, default=0)
    penalties_kicked: Mapped[int] = mapped_column(Integer, default=0)
    drop_goals: Mapped[int] = mapped_column(Integer, default=0)
    defenders_beaten: Mapped[int] = mapped_column(Integer, default=0)
    metres_carried: Mapped[int] = mapped_column(Integer, default=0)
    clean_breaks: Mapped[int] = mapped_column(Integer, default=0)
    offloads: Mapped[int] = mapped_column(Integer, default=0)

    # Defensive
    tackles_made: Mapped[int] = mapped_column(Integer, default=0)
    tackles_missed: Mapped[int] = mapped_column(Integer, default=0)
    turnovers_won: Mapped[int] = mapped_column(Integer, default=0)
    lineout_steals: Mapped[int] = mapped_column(Integer, default=0)

    # Scrums
    scrums_won: Mapped[int] = mapped_column(Integer, default=0)

    # Discipline
    penalties_conceded: Mapped[int] = mapped_column(Integer, default=0)
    yellow_cards: Mapped[int] = mapped_column(Integer, default=0)
    red_cards: Mapped[int] = mapped_column(Integer, default=0)

    # Calculated
    fantasy_points: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 2), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    player: Mapped["Player"] = relationship("Player", back_populates="club_stats")


class FantasyRoundStats(Base):
    __tablename__ = "fantasy_round_stats"
    __table_args__ = (
        UniqueConstraint("player_id", "season", "round", name="uq_fantasy_round_stats_player_season_round"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id"), nullable=False)
    season: Mapped[int] = mapped_column(Integer, nullable=False)
    round: Mapped[int] = mapped_column(Integer, nullable=False)

    # Attacking
    tries: Mapped[int] = mapped_column(Integer, default=0)
    try_assists: Mapped[int] = mapped_column(Integer, default=0)
    conversions: Mapped[int] = mapped_column(Integer, default=0)
    penalties_kicked: Mapped[int] = mapped_column(Integer, default=0)
    drop_goals: Mapped[int] = mapped_column(Integer, default=0)
    defenders_beaten: Mapped[int] = mapped_column(Integer, default=0)
    metres_carried: Mapped[int] = mapped_column(Integer, default=0)
    clean_breaks: Mapped[int] = mapped_column(Integer, default=0)
    offloads: Mapped[int] = mapped_column(Integer, default=0)
    fifty_22_kicks: Mapped[int] = mapped_column(Integer, default=0)

    # Defensive
    tackles_made: Mapped[int] = mapped_column(Integer, default=0)
    lineout_steals: Mapped[int] = mapped_column(Integer, default=0)
    breakdown_steals: Mapped[int] = mapped_column(Integer, default=0)
    kick_returns: Mapped[int] = mapped_column(Integer, default=0)

    # Scrums
    scrums_won: Mapped[int] = mapped_column(Integer, default=0)

    # Discipline
    penalties_conceded: Mapped[int] = mapped_column(Integer, default=0)
    yellow_cards: Mapped[int] = mapped_column(Integer, default=0)
    red_cards: Mapped[int] = mapped_column(Integer, default=0)

    # Match
    minutes_played: Mapped[int] = mapped_column(Integer, default=0)
    player_of_match: Mapped[bool] = mapped_column(Boolean, default=False)

    # Calculated
    fantasy_points: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 2), nullable=True)

    scraped_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    player: Mapped["Player"] = relationship("Player", back_populates="fantasy_round_stats")


from app.models.player import Player
