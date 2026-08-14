"""Add Phase 4 fixed-seed playoff rounds and match seeding.

Revision ID: 20260813_0005
Revises: 20260813_0004
Create Date: 2026-08-13
"""

from typing import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260813_0005"
down_revision: str | None = "20260813_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "playoff_rounds",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tournament_id", sa.Uuid(), nullable=False),
        sa.Column("stage_no", sa.Integer(), nullable=False),
        sa.Column("bracket_size", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("stage_no >= 1", name="ck_playoff_round_stage"),
        sa.CheckConstraint("bracket_size >= 2", name="ck_playoff_round_bracket_size"),
        sa.CheckConstraint("status in ('DRAFT', 'PUBLISHED', 'COMPLETED')", name="ck_playoff_round_status"),
        sa.ForeignKeyConstraint(["tournament_id"], ["tournaments.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tournament_id", "stage_no", name="uq_playoff_round_tournament_stage"),
    )
    op.create_index("ix_playoff_rounds_tournament_status", "playoff_rounds", ["tournament_id", "status"])

    with op.batch_alter_table("matches") as batch_op:
        batch_op.add_column(sa.Column("playoff_round_id", sa.Uuid(), nullable=True))
        batch_op.add_column(sa.Column("seed_a", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("seed_b", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            "fk_matches_playoff_round_id_playoff_rounds",
            "playoff_rounds",
            ["playoff_round_id"],
            ["id"],
            ondelete="CASCADE",
        )
        batch_op.create_unique_constraint("uq_match_playoff_round_table", ["playoff_round_id", "table_no"])
        batch_op.create_check_constraint("ck_matches_seed_a", "seed_a is null or seed_a >= 1")
        batch_op.create_check_constraint("ck_matches_seed_b", "seed_b is null or seed_b >= 1")


def downgrade() -> None:
    with op.batch_alter_table("matches") as batch_op:
        batch_op.drop_constraint("ck_matches_seed_b", type_="check")
        batch_op.drop_constraint("ck_matches_seed_a", type_="check")
        batch_op.drop_constraint("uq_match_playoff_round_table", type_="unique")
        batch_op.drop_constraint("fk_matches_playoff_round_id_playoff_rounds", type_="foreignkey")
        batch_op.drop_column("seed_b")
        batch_op.drop_column("seed_a")
        batch_op.drop_column("playoff_round_id")
    op.drop_index("ix_playoff_rounds_tournament_status", table_name="playoff_rounds")
    op.drop_table("playoff_rounds")
