"""add workspace auth profile columns to user_settings

Revision ID: 593f7ce4330a
Revises: c4e91a96cf27
Create Date: 2026-02-16 21:16:31.797515

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "593f7ce4330a"
down_revision: str | Sequence[str] | None = "c4e91a96cf27"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add profile and feature flag columns to user_settings
    op.add_column("user_settings", sa.Column("email", sa.String(length=255), nullable=True))
    op.add_column("user_settings", sa.Column("name", sa.String(length=255), nullable=True))
    op.add_column("user_settings", sa.Column("avatar_url", sa.String(length=500), nullable=True))
    op.add_column("user_settings", sa.Column("company_name", sa.String(length=255), nullable=True))
    op.add_column("user_settings", sa.Column("role", sa.String(length=100), nullable=True))
    op.add_column("user_settings", sa.Column("timezone", sa.String(length=100), nullable=True, server_default="UTC"))
    op.add_column(
        "user_settings", sa.Column("onboarding_completed", sa.Boolean(), nullable=False, server_default="false")
    )
    op.add_column("user_settings", sa.Column("beta_features", postgresql.JSONB(astext_type=sa.Text()), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    # Drop profile and feature flag columns from user_settings
    op.drop_column("user_settings", "beta_features")
    op.drop_column("user_settings", "onboarding_completed")
    op.drop_column("user_settings", "timezone")
    op.drop_column("user_settings", "role")
    op.drop_column("user_settings", "company_name")
    op.drop_column("user_settings", "avatar_url")
    op.drop_column("user_settings", "name")
    op.drop_column("user_settings", "email")
