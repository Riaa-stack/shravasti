"""add_admin_flags_to_papers

Revision ID: 1a2e233cc026
Revises: b7a42c19d8e1
Create Date: 2026-10-19 12:40:04.747671

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1a2e233cc026'
down_revision: Union[str, None] = 'b7a42c19d8e1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('papers', sa.Column('is_flagged', sa.Boolean(), server_default=sa.text('false'), nullable=False))
    op.add_column('papers', sa.Column('flag_reason', sa.String(length=500), nullable=True))
    op.add_column('papers', sa.Column('is_available_for_ai', sa.Boolean(), server_default=sa.text('true'), nullable=False))


def downgrade() -> None:
    op.drop_column('papers', 'is_available_for_ai')
    op.drop_column('papers', 'flag_reason')
    op.drop_column('papers', 'is_flagged')
