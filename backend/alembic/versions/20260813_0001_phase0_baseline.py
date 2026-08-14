"""Establish the Phase 0 migration baseline.

Revision ID: 20260813_0001
Revises:
Create Date: 2026-08-13
"""

from typing import Sequence

revision: str = "20260813_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Business tables are introduced with their owning milestone."""


def downgrade() -> None:
    """The baseline has no business objects to remove."""

