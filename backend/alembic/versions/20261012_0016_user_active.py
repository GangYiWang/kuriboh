"""Add user active status.

Revision ID: 20261012_0016
Revises: 20260922_0015
Create Date: 2026-10-12
"""

from typing import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261012_0016"
down_revision: str | None = "20260922_0015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("active", sa.Boolean(), server_default=sa.true(), nullable=False),
    )


def downgrade() -> None:
    op.drop_column("users", "active")
