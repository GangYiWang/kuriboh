from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.matches.models import Match
    from app.registrations.models import TournamentParticipant
    from app.tournaments.models import Tournament
    from app.users.models import User


class SwissRoundStatus(StrEnum):
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"
    COMPLETED = "COMPLETED"


class SwissRound(TimestampMixin, Base):
    __tablename__ = "swiss_rounds"
    __table_args__ = (
        UniqueConstraint("tournament_id", "round_no", name="uq_swiss_round_tournament_number"),
        CheckConstraint("round_no >= 1", name="ck_swiss_round_number"),
        CheckConstraint("status in ('DRAFT', 'PUBLISHED', 'COMPLETED')", name="ck_swiss_round_status"),
        Index("ix_swiss_rounds_tournament_status", "tournament_id", "status"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    tournament_id: Mapped[UUID] = mapped_column(ForeignKey("tournaments.id", ondelete="CASCADE"), nullable=False)
    round_no: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default=SwissRoundStatus.DRAFT.value)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    tournament: Mapped[Tournament] = relationship(back_populates="swiss_round_items")
    matches: Mapped[list[Match]] = relationship(back_populates="swiss_round", cascade="all, delete-orphan")
    rankings: Mapped[list[RankingSnapshot]] = relationship(back_populates="swiss_round", cascade="all, delete-orphan")


class RankingSnapshot(TimestampMixin, Base):
    __tablename__ = "ranking_snapshots"
    __table_args__ = (
        UniqueConstraint("swiss_round_id", "participant_id", name="uq_ranking_round_participant"),
        UniqueConstraint("swiss_round_id", "rank", name="uq_ranking_round_rank"),
        CheckConstraint("rank >= 1", name="ck_ranking_rank"),
        CheckConstraint("wins >= 0 and losses >= 0", name="ck_ranking_record"),
        CheckConstraint("omw >= 0 and omw <= 1", name="ck_ranking_omw"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    tournament_id: Mapped[UUID] = mapped_column(ForeignKey("tournaments.id", ondelete="CASCADE"), nullable=False)
    swiss_round_id: Mapped[UUID] = mapped_column(ForeignKey("swiss_rounds.id", ondelete="CASCADE"), nullable=False)
    participant_id: Mapped[UUID] = mapped_column(
        ForeignKey("tournament_participants.id", ondelete="CASCADE"), nullable=False
    )
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    wins: Mapped[int] = mapped_column(Integer, nullable=False)
    losses: Mapped[int] = mapped_column(Integer, nullable=False)
    omw: Mapped[float] = mapped_column(Numeric(8, 6), nullable=False)
    loss_round_score: Mapped[int] = mapped_column(Integer, nullable=False)

    swiss_round: Mapped[SwissRound] = relationship(back_populates="rankings")
    participant: Mapped[TournamentParticipant] = relationship(back_populates="ranking_snapshots")


class Withdrawal(TimestampMixin, Base):
    __tablename__ = "withdrawals"
    __table_args__ = (
        UniqueConstraint("participant_id", name="uq_withdrawal_participant"),
        CheckConstraint("after_round_no >= 0", name="ck_withdrawal_after_round"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    tournament_id: Mapped[UUID] = mapped_column(ForeignKey("tournaments.id", ondelete="CASCADE"), nullable=False)
    participant_id: Mapped[UUID] = mapped_column(
        ForeignKey("tournament_participants.id", ondelete="RESTRICT"), nullable=False
    )
    after_round_no: Mapped[int] = mapped_column(Integer, nullable=False)
    operator_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)

    participant: Mapped[TournamentParticipant] = relationship(back_populates="withdrawal")
    operator: Mapped[User] = relationship()
