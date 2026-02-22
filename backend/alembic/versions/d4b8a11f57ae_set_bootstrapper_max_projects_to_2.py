"""set bootstrapper max_projects to 2

Revision ID: d4b8a11f57ae
Revises: 892d2f2ce669
Create Date: 2026-02-20 11:45:00.000000

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d4b8a11f57ae"
down_revision: str | Sequence[str] | None = "892d2f2ce669"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("UPDATE plan_tiers SET max_projects = 2 WHERE slug = 'bootstrapper'")


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("UPDATE plan_tiers SET max_projects = 3 WHERE slug = 'bootstrapper'")
