from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, Index, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.auth.roles import Role
from app.db.base import Base
from app.db.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.content.models import Announcement, BanlistVersion
    from app.registrations.models import Registration, TournamentParticipant
    from app.tournaments.models import Tournament
    from app.deck_submissions.models import DeckSubmission


class User(TimestampMixin, Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(
            "role in ('PLAYER', 'TOURNAMENT_ADMIN')",
            name="ck_users_role",
        ),
        CheckConstraint(
            "phone_number is not null or qq_number is not null",
            name="ck_users_login_identifier",
        ),
        Index(
            "ux_users_login_identifier",
            text("COALESCE(phone_number, qq_number)"),
            unique=True,
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    phone_number: Mapped[str | None] = mapped_column(String(20), unique=True, index=True, nullable=True)
    qq_number: Mapped[str | None] = mapped_column(String(20), unique=True, index=True, nullable=True)
    nickname: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    qq_openid: Mapped[str | None] = mapped_column(String(128), unique=True, nullable=True)
    role: Mapped[str] = mapped_column(String(32), nullable=False, default=Role.PLAYER.value)

    banlist_versions: Mapped[list[BanlistVersion]] = relationship(back_populates="created_by")
    announcements: Mapped[list[Announcement]] = relationship(back_populates="author")
    created_tournaments: Mapped[list[Tournament]] = relationship(back_populates="created_by")
    registrations: Mapped[list[Registration]] = relationship(
        back_populates="user", foreign_keys="Registration.user_id"
    )
    tournament_participations: Mapped[list[TournamentParticipant]] = relationship(back_populates="user")
