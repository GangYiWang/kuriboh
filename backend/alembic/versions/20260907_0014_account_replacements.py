"""Add tournament account replacement requests and reservations.

Revision ID: 20260907_0014
Revises: 20260907_0013
Create Date: 2026-09-07
"""

from typing import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260907_0014"
down_revision: str | None = "20260907_0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint(
        "uq_tournament_accounts_registration_type",
        "tournament_accounts",
        type_="unique",
    )
    op.drop_constraint("ck_tournament_accounts_status", "tournament_accounts", type_="check")
    op.create_check_constraint(
        "ck_tournament_accounts_status",
        "tournament_accounts",
        "status in ('AVAILABLE', 'RESERVED', 'CLAIMED', 'INVALID')",
    )
    op.create_index(
        "uq_tournament_accounts_active_registration_type",
        "tournament_accounts",
        ["claimed_registration_id", "account_type"],
        unique=True,
        postgresql_where=sa.text("status in ('RESERVED', 'CLAIMED')"),
    )
    op.create_table(
        "account_replacement_requests",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tournament_id", sa.Uuid(), nullable=False),
        sa.Column("registration_id", sa.Uuid(), nullable=False),
        sa.Column("account_type", sa.String(length=16), nullable=False),
        sa.Column("original_account_id", sa.Uuid(), nullable=False),
        sa.Column("replacement_account_id", sa.Uuid(), nullable=True),
        sa.Column("reason", sa.String(length=500), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("reviewed_by_id", sa.Uuid(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejection_reason", sa.String(length=500), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("account_type in ('KONAMI', 'STEAM')", name="ck_account_replacement_requests_type"),
        sa.CheckConstraint(
            "status in ('PENDING', 'APPROVED', 'COMPLETED', 'REJECTED')",
            name="ck_account_replacement_requests_status",
        ),
        sa.ForeignKeyConstraint(["original_account_id"], ["tournament_accounts.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["registration_id"], ["registrations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["replacement_account_id"], ["tournament_accounts.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["reviewed_by_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["tournament_id"], ["tournaments.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_account_replacement_requests_open_registration_type",
        "account_replacement_requests",
        ["registration_id", "account_type"],
        unique=True,
        postgresql_where=sa.text("status in ('PENDING', 'APPROVED')"),
    )
    op.create_index(
        "ix_account_replacement_requests_tournament_status_created",
        "account_replacement_requests",
        ["tournament_id", "status", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_account_replacement_requests_tournament_status_created",
        table_name="account_replacement_requests",
    )
    op.drop_index(
        "uq_account_replacement_requests_open_registration_type",
        table_name="account_replacement_requests",
    )
    op.drop_table("account_replacement_requests")
    op.drop_index(
        "uq_tournament_accounts_active_registration_type",
        table_name="tournament_accounts",
    )
    op.execute(
        "update tournament_accounts set status = 'AVAILABLE', claimed_registration_id = null, "
        "claimed_by_user_id = null, claimed_at = null where status = 'RESERVED'"
    )
    op.execute(
        "update tournament_accounts set claimed_registration_id = null where status = 'INVALID'"
    )
    op.drop_constraint("ck_tournament_accounts_status", "tournament_accounts", type_="check")
    op.create_check_constraint(
        "ck_tournament_accounts_status",
        "tournament_accounts",
        "status in ('AVAILABLE', 'CLAIMED', 'INVALID')",
    )
    op.create_unique_constraint(
        "uq_tournament_accounts_registration_type",
        "tournament_accounts",
        ["claimed_registration_id", "account_type"],
    )
