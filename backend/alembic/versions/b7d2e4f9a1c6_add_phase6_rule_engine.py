"""Add Phase 6 rule metadata, seeded MVP rules, and rule results.

Revision ID: b7d2e4f9a1c6
Revises: 9c4e1f6a2b7d
"""
from typing import Sequence, Union
from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa


revision: str = "b7d2e4f9a1c6"
down_revision: Union[str, None] = "9c4e1f6a2b7d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

DCA_SOURCE = (
    "https://consumeraffairs.nic.in/sites/default/files/"
    "file-uploads/legal-metrology/packaged-commoditiesrules.pdf"
)
FSSAI_SOURCE = "https://www.fssai.gov.in/cms/food-safety-and-standards-regulations.php"


def upgrade() -> None:
    for column in (
        sa.Column("rule_id", sa.String(length=50), nullable=True),
        sa.Column("rule_family", sa.String(length=50), nullable=True),
        sa.Column("legal_reference", sa.String(length=255), nullable=True),
        sa.Column("requirement", sa.Text(), nullable=True),
        sa.Column("applicability_conditions", sa.JSON(), nullable=True),
        sa.Column("exemptions", sa.JSON(), nullable=True),
        sa.Column("required_declaration", sa.String(length=50), nullable=True),
        sa.Column("validation_type", sa.String(length=50), nullable=True),
        sa.Column("effective_from", sa.Date(), nullable=True),
        sa.Column("effective_to", sa.Date(), nullable=True),
        sa.Column("rule_version", sa.String(length=30), nullable=True),
        sa.Column("source_url", sa.String(length=500), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=True),
    ):
        op.add_column("rules", column)
    op.create_unique_constraint("uq_rules_rule_id", "rules", ["rule_id"])
    op.execute("UPDATE rules SET rule_id = rule_code, active = is_active")
    op.alter_column("rules", "rule_id", nullable=False)
    op.alter_column("rules", "active", nullable=False)

    op.create_table(
        "rule_results",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("inspection_id", sa.String(length=36), nullable=False),
        sa.Column("rule_id", sa.String(length=50), nullable=False),
        sa.Column("rule_definition_id", sa.String(length=36), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("severity", sa.String(length=20), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("legal_reference", sa.String(length=255), nullable=False),
        sa.Column("evidence", sa.JSON(), nullable=True),
        sa.Column("declaration_ids", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["inspection_id"], ["inspections.id"]),
        sa.ForeignKeyConstraint(["rule_definition_id"], ["rules.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_rule_results_inspection_id", "rule_results", ["inspection_id"])
    op.create_index("ix_rule_results_rule_id", "rule_results", ["rule_id"])
    op.create_index(
        "ix_rule_results_rule_definition_id", "rule_results", ["rule_definition_id"]
    )

    rules = sa.table(
        "rules",
        sa.column("id", sa.String),
        sa.column("rule_code", sa.String),
        sa.column("rule_id", sa.String),
        sa.column("title", sa.String),
        sa.column("description", sa.Text),
        sa.column("category", sa.String),
        sa.column("severity", sa.String),
        sa.column("is_active", sa.Boolean),
        sa.column("rule_family", sa.String),
        sa.column("legal_reference", sa.String),
        sa.column("requirement", sa.Text),
        sa.column("applicability_conditions", sa.JSON),
        sa.column("exemptions", sa.JSON),
        sa.column("required_declaration", sa.String),
        sa.column("validation_type", sa.String),
        sa.column("rule_version", sa.String),
        sa.column("source_url", sa.String),
        sa.column("notes", sa.Text),
        sa.column("active", sa.Boolean),
        sa.column("created_at", sa.DateTime),
    )
    seed = [
        ("LM-PC-001", "LMPC", "Rule 3", "Applicability & Exemption Limits", "applicability", "HIGH", "Determine whether packaged-commodity requirements apply.", "APPLICABILITY_GATEWAY", None, DCA_SOURCE),
        ("LM-PC-002", "LMPC", "Rule 6(1)(a)", "Identity of Manufacturer / Packer / Importer", "identity", "HIGH", "Declare the identity and address of manufacturer, packer, or importer.", "PRESENCE", "MANUFACTURER", DCA_SOURCE),
        ("LM-PC-003", "LMPC", "Rule 6(1)(b)", "Generic Commodity Name", "product_name", "HIGH", "Declare the generic name of the commodity.", "GENERIC_NAME", "PRODUCT_NAME", DCA_SOURCE),
        ("LM-PC-004", "LMPC", "Rule 6(1)(c)", "Net Quantity Presence", "net_quantity", "HIGH", "Declare net quantity using a numeric value and recognizable unit.", "NUMERIC_UNIT", "NET_QUANTITY", DCA_SOURCE),
        ("LM-PC-005", "LMPC", "Rule 6(1)(e)", "Retail Sale Price / MRP", "mrp", "HIGH", "Declare the retail sale price / maximum retail price.", "PRICE", "MRP", DCA_SOURCE),
        ("LM-PC-008", "LMPC", "Rule 6(2)", "Consumer Care Information", "consumer_care", "MEDIUM", "Declare consumer-care contact information.", "CONTACT", "CONSUMER_CARE", DCA_SOURCE),
        ("LM-PC-009", "LMPC", "Rule 6(11)", "Unit Sale Price", "unit_sale_price", "MEDIUM", "Evaluate unit sale price only when its applicability and basis are determinable.", "CONTEXTUAL", "UNIT_SALE_PRICE", DCA_SOURCE),
        ("LM-PC-010", "LMPC", "Rule 6(1)(aa)", "Country of Origin", "origin", "HIGH", "Declare country of origin for imported commodities.", "IMPORTED_ONLY", "COUNTRY_OF_ORIGIN", DCA_SOURCE),
        ("FSSAI-001", "FSSAI", "FSS (Labelling and Display) Regulations 2020", "Date of Manufacture / Packaging", "food_date", "HIGH", "Declare the applicable date of manufacture or packaging for food.", "DATE", "MANUFACTURING_DATE", FSSAI_SOURCE),
        ("FSSAI-002", "FSSAI", "FSS (Labelling and Display) Regulations 2020", "Expiry / Use-by Date", "food_date", "HIGH", "Declare an expiry or use-by date for food.", "EXPIRY_USE_BY", "USE_BY", FSSAI_SOURCE),
        ("FSSAI-003", "FSSAI", "FSS (Labelling and Display) Regulations 2020", "Batch / Lot Number", "batch", "HIGH", "Declare a batch, lot, or code identifier for food.", "BATCH", "BATCH_LOT_NUMBER", FSSAI_SOURCE),
    ]
    rows = []
    for index, (rule_id, family, reference, title, category, severity, requirement, validation, required, source) in enumerate(seed, 1):
        rule_uuid = f"00000000-0000-0000-0000-{index:012d}"
        rows.append(
            {
                "id": rule_uuid,
                "rule_code": rule_id,
                "rule_id": rule_id,
                "title": title,
                "description": requirement,
                "category": category,
                "severity": severity,
                "is_active": True,
                "rule_family": family,
                "legal_reference": reference,
                "requirement": requirement,
                "applicability_conditions": {"source": "deterministic_context"},
                "exemptions": [],
                "required_declaration": required,
                "validation_type": validation,
                "rule_version": "MVP-1",
                "source_url": source,
                "notes": "Seeded MVP definition; applicability remains conservative where context is unavailable.",
                "active": True,
                "created_at": datetime.now(timezone.utc),
            }
        )
    op.bulk_insert(rules, rows)


def downgrade() -> None:
    op.drop_index("ix_rule_results_rule_definition_id", table_name="rule_results")
    op.drop_index("ix_rule_results_rule_id", table_name="rule_results")
    op.drop_index("ix_rule_results_inspection_id", table_name="rule_results")
    op.drop_table("rule_results")
    op.drop_constraint("uq_rules_rule_id", "rules", type_="unique")
    for column in (
        "active", "notes", "source_url", "rule_version", "effective_to",
        "effective_from", "validation_type", "required_declaration",
        "exemptions", "applicability_conditions", "requirement",
        "legal_reference", "rule_family", "rule_id",
    ):
        op.drop_column("rules", column)
