"""add move chinese names

Revision ID: 01e9ec08d5ac
Revises: 30b90438d428
Create Date: 2026-09-23 22:26:38.514977

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '01e9ec08d5ac'
down_revision: Union[str, Sequence[str], None] = '30b90438d428'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: Chinese move names, from a Chinese wiki or marked as translations.

    Existing rows get NULLs, which satisfy the checks; the next seed sync fills them in.
    """
    op.add_column('moves', sa.Column('name_zh', sa.String(length=200), nullable=True))
    op.add_column('moves', sa.Column('name_zh_source', sa.String(length=20), nullable=True))
    op.add_column('moves', sa.Column('name_zh_source_url', sa.Text(), nullable=True))
    # Autogenerate does not detect check constraints; these mirror models.Move.
    op.create_check_constraint(
        'ck_moves_name_zh_source', 'moves', "name_zh_source IS NULL OR name_zh_source IN ('wiki', 'translation')"
    )
    op.create_check_constraint('ck_moves_name_zh_has_source', 'moves', '(name_zh IS NULL) = (name_zh_source IS NULL)')
    op.create_check_constraint(
        'ck_moves_name_zh_source_url', 'moves', "(name_zh_source = 'wiki') = (name_zh_source_url IS NOT NULL)"
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('ck_moves_name_zh_source_url', 'moves', type_='check')
    op.drop_constraint('ck_moves_name_zh_has_source', 'moves', type_='check')
    op.drop_constraint('ck_moves_name_zh_source', 'moves', type_='check')
    op.drop_column('moves', 'name_zh_source_url')
    op.drop_column('moves', 'name_zh_source')
    op.drop_column('moves', 'name_zh')
