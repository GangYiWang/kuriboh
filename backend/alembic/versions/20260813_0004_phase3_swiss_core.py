"""Add Phase 3 Swiss rounds, matches, rankings, withdrawals, and audit logs.

Revision ID: 20260813_0004
Revises: 20260813_0003
Create Date: 2026-08-13
"""

from typing import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260813_0004"
down_revision: str | None = "20260813_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "swiss_rounds",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tournament_id", sa.Uuid(), nullable=False),
        sa.Column("round_no", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("round_no >= 1", name="ck_swiss_round_number"),
        sa.CheckConstraint("status in ('DRAFT', 'PUBLISHED', 'COMPLETED')", name="ck_swiss_round_status"),
        sa.ForeignKeyConstraint(["tournament_id"], ["tournaments.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tournament_id", "round_no", name="uq_swiss_round_tournament_number"),
    )
    op.create_index("ix_swiss_rounds_tournament_status", "swiss_rounds", ["tournament_id", "status"])

    op.create_table(
        "matches",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tournament_id", sa.Uuid(), nullable=False),
        sa.Column("swiss_round_id", sa.Uuid(), nullable=True),
        sa.Column("stage", sa.String(length=24), nullable=False),
        sa.Column("round_no", sa.Integer(), nullable=False),
        sa.Column("table_no", sa.Integer(), nullable=False),
        sa.Column("player_a_id", sa.Uuid(), nullable=False),
        sa.Column("player_b_id", sa.Uuid(), nullable=True),
        sa.Column("winner_id", sa.Uuid(), nullable=True),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("result_source", sa.String(length=24), nullable=True),
        sa.Column("result_locked", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("stage in ('SWISS', 'ELIMINATION')", name="ck_matches_stage"),
        sa.CheckConstraint("status in ('WAITING', 'CONFLICT', 'COMPLETED')", name="ck_matches_status"),
        sa.CheckConstraint(
            "result_source is null or result_source in ('PLAYERS', 'ADMIN', 'BYE')",
            name="ck_matches_result_source",
        ),
        sa.CheckConstraint("table_no >= 1 and round_no >= 1", name="ck_matches_numbers"),
        sa.CheckConstraint("player_b_id is null or player_a_id <> player_b_id", name="ck_matches_distinct_players"),
        sa.ForeignKeyConstraint(["player_a_id"], ["tournament_participants.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["player_b_id"], ["tournament_participants.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["swiss_round_id"], ["swiss_rounds.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tournament_id"], ["tournaments.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["winner_id"], ["tournament_participants.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("swiss_round_id", "table_no", name="uq_match_round_table"),
    )
    op.create_index(
        "ix_matches_tournament_round_status", "matches", ["tournament_id", "round_no", "status"]
    )

    op.create_table(
        "match_submissions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("match_id", sa.Uuid(), nullable=False),
        sa.Column("participant_id", sa.Uuid(), nullable=False),
        sa.Column("submitted_result", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("submitted_result in ('WIN', 'LOSS')", name="ck_submission_result"),
        sa.ForeignKeyConstraint(["match_id"], ["matches.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["participant_id"], ["tournament_participants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("match_id", "participant_id", name="uq_submission_match_participant"),
    )

    op.create_table(
        "ranking_snapshots",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tournament_id", sa.Uuid(), nullable=False),
        sa.Column("swiss_round_id", sa.Uuid(), nullable=False),
        sa.Column("participant_id", sa.Uuid(), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("wins", sa.Integer(), nullable=False),
        sa.Column("losses", sa.Integer(), nullable=False),
        sa.Column("omw", sa.Numeric(precision=8, scale=6), nullable=False),
        sa.Column("loss_round_score", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("rank >= 1", name="ck_ranking_rank"),
        sa.CheckConstraint("wins >= 0 and losses >= 0", name="ck_ranking_record"),
        sa.CheckConstraint("omw >= 0 and omw <= 1", name="ck_ranking_omw"),
        sa.ForeignKeyConstraint(["participant_id"], ["tournament_participants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["swiss_round_id"], ["swiss_rounds.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tournament_id"], ["tournaments.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("swiss_round_id", "participant_id", name="uq_ranking_round_participant"),
        sa.UniqueConstraint("swiss_round_id", "rank", name="uq_ranking_round_rank"),
    )

    op.create_table(
        "withdrawals",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tournament_id", sa.Uuid(), nullable=False),
        sa.Column("participant_id", sa.Uuid(), nullable=False),
        sa.Column("after_round_no", sa.Integer(), nullable=False),
        sa.Column("operator_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("after_round_no >= 0", name="ck_withdrawal_after_round"),
        sa.ForeignKeyConstraint(["operator_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["participant_id"], ["tournament_participants.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["tournament_id"], ["tournaments.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("participant_id", name="uq_withdrawal_participant"),
    )

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("operator_id", sa.Uuid(), nullable=False),
        sa.Column("action_type", sa.String(length=64), nullable=False),
        sa.Column("target_type", sa.String(length=64), nullable=False),
        sa.Column("target_id", sa.String(length=64), nullable=False),
        sa.Column("before_json", sa.JSON(), nullable=True),
        sa.Column("after_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["operator_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_logs_target", "audit_logs", ["target_type", "target_id"])


def downgrade() -> None:
    op.drop_index("ix_audit_logs_target", table_name="audit_logs")
    op.drop_table("audit_logs")
    op.drop_table("withdrawals")
    op.drop_table("ranking_snapshots")
    op.drop_table("match_submissions")
    op.drop_index("ix_matches_tournament_round_status", table_name="matches")
    op.drop_table("matches")
    op.drop_index("ix_swiss_rounds_tournament_status", table_name="swiss_rounds")
    op.drop_table("swiss_rounds")
