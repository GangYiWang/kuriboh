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
    from app.matches.models import MatchSubmission
    from app.swiss.models import RankingSnapshot, Withdrawal
    from app.tournaments.models import Tournament
    from app.users.models import User


class RegistrationStatus(StrEnum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    CANCELED = "CANCELED"


class ParticipantStatus(StrEnum):
    ACTIVE = "ACTIVE"
    WITHDRAWN = "WITHDRAWN"


class Registration(TimestampMixin, Base):
    __tablename__ = "registrations"
    __table_args__ = (
        UniqueConstraint("tournament_id", "user_id", name="uq_registration_tournament_user"),
        CheckConstraint(
            "status in ('PENDING', 'APPROVED', 'REJECTED', 'CANCELED')",
            name="ck_registrations_status",
        ),
        Index("ix_registrations_tournament_status", "tournament_id", "status"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    tournament_id: Mapped[UUID] = mapped_column(ForeignKey("tournaments.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default=RegistrationStatus.PENDING.value)
    reviewed_by_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    tournament: Mapped[Tournament] = relationship(back_populates="registrations")
    user: Mapped[User] = relationship(back_populates="registrations", foreign_keys=[user_id])
    reviewed_by: Mapped[User | None] = relationship(foreign_keys=[reviewed_by_id])
    participant: Mapped[TournamentParticipant | None] = relationship(back_populates="registration")


class TournamentParticipant(TimestampMixin, Base):
    __tablename__ = "tournament_participants"
    __table_args__ = (
        UniqueConstraint("tournament_id", "user_id", name="uq_participant_tournament_user"),
        UniqueConstraint("registration_id", name="uq_participant_registration"),
        CheckConstraint("status in ('ACTIVE', 'WITHDRAWN')", name="ck_participants_status"),
        CheckConstraint("bye_count >= 0", name="ck_participants_bye_count"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    tournament_id: Mapped[UUID] = mapped_column(ForeignKey("tournaments.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    registration_id: Mapped[UUID] = mapped_column(ForeignKey("registrations.id", ondelete="RESTRICT"), nullable=False)
    nickname_snapshot: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default=ParticipantStatus.ACTIVE.value)
    bye_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    tournament: Mapped[Tournament] = relationship(back_populates="participants")
    user: Mapped[User] = relationship(back_populates="tournament_participations")
    registration: Mapped[Registration] = relationship(back_populates="participant")
    match_submissions: Mapped[list[MatchSubmission]] = relationship(back_populates="participant")
    ranking_snapshots: Mapped[list[RankingSnapshot]] = relationship(back_populates="participant")
    withdrawal: Mapped[Withdrawal | None] = relationship(back_populates="participant")
