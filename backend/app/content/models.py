from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.tournaments.models import Tournament
    from app.users.models import User


class BanlistVersion(TimestampMixin, Base):
    __tablename__ = "banlist_versions"
    __table_args__ = (
        UniqueConstraint("major_version", "minor_version", name="uq_banlist_version_number"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    major_version: Mapped[int] = mapped_column(Integer, nullable=False)
    minor_version: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    content_html: Mapped[str] = mapped_column(Text, nullable=False)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_by_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)

    created_by: Mapped[User] = relationship(back_populates="banlist_versions")
    tournaments: Mapped[list[Tournament]] = relationship(back_populates="banlist_version")

    @property
    def version(self) -> str:
        return f"V{self.major_version}.{self.minor_version}"


class Announcement(TimestampMixin, Base):
    __tablename__ = "announcements"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    content_html: Mapped[str] = mapped_column(Text, nullable=False)
    is_pinned: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    author_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)

    author: Mapped[User] = relationship(back_populates="announcements")
