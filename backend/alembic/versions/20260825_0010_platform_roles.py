"""Separate platform roles from tournament identities.

Revision ID: 20260825_0010
Revises: 20260824_0009
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260825_0010"
down_revision: str | None = "20260824_0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint("ck_users_role", "users", type_="check")
    connection = op.get_bind()
    connection.execute(sa.text("UPDATE users SET role = 'USER' WHERE role = 'PLAYER'"))
    connection.execute(sa.text(
        "UPDATE users SET role = 'PLATFORM_ADMIN' WHERE role = 'TOURNAMENT_ADMIN'"
    ))
    op.create_check_constraint(
        "ck_users_role",
        "users",
        "role in ('USER', 'PLATFORM_ADMIN')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_users_role", "users", type_="check")
    connection = op.get_bind()
    connection.execute(sa.text("UPDATE users SET role = 'PLAYER' WHERE role = 'USER'"))
    connection.execute(sa.text(
        "UPDATE users SET role = 'TOURNAMENT_ADMIN' WHERE role = 'PLATFORM_ADMIN'"
    ))
    op.create_check_constraint(
        "ck_users_role",
        "users",
        "role in ('PLAYER', 'TOURNAMENT_ADMIN')",
    )
