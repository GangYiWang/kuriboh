"""Add tournament account carryover lineage.

Revision ID: 20260922_0015
Revises: 20260907_0014
Create Date: 2026-09-22
"""

from typing import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260922_0015"
down_revision: str | None = "20260907_0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "tournament_accounts",
        sa.Column("transferred_from_account_id", sa.Uuid(), nullable=True),
    )
    op.create_foreign_key(
        "fk_tournament_accounts_transferred_from",
        "tournament_accounts",
        "tournament_accounts",
        ["transferred_from_account_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_unique_constraint(
        "uq_tournament_accounts_transferred_from",
        "tournament_accounts",
        ["transferred_from_account_id"],
    )
    op.drop_constraint("ck_tournament_accounts_status", "tournament_accounts", type_="check")
    op.create_check_constraint(
        "ck_tournament_accounts_status",
        "tournament_accounts",
        "status in ('AVAILABLE', 'RESERVED', 'CLAIMED', 'INVALID', 'TRANSFERRED')",
    )


def downgrade() -> None:
    op.execute("update tournament_accounts set status = 'INVALID' where status = 'TRANSFERRED'")
    op.drop_constraint("ck_tournament_accounts_status", "tournament_accounts", type_="check")
    op.create_check_constraint(
        "ck_tournament_accounts_status",
        "tournament_accounts",
        "status in ('AVAILABLE', 'RESERVED', 'CLAIMED', 'INVALID')",
    )
    op.drop_constraint(
        "uq_tournament_accounts_transferred_from",
        "tournament_accounts",
        type_="unique",
    )
    op.drop_constraint(
        "fk_tournament_accounts_transferred_from",
        "tournament_accounts",
        type_="foreignkey",
    )
    op.drop_column("tournament_accounts", "transferred_from_account_id")
