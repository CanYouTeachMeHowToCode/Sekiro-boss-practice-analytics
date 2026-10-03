"""add move source

Revision ID: 6849ddf003e3
Revises: 4b0d6abd4d80
Create Date: 2026-10-03 02:32:35.605013

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6849ddf003e3'
down_revision: Union[str, Sequence[str], None] = '4b0d6abd4d80'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: an optional per-move source, for a move whose data comes from a
    different page than its boss's. Null means the move uses the boss's source.
    """
    op.add_column('moves', sa.Column('source_name', sa.String(length=200), nullable=True))
    op.add_column('moves', sa.Column('source_url', sa.Text(), nullable=True))
    # Autogenerate does not detect check constraints; this mirrors models.Move.
    op.create_check_constraint('ck_moves_source_complete', 'moves', '(source_name IS NULL) = (source_url IS NULL)')


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('ck_moves_source_complete', 'moves', type_='check')
    op.drop_column('moves', 'source_url')
    op.drop_column('moves', 'source_name')
