"""Allow legacy rules without Phase 6 metadata.

Revision ID: c8e3f5a1b2d4
Revises: b7d2e4f9a1c6
"""
from typing import Sequence, Union

from alembic import op


revision: str = "c8e3f5a1b2d4"
down_revision: Union[str, None] = "b7d2e4f9a1c6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column("rules", "rule_id", nullable=True)


def downgrade() -> None:
    op.alter_column("rules", "rule_id", nullable=False)
