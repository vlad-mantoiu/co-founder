"""Tests for AutonomousRunner — verifies NotImplementedError on stub methods and protocol compliance.

These tests confirm that AutonomousRunner:
1. Satisfies the Runner protocol (isinstance check passes)
2. Raises NotImplementedError for every pre-existing pipeline method (run, step, generate_*, etc.)
3. run_agent_loop() is now implemented (Phase 41) — tested separately in test_taor_loop.py

Note: run_agent_loop() NotImplementedError tests removed in Phase 41 when the method was implemented.
"""

import inspect

import pytest

from app.agent.runner import Runner
from app.agent.runner_autonomous import AutonomousRunner
from app.agent.state import CoFounderState, create_initial_state

pytestmark = pytest.mark.unit

# Methods implemented in Phase 41 — not expected to raise NotImplementedError
_IMPLEMENTED_METHODS = {"run_agent_loop"}


def _minimal_state() -> CoFounderState:
    """Create a minimal CoFounderState for testing."""
    return create_initial_state(
        user_id="test-user",
        project_id="test-project",
        project_path="/tmp/test",
        goal="Test autonomous runner stub",
    )


@pytest.mark.asyncio
async def test_autonomous_runner_run_raises_not_implemented():
    """AutonomousRunner.run() raises NotImplementedError — pipeline method, not yet implemented."""
    runner = AutonomousRunner()
    state = _minimal_state()

    with pytest.raises(NotImplementedError) as exc_info:
        await runner.run(state)

    assert "AutonomousRunner" in str(exc_info.value) or "not yet implemented" in str(exc_info.value).lower()


def test_autonomous_runner_satisfies_protocol():
    """isinstance(AutonomousRunner(), Runner) is True — all protocol methods are present."""
    runner = AutonomousRunner()
    assert isinstance(runner, Runner), "AutonomousRunner must satisfy Runner protocol"


@pytest.mark.asyncio
async def test_autonomous_runner_pipeline_methods_raise_not_implemented():
    """All pre-existing pipeline protocol methods raise NotImplementedError.

    run_agent_loop() is excluded — it was implemented in Phase 41 (see test_taor_loop.py).
    """
    runner = AutonomousRunner()
    state = _minimal_state()

    # Collect all public protocol methods
    protocol_methods = [
        name
        for name, method in inspect.getmembers(Runner)
        if not name.startswith("_") and callable(method)
    ]

    # Must have at least 13 methods (original 13 + run_agent_loop)
    assert len(protocol_methods) >= 14, f"Expected 14+ protocol methods, got {len(protocol_methods)}: {protocol_methods}"

    # Every stub method (excluding implemented ones) must raise NotImplementedError
    for method_name in protocol_methods:
        if method_name in _IMPLEMENTED_METHODS:
            continue  # Implemented in Phase 41 — tested in test_taor_loop.py

        method = getattr(runner, method_name, None)
        assert method is not None, f"AutonomousRunner missing method: {method_name}"
        assert callable(method), f"AutonomousRunner.{method_name} is not callable"

        # Call with minimal valid args based on method name
        if method_name == "run":
            coro = method(state)
        elif method_name == "step":
            coro = method(state, "architect")
        elif method_name == "generate_questions":
            coro = method({})
        elif method_name == "generate_brief":
            coro = method({})
        elif method_name == "generate_artifacts":
            coro = method({})
        elif method_name == "generate_understanding_questions":
            coro = method({})
        elif method_name == "generate_idea_brief":
            coro = method("idea", [], {})
        elif method_name == "check_question_relevance":
            coro = method("idea", [], {}, [])
        elif method_name == "assess_section_confidence":
            coro = method("problem_statement", "some content")
        elif method_name == "generate_execution_options":
            coro = method({})
        elif method_name == "generate_strategy_graph":
            coro = method("idea", {}, {})
        elif method_name == "generate_mvp_timeline":
            coro = method("idea", {}, "bootstrapper")
        elif method_name == "generate_app_architecture":
            coro = method("idea", {}, "bootstrapper")
        else:
            # Unknown method — skip to avoid false failures on protocol extensions
            continue

        with pytest.raises(NotImplementedError, match=r"(?i)(autonomous|not yet implemented|phase 41)"):
            await coro


@pytest.mark.asyncio
async def test_autonomous_runner_step_raises_not_implemented():
    """AutonomousRunner.step() raises NotImplementedError."""
    runner = AutonomousRunner()
    state = _minimal_state()

    with pytest.raises(NotImplementedError):
        await runner.step(state, "architect")


@pytest.mark.asyncio
async def test_autonomous_runner_generate_questions_raises_not_implemented():
    """AutonomousRunner.generate_questions() raises NotImplementedError."""
    runner = AutonomousRunner()

    with pytest.raises(NotImplementedError):
        await runner.generate_questions({})


@pytest.mark.asyncio
async def test_autonomous_runner_generate_brief_raises_not_implemented():
    """AutonomousRunner.generate_brief() raises NotImplementedError."""
    runner = AutonomousRunner()

    with pytest.raises(NotImplementedError):
        await runner.generate_brief({})
