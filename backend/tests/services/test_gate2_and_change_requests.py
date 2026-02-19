"""Tests for Gate 2 (solidification) and ChangeRequestService.

TDD coverage:
1. test_gate2_created_with_solidification_type — Gate 2 options are GATE_2_OPTIONS
2. test_gate2_resolution_includes_alignment — Resolve with 'iterate' stores alignment_score + scope_creep_detected
3. test_create_change_request_creates_artifact — Artifact created with artifact_type="change_request_1"
4. test_change_request_references_build_version — content includes references_build_version
5. test_change_request_includes_iteration_depth — content has iteration_number and tier_limit (ITER-01, ITER-02)
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.schemas.decision_gates import GATE_2_OPTIONS

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_project(clerk_user_id: str = "user-001", project_id: str | None = None) -> MagicMock:
    """Return a fake Project ORM object."""
    project = MagicMock()
    project.id = uuid.UUID(project_id) if project_id else uuid.uuid4()
    project.clerk_user_id = clerk_user_id
    project.name = "Test Project"
    project.stage_number = 2
    return project


def _make_gate(gate_type: str = "solidification") -> MagicMock:
    """Return a fake DecisionGate ORM object."""
    gate = MagicMock()
    gate.id = uuid.uuid4()
    gate.gate_type = gate_type
    gate.status = "pending"
    gate.decision = None
    gate.decided_at = None
    gate.context = {}
    return gate


def _make_artifact(artifact_type: str, content: dict | None = None) -> MagicMock:
    """Return a fake Artifact ORM object."""
    artifact = MagicMock()
    artifact.id = uuid.uuid4()
    artifact.artifact_type = artifact_type
    artifact.current_content = content or {}
    return artifact


def _make_job(build_version: str = "build_v0_1", tier: str = "bootstrapper") -> MagicMock:
    """Return a fake Job ORM object."""
    job = MagicMock()
    job.id = uuid.uuid4()
    job.build_version = build_version
    job.tier = tier
    job.status = "ready"
    return job


def _mock_session_factory(scalar_results: list):
    """Build a mock session factory that returns scalars in order.

    scalar_results: list of values to return for each successive execute() call.
    Each value may be a single object (scalar_one_or_none) or a list (scalars().all()).
    """
    call_count = [0]

    mock_session = AsyncMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)
    mock_session.add = MagicMock()
    mock_session.commit = AsyncMock()
    mock_session.refresh = AsyncMock()

    async def fake_execute(_query):
        idx = call_count[0]
        call_count[0] += 1
        result_value = scalar_results[idx] if idx < len(scalar_results) else None

        mock_result = MagicMock()
        if isinstance(result_value, list):
            # Return as scalars().all()
            mock_scalars = MagicMock()
            mock_scalars.all = MagicMock(return_value=result_value)
            mock_result.scalars = MagicMock(return_value=mock_scalars)
            mock_result.scalar_one_or_none = MagicMock(return_value=None)
        else:
            mock_result.scalar_one_or_none = MagicMock(return_value=result_value)
            mock_scalars = MagicMock()
            mock_scalars.all = MagicMock(return_value=[])
            mock_result.scalars = MagicMock(return_value=mock_scalars)
        return mock_result

    mock_session.execute = fake_execute

    mock_factory = MagicMock()
    mock_factory.return_value = mock_session
    return mock_factory


# ---------------------------------------------------------------------------
# Test 1: Gate 2 created with solidification type returns GATE_2_OPTIONS
# ---------------------------------------------------------------------------


async def test_gate2_created_with_solidification_type():
    """When create_gate() is called with gate_type='solidification', options are GATE_2_OPTIONS."""
    from app.agent.runner_fake import RunnerFake
    from app.services.gate_service import GateService

    project_id_str = "00000000-0000-0000-0000-000000000001"
    project = _make_project(project_id=project_id_str)
    gate_id = uuid.uuid4()

    # execute() calls: (1) project ownership, (2) existing pending gate check, (3) idea_brief artifact
    mock_factory = _mock_session_factory([project, None, None])

    # JourneyService.create_gate mock
    with patch("app.services.gate_service.JourneyService") as mock_journey_cls:
        mock_journey = AsyncMock()
        mock_journey.create_gate = AsyncMock(return_value=gate_id)
        mock_journey_cls.return_value = mock_journey

        runner = RunnerFake()
        service = GateService(runner, mock_factory)
        response = await service.create_gate(
            clerk_user_id="user-001",
            project_id=project_id_str,
            gate_type="solidification",
        )

    assert response.gate_type == "solidification"
    assert response.status == "pending"
    # Options must be the Gate 2 options
    assert len(response.options) == 3
    option_values = [o.value for o in response.options]
    assert option_values == ["iterate", "ship", "park"]
    # Verify it is exactly GATE_2_OPTIONS
    assert response.options == GATE_2_OPTIONS


# ---------------------------------------------------------------------------
# Test 2: Gate 2 resolution stores alignment_score + scope_creep_detected
# ---------------------------------------------------------------------------


async def test_gate2_resolution_includes_alignment():
    """resolve_gate() with gate_type='solidification' and decision='iterate' stores alignment in context."""
    from app.agent.runner_fake import RunnerFake
    from app.services.gate_service import GateService

    project_id_str = "00000000-0000-0000-0000-000000000002"
    project = _make_project(project_id=project_id_str)
    gate = _make_gate(gate_type="solidification")
    gate.project_id = project.id

    # Artifacts for _compute_gate2_alignment: (1) mvp_scope, (2) change_request_* list
    mvp_scope_content = {
        "core_features": [
            {"name": "user authentication"},
            {"name": "dashboard"},
        ]
    }
    mvp_artifact = _make_artifact("mvp_scope", mvp_scope_content)

    # execute() order for resolve_gate:
    # (1) load gate by id, (2) load project ownership
    # Then _compute_gate2_alignment: (3) mvp_scope artifact, (4) change_request_* artifacts (list)
    mock_factory = _mock_session_factory([gate, project, mvp_artifact, []])

    with (
        patch("app.services.gate_service.JourneyService") as mock_journey_cls,
        patch("app.services.gate_service.flag_modified"),
    ):
        mock_journey = AsyncMock()
        mock_journey.decide_gate = AsyncMock()
        mock_journey_cls.return_value = mock_journey

        runner = RunnerFake()
        service = GateService(runner, mock_factory)
        response = await service.resolve_gate(
            clerk_user_id="user-001",
            gate_id=str(gate.id),
            decision="iterate",
        )

    assert response.decision == "iterate"
    assert response.status == "decided"
    assert "Alignment:" in response.resolution_summary
    assert response.next_action == "Submit your change request"
    # Gate context was modified to include alignment_score and scope_creep_detected
    assert "alignment_score" in gate.context
    assert "scope_creep_detected" in gate.context


# ---------------------------------------------------------------------------
# Test 3: create_change_request creates Artifact with correct artifact_type
# ---------------------------------------------------------------------------


async def test_create_change_request_creates_artifact():
    """ChangeRequestService.create_change_request() creates Artifact with artifact_type='change_request_1'."""
    from app.agent.runner_fake import RunnerFake
    from app.services.change_request_service import ChangeRequestService

    project_id_str = "00000000-0000-0000-0000-000000000003"
    project = _make_project(project_id=project_id_str)
    latest_build = _make_job(build_version="build_v0_1", tier="bootstrapper")
    mvp_artifact = _make_artifact(
        "mvp_scope",
        {"core_features": [{"name": "user auth"}, {"name": "dashboard"}]},
    )

    # execute() order: (1) project, (2) latest job, (3) mvp_scope, (4) existing change_requests list
    mock_factory = _mock_session_factory([project, latest_build, mvp_artifact, []])

    # Capture the artifact passed to session.add
    captured_artifacts: list = []
    mock_factory.return_value.__aenter__.return_value.add = MagicMock(
        side_effect=lambda a: captured_artifacts.append(a)
    )

    # Override refresh to set the artifact id on the object
    async def fake_refresh(artifact):
        artifact.id = uuid.uuid4()

    mock_factory.return_value.__aenter__.return_value.refresh = fake_refresh

    runner = RunnerFake()
    service = ChangeRequestService(runner, mock_factory)
    result = await service.create_change_request(
        clerk_user_id="user-001",
        project_id=project_id_str,
        description="Add dark mode to the dashboard",
    )

    # Artifact was added to session
    assert len(captured_artifacts) == 1
    artifact = captured_artifacts[0]
    assert artifact.artifact_type == "change_request_1"
    assert artifact.current_content["_schema_version"] == 1
    assert artifact.current_content["change_description"] == "Add dark mode to the dashboard"
    assert artifact.current_content["iteration_number"] == 1

    # Response fields
    assert result["iteration_number"] == 1
    assert result["artifact_type"] == "change_request_1"


# ---------------------------------------------------------------------------
# Test 4: change request references build_version
# ---------------------------------------------------------------------------


async def test_change_request_references_build_version():
    """Change request content includes references_build_version matching latest build."""
    from app.agent.runner_fake import RunnerFake
    from app.services.change_request_service import ChangeRequestService

    project_id_str = "00000000-0000-0000-0000-000000000004"
    project = _make_project(project_id=project_id_str)
    latest_build = _make_job(build_version="build_v0_3", tier="partner")
    mvp_artifact = _make_artifact("mvp_scope", {"core_features": []})

    mock_factory = _mock_session_factory([project, latest_build, mvp_artifact, []])

    captured_artifacts: list = []
    mock_factory.return_value.__aenter__.return_value.add = MagicMock(
        side_effect=lambda a: captured_artifacts.append(a)
    )

    async def fake_refresh(artifact):
        artifact.id = uuid.uuid4()

    mock_factory.return_value.__aenter__.return_value.refresh = fake_refresh

    runner = RunnerFake()
    service = ChangeRequestService(runner, mock_factory)
    result = await service.create_change_request(
        clerk_user_id="user-001",
        project_id=project_id_str,
        description="Improve performance of API",
    )

    assert result["build_version"] == "build_v0_3"
    artifact = captured_artifacts[0]
    assert artifact.current_content["references_build_version"] == "build_v0_3"


# ---------------------------------------------------------------------------
# Test 5: change request includes iteration_number and tier_limit (ITER-01, ITER-02)
# ---------------------------------------------------------------------------


async def test_change_request_includes_iteration_depth():
    """Change request content has iteration_number and tier_limit fields (ITER-01, ITER-02)."""
    from app.agent.runner_fake import RunnerFake
    from app.queue.schemas import TIER_ITERATION_DEPTH
    from app.services.change_request_service import ChangeRequestService

    project_id_str = "00000000-0000-0000-0000-000000000005"
    project = _make_project(project_id=project_id_str)
    # Partner tier has iteration depth of 3
    latest_build = _make_job(build_version="build_v0_2", tier="partner")
    mvp_artifact = _make_artifact("mvp_scope", {"core_features": []})

    # Simulate 2 existing change_requests already created
    existing_cr_1 = _make_artifact("change_request_1", {"description": "First change", "_schema_version": 1})
    existing_cr_2 = _make_artifact("change_request_2", {"description": "Second change", "_schema_version": 1})

    mock_factory = _mock_session_factory([project, latest_build, mvp_artifact, [existing_cr_1, existing_cr_2]])

    captured_artifacts: list = []
    mock_factory.return_value.__aenter__.return_value.add = MagicMock(
        side_effect=lambda a: captured_artifacts.append(a)
    )

    async def fake_refresh(artifact):
        artifact.id = uuid.uuid4()

    mock_factory.return_value.__aenter__.return_value.refresh = fake_refresh

    runner = RunnerFake()
    service = ChangeRequestService(runner, mock_factory)
    result = await service.create_change_request(
        clerk_user_id="user-001",
        project_id=project_id_str,
        description="Add export to CSV feature",
    )

    # iteration_number = 3 (two existing + this one)
    assert result["iteration_number"] == 3
    # tier_limit for partner = 3
    assert result["tier_limit"] == TIER_ITERATION_DEPTH["partner"]
    assert result["tier_limit"] == 3

    artifact = captured_artifacts[0]
    assert artifact.artifact_type == "change_request_3"
    assert artifact.current_content["iteration_number"] == 3
    assert artifact.current_content["tier_limit"] == 3
    # alignment_score and scope_creep_detected must be present (ITER-03)
    assert "alignment_score" in artifact.current_content
    assert "scope_creep_detected" in artifact.current_content
