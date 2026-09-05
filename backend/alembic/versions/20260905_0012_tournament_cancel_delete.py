"""Add tournament cancellation and soft deletion.

Revision ID: 20260905_0012
Revises: 20260827_0011
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260905_0012"
down_revision: str | None = "20260827_0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("tournaments", sa.Column("canceled_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("tournaments", sa.Column("cancellation_reason", sa.String(length=500), nullable=True))
    op.add_column("tournaments", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_tournaments_deleted_at", "tournaments", ["deleted_at"])
    op.drop_constraint("ck_tournaments_status", "tournaments", type_="check")
    op.create_check_constraint(
        "ck_tournaments_status",
        "tournaments",
        "status in ('DRAFT', 'REGISTRATION', 'SWISS', 'ELIMINATION', 'ENDED', 'CANCELED')",
    )
    op.create_check_constraint(
        "ck_tournaments_cancellation",
        "tournaments",
        "(status = 'CANCELED' and canceled_at is not null) or "
        "(status <> 'CANCELED' and canceled_at is null and cancellation_reason is null)",
    )


def downgrade() -> None:
    op.drop_constraint("ck_tournaments_cancellation", "tournaments", type_="check")
    op.drop_constraint("ck_tournaments_status", "tournaments", type_="check")
    op.execute("UPDATE tournaments SET status = 'REGISTRATION' WHERE status = 'CANCELED'")
    op.create_check_constraint(
        "ck_tournaments_status",
        "tournaments",
        "status in ('DRAFT', 'REGISTRATION', 'SWISS', 'ELIMINATION', 'ENDED')",
    )
    op.drop_index("ix_tournaments_deleted_at", table_name="tournaments")
    op.drop_column("tournaments", "deleted_at")
    op.drop_column("tournaments", "cancellation_reason")
    op.drop_column("tournaments", "canceled_at")
