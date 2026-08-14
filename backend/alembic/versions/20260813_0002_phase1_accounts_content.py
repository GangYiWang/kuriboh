"""Add Phase 1 accounts and content tables.

Revision ID: 20260813_0002
Revises: 20260813_0001
Create Date: 2026-08-13
"""

from typing import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260813_0002"
down_revision: str | None = "20260813_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("qq_number", sa.String(length=20), nullable=False),
        sa.Column("nickname", sa.String(length=50), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("qq_openid", sa.String(length=128), nullable=True),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("role in ('PLAYER', 'TOURNAMENT_ADMIN')", name="ck_users_role"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("qq_openid"),
    )
    op.create_index(op.f("ix_users_nickname"), "users", ["nickname"], unique=True)
    op.create_index(op.f("ix_users_qq_number"), "users", ["qq_number"], unique=True)

    op.create_table(
        "announcements",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("content_html", sa.Text(), nullable=False),
        sa.Column("is_pinned", sa.Boolean(), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("author_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["author_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "banlist_versions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("major_version", sa.Integer(), nullable=False),
        sa.Column("minor_version", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=120), nullable=False),
        sa.Column("content_html", sa.Text(), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("major_version", "minor_version", name="uq_banlist_version_number"),
    )


def downgrade() -> None:
    op.drop_table("banlist_versions")
    op.drop_table("announcements")
    op.drop_index(op.f("ix_users_qq_number"), table_name="users")
    op.drop_index(op.f("ix_users_nickname"), table_name="users")
    op.drop_table("users")
