from __future__ import annotations

from enum import StrEnum
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.playoffs.models import PlayoffRound
    from app.registrations.models import TournamentParticipant
    from app.swiss.models import SwissRound
    from app.tournaments.models import Tournament


class MatchStage(StrEnum):
    SWISS = "SWISS"
    ELIMINATION = "ELIMINATION"


class MatchStatus(StrEnum):
    WAITING = "WAITING"
    CONFLICT = "CONFLICT"
    COMPLETED = "COMPLETED"


class ResultSource(StrEnum):
    PLAYERS = "PLAYERS"
    ADMIN = "ADMIN"
    BYE = "BYE"


class SubmittedResult(StrEnum):
    WIN = "WIN"
    LOSS = "LOSS"


class Match(TimestampMixin, Base):
    __tablename__ = "matches"
    __table_args__ = (
        UniqueConstraint("swiss_round_id", "table_no", name="uq_match_round_table"),
        UniqueConstraint("playoff_round_id", "table_no", name="uq_match_playoff_round_table"),
        CheckConstraint("stage in ('SWISS', 'ELIMINATION')", name="ck_matches_stage"),
        CheckConstraint("status in ('WAITING', 'CONFLICT', 'COMPLETED')", name="ck_matches_status"),
        CheckConstraint(
            "result_source is null or result_source in ('PLAYERS', 'ADMIN', 'BYE')",
            name="ck_matches_result_source",
        ),
        CheckConstraint("table_no >= 1 and round_no >= 1", name="ck_matches_numbers"),
        CheckConstraint("player_b_id is null or player_a_id <> player_b_id", name="ck_matches_distinct_players"),
        CheckConstraint("seed_a is null or seed_a >= 1", name="ck_matches_seed_a"),
        CheckConstraint("seed_b is null or seed_b >= 1", name="ck_matches_seed_b"),
        Index("ix_matches_tournament_round_status", "tournament_id", "round_no", "status"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    tournament_id: Mapped[UUID] = mapped_column(ForeignKey("tournaments.id", ondelete="CASCADE"), nullable=False)
    swiss_round_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("swiss_rounds.id", ondelete="CASCADE"), nullable=True
    )
    playoff_round_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("playoff_rounds.id", ondelete="CASCADE"), nullable=True
    )
    stage: Mapped[str] = mapped_column(String(24), nullable=False, default=MatchStage.SWISS.value)
    round_no: Mapped[int] = mapped_column(Integer, nullable=False)
    table_no: Mapped[int] = mapped_column(Integer, nullable=False)
    seed_a: Mapped[int | None] = mapped_column(Integer, nullable=True)
    seed_b: Mapped[int | None] = mapped_column(Integer, nullable=True)
    player_a_id: Mapped[UUID] = mapped_column(
        ForeignKey("tournament_participants.id", ondelete="RESTRICT"), nullable=False
    )
    player_b_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("tournament_participants.id", ondelete="RESTRICT"), nullable=True
    )
    winner_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("tournament_participants.id", ondelete="RESTRICT"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(24), nullable=False, default=MatchStatus.WAITING.value)
    result_source: Mapped[str | None] = mapped_column(String(24), nullable=True)
    result_locked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    tournament: Mapped[Tournament] = relationship(back_populates="matches")
    swiss_round: Mapped[SwissRound | None] = relationship(back_populates="matches")
    playoff_round: Mapped[PlayoffRound | None] = relationship(back_populates="matches")
    player_a: Mapped[TournamentParticipant] = relationship(foreign_keys=[player_a_id])
    player_b: Mapped[TournamentParticipant | None] = relationship(foreign_keys=[player_b_id])
    winner: Mapped[TournamentParticipant | None] = relationship(foreign_keys=[winner_id])
    submissions: Mapped[list[MatchSubmission]] = relationship(back_populates="match", cascade="all, delete-orphan")


class MatchSubmission(TimestampMixin, Base):
    __tablename__ = "match_submissions"
    __table_args__ = (
        UniqueConstraint("match_id", "participant_id", name="uq_submission_match_participant"),
        CheckConstraint("submitted_result in ('WIN', 'LOSS')", name="ck_submission_result"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    match_id: Mapped[UUID] = mapped_column(ForeignKey("matches.id", ondelete="CASCADE"), nullable=False)
    participant_id: Mapped[UUID] = mapped_column(
        ForeignKey("tournament_participants.id", ondelete="CASCADE"), nullable=False
    )
    submitted_result: Mapped[str] = mapped_column(String(16), nullable=False)

    match: Mapped[Match] = relationship(back_populates="submissions")
    participant: Mapped[TournamentParticipant] = relationship(back_populates="match_submissions")
