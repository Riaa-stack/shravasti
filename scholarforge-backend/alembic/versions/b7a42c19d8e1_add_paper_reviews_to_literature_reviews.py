"""Persist individual paper reviews in literature review reports.

Revision ID: b7a42c19d8e1
Revises: 04e7cb2ab0a7
Create Date: 2026-10-12
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "b7a42c19d8e1"
down_revision: Union[str, None] = "6d4a5837093a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "literature_reviews",
        sa.Column("paper_reviews", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("literature_reviews", "paper_reviews")
