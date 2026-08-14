"""Add public tournament codes.

Revision ID: 20260814_0008
Revises: 20260813_0007
"""

from collections.abc import Sequence
import secrets

from alembic import op
import sqlalchemy as sa


revision: str = "20260814_0008"
down_revision: str | None = "20260813_0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def upgrade() -> None:
    op.add_column("tournaments", sa.Column("code", sa.String(length=6), nullable=True))
    connection = op.get_bind()
    rows = connection.execute(
        sa.text("SELECT id FROM tournaments WHERE status <> 'DRAFT'")
    ).fetchall()
    used: set[str] = set()
    for row in rows:
        while True:
            code = "".join(secrets.choice(CODE_ALPHABET) for _ in range(6))
            if code not in used:
                used.add(code)
                break
        connection.execute(
            sa.text("UPDATE tournaments SET code = :code WHERE id = :id"),
            {"code": code, "id": row.id},
        )
    op.create_index("ix_tournaments_code", "tournaments", ["code"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_tournaments_code", table_name="tournaments")
    op.drop_column("tournaments", "code")
