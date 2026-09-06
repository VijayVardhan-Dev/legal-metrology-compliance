"""Add persisted nutrition and ingredient analyses.

Revision ID: n6f7a8b9c0d1
Revises: m5e6f7a8b9c0
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "n6f7a8b9c0d1"
down_revision: Union[str, None] = "m5e6f7a8b9c0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "nutrition_analyses",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("inspection_id", sa.String(length=36), nullable=False),
        sa.Column("ocr_result_id", sa.String(length=36), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("nutrition_confidence", sa.Float(), nullable=True),
        sa.Column("ingredient_confidence", sa.Float(), nullable=True),
        sa.Column("source_text", sa.Text(), nullable=True),
        sa.Column("ingredient_text", sa.Text(), nullable=True),
        sa.Column("nutrition", sa.JSON(), nullable=True),
        sa.Column("ingredients", sa.JSON(), nullable=True),
        sa.Column("allergens", sa.JSON(), nullable=True),
        sa.Column("insights", sa.JSON(), nullable=True),
        sa.Column("sections", sa.JSON(), nullable=True),
        sa.Column("warnings", sa.JSON(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["inspection_id"], ["inspections.id"]),
        sa.ForeignKeyConstraint(["ocr_result_id"], ["ocr_results.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("inspection_id"),
    )
    op.create_index("ix_nutrition_analyses_inspection_id", "nutrition_analyses", ["inspection_id"], unique=True)
    op.create_index("ix_nutrition_analyses_ocr_result_id", "nutrition_analyses", ["ocr_result_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_nutrition_analyses_ocr_result_id", table_name="nutrition_analyses")
    op.drop_index("ix_nutrition_analyses_inspection_id", table_name="nutrition_analyses")
    op.drop_table("nutrition_analyses")
