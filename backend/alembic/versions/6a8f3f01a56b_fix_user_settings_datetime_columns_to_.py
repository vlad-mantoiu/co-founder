"""fix user_settings datetime columns to use timezone

Revision ID: 6a8f3f01a56b
Revises: 593f7ce4330a
Create Date: 2026-02-16 21:20:14.109725

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '6a8f3f01a56b'
down_revision: str | Sequence[str] | None = '593f7ce4330a'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Alter datetime columns to use TIMESTAMP WITH TIME ZONE
    op.alter_column('user_settings', 'created_at',
                    type_=sa.DateTime(timezone=True),
                    existing_type=sa.DateTime(),
                    existing_nullable=False)
    op.alter_column('user_settings', 'updated_at',
                    type_=sa.DateTime(timezone=True),
                    existing_type=sa.DateTime(),
                    existing_nullable=False)


def downgrade() -> None:
    """Downgrade schema."""
    # Revert datetime columns to TIMESTAMP WITHOUT TIME ZONE
    op.alter_column('user_settings', 'created_at',
                    type_=sa.DateTime(),
                    existing_type=sa.DateTime(timezone=True),
                    existing_nullable=False)
    op.alter_column('user_settings', 'updated_at',
                    type_=sa.DateTime(),
                    existing_type=sa.DateTime(timezone=True),
                    existing_nullable=False)
