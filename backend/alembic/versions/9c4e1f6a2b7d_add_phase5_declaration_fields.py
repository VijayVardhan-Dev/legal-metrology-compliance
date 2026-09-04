"""Add Phase 5 declaration extraction fields.

Revision ID: 9c4e1f6a2b7d
Revises: f7b2c9d41e03
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "9c4e1f6a2b7d"
down_revision: Union[str, None] = "f7b2c9d41e03"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "declarations",
        sa.Column("declaration_type", sa.String(length=50), nullable=True),
    )
    op.add_column(
        "declarations", sa.Column("normalized_value", sa.JSON(), nullable=True)
    )
    op.add_column(
        "declarations", sa.Column("unit", sa.String(length=20), nullable=True)
    )
    op.add_column(
        "declarations", sa.Column("source_text", sa.Text(), nullable=True)
    )
    op.add_column(
        "declarations", sa.Column("ocr_confidence", sa.Float(), nullable=True)
    )
    op.add_column(
        "declarations",
        sa.Column("extraction_method", sa.String(length=30), nullable=True),
    )
    op.add_column(
        "declarations",
        sa.Column("status", sa.String(length=30), nullable=True),
    )
    op.add_column(
        "declarations",
        sa.Column("ocr_text_region_id", sa.String(length=36), nullable=True),
    )
    op.add_column(
        "declarations",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_declarations_declaration_type",
        "declarations",
        ["declaration_type"],
        unique=False,
    )
    op.create_index(
        "ix_declarations_ocr_text_region_id",
        "declarations",
        ["ocr_text_region_id"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_declarations_ocr_text_region_id",
        "declarations",
        "ocr_text_regions",
        ["ocr_text_region_id"],
        ["id"],
    )
    op.execute(
        """
        UPDATE declarations
        SET declaration_type = UPPER(field_name),
            source_text = COALESCE(value, ''),
            extraction_method = 'REVIEW_REQUIRED',
            status = 'INCOMPLETE',
            updated_at = created_at
        WHERE declaration_type IS NULL
        """
    )
    op.alter_column("declarations", "declaration_type", nullable=False)
    op.alter_column("declarations", "source_text", nullable=False)
    op.alter_column("declarations", "extraction_method", nullable=False)
    op.alter_column("declarations", "status", nullable=False)
    op.alter_column("declarations", "updated_at", nullable=False)


def downgrade() -> None:
    op.drop_constraint(
        "fk_declarations_ocr_text_region_id",
        "declarations",
        type_="foreignkey",
    )
    op.drop_index("ix_declarations_ocr_text_region_id", table_name="declarations")
    op.drop_index("ix_declarations_declaration_type", table_name="declarations")
    op.drop_column("declarations", "updated_at")
    op.drop_column("declarations", "ocr_text_region_id")
    op.drop_column("declarations", "status")
    op.drop_column("declarations", "extraction_method")
    op.drop_column("declarations", "ocr_confidence")
    op.drop_column("declarations", "source_text")
    op.drop_column("declarations", "unit")
    op.drop_column("declarations", "normalized_value")
    op.drop_column("declarations", "declaration_type")
