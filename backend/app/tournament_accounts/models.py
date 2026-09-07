from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import TimestampMixin

if TYPE_CHECKING:
    from app.registrations.models import Registration
    from app.tournaments.models import Tournament
    from app.users.models import User


class AccountType(StrEnum):
    KONAMI = "KONAMI"
    STEAM = "STEAM"


class TournamentAccountStatus(StrEnum):
    AVAILABLE = "AVAILABLE"
    RESERVED = "RESERVED"
    CLAIMED = "CLAIMED"
    INVALID = "INVALID"


class AccountReplacementStatus(StrEnum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    COMPLETED = "COMPLETED"
    REJECTED = "REJECTED"


class AccountImportBatch(TimestampMixin, Base):
    __tablename__ = "account_import_batches"
    __table_args__ = (
        CheckConstraint("account_type in ('KONAMI', 'STEAM')", name="ck_account_import_batches_type"),
        CheckConstraint("imported_count > 0", name="ck_account_import_batches_count"),
        Index("ix_account_import_batches_tournament_created", "tournament_id", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    tournament_id: Mapped[UUID] = mapped_column(ForeignKey("tournaments.id", ondelete="CASCADE"), nullable=False)
    account_type: Mapped[str] = mapped_column(String(16), nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    imported_count: Mapped[int] = mapped_column(Integer, nullable=False)
    imported_by_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)

    tournament: Mapped[Tournament] = relationship()
    imported_by: Mapped[User] = relationship()
    accounts: Mapped[list[TournamentAccount]] = relationship(back_populates="import_batch")


class TournamentAccount(TimestampMixin, Base):
    __tablename__ = "tournament_accounts"
    __table_args__ = (
        CheckConstraint("account_type in ('KONAMI', 'STEAM')", name="ck_tournament_accounts_type"),
        CheckConstraint(
            "status in ('AVAILABLE', 'RESERVED', 'CLAIMED', 'INVALID')",
            name="ck_tournament_accounts_status",
        ),
        UniqueConstraint(
            "tournament_id",
            "account_type",
            "account_digest",
            name="uq_tournament_accounts_identifier",
        ),
        Index(
            "uq_tournament_accounts_active_registration_type",
            "claimed_registration_id",
            "account_type",
            unique=True,
            postgresql_where=text("status in ('RESERVED', 'CLAIMED')"),
            sqlite_where=text("status in ('RESERVED', 'CLAIMED')"),
        ),
        Index(
            "ix_tournament_accounts_inventory",
            "tournament_id",
            "account_type",
            "status",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    tournament_id: Mapped[UUID] = mapped_column(ForeignKey("tournaments.id", ondelete="CASCADE"), nullable=False)
    import_batch_id: Mapped[UUID] = mapped_column(
        ForeignKey("account_import_batches.id", ondelete="CASCADE"), nullable=False
    )
    account_type: Mapped[str] = mapped_column(String(16), nullable=False)
    account_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    account_ciphertext: Mapped[str] = mapped_column(Text, nullable=False)
    password_ciphertext: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default=TournamentAccountStatus.AVAILABLE.value
    )
    claimed_registration_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("registrations.id", ondelete="RESTRICT"), nullable=True
    )
    claimed_by_user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=True
    )
    claimed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    tournament: Mapped[Tournament] = relationship()
    import_batch: Mapped[AccountImportBatch] = relationship(back_populates="accounts")
    claimed_registration: Mapped[Registration | None] = relationship()
    claimed_by: Mapped[User | None] = relationship()


class AccountReplacementRequest(TimestampMixin, Base):
    __tablename__ = "account_replacement_requests"
    __table_args__ = (
        CheckConstraint("account_type in ('KONAMI', 'STEAM')", name="ck_account_replacement_requests_type"),
        CheckConstraint(
            "status in ('PENDING', 'APPROVED', 'COMPLETED', 'REJECTED')",
            name="ck_account_replacement_requests_status",
        ),
        Index(
            "uq_account_replacement_requests_open_registration_type",
            "registration_id",
            "account_type",
            unique=True,
            postgresql_where=text("status in ('PENDING', 'APPROVED')"),
            sqlite_where=text("status in ('PENDING', 'APPROVED')"),
        ),
        Index(
            "ix_account_replacement_requests_tournament_status_created",
            "tournament_id",
            "status",
            "created_at",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    tournament_id: Mapped[UUID] = mapped_column(ForeignKey("tournaments.id", ondelete="CASCADE"), nullable=False)
    registration_id: Mapped[UUID] = mapped_column(ForeignKey("registrations.id", ondelete="RESTRICT"), nullable=False)
    account_type: Mapped[str] = mapped_column(String(16), nullable=False)
    original_account_id: Mapped[UUID] = mapped_column(
        ForeignKey("tournament_accounts.id", ondelete="RESTRICT"), nullable=False
    )
    replacement_account_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("tournament_accounts.id", ondelete="RESTRICT"), nullable=True
    )
    reason: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default=AccountReplacementStatus.PENDING.value
    )
    reviewed_by_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=True
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    tournament: Mapped[Tournament] = relationship()
    registration: Mapped[Registration] = relationship()
    original_account: Mapped[TournamentAccount] = relationship(foreign_keys=[original_account_id])
    replacement_account: Mapped[TournamentAccount | None] = relationship(foreign_keys=[replacement_account_id])
    reviewed_by: Mapped[User | None] = relationship()
