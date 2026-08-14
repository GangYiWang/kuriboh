from __future__ import annotations

from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

from sqlalchemy import ForeignKey, Index, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.tournaments.models import Tournament
    from app.users.models import User


class AuditLog(TimestampMixin, Base):
    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_logs_target", "target_type", "target_id"),
        Index("ix_audit_logs_tournament_created", "tournament_id", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    operator_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    tournament_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("tournaments.id", ondelete="CASCADE"), nullable=True
    )
    action_type: Mapped[str] = mapped_column(String(64), nullable=False)
    target_type: Mapped[str] = mapped_column(String(64), nullable=False)
    target_id: Mapped[str] = mapped_column(String(64), nullable=False)
    before_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    after_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    operator: Mapped[User] = relationship()
    tournament: Mapped[Tournament | None] = relationship()
