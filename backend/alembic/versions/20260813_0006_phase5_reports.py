"""Add Phase 5 tournament ending, deck submissions, and weekly reports.

Revision ID: 20260813_0006
Revises: 20260813_0005
Create Date: 2026-08-13
"""

from typing import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260813_0006"
down_revision: str | None = "20260813_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("tournaments", sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True))
    op.create_table(
        "deck_submissions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tournament_id", sa.Uuid(), nullable=False),
        sa.Column("participant_id", sa.Uuid(), nullable=False),
        sa.Column("placement", sa.Integer(), nullable=False),
        sa.Column("image_path", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("review_note", sa.Text(), nullable=True),
        sa.Column("reviewed_by_id", sa.Uuid(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("placement between 1 and 4", name="ck_deck_submission_placement"),
        sa.CheckConstraint(
            "status in ('NOT_UPLOADED', 'PENDING_REVIEW', 'REUPLOAD_REQUIRED', 'APPROVED')",
            name="ck_deck_submission_status",
        ),
        sa.ForeignKeyConstraint(["participant_id"], ["tournament_participants.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["reviewed_by_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["tournament_id"], ["tournaments.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tournament_id", "participant_id", name="uq_deck_submission_tournament_participant"
        ),
    )
    op.create_index(
        "ix_deck_submissions_tournament_status", "deck_submissions", ["tournament_id", "status"]
    )
    op.create_table(
        "weekly_reports",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tournament_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("snapshot_content", sa.JSON(), nullable=False),
        sa.Column("generated_by_id", sa.Uuid(), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("status in ('DRAFT', 'PUBLISHED')", name="ck_weekly_report_status"),
        sa.ForeignKeyConstraint(["generated_by_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["tournament_id"], ["tournaments.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tournament_id", name="uq_weekly_report_tournament"),
    )
    op.create_index(
        "ix_weekly_reports_status_published", "weekly_reports", ["status", "published_at"]
    )


def downgrade() -> None:
    op.drop_index("ix_weekly_reports_status_published", table_name="weekly_reports")
    op.drop_table("weekly_reports")
    op.drop_index("ix_deck_submissions_tournament_status", table_name="deck_submissions")
    op.drop_table("deck_submissions")
    op.drop_column("tournaments", "ended_at")
