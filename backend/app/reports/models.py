from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any, TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.tournaments.models import Tournament
    from app.users.models import User


class WeeklyReportStatus(StrEnum):
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"


class WeeklyReport(TimestampMixin, Base):
    __tablename__ = "weekly_reports"
    __table_args__ = (
        UniqueConstraint("tournament_id", name="uq_weekly_report_tournament"),
        CheckConstraint("status in ('DRAFT', 'PUBLISHED')", name="ck_weekly_report_status"),
        Index("ix_weekly_reports_status_published", "status", "published_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    tournament_id: Mapped[UUID] = mapped_column(ForeignKey("tournaments.id", ondelete="RESTRICT"), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default=WeeklyReportStatus.DRAFT.value)
    snapshot_content: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    generated_by_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    tournament: Mapped[Tournament] = relationship()
    generated_by: Mapped[User] = relationship()
