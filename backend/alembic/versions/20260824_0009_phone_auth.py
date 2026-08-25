"""Add phone-number authentication while retaining QQ numbers.

Revision ID: 20260824_0009
Revises: 20260814_0008
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260824_0009"
down_revision: str | None = "20260814_0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("phone_number", sa.String(length=20), nullable=True))
    op.create_index("ix_users_phone_number", "users", ["phone_number"], unique=True)
    op.alter_column(
        "users",
        "qq_number",
        existing_type=sa.String(length=20),
        nullable=True,
    )
    op.create_check_constraint(
        "ck_users_login_identifier",
        "users",
        "phone_number is not null or qq_number is not null",
    )
    op.create_index(
        "ux_users_login_identifier",
        "users",
        [sa.text("COALESCE(phone_number, qq_number)")],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ux_users_login_identifier", table_name="users")
    op.drop_constraint("ck_users_login_identifier", "users", type_="check")
    connection = op.get_bind()
    connection.execute(sa.text(
        "UPDATE users SET qq_number = phone_number "
        "WHERE qq_number IS NULL"
    ))
    op.alter_column(
        "users",
        "qq_number",
        existing_type=sa.String(length=20),
        nullable=False,
    )
    op.drop_index("ix_users_phone_number", table_name="users")
    op.drop_column("users", "phone_number")
