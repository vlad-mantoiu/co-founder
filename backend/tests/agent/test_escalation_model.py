"""Unit tests for AgentEscalation ORM model.

Verifies model instantiation, default values, field names, and SSE event type constants.
No database connection required — SQLAlchemy models are pure Python objects.
"""

from app.db.models.agent_escalation import AgentEscalation
from app.queue.state_machine import SSEEventType


class TestAgentEscalationDefaults:
    def test_agent_escalation_defaults(self) -> None:
        """AgentEscalation instantiates with correct defaults for status, attempts_summary, and options."""
        escalation = AgentEscalation(
            session_id="sess-abc",
            job_id="job-123",
            project_id="proj-xyz",
            error_type="bash_error",
            error_signature="proj-xyz:bash_error:abc123",
            plain_english_problem="The npm install command failed with a permission error.",
            recommended_action="Try running with sudo or fix permissions.",
        )

        assert escalation.session_id == "sess-abc"
        assert escalation.job_id == "job-123"
        assert escalation.project_id == "proj-xyz"
        assert escalation.error_type == "bash_error"
        assert escalation.error_signature == "proj-xyz:bash_error:abc123"
        # Default values set via __init__ setdefault
        assert escalation.status == "pending"
        assert escalation.attempts_summary == []
        assert escalation.options == []
        # Nullable fields default to None
        assert escalation.founder_decision is None
        assert escalation.founder_guidance is None
        assert escalation.resolved_at is None

    def test_agent_escalation_tablename(self) -> None:
        """AgentEscalation maps to the agent_escalations table."""
        assert AgentEscalation.__tablename__ == "agent_escalations"

    def test_agent_escalation_required_fields(self) -> None:
        """AgentEscalation accepts all required fields without error."""
        escalation = AgentEscalation(
            session_id="sess-001",
            job_id="job-456",
            project_id="proj-789",
            error_type="import_error",
            error_signature="proj-789:import_error:deadbeef",
            plain_english_problem="Python cannot find the 'requests' module.",
            recommended_action="Install 'requests' package using pip.",
            attempts_summary=[
                "Attempt 1: Tried running pip install — got a network timeout.",
                "Attempt 2: Tried offline install — package not cached.",
            ],
            options=[
                {"value": "retry", "label": "Retry", "description": "Try again with a different approach."},
                {"value": "skip", "label": "Skip", "description": "Skip this step and continue."},
                {
                    "value": "provide_guidance",
                    "label": "Provide guidance",
                    "description": "Give the agent specific instructions.",
                },
            ],
        )

        assert escalation.session_id == "sess-001"
        assert escalation.project_id == "proj-789"
        assert escalation.error_type == "import_error"
        assert len(escalation.attempts_summary) == 2
        assert len(escalation.options) == 3
        assert escalation.status == "pending"

    def test_agent_escalation_resolved_fields(self) -> None:
        """AgentEscalation stores founder_decision and founder_guidance correctly."""
        from datetime import UTC, datetime

        resolved_at = datetime.now(UTC)
        escalation = AgentEscalation(
            session_id="sess-resolved",
            job_id="job-resolved",
            project_id="proj-resolved",
            error_type="test_failure",
            error_signature="proj-resolved:test_failure:cafebabe",
            plain_english_problem="Unit test suite is failing.",
            recommended_action="Fix or skip failing tests.",
            status="resolved",
            founder_decision="provide_guidance",
            founder_guidance="Run tests with --ignore=tests/integration to skip slow tests.",
            resolved_at=resolved_at,
        )

        assert escalation.status == "resolved"
        assert escalation.founder_decision == "provide_guidance"
        assert escalation.founder_guidance == "Run tests with --ignore=tests/integration to skip slow tests."
        assert escalation.resolved_at == resolved_at


class TestAgentEscalationImport:
    def test_agent_escalation_import_from_models(self) -> None:
        """AgentEscalation is importable via app.db.models public API."""
        from app.db.models import AgentEscalation as ImportedEscalation

        assert ImportedEscalation is AgentEscalation

    def test_agent_escalation_in_all(self) -> None:
        """AgentEscalation is listed in app.db.models.__all__."""
        import app.db.models as models_module

        assert "AgentEscalation" in models_module.__all__


class TestSSEEventTypes:
    def test_sse_event_type_agent_waiting_for_input_exists(self) -> None:
        """SSEEventType has AGENT_WAITING_FOR_INPUT constant."""
        assert hasattr(SSEEventType, "AGENT_WAITING_FOR_INPUT")
        assert SSEEventType.AGENT_WAITING_FOR_INPUT == "agent.waiting_for_input"

    def test_sse_event_type_agent_retrying_exists(self) -> None:
        """SSEEventType has AGENT_RETRYING constant."""
        assert hasattr(SSEEventType, "AGENT_RETRYING")
        assert SSEEventType.AGENT_RETRYING == "agent.retrying"

    def test_sse_event_type_agent_escalation_resolved_exists(self) -> None:
        """SSEEventType has AGENT_ESCALATION_RESOLVED constant."""
        assert hasattr(SSEEventType, "AGENT_ESCALATION_RESOLVED")
        assert SSEEventType.AGENT_ESCALATION_RESOLVED == "agent.escalation_resolved"

    def test_sse_event_type_agent_build_paused_exists(self) -> None:
        """SSEEventType has AGENT_BUILD_PAUSED constant."""
        assert hasattr(SSEEventType, "AGENT_BUILD_PAUSED")
        assert SSEEventType.AGENT_BUILD_PAUSED == "agent.build_paused"

    def test_all_four_new_sse_constants_exist(self) -> None:
        """All 4 Phase 45 SSE event type constants exist and have correct values."""
        expected = {
            "AGENT_WAITING_FOR_INPUT": "agent.waiting_for_input",
            "AGENT_RETRYING": "agent.retrying",
            "AGENT_ESCALATION_RESOLVED": "agent.escalation_resolved",
            "AGENT_BUILD_PAUSED": "agent.build_paused",
        }
        for attr, value in expected.items():
            assert hasattr(SSEEventType, attr), f"SSEEventType missing {attr}"
            assert getattr(SSEEventType, attr) == value, f"SSEEventType.{attr} has wrong value"
