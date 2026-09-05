"""Add Phase 8 compliance summaries and traceable rule evidence.

Revision ID: j2b3c4d5e6f7
Revises: h1a2b3c4d5e6
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "j2b3c4d5e6f7"
down_revision: Union[str, None] = "h1a2b3c4d5e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "compliance_runs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("inspection_id", sa.String(length=36), nullable=False),
        sa.Column("overall_status", sa.String(length=30), nullable=False),
        sa.Column("total_rules", sa.Integer(), nullable=False),
        sa.Column("compliant_rules", sa.Integer(), nullable=False),
        sa.Column("non_compliant_rules", sa.Integer(), nullable=False),
        sa.Column("review_required_rules", sa.Integer(), nullable=False),
        sa.Column("applicable_rules", sa.Integer(), nullable=False),
        sa.Column("not_applicable_rules", sa.Integer(), nullable=False),
        sa.Column("overall_confidence", sa.Float(), nullable=True),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("rule_engine_version", sa.String(length=30), nullable=False),
        sa.Column("classification_version", sa.String(length=50), nullable=True),
        sa.Column("ocr_result_id", sa.String(length=36), nullable=True),
        sa.Column("visual_analysis_id", sa.String(length=36), nullable=True),
        sa.ForeignKeyConstraint(["inspection_id"], ["inspections.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("inspection_id"),
    )
    op.create_index("ix_compliance_runs_inspection_id", "compliance_runs", ["inspection_id"])
    op.create_index("ix_compliance_runs_ocr_result_id", "compliance_runs", ["ocr_result_id"])
    op.create_index("ix_compliance_runs_visual_analysis_id", "compliance_runs", ["visual_analysis_id"])
    op.add_column(
        "rule_results",
        sa.Column("applicability_status", sa.String(length=30), nullable=False, server_default="APPLICABLE"),
    )
    op.add_column("rule_results", sa.Column("confidence", sa.Float(), nullable=True))
    op.add_column("rule_results", sa.Column("ocr_region_ids", sa.JSON(), nullable=True))
    op.add_column("rule_results", sa.Column("visual_finding_ids", sa.JSON(), nullable=True))
    op.add_column("rule_results", sa.Column("warnings", sa.JSON(), nullable=True))
    op.alter_column("rule_results", "applicability_status", server_default=None)


def downgrade() -> None:
    for column in ("warnings", "visual_finding_ids", "ocr_region_ids", "confidence", "applicability_status"):
        op.drop_column("rule_results", column)
    op.drop_index("ix_compliance_runs_visual_analysis_id", table_name="compliance_runs")
    op.drop_index("ix_compliance_runs_ocr_result_id", table_name="compliance_runs")
    op.drop_index("ix_compliance_runs_inspection_id", table_name="compliance_runs")
    op.drop_table("compliance_runs")
