"""boss source and chinese name

Revision ID: 49210234f07d
Revises: c3f89c625c78
Create Date: 2026-09-22 19:43:05.075433

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '49210234f07d'
down_revision: Union[str, Sequence[str], None] = 'c3f89c625c78'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('bosses', sa.Column('name_zh', sa.String(length=200), nullable=True))
    op.add_column('bosses', sa.Column('source_name', sa.String(length=200), nullable=True))
    # Source moves to the boss level. These move columns were never written by
    # the seed sync or the API, so dropping them loses no data.
    op.drop_column('moves', 'source_url')
    op.drop_column('moves', 'source_name')


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column('moves', sa.Column('source_name', sa.VARCHAR(length=200), autoincrement=False, nullable=True))
    op.add_column('moves', sa.Column('source_url', sa.TEXT(), autoincrement=False, nullable=True))
    op.drop_column('bosses', 'source_name')
    op.drop_column('bosses', 'name_zh')
