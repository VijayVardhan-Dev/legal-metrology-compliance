"""Add Phase 7 visual analysis results.

Revision ID: g8c4d2e1f907
Revises: f7b2c9d41e03
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "g8c4d2e1f907"
down_revision: Union[str, None] = "f7b2c9d41e03"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "visual_analyses",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("inspection_id", sa.String(length=36), nullable=False),
        sa.Column("evidence_id", sa.String(length=36), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("processing_status", sa.String(length=30), nullable=False),
        sa.Column("quality_status", sa.String(length=30), nullable=False),
        sa.Column("image_width", sa.Integer(), nullable=True),
        sa.Column("image_height", sa.Integer(), nullable=True),
        sa.Column("quality_score", sa.Float(), nullable=True),
        sa.Column("metrics", sa.JSON(), nullable=True),
        sa.Column("visibility_flags", sa.JSON(), nullable=True),
        sa.Column("findings", sa.JSON(), nullable=True),
        sa.Column("warnings", sa.JSON(), nullable=True),
        sa.Column("declarations", sa.JSON(), nullable=True),
        sa.Column("calibration", sa.JSON(), nullable=True),
        sa.Column("evidence", sa.JSON(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["inspection_id"], ["inspections.id"]),
        sa.ForeignKeyConstraint(["evidence_id"], ["evidence.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("inspection_id"),
    )
    op.create_index("ix_visual_analyses_inspection_id", "visual_analyses", ["inspection_id"])
    op.create_index("ix_visual_analyses_evidence_id", "visual_analyses", ["evidence_id"])


def downgrade() -> None:
    op.drop_index("ix_visual_analyses_evidence_id", table_name="visual_analyses")
    op.drop_index("ix_visual_analyses_inspection_id", table_name="visual_analyses")
    op.drop_table("visual_analyses")
