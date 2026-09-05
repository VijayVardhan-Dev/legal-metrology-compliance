"""Merge the product-category and visual-analysis migration branches.

Revision ID: h1a2b3c4d5e6
Revises: d4f6a8b2c1e7, g8c4d2e1f907
"""
from typing import Sequence, Union


revision: str = "h1a2b3c4d5e6"
down_revision: Union[str, tuple[str, str], None] = (
    "d4f6a8b2c1e7",
    "g8c4d2e1f907",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
