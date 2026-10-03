"""shift isshin attempts for way of tomoe phase

The Isshin, the Sword Saint fight starts with Genichiro, Way of Tomoe. The seed data
now records that as phase 1, so Isshin's own phases move from 1-3 to 2-4. Existing
attempts keep pointing at the same part of the fight by moving up one phase.

Revision ID: 76532dd774e5
Revises: 6849ddf003e3
Create Date: 2026-10-03 02:32:51.211107

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '76532dd774e5'
down_revision: Union[str, Sequence[str], None] = '6849ddf003e3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


ISSHIN = "(SELECT id FROM bosses WHERE slug = 'isshin-sword-saint')"


def upgrade() -> None:
    """Upgrade data: Isshin attempts move up one phase."""
    op.execute(f"UPDATE attempts SET phase_reached = phase_reached + 1 WHERE boss_id = {ISSHIN}")


def downgrade() -> None:
    """Downgrade data: attempts in the Way of Tomoe phase have no older equivalent; keep them at phase 1."""
    op.execute(f"UPDATE attempts SET phase_reached = GREATEST(phase_reached - 1, 1) WHERE boss_id = {ISSHIN}")
