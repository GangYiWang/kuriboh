from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.users.models import User


class MessageType(StrEnum):
    REGISTRATION_APPROVED = "REGISTRATION_APPROVED"
    REGISTRATION_REJECTED = "REGISTRATION_REJECTED"
    REGISTRATION_CANCELED = "REGISTRATION_CANCELED"
    TOURNAMENT_NOTICE = "TOURNAMENT_NOTICE"
    PLATFORM_NOTICE = "PLATFORM_NOTICE"
    REPORT_PUBLISHED = "REPORT_PUBLISHED"


class Message(TimestampMixin, Base):
    __tablename__ = "messages"
    __table_args__ = (
        CheckConstraint(
            "type in ('REGISTRATION_APPROVED', 'REGISTRATION_REJECTED', "
            "'REGISTRATION_CANCELED', 'TOURNAMENT_NOTICE', 'PLATFORM_NOTICE', 'REPORT_PUBLISHED')",
            name="ck_messages_type",
        ),
        Index("ix_messages_recipient_read_created", "recipient_id", "read_at", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    recipient_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    sender_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    type: Mapped[str] = mapped_column(String(40), nullable=False)
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    action_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    related_type: Mapped[str | None] = mapped_column(String(40), nullable=True)
    related_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    dedupe_key: Mapped[str | None] = mapped_column(String(160), unique=True, nullable=True)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    recipient: Mapped[User] = relationship(foreign_keys=[recipient_id])
    sender: Mapped[User | None] = relationship(foreign_keys=[sender_id])
