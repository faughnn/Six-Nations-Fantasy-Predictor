from datetime import datetime, date
from typing import Optional
from decimal import Decimal
from sqlalchemy import String, DateTime, Date, Integer, ForeignKey, Numeric, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Odds(Base):
    __tablename__ = "odds"
    __table_args__ = (
        UniqueConstraint('player_id', 'season', 'round', name='uq_odds_player_season_round'),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id"), nullable=False)
    season: Mapped[int] = mapped_column(Integer, nullable=False)
    round: Mapped[int] = mapped_column(Integer, nullable=False)
    match_date: Mapped[date] = mapped_column(Date, nullable=False)

    # Try scorer odds (decimal format)
    anytime_try_scorer: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 2), nullable=True)
    first_try_scorer: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 2), nullable=True)
    two_plus_tries: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 2), nullable=True)

    # Player of match
    player_of_match: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 2), nullable=True)

    scraped_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    source: Mapped[str] = mapped_column(String(50), default="oddschecker")

    player: Mapped["Player"] = relationship("Player", back_populates="odds")


class MatchOdds(Base):
    __tablename__ = "match_odds"
    __table_args__ = (
        UniqueConstraint('season', 'round', 'home_team', 'away_team', name='uq_match_odds_season_round_teams'),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    season: Mapped[int] = mapped_column(Integer, nullable=False)
    round: Mapped[int] = mapped_column(Integer, nullable=False)
    match_date: Mapped[date] = mapped_column(Date, nullable=False)
    home_team: Mapped[str] = mapped_column(String(50), nullable=False)
    away_team: Mapped[str] = mapped_column(String(50), nullable=False)

    # Match result odds
    home_win: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 2), nullable=True)
    away_win: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 2), nullable=True)
    draw: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 2), nullable=True)

    # Totals
    over_under_line: Mapped[Optional[Decimal]] = mapped_column(Numeric(4, 1), nullable=True)
    over_odds: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 2), nullable=True)
    under_odds: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 2), nullable=True)

    # Handicap
    handicap_line: Mapped[Optional[Decimal]] = mapped_column(Numeric(4, 1), nullable=True)
    home_handicap_odds: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 2), nullable=True)
    away_handicap_odds: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 2), nullable=True)

    scraped_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


from app.models.player import Player
