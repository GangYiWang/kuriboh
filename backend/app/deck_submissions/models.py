from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.registrations.models import TournamentParticipant
    from app.tournaments.models import Tournament
    from app.users.models import User


class DeckSubmissionStatus(StrEnum):
    NOT_UPLOADED = "NOT_UPLOADED"
    PENDING_REVIEW = "PENDING_REVIEW"
    REUPLOAD_REQUIRED = "REUPLOAD_REQUIRED"
    APPROVED = "APPROVED"


class DeckSubmission(TimestampMixin, Base):
    __tablename__ = "deck_submissions"
    __table_args__ = (
        UniqueConstraint("tournament_id", "participant_id", name="uq_deck_submission_tournament_participant"),
        CheckConstraint("placement between 1 and 4", name="ck_deck_submission_placement"),
        CheckConstraint(
            "status in ('NOT_UPLOADED', 'PENDING_REVIEW', 'REUPLOAD_REQUIRED', 'APPROVED')",
            name="ck_deck_submission_status",
        ),
        Index("ix_deck_submissions_tournament_status", "tournament_id", "status"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    tournament_id: Mapped[UUID] = mapped_column(ForeignKey("tournaments.id", ondelete="CASCADE"), nullable=False)
    participant_id: Mapped[UUID] = mapped_column(
        ForeignKey("tournament_participants.id", ondelete="RESTRICT"), nullable=False
    )
    placement: Mapped[int] = mapped_column(Integer, nullable=False)
    image_path: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default=DeckSubmissionStatus.NOT_UPLOADED.value)
    review_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_by_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    tournament: Mapped[Tournament] = relationship()
    participant: Mapped[TournamentParticipant] = relationship()
    reviewed_by: Mapped[User | None] = relationship()
