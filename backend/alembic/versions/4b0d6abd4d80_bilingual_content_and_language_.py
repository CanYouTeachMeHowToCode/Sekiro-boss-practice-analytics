"""bilingual content and language preference

Revision ID: 4b0d6abd4d80
Revises: 01e9ec08d5ac
Create Date: 2026-09-23 23:11:42.011448

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4b0d6abd4d80'
down_revision: Union[str, Sequence[str], None] = '01e9ec08d5ac'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: Chinese boss content and each user's interface language.

    Existing rows get NULLs; the next seed sync fills in the Chinese content.
    """
    op.add_column('boss_phases', sa.Column('name_zh', sa.String(length=100), nullable=True))
    op.add_column('bosses', sa.Column('location_zh', sa.String(length=200), nullable=True))
    op.add_column('moves', sa.Column('description_zh', sa.Text(), nullable=True))
    op.add_column('moves', sa.Column('telegraph_zh', sa.Text(), nullable=True))
    op.add_column('moves', sa.Column('counter_zh', sa.Text(), nullable=True))
    op.add_column('moves', sa.Column('common_mistakes_zh', sa.Text(), nullable=True))
    op.add_column('users', sa.Column('preferred_language', sa.String(length=5), nullable=True))
    # Autogenerate does not detect check constraints; this mirrors models.User.
    op.create_check_constraint(
        'ck_users_preferred_language', 'users', "preferred_language IS NULL OR preferred_language IN ('en', 'zh')"
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('ck_users_preferred_language', 'users', type_='check')
    op.drop_column('users', 'preferred_language')
    op.drop_column('moves', 'common_mistakes_zh')
    op.drop_column('moves', 'counter_zh')
    op.drop_column('moves', 'telegraph_zh')
    op.drop_column('moves', 'description_zh')
    op.drop_column('bosses', 'location_zh')
    op.drop_column('boss_phases', 'name_zh')
