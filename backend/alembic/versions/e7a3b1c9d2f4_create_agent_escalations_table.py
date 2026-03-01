"""create agent_escalations table

Revision ID: e7a3b1c9d2f4
Revises: f3c9a72b1d08
Create Date: 2026-03-01 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e7a3b1c9d2f4"
down_revision: str | Sequence[str] | None = "f3c9a72b1d08"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create agent_escalations table for the self-healing error model (Phase 45)."""
    op.create_table(
        "agent_escalations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", sa.String(length=255), nullable=False),
        sa.Column("job_id", sa.String(length=255), nullable=False),
        sa.Column("project_id", sa.String(length=255), nullable=False),
        sa.Column("error_type", sa.String(length=255), nullable=False),
        sa.Column("error_signature", sa.String(length=255), nullable=False),
        sa.Column("plain_english_problem", sa.Text(), nullable=False),
        sa.Column("attempts_summary", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[]"),
        sa.Column("recommended_action", sa.Text(), nullable=False),
        sa.Column("options", postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default="[]"),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="pending"),
        sa.Column("founder_decision", sa.String(length=255), nullable=True),
        sa.Column("founder_guidance", sa.Text(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_agent_escalations_session_id"), "agent_escalations", ["session_id"], unique=False)
    op.create_index(op.f("ix_agent_escalations_job_id"), "agent_escalations", ["job_id"], unique=False)
    op.create_index(op.f("ix_agent_escalations_project_id"), "agent_escalations", ["project_id"], unique=False)
    op.create_index(
        op.f("ix_agent_escalations_error_signature"), "agent_escalations", ["error_signature"], unique=False
    )


def downgrade() -> None:
    """Drop agent_escalations table."""
    op.drop_index(op.f("ix_agent_escalations_error_signature"), table_name="agent_escalations")
    op.drop_index(op.f("ix_agent_escalations_project_id"), table_name="agent_escalations")
    op.drop_index(op.f("ix_agent_escalations_job_id"), table_name="agent_escalations")
    op.drop_index(op.f("ix_agent_escalations_session_id"), table_name="agent_escalations")
    op.drop_table("agent_escalations")
