"""Unit tests for AgentCheckpoint, AgentSession, and UserSettings ORM model shapes.

These tests verify model instantiation, default values, and table names.
No database connection is needed — SQLAlchemy models are pure Python objects.
"""

from app.db.models.agent_checkpoint import AgentCheckpoint
from app.db.models.agent_session import AgentSession
from app.db.models.user_settings import UserSettings


class TestAgentCheckpointDefaults:
    def test_agent_checkpoint_defaults(self) -> None:
        """AgentCheckpoint instantiates with correct defaults for all optional fields."""
        checkpoint = AgentCheckpoint(session_id="sess-abc", job_id="job-123")

        assert checkpoint.session_id == "sess-abc"
        assert checkpoint.job_id == "job-123"
        # Default values from Column(default=...)
        assert checkpoint.message_history == []
        assert checkpoint.retry_counts == {}
        assert checkpoint.session_cost_microdollars == 0
        assert checkpoint.daily_budget_microdollars == 0
        assert checkpoint.iteration_number == 0
        assert checkpoint.agent_state == "working"
        # Nullable fields default to None
        assert checkpoint.sandbox_id is None
        assert checkpoint.current_phase is None

    def test_agent_checkpoint_tablename(self) -> None:
        """AgentCheckpoint maps to the agent_checkpoints table."""
        assert AgentCheckpoint.__tablename__ == "agent_checkpoints"

    def test_agent_checkpoint_all_fields(self) -> None:
        """AgentCheckpoint accepts all field values without error."""
        checkpoint = AgentCheckpoint(
            session_id="sess-xyz",
            job_id="job-456",
            message_history=[{"role": "user", "content": "hello"}],
            sandbox_id="sbx-001",
            current_phase="implement",
            retry_counts={"job-456:bash_error:abc123": 2},
            session_cost_microdollars=150_000,
            daily_budget_microdollars=5_000_000,
            iteration_number=7,
            agent_state="sleeping",
        )

        assert checkpoint.sandbox_id == "sbx-001"
        assert checkpoint.current_phase == "implement"
        assert checkpoint.session_cost_microdollars == 150_000
        assert checkpoint.iteration_number == 7
        assert checkpoint.agent_state == "sleeping"


class TestAgentSessionDefaults:
    def test_agent_session_defaults(self) -> None:
        """AgentSession instantiates with correct defaults for status and cost fields."""
        session = AgentSession(
            id="sess-uuid-001",
            job_id="job-789",
            clerk_user_id="user_clerk_abc",
            tier="bootstrapper",
            model_used="claude-sonnet-4-6",
        )

        assert session.id == "sess-uuid-001"
        assert session.job_id == "job-789"
        assert session.clerk_user_id == "user_clerk_abc"
        assert session.tier == "bootstrapper"
        assert session.model_used == "claude-sonnet-4-6"
        assert session.status == "working"
        assert session.cumulative_cost_microdollars == 0
        assert session.daily_budget_microdollars == 0
        assert session.last_checkpoint_at is None
        assert session.completed_at is None

    def test_agent_session_tablename(self) -> None:
        """AgentSession maps to the agent_sessions table."""
        assert AgentSession.__tablename__ == "agent_sessions"

    def test_agent_session_tier_values(self) -> None:
        """AgentSession accepts all valid tier values."""
        for tier in ("bootstrapper", "partner", "cto_scale"):
            session = AgentSession(
                id=f"sess-{tier}",
                job_id="job-001",
                clerk_user_id="user_abc",
                tier=tier,
                model_used="claude-sonnet-4-6",
            )
            assert session.tier == tier


class TestUserSettingsRenewalDate:
    def test_user_settings_has_renewal_date(self) -> None:
        """UserSettings ORM model has a subscription_renewal_date attribute."""
        assert hasattr(UserSettings, "subscription_renewal_date")

    def test_user_settings_renewal_date_is_nullable(self) -> None:
        """subscription_renewal_date column is nullable (existing users have no renewal date yet)."""
        col = UserSettings.__table__.c.subscription_renewal_date
        assert col.nullable is True
