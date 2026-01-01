from datetime import datetime, date
from typing import Optional, List
from sqlalchemy import String, Boolean, DateTime, Date, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Player(Base):
    __tablename__ = "players"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    country: Mapped[str] = mapped_column(String(50), nullable=False)
    fantasy_position: Mapped[str] = mapped_column(String(50), nullable=False)
    is_kicker: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    clubs: Mapped[List["PlayerClub"]] = relationship("PlayerClub", back_populates="player")
    six_nations_stats: Mapped[List["SixNationsStats"]] = relationship("SixNationsStats", back_populates="player")
    club_stats: Mapped[List["ClubStats"]] = relationship("ClubStats", back_populates="player")
    prices: Mapped[List["FantasyPrice"]] = relationship("FantasyPrice", back_populates="player")
    odds: Mapped[List["Odds"]] = relationship("Odds", back_populates="player")
    predictions: Mapped[List["Prediction"]] = relationship("Prediction", back_populates="player")
    team_selections: Mapped[List["TeamSelection"]] = relationship("TeamSelection", back_populates="player")


class PlayerClub(Base):
    __tablename__ = "player_clubs"

    id: Mapped[int] = mapped_column(primary_key=True)
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id"), nullable=False)
    club: Mapped[str] = mapped_column(String(255), nullable=False)
    league: Mapped[str] = mapped_column(String(50), nullable=False)
    season: Mapped[str] = mapped_column(String(10), nullable=False)
    start_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    player: Mapped["Player"] = relationship("Player", back_populates="clubs")


# Forward references for type hints
from app.models.stats import SixNationsStats, ClubStats
from app.models.prediction import FantasyPrice, Prediction, TeamSelection
from app.models.odds import Odds
