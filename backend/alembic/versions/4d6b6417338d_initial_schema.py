"""initial schema

Revision ID: 4d6b6417338d
Revises: 
Create Date: 2026-09-22 17:02:54.689205

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4d6b6417338d'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('games',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('slug', sa.String(length=100), nullable=False),
    sa.Column('name', sa.String(length=200), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('slug')
    )
    op.create_table('bosses',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('game_id', sa.Integer(), nullable=False),
    sa.Column('slug', sa.String(length=100), nullable=False),
    sa.Column('name', sa.String(length=200), nullable=False),
    sa.Column('location', sa.String(length=200), nullable=False),
    sa.Column('source_url', sa.Text(), nullable=True),
    sa.ForeignKeyConstraint(['game_id'], ['games.id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('slug')
    )
    op.create_table('boss_phases',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('boss_id', sa.Integer(), nullable=False),
    sa.Column('phase_number', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=100), nullable=False),
    sa.ForeignKeyConstraint(['boss_id'], ['bosses.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('boss_id', 'phase_number')
    )
    op.create_table('moves',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('boss_id', sa.Integer(), nullable=False),
    sa.Column('slug', sa.String(length=100), nullable=False),
    sa.Column('name', sa.String(length=200), nullable=False),
    sa.Column('move_type', sa.String(length=50), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('telegraph', sa.Text(), nullable=True),
    sa.Column('counter', sa.Text(), nullable=True),
    sa.Column('common_mistakes', sa.Text(), nullable=True),
    sa.Column('source_name', sa.String(length=200), nullable=True),
    sa.Column('source_url', sa.Text(), nullable=True),
    sa.ForeignKeyConstraint(['boss_id'], ['bosses.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('boss_id', 'slug')
    )
    op.create_table('attempts',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('boss_id', sa.Integer(), nullable=False),
    sa.Column('result', sa.String(length=20), nullable=False),
    sa.Column('phase_reached', sa.Integer(), nullable=False),
    sa.Column('failure_move_id', sa.Integer(), nullable=True),
    sa.Column('failure_category', sa.String(length=20), nullable=True),
    sa.Column('notes', sa.Text(), server_default='', nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("failure_category IS NULL OR failure_category IN ('other', 'not_sure')", name='ck_attempts_failure_category'),
    sa.CheckConstraint("result = 'failed' OR (failure_move_id IS NULL AND failure_category IS NULL)", name='ck_attempts_victory_has_no_failure'),
    sa.CheckConstraint("result IN ('failed', 'victory')", name='ck_attempts_result'),
    sa.CheckConstraint('failure_move_id IS NULL OR failure_category IS NULL', name='ck_attempts_single_failure_cause'),
    sa.ForeignKeyConstraint(['boss_id'], ['bosses.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['failure_move_id'], ['moves.id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_attempts_boss_id'), 'attempts', ['boss_id'], unique=False)
    op.create_table('phase_moves',
    sa.Column('boss_phase_id', sa.Integer(), nullable=False),
    sa.Column('move_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['boss_phase_id'], ['boss_phases.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['move_id'], ['moves.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('boss_phase_id', 'move_id')
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('phase_moves')
    op.drop_index(op.f('ix_attempts_boss_id'), table_name='attempts')
    op.drop_table('attempts')
    op.drop_table('moves')
    op.drop_table('boss_phases')
    op.drop_table('bosses')
    op.drop_table('games')
