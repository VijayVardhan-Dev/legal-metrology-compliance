"""Add deterministic product category classifications.

Revision ID: d4f6a8b2c1e7
Revises: c8e3f5a1b2d4
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d4f6a8b2c1e7"
down_revision: Union[str, None] = "c8e3f5a1b2d4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "product_categories",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("inspection_id", sa.String(length=36), nullable=False),
        sa.Column("product_id", sa.String(length=36), nullable=False),
        sa.Column("category", sa.String(length=50), nullable=False),
        sa.Column("subcategory", sa.String(length=80), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("evidence", sa.JSON(), nullable=True),
        sa.Column("source_text", sa.String(), nullable=True),
        sa.Column("classification_method", sa.String(length=30), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["inspection_id"], ["inspections.id"]),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("inspection_id"),
    )
    op.create_index(
        "ix_product_categories_inspection_id",
        "product_categories",
        ["inspection_id"],
        unique=True,
    )
    op.create_index(
        "ix_product_categories_product_id",
        "product_categories",
        ["product_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_product_categories_product_id", table_name="product_categories")
    op.drop_index("ix_product_categories_inspection_id", table_name="product_categories")
    op.drop_table("product_categories")
