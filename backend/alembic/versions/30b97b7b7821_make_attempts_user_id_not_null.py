"""make attempts user_id not null

V3 kept attempts recorded before accounts existed ownerless, hidden from everyone, until they
were claimed. Every attempt now has an owner.

Revision ID: 30b97b7b7821
Revises: 5bc59c89a1b6
Create Date: 2026-10-15 23:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '30b97b7b7821'
down_revision: Union[str, Sequence[str], None] = '5bc59c89a1b6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: attempts.user_id becomes NOT NULL.

    Fails, and changes nothing, while any attempt has no owner: claim them first. No attempt is
    deleted or assigned to anyone automatically.
    """
    ownerless = op.get_bind().scalar(sa.text("SELECT count(*) FROM attempts WHERE user_id IS NULL"))
    if ownerless:
        raise RuntimeError(
            f"{ownerless} attempt(s) have no owner. Assign them to an account first with "
            "`python -m scripts.claim_attempts <username>` (with Docker Compose: "
            "`docker compose run --rm backend python -m scripts.claim_attempts <username>`), then upgrade again."
        )
    op.alter_column('attempts', 'user_id', existing_type=sa.Integer(), nullable=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column('attempts', 'user_id', existing_type=sa.Integer(), nullable=True)
