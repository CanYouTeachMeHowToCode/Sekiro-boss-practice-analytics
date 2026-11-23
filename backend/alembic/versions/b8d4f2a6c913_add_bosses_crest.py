"""add bosses.crest

V4 Milestone 4, visual style B: each boss is marked by a gold crest with one character in it instead of a picture
(no game art). The character is boss data, so later bosses need no page changes (owner, 2026-11-18); which character
each boss gets is still the owner's to decide, so every existing boss starts without one.

Revision ID: b8d4f2a6c913
Revises: e5b2c8d41f07
Create Date: 2026-11-23 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b8d4f2a6c913'
down_revision: Union[str, Sequence[str], None] = 'e5b2c8d41f07'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('bosses', sa.Column('crest', sa.String(length=1), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('bosses', 'crest')
