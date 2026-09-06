"""Add barcode and food database fields to nutrition analyses.

Revision ID: o7a8b9c0d1e2
Revises: n6f7a8b9c0d1
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "o7a8b9c0d1e2"
down_revision: Union[str, None] = "n6f7a8b9c0d1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("nutrition_analyses", sa.Column("barcode", sa.String(length=20), nullable=True))
    op.add_column("nutrition_analyses", sa.Column("product_database", sa.JSON(), nullable=True))
    op.add_column("nutrition_analyses", sa.Column("source_comparison", sa.JSON(), nullable=True))
    op.add_column("nutrition_analyses", sa.Column("suitability", sa.JSON(), nullable=True))
    op.create_index("ix_nutrition_analyses_barcode", "nutrition_analyses", ["barcode"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_nutrition_analyses_barcode", table_name="nutrition_analyses")
    op.drop_column("nutrition_analyses", "suitability")
    op.drop_column("nutrition_analyses", "source_comparison")
    op.drop_column("nutrition_analyses", "product_database")
    op.drop_column("nutrition_analyses", "barcode")
