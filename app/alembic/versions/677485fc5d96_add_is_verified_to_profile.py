"""add is_verified to profile

Revision ID: 677485fc5d96
Revises: c5a1c8662497
Create Date: 2026-07-16 12:09:34.760205

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '677485fc5d96'
down_revision: Union[str, Sequence[str], None] = 'c5a1c8662497'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('profiles', sa.Column('is_verified', sa.Boolean(), server_default=sa.text('false'), nullable=False))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('profiles', 'is_verified')
