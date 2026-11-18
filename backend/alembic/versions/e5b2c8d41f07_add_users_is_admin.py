"""add users.is_admin

V4 Milestone 4: admins may open every user's recordings and reports, read-only (owner decision, 2026-11-18). Every
existing user starts as a non-admin; scripts/set_admin.py changes it.

Revision ID: e5b2c8d41f07
Revises: a7c3e19d5b42
Create Date: 2026-11-18 08:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e5b2c8d41f07'
down_revision: Union[str, Sequence[str], None] = 'a7c3e19d5b42'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('users', sa.Column('is_admin', sa.Boolean(), server_default=sa.false(), nullable=False))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('users', 'is_admin')
