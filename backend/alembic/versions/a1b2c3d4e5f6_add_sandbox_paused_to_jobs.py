"""add sandbox_paused to jobs

Revision ID: a1b2c3d4e5f6
Revises: d4b8a11f57ae
Create Date: 2026-02-22 09:13:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: str | Sequence[str] | None = "d4b8a11f57ae"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add sandbox_paused column to jobs table."""
    op.add_column(
        "jobs",
        sa.Column("sandbox_paused", sa.Boolean(), nullable=False, server_default="false"),
    )


def downgrade() -> None:
    """Remove sandbox_paused column from jobs table."""
    op.drop_column("jobs", "sandbox_paused")
