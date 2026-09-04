"""Add image dimensions to ocr_results and normalized bbox to ocr_text_regions

Revision ID: f7b2c9d41e03
Revises: d3eca8aba13e
Create Date: 2026-09-04 14:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f7b2c9d41e03'
down_revision: Union[str, None] = 'd3eca8aba13e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- ocr_results: add image dimension columns ---
    op.add_column('ocr_results', sa.Column('image_width', sa.Integer(), nullable=True))
    op.add_column('ocr_results', sa.Column('image_height', sa.Integer(), nullable=True))

    # --- ocr_text_regions: add normalized bbox columns ---
    op.add_column('ocr_text_regions', sa.Column('bbox_x', sa.Integer(), nullable=True))
    op.add_column('ocr_text_regions', sa.Column('bbox_y', sa.Integer(), nullable=True))
    op.add_column('ocr_text_regions', sa.Column('bbox_width', sa.Integer(), nullable=True))
    op.add_column('ocr_text_regions', sa.Column('bbox_height', sa.Integer(), nullable=True))


def downgrade() -> None:
    # --- ocr_text_regions: remove normalized bbox columns ---
    op.drop_column('ocr_text_regions', 'bbox_height')
    op.drop_column('ocr_text_regions', 'bbox_width')
    op.drop_column('ocr_text_regions', 'bbox_y')
    op.drop_column('ocr_text_regions', 'bbox_x')

    # --- ocr_results: remove image dimension columns ---
    op.drop_column('ocr_results', 'image_height')
    op.drop_column('ocr_results', 'image_width')
