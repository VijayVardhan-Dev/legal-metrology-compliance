"""Add indexes used by Phase 10 history and dashboard queries.

Revision ID: m5e6f7a8b9c0
Revises: l4d5e6f7a8b9
"""
from typing import Sequence, Union

from alembic import op


revision: str = "m5e6f7a8b9c0"
down_revision: Union[str, None] = "l4d5e6f7a8b9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index("ix_inspections_created_at", "inspections", ["created_at"])
    op.create_index("ix_inspections_updated_at", "inspections", ["updated_at"])
    op.create_index("ix_products_name", "products", ["name"])
    op.create_index("ix_products_category", "products", ["category"])
    op.create_index("ix_product_categories_category", "product_categories", ["category"])
    op.create_index("ix_product_categories_subcategory", "product_categories", ["subcategory"])
    op.create_index("ix_compliance_runs_overall_status", "compliance_runs", ["overall_status"])
    op.create_index("ix_compliance_runs_overall_confidence", "compliance_runs", ["overall_confidence"])
    op.create_index("ix_rule_results_status", "rule_results", ["status"])


def downgrade() -> None:
    op.drop_index("ix_rule_results_status", table_name="rule_results")
    op.drop_index("ix_compliance_runs_overall_confidence", table_name="compliance_runs")
    op.drop_index("ix_compliance_runs_overall_status", table_name="compliance_runs")
    op.drop_index("ix_product_categories_subcategory", table_name="product_categories")
    op.drop_index("ix_product_categories_category", table_name="product_categories")
    op.drop_index("ix_products_category", table_name="products")
    op.drop_index("ix_products_name", table_name="products")
    op.drop_index("ix_inspections_updated_at", table_name="inspections")
    op.drop_index("ix_inspections_created_at", table_name="inspections")
