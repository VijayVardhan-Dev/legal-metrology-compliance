"""Add optional NLP enrichment to nutrition analyses.

Revision ID: p8b9c0d1e2f3
Revises: o7a8b9c0d1e2
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "p8b9c0d1e2f3"
down_revision: Union[str, None] = "o7a8b9c0d1e2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("nutrition_analyses", sa.Column("nlp_analysis", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("nutrition_analyses", "nlp_analysis")
