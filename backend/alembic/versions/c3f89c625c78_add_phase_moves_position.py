"""add phase_moves position

Revision ID: c3f89c625c78
Revises: 4d6b6417338d
Create Date: 2026-09-22 18:44:49.918167

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c3f89c625c78'
down_revision: Union[str, Sequence[str], None] = '4d6b6417338d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Autogenerate added this as NOT NULL with no default, which fails on a
    # table that already has rows. Backfill with 0, then drop the default so
    # new rows must supply an explicit position.
    op.add_column('phase_moves', sa.Column('position', sa.Integer(), nullable=False, server_default='0'))
    op.alter_column('phase_moves', 'position', server_default=None)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('phase_moves', 'position')
