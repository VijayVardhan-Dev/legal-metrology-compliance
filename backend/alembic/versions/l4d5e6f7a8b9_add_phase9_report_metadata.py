"""Add Phase 9 report metadata.

Revision ID: l4d5e6f7a8b9
Revises: k3c4d5e6f7a8
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "l4d5e6f7a8b9"
down_revision: Union[str, None] = "k3c4d5e6f7a8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE SEQUENCE lm_report_number_seq START 1")
    op.add_column("reports", sa.Column("report_number", sa.String(length=30), nullable=True))
    op.add_column("reports", sa.Column("report_status", sa.String(length=30), nullable=True))
    op.add_column("reports", sa.Column("overall_compliance_status", sa.String(length=30), nullable=True))
    op.add_column("reports", sa.Column("overall_confidence", sa.Float(), nullable=True))
    op.add_column("reports", sa.Column("compliance_run_id", sa.String(length=36), nullable=True))
    op.add_column("reports", sa.Column("rule_engine_version", sa.String(length=30), nullable=True))
    op.add_column("reports", sa.Column("classification_version", sa.String(length=50), nullable=True))
    op.add_column("reports", sa.Column("ocr_result_id", sa.String(length=36), nullable=True))
    op.add_column("reports", sa.Column("visual_analysis_id", sa.String(length=36), nullable=True))
    op.add_column("reports", sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True))
    op.execute(
        "UPDATE reports SET report_number = 'LEGACY-' || id, report_status = 'COMPLETED', "
        "overall_compliance_status = 'REVIEW_REQUIRED', updated_at = created_at "
        "WHERE report_number IS NULL"
    )
    op.alter_column("reports", "report_number", nullable=False)
    op.alter_column("reports", "report_status", nullable=False)
    op.alter_column("reports", "overall_compliance_status", nullable=False)
    op.alter_column("reports", "updated_at", nullable=False)
    op.create_unique_constraint("uq_reports_report_number", "reports", ["report_number"])
    op.create_index("ix_reports_compliance_run_id", "reports", ["compliance_run_id"])
    op.create_index("ix_reports_ocr_result_id", "reports", ["ocr_result_id"])
    op.create_index("ix_reports_visual_analysis_id", "reports", ["visual_analysis_id"])
    op.create_foreign_key("fk_reports_compliance_run_id", "reports", "compliance_runs", ["compliance_run_id"], ["id"])
    op.create_foreign_key("fk_reports_ocr_result_id", "reports", "ocr_results", ["ocr_result_id"], ["id"])
    op.create_foreign_key("fk_reports_visual_analysis_id", "reports", "visual_analyses", ["visual_analysis_id"], ["id"])


def downgrade() -> None:
    op.drop_constraint("fk_reports_visual_analysis_id", "reports", type_="foreignkey")
    op.drop_constraint("fk_reports_ocr_result_id", "reports", type_="foreignkey")
    op.drop_constraint("fk_reports_compliance_run_id", "reports", type_="foreignkey")
    op.drop_index("ix_reports_visual_analysis_id", table_name="reports")
    op.drop_index("ix_reports_ocr_result_id", table_name="reports")
    op.drop_index("ix_reports_compliance_run_id", table_name="reports")
    op.drop_constraint("uq_reports_report_number", "reports", type_="unique")
    for column in ("updated_at", "visual_analysis_id", "ocr_result_id", "classification_version",
                   "rule_engine_version", "compliance_run_id", "overall_confidence",
                   "overall_compliance_status", "report_status", "report_number"):
        op.drop_column("reports", column)
    op.execute("DROP SEQUENCE lm_report_number_seq")
