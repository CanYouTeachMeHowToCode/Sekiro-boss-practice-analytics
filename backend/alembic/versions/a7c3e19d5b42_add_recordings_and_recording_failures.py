"""add recordings and recording_failures

V4 Milestone 3: fight recordings users upload, and the failures the pipeline finds in them. The videos stay on disk;
only their metadata and paths are stored.

Revision ID: a7c3e19d5b42
Revises: 30b97b7b7821
Create Date: 2026-10-25 20:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a7c3e19d5b42'
down_revision: Union[str, Sequence[str], None] = '30b97b7b7821'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'recordings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('boss_id', sa.Integer(), nullable=False),
        sa.Column('original_filename', sa.String(length=255), nullable=False),
        sa.Column('storage_path', sa.Text(), nullable=False),
        sa.Column('size_bytes', sa.BigInteger(), nullable=False),
        sa.Column('sha256', sa.String(length=64), nullable=False),
        sa.Column('status', sa.String(length=20), server_default='uploaded', nullable=False),
        sa.Column('reject_code', sa.String(length=40), nullable=True),
        sa.Column('progress', sa.Float(), server_default='0', nullable=False),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('duration_s', sa.Float(), nullable=True),
        sa.Column('width', sa.Integer(), nullable=True),
        sa.Column('height', sa.Integer(), nullable=True),
        sa.Column('fps', sa.Float(), nullable=True),
        sa.Column('pipeline_version', sa.String(length=40), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('uploaded', 'checking', 'rejected', 'queued', 'processing', 'done', 'failed')",
            name='ck_recordings_status',
        ),
        sa.CheckConstraint('progress >= 0 AND progress <= 1', name='ck_recordings_progress'),
        sa.CheckConstraint(
            "status = 'rejected' OR reject_code IS NULL", name='ck_recordings_reject_code_only_if_rejected'
        ),
        sa.ForeignKeyConstraint(['boss_id'], ['bosses.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_recordings_status', 'recordings', ['status'], unique=False)
    op.create_index('ix_recordings_user_id_created_at', 'recordings', ['user_id', 'created_at'], unique=False)
    op.create_table(
        'recording_failures',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('recording_id', sa.Integer(), nullable=False),
        sa.Column('time_s', sa.Float(), nullable=False),
        sa.Column('type', sa.String(length=20), nullable=False),
        sa.Column('phase', sa.Integer(), nullable=False),
        sa.Column('sure', sa.Boolean(), nullable=False),
        sa.Column('move_id', sa.Integer(), nullable=True),
        sa.Column('candidates', sa.JSON(), nullable=False),
        sa.Column('events', sa.JSON(), nullable=False),
        sa.Column('clip_path', sa.Text(), nullable=True),
        sa.CheckConstraint("type IN ('damage', 'posture_break', 'death')", name='ck_recording_failures_type'),
        sa.CheckConstraint('sure OR move_id IS NULL', name='ck_recording_failures_move_only_if_sure'),
        sa.ForeignKeyConstraint(['move_id'], ['moves.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['recording_id'], ['recordings.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_recording_failures_recording_id'), 'recording_failures', ['recording_id'], unique=False
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_recording_failures_recording_id'), table_name='recording_failures')
    op.drop_table('recording_failures')
    op.drop_index('ix_recordings_user_id_created_at', table_name='recordings')
    op.drop_index('ix_recordings_status', table_name='recordings')
    op.drop_table('recordings')
