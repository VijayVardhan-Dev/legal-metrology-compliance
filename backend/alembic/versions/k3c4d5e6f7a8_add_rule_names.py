"""Store rule names with persisted Phase 8 results.

Revision ID: k3c4d5e6f7a8
Revises: j2b3c4d5e6f7
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "k3c4d5e6f7a8"
down_revision: Union[str, None] = "j2b3c4d5e6f7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "rule_results",
        sa.Column("rule_name", sa.String(length=255), nullable=False, server_default=""),
    )
    op.alter_column("rule_results", "rule_name", server_default=None)


def downgrade() -> None:
    op.drop_column("rule_results", "rule_name")
