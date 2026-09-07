"""Add tournament account inventory and claim records.

Revision ID: 20260907_0013
Revises: 20260905_0012
Create Date: 2026-09-07
"""

from typing import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260907_0013"
down_revision: str | None = "20260905_0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "account_import_batches",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tournament_id", sa.Uuid(), nullable=False),
        sa.Column("account_type", sa.String(length=16), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("imported_count", sa.Integer(), nullable=False),
        sa.Column("imported_by_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("account_type in ('KONAMI', 'STEAM')", name="ck_account_import_batches_type"),
        sa.CheckConstraint("imported_count > 0", name="ck_account_import_batches_count"),
        sa.ForeignKeyConstraint(["imported_by_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["tournament_id"], ["tournaments.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_account_import_batches_tournament_created",
        "account_import_batches",
        ["tournament_id", "created_at"],
        unique=False,
    )

    op.create_table(
        "tournament_accounts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tournament_id", sa.Uuid(), nullable=False),
        sa.Column("import_batch_id", sa.Uuid(), nullable=False),
        sa.Column("account_type", sa.String(length=16), nullable=False),
        sa.Column("account_digest", sa.String(length=64), nullable=False),
        sa.Column("account_ciphertext", sa.Text(), nullable=False),
        sa.Column("password_ciphertext", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("claimed_registration_id", sa.Uuid(), nullable=True),
        sa.Column("claimed_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("account_type in ('KONAMI', 'STEAM')", name="ck_tournament_accounts_type"),
        sa.CheckConstraint(
            "status in ('AVAILABLE', 'CLAIMED', 'INVALID')",
            name="ck_tournament_accounts_status",
        ),
        sa.ForeignKeyConstraint(["claimed_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["claimed_registration_id"], ["registrations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["import_batch_id"], ["account_import_batches.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tournament_id"], ["tournaments.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tournament_id", "account_type", "account_digest", name="uq_tournament_accounts_identifier"
        ),
        sa.UniqueConstraint(
            "claimed_registration_id", "account_type", name="uq_tournament_accounts_registration_type"
        ),
    )
    op.create_index(
        "ix_tournament_accounts_inventory",
        "tournament_accounts",
        ["tournament_id", "account_type", "status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_tournament_accounts_inventory", table_name="tournament_accounts")
    op.drop_table("tournament_accounts")
    op.drop_index("ix_account_import_batches_tournament_created", table_name="account_import_batches")
    op.drop_table("account_import_batches")
