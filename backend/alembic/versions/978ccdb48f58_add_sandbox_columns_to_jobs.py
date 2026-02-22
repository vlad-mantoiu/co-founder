"""add sandbox columns to jobs

Revision ID: 978ccdb48f58
Revises: 1cbc4ccfd46b
Create Date: 2026-02-17 18:15:06.064733

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "978ccdb48f58"
down_revision: str | Sequence[str] | None = "1cbc4ccfd46b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add sandbox build result columns to jobs table."""
    op.add_column("jobs", sa.Column("sandbox_id", sa.String(length=255), nullable=True))
    op.add_column("jobs", sa.Column("preview_url", sa.Text(), nullable=True))
    op.add_column("jobs", sa.Column("build_version", sa.String(length=50), nullable=True))
    op.add_column("jobs", sa.Column("workspace_path", sa.String(length=500), nullable=True))


def downgrade() -> None:
    """Remove sandbox build result columns from jobs table."""
    op.drop_column("jobs", "workspace_path")
    op.drop_column("jobs", "build_version")
    op.drop_column("jobs", "preview_url")
    op.drop_column("jobs", "sandbox_id")
