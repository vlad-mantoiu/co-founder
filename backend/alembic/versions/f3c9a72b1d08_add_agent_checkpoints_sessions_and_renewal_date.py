"""add agent_checkpoints, agent_sessions, and subscription_renewal_date

Revision ID: f3c9a72b1d08
Revises: a1b2c3d4e5f6
Create Date: 2026-02-26 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f3c9a72b1d08"
down_revision: str | Sequence[str] | None = "a1b2c3d4e5f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create agent_checkpoints table
    op.create_table(
        "agent_checkpoints",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("session_id", sa.String(length=255), nullable=False),
        sa.Column("job_id", sa.String(length=255), nullable=False),
        sa.Column("message_history", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("sandbox_id", sa.String(length=255), nullable=True),
        sa.Column("current_phase", sa.String(length=255), nullable=True),
        sa.Column("retry_counts", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("session_cost_microdollars", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("daily_budget_microdollars", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("iteration_number", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("agent_state", sa.String(length=50), nullable=False, server_default="working"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_agent_checkpoints_session_id"), "agent_checkpoints", ["session_id"], unique=False)
    op.create_index(op.f("ix_agent_checkpoints_job_id"), "agent_checkpoints", ["job_id"], unique=False)

    # Create agent_sessions table
    op.create_table(
        "agent_sessions",
        sa.Column("id", sa.String(length=255), nullable=False),
        sa.Column("job_id", sa.String(length=255), nullable=False),
        sa.Column("clerk_user_id", sa.String(length=255), nullable=False),
        sa.Column("tier", sa.String(length=50), nullable=False),
        sa.Column("model_used", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="working"),
        sa.Column("cumulative_cost_microdollars", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("daily_budget_microdollars", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("last_checkpoint_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_agent_sessions_job_id"), "agent_sessions", ["job_id"], unique=False)
    op.create_index(op.f("ix_agent_sessions_clerk_user_id"), "agent_sessions", ["clerk_user_id"], unique=False)

    # Add subscription_renewal_date to user_settings
    op.add_column(
        "user_settings",
        sa.Column("subscription_renewal_date", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("user_settings", "subscription_renewal_date")
    op.drop_index(op.f("ix_agent_sessions_clerk_user_id"), table_name="agent_sessions")
    op.drop_index(op.f("ix_agent_sessions_job_id"), table_name="agent_sessions")
    op.drop_table("agent_sessions")
    op.drop_index(op.f("ix_agent_checkpoints_job_id"), table_name="agent_checkpoints")
    op.drop_index(op.f("ix_agent_checkpoints_session_id"), table_name="agent_checkpoints")
    op.drop_table("agent_checkpoints")
