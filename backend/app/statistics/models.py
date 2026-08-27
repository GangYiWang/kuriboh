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
    from app.registrations.models import TournamentParticipant
    from app.tournaments.models import Tournament
    from app.users.models import User


class TournamentFinishLevel(StrEnum):
    PARTICIPATED = "PARTICIPATED"
    TOP_8 = "TOP_8"
    TOP_4 = "TOP_4"
    RUNNER_UP = "RUNNER_UP"
    CHAMPION = "CHAMPION"


class TournamentPlayerResult(TimestampMixin, Base):
    __tablename__ = "tournament_player_results"
    __table_args__ = (
        UniqueConstraint("tournament_id", "participant_id", name="uq_result_tournament_participant"),
        UniqueConstraint("tournament_id", "user_id", name="uq_result_tournament_user"),
        UniqueConstraint("tournament_id", "placement", name="uq_result_tournament_placement"),
        CheckConstraint(
            "participant_status in ('ACTIVE', 'WITHDRAWN')",
            name="ck_result_participant_status",
        ),
        CheckConstraint(
            "finish_level in ('PARTICIPATED', 'TOP_8', 'TOP_4', 'RUNNER_UP', 'CHAMPION')",
            name="ck_result_finish_level",
        ),
        CheckConstraint("placement is null or placement between 1 and 4", name="ck_result_placement"),
        CheckConstraint("swiss_rank is null or swiss_rank >= 1", name="ck_result_swiss_rank"),
        CheckConstraint("wins >= 0 and losses >= 0 and bye_count >= 0", name="ck_result_record"),
        CheckConstraint("points_awarded >= 0", name="ck_result_points"),
        CheckConstraint("points_rule_version >= 1", name="ck_result_points_rule_version"),
        Index("ix_results_user_settled", "user_id", "settled_at"),
        Index("ix_results_tournament_placement", "tournament_id", "placement"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    tournament_id: Mapped[UUID] = mapped_column(ForeignKey("tournaments.id", ondelete="CASCADE"), nullable=False)
    participant_id: Mapped[UUID] = mapped_column(
        ForeignKey("tournament_participants.id", ondelete="RESTRICT"), nullable=False
    )
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    participant_status: Mapped[str] = mapped_column(String(24), nullable=False)
    finish_level: Mapped[str] = mapped_column(String(24), nullable=False)
    placement: Mapped[int | None] = mapped_column(Integer, nullable=True)
    swiss_rank: Mapped[int | None] = mapped_column(Integer, nullable=True)
    wins: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    losses: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    bye_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    points_awarded: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    points_rule_version: Mapped[int] = mapped_column(Integer, nullable=False)
    settled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    tournament: Mapped[Tournament] = relationship()
    participant: Mapped[TournamentParticipant] = relationship()
    user: Mapped[User] = relationship()


class PlayerStatistics(TimestampMixin, Base):
    __tablename__ = "player_statistics"
    __table_args__ = (
        CheckConstraint(
            "tournament_count >= 0 and total_points >= 0 and champion_count >= 0 "
            "and runner_up_count >= 0 and top_4_count >= 0 and top_8_count >= 0 "
            "and total_wins >= 0 and total_losses >= 0 and total_byes >= 0",
            name="ck_player_statistics_nonnegative",
        ),
    )

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    tournament_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_points: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    champion_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    runner_up_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    top_4_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    top_8_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_wins: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_losses: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_byes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    user: Mapped[User] = relationship()
