"""merge iaijutsu into receding tide

V3.1 rebuilt castle Genichiro's moveset from engine evidence, and the project owner decided
that Iaijutsu is the second half of Receding Tide (research/ground_truth/semantic/
genichiro_product_moveset.md). The seed no longer lists Iaijutsu, and seed sync never deletes
moves, so this migration moves its attempts to Receding Tide and then deletes it, as CLAUDE.md
section 45 requires.

Revision ID: 5bc59c89a1b6
Revises: 76532dd774e5
Create Date: 2026-10-15 23:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5bc59c89a1b6'
down_revision: Union[str, Sequence[str], None] = '76532dd774e5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


GENICHIRO = "(SELECT id FROM bosses WHERE slug = 'genichiro-ashina')"


def upgrade() -> None:
    """Upgrade data: Iaijutsu attempts point at Receding Tide, then Iaijutsu is deleted.

    Its phase links go with it (ON DELETE CASCADE). The move is deleted only once no attempt
    references it, so a database without Receding Tide keeps it. A fresh database has neither
    move yet (the seed is synced after the migrations), and nothing happens.
    """
    op.execute(
        f"""
        UPDATE attempts SET failure_move_id = r.id
        FROM moves i, moves r
        WHERE attempts.failure_move_id = i.id
          AND i.boss_id = {GENICHIRO} AND i.slug = 'iaijutsu'
          AND r.boss_id = {GENICHIRO} AND r.slug = 'receding-tide'
        """
    )
    op.execute(
        f"""
        DELETE FROM moves
        WHERE boss_id = {GENICHIRO} AND slug = 'iaijutsu'
          AND NOT EXISTS (SELECT 1 FROM attempts WHERE attempts.failure_move_id = moves.id)
        """
    )


def downgrade() -> None:
    """Downgrade data: nothing to undo.

    The moved attempts cannot be told apart from Receding Tide ones, so they stay there. The
    older seed re-creates Iaijutsu on its next sync.
    """
