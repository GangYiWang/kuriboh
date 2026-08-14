"""Add Phase 6 messages and tournament-scoped audit logs.

Revision ID: 20260813_0007
Revises: 20260813_0006
Create Date: 2026-08-13
"""

from typing import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260813_0007"
down_revision: str | None = "20260813_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("audit_logs") as batch_op:
        batch_op.add_column(sa.Column("tournament_id", sa.Uuid(), nullable=True))
        batch_op.create_foreign_key(
            "fk_audit_logs_tournament_id_tournaments",
            "tournaments",
            ["tournament_id"],
            ["id"],
            ondelete="CASCADE",
        )
    op.create_index(
        "ix_audit_logs_tournament_created",
        "audit_logs",
        ["tournament_id", "created_at"],
    )
    op.create_table(
        "messages",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("recipient_id", sa.Uuid(), nullable=False),
        sa.Column("sender_id", sa.Uuid(), nullable=True),
        sa.Column("type", sa.String(length=40), nullable=False),
        sa.Column("title", sa.String(length=120), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("action_url", sa.String(length=255), nullable=True),
        sa.Column("related_type", sa.String(length=40), nullable=True),
        sa.Column("related_id", sa.String(length=64), nullable=True),
        sa.Column("dedupe_key", sa.String(length=160), nullable=True),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "type in ('REGISTRATION_APPROVED', 'REGISTRATION_REJECTED', "
            "'REGISTRATION_CANCELED', 'TOURNAMENT_NOTICE', 'PLATFORM_NOTICE', 'REPORT_PUBLISHED')",
            name="ck_messages_type",
        ),
        sa.ForeignKeyConstraint(["recipient_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["sender_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("dedupe_key"),
    )
    op.create_index(
        "ix_messages_recipient_read_created",
        "messages",
        ["recipient_id", "read_at", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_messages_recipient_read_created", table_name="messages")
    op.drop_table("messages")
    op.drop_index("ix_audit_logs_tournament_created", table_name="audit_logs")
    with op.batch_alter_table("audit_logs") as batch_op:
        batch_op.drop_constraint("fk_audit_logs_tournament_id_tournaments", type_="foreignkey")
        batch_op.drop_column("tournament_id")
