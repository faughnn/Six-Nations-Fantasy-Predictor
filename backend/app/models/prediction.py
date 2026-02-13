from datetime import datetime
from typing import Optional
from decimal import Decimal
from sqlalchemy import String, Boolean, DateTime, Integer, ForeignKey, Numeric, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class FantasyPrice(Base):
    __tablename__ = "fantasy_prices"

    id: Mapped[int] = mapped_column(primary_key=True)
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id"), nullable=False)
    season: Mapped[int] = mapped_column(Integer, nullable=False)
    round: Mapped[int] = mapped_column(Integer, nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(5, 1), nullable=False)
    ownership_pct: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2), nullable=True)
    availability: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (UniqueConstraint("player_id", "season", "round", name="uq_player_season_round"),)

    player: Mapped["Player"] = relationship("Player", back_populates="prices")


class TeamSelection(Base):
    __tablename__ = "team_selections"

    id: Mapped[int] = mapped_column(primary_key=True)
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id"), nullable=False)
    season: Mapped[int] = mapped_column(Integer, nullable=False)
    round: Mapped[int] = mapped_column(Integer, nullable=False)
    squad_position: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    is_starting: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    actual_position: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    __table_args__ = (UniqueConstraint("player_id", "season", "round", name="uq_selection_player_season_round"),)

    player: Mapped["Player"] = relationship("Player", back_populates="team_selections")


class Prediction(Base):
    __tablename__ = "predictions"

    id: Mapped[int] = mapped_column(primary_key=True)
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id"), nullable=False)
    season: Mapped[int] = mapped_column(Integer, nullable=False)
    round: Mapped[int] = mapped_column(Integer, nullable=False)
    predicted_points: Mapped[Decimal] = mapped_column(Numeric(6, 2), nullable=False)
    confidence_lower: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 2), nullable=True)
    confidence_upper: Mapped[Optional[Decimal]] = mapped_column(Numeric(6, 2), nullable=True)
    model_version: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    player: Mapped["Player"] = relationship("Player", back_populates="predictions")


from app.models.player import Player
