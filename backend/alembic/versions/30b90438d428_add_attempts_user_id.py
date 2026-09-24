"""add attempts user_id

Revision ID: 30b90438d428
Revises: 980c7a879ddb
Create Date: 2026-09-23 20:30:36.048915

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '30b90438d428'
down_revision: Union[str, Sequence[str], None] = '980c7a879ddb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema.

    user_id is nullable: attempts recorded before accounts existed stay
    ownerless, and hidden from everyone, until they are assigned explicitly
    with `python -m scripts.claim_attempts <username>`. No rows are deleted.
    """
    op.add_column('attempts', sa.Column('user_id', sa.Integer(), nullable=True))
    op.create_index('ix_attempts_user_id_boss_id', 'attempts', ['user_id', 'boss_id'], unique=False)
    op.create_foreign_key('attempts_user_id_fkey', 'attempts', 'users', ['user_id'], ['id'], ondelete='RESTRICT')


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('attempts_user_id_fkey', 'attempts', type_='foreignkey')
    op.drop_index('ix_attempts_user_id_boss_id', table_name='attempts')
    op.drop_column('attempts', 'user_id')
