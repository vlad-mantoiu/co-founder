"""add state machine models: stage_configs, decision_gates, stage_events

Revision ID: c4e91a96cf27
Revises: 07386005c472
Create Date: 2026-02-16 20:30:03.253492

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c4e91a96cf27"
down_revision: str | Sequence[str] | None = "07386005c472"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create stage_configs table
    op.create_table(
        "stage_configs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("stage_number", sa.Integer(), nullable=False),
        sa.Column("milestones", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("exit_criteria", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("blocking_risks", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("suggested_focus", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id", "stage_number", name="uq_project_stage"),
    )
    op.create_index(op.f("ix_stage_configs_project_id"), "stage_configs", ["project_id"], unique=False)

    # Create decision_gates table
    op.create_table(
        "decision_gates",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("gate_type", sa.String(length=50), nullable=False),
        sa.Column("stage_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("decision", sa.String(length=50), nullable=True),
        sa.Column("decided_by", sa.String(length=50), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("context", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_decision_gates_project_id"), "decision_gates", ["project_id"], unique=False)

    # Create stage_events table
    op.create_table(
        "stage_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("correlation_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.String(length=50), nullable=False),
        sa.Column("from_stage", sa.String(length=50), nullable=True),
        sa.Column("to_stage", sa.String(length=50), nullable=True),
        sa.Column("actor", sa.String(length=50), nullable=False),
        sa.Column("detail", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_stage_events_correlation_id"), "stage_events", ["correlation_id"], unique=False)
    op.create_index(op.f("ix_stage_events_created_at"), "stage_events", ["created_at"], unique=False)
    op.create_index(op.f("ix_stage_events_project_id"), "stage_events", ["project_id"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    # Drop stage_events table
    op.drop_index(op.f("ix_stage_events_project_id"), table_name="stage_events")
    op.drop_index(op.f("ix_stage_events_created_at"), table_name="stage_events")
    op.drop_index(op.f("ix_stage_events_correlation_id"), table_name="stage_events")
    op.drop_table("stage_events")

    # Drop decision_gates table
    op.drop_index(op.f("ix_decision_gates_project_id"), table_name="decision_gates")
    op.drop_table("decision_gates")

    # Drop stage_configs table
    op.drop_index(op.f("ix_stage_configs_project_id"), table_name="stage_configs")
    op.drop_table("stage_configs")
