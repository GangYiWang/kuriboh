"""Add Phase 2 tournaments, registrations, and participant snapshots.

Revision ID: 20260813_0003
Revises: 20260813_0002
Create Date: 2026-08-13
"""

from typing import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260813_0003"
down_revision: str | None = "20260813_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "tournaments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("planned_start_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("max_players", sa.Integer(), nullable=True),
        sa.Column("swiss_rounds", sa.Integer(), nullable=True),
        sa.Column("playoff_size", sa.Integer(), nullable=True),
        sa.Column("banlist_version_id", sa.Uuid(), nullable=True),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "status in ('DRAFT', 'REGISTRATION', 'SWISS', 'ELIMINATION', 'ENDED')",
            name="ck_tournaments_status",
        ),
        sa.CheckConstraint("max_players is null or max_players >= 2", name="ck_tournaments_max_players"),
        sa.CheckConstraint("swiss_rounds is null or swiss_rounds >= 1", name="ck_tournaments_swiss_rounds"),
        sa.CheckConstraint("playoff_size is null or playoff_size >= 2", name="ck_tournaments_playoff_size"),
        sa.ForeignKeyConstraint(["banlist_version_id"], ["banlist_versions.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_tournaments_status_start", "tournaments", ["status", "planned_start_at"], unique=False)

    op.create_table(
        "registrations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tournament_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("reviewed_by_id", sa.Uuid(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "status in ('PENDING', 'APPROVED', 'REJECTED', 'CANCELED')",
            name="ck_registrations_status",
        ),
        sa.ForeignKeyConstraint(["reviewed_by_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["tournament_id"], ["tournaments.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tournament_id", "user_id", name="uq_registration_tournament_user"),
    )
    op.create_index("ix_registrations_tournament_status", "registrations", ["tournament_id", "status"], unique=False)

    op.create_table(
        "tournament_participants",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tournament_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("registration_id", sa.Uuid(), nullable=False),
        sa.Column("nickname_snapshot", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("bye_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("status in ('ACTIVE', 'WITHDRAWN')", name="ck_participants_status"),
        sa.CheckConstraint("bye_count >= 0", name="ck_participants_bye_count"),
        sa.ForeignKeyConstraint(["registration_id"], ["registrations.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["tournament_id"], ["tournaments.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("registration_id", name="uq_participant_registration"),
        sa.UniqueConstraint("tournament_id", "user_id", name="uq_participant_tournament_user"),
    )


def downgrade() -> None:
    op.drop_table("tournament_participants")
    op.drop_index("ix_registrations_tournament_status", table_name="registrations")
    op.drop_table("registrations")
    op.drop_index("ix_tournaments_status_start", table_name="tournaments")
    op.drop_table("tournaments")
