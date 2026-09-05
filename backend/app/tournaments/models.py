from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.content.models import BanlistVersion
    from app.registrations.models import Registration, TournamentParticipant
    from app.users.models import User
    from app.matches.models import Match
    from app.playoffs.models import PlayoffRound
    from app.swiss.models import SwissRound


class TournamentStatus(StrEnum):
    DRAFT = "DRAFT"
    REGISTRATION = "REGISTRATION"
    SWISS = "SWISS"
    ELIMINATION = "ELIMINATION"
    ENDED = "ENDED"
    CANCELED = "CANCELED"


class Tournament(TimestampMixin, Base):
    __tablename__ = "tournaments"
    __table_args__ = (
        CheckConstraint(
            "status in ('DRAFT', 'REGISTRATION', 'SWISS', 'ELIMINATION', 'ENDED', 'CANCELED')",
            name="ck_tournaments_status",
        ),
        CheckConstraint(
            "(status = 'CANCELED' and canceled_at is not null) or "
            "(status <> 'CANCELED' and canceled_at is null and cancellation_reason is null)",
            name="ck_tournaments_cancellation",
        ),
        CheckConstraint("max_players is null or max_players >= 2", name="ck_tournaments_max_players"),
        CheckConstraint("swiss_rounds is null or swiss_rounds >= 1", name="ck_tournaments_swiss_rounds"),
        CheckConstraint("playoff_size is null or playoff_size >= 2", name="ck_tournaments_playoff_size"),
        Index("ix_tournaments_status_start", "status", "planned_start_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    code: Mapped[str | None] = mapped_column(String(6), unique=True, index=True, nullable=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    planned_start_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    max_players: Mapped[int | None] = mapped_column(Integer, nullable=True)
    swiss_rounds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    playoff_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    banlist_version_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("banlist_versions.id", ondelete="RESTRICT"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(24), nullable=False, default=TournamentStatus.DRAFT.value)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    canceled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancellation_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    created_by_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)

    banlist_version: Mapped[BanlistVersion | None] = relationship(back_populates="tournaments")
    created_by: Mapped[User] = relationship(back_populates="created_tournaments")
    registrations: Mapped[list[Registration]] = relationship(back_populates="tournament")
    participants: Mapped[list[TournamentParticipant]] = relationship(back_populates="tournament")
    swiss_round_items: Mapped[list[SwissRound]] = relationship(back_populates="tournament")
    playoff_round_items: Mapped[list[PlayoffRound]] = relationship(back_populates="tournament")
    matches: Mapped[list[Match]] = relationship(back_populates="tournament")
