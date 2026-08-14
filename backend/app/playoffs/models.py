from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.matches.models import Match
    from app.tournaments.models import Tournament


class PlayoffRoundStatus(StrEnum):
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"
    COMPLETED = "COMPLETED"


class PlayoffRound(TimestampMixin, Base):
    __tablename__ = "playoff_rounds"
    __table_args__ = (
        UniqueConstraint("tournament_id", "stage_no", name="uq_playoff_round_tournament_stage"),
        CheckConstraint("stage_no >= 1", name="ck_playoff_round_stage"),
        CheckConstraint("bracket_size >= 2", name="ck_playoff_round_bracket_size"),
        CheckConstraint("status in ('DRAFT', 'PUBLISHED', 'COMPLETED')", name="ck_playoff_round_status"),
        Index("ix_playoff_rounds_tournament_status", "tournament_id", "status"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    tournament_id: Mapped[UUID] = mapped_column(ForeignKey("tournaments.id", ondelete="CASCADE"), nullable=False)
    stage_no: Mapped[int] = mapped_column(Integer, nullable=False)
    bracket_size: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default=PlayoffRoundStatus.DRAFT.value)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    tournament: Mapped[Tournament] = relationship(back_populates="playoff_round_items")
    matches: Mapped[list[Match]] = relationship(back_populates="playoff_round", cascade="all, delete-orphan")
