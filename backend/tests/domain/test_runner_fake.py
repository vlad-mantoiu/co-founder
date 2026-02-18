"""Tests for RunnerFake scenario-based test double.

Validates all 4 scenarios: happy_path, llm_failure, partial_build, rate_limited.
Tests confirm RunnerFake satisfies Runner protocol and provides realistic content.
"""

import time
from datetime import timezone

import pytest

from app.agent.runner import Runner
from app.agent.runner_fake import RunnerFake
from app.agent.state import create_initial_state

pytestmark = pytest.mark.unit


# =============================================================================
# HAPPY PATH SCENARIO TESTS
# =============================================================================


@pytest.mark.asyncio
async def test_happy_path_run_returns_complete_state():
    """RunnerFake('happy_path').run() returns state with is_complete=True and realistic content."""
    runner = RunnerFake(scenario="happy_path")
    state = create_initial_state(
        user_id="test-user",
        project_id="test-project",
        project_path="/tmp/test",
        goal="Build an inventory tracker",
    )

    result = await runner.run(state)

    # Completeness checks
    assert result["is_complete"] is True
    assert len(result["plan"]) > 0
    assert len(result["working_files"]) > 0
    assert result["current_node"] == "git_manager"

    # Realistic content checks
    assert any("Product" in step["description"] or "model" in step["description"].lower()
               for step in result["plan"])
    assert result["last_command_exit_code"] == 0


@pytest.mark.asyncio
async def test_happy_path_step_returns_stage_state():
    """RunnerFake('happy_path').step() returns state updated for specific stage."""
    runner = RunnerFake(scenario="happy_path")
    state = create_initial_state(
        user_id="test-user",
        project_id="test-project",
        project_path="/tmp/test",
        goal="Build an inventory tracker",
    )

    result = await runner.step(state, "architect")

    assert result["current_node"] == "architect"
    assert len(result["plan"]) > 0


@pytest.mark.asyncio
async def test_happy_path_generate_questions_returns_questions():
    """RunnerFake('happy_path').generate_questions() returns list of realistic questions."""
    runner = RunnerFake(scenario="happy_path")

    questions = await runner.generate_questions({"idea": "inventory tracker"})

    assert len(questions) >= 5
    for q in questions:
        assert "id" in q
        assert "text" in q
        assert "required" in q
        # Questions should be realistic, not placeholders
        assert len(q["text"]) > 10


@pytest.mark.asyncio
async def test_happy_path_generate_brief_returns_brief():
    """RunnerFake('happy_path').generate_brief() returns complete brief with all required keys."""
    runner = RunnerFake(scenario="happy_path")
    answers = {"q1": "Retail shop owners", "q2": "Inventory tracking"}

    brief = await runner.generate_brief(answers)

    # Verify all 8 required keys exist
    required_keys = [
        "problem_statement",
        "target_user",
        "value_prop",
        "differentiation",
        "monetization_hypothesis",
        "assumptions",
        "risks",
        "smallest_viable_experiment",
    ]
    for key in required_keys:
        assert key in brief
        assert isinstance(brief[key], str)
        assert len(brief[key]) > 0


@pytest.mark.asyncio
async def test_happy_path_generate_artifacts_returns_artifacts():
    """RunnerFake('happy_path').generate_artifacts() returns all 5 artifact documents."""
    runner = RunnerFake(scenario="happy_path")
    brief = {"problem_statement": "Inventory tracking", "target_user": "Shop owners"}

    artifacts = await runner.generate_artifacts(brief)

    # Verify all 5 artifact keys exist
    required_keys = ["product_brief", "mvp_scope", "milestones", "risk_log", "how_it_works"]
    for key in required_keys:
        assert key in artifacts
        assert isinstance(artifacts[key], str)
        assert len(artifacts[key]) > 0


@pytest.mark.asyncio
async def test_happy_path_plan_has_realistic_content():
    """Plan steps contain realistic descriptions and file paths, not placeholder text."""
    runner = RunnerFake(scenario="happy_path")
    state = create_initial_state(
        user_id="test-user",
        project_id="test-project",
        project_path="/tmp/test",
        goal="Build an inventory tracker",
    )

    result = await runner.run(state)

    # Check plan steps are realistic
    for step in result["plan"]:
        # Not just "test" or "placeholder"
        assert "test" not in step["description"].lower() or "pytest" in step["description"].lower()
        assert "placeholder" not in step["description"].lower()
        # Has actual file paths
        assert len(step["files_to_modify"]) > 0
        # File paths look plausible
        for filepath in step["files_to_modify"]:
            assert "/" in filepath or "\\" in filepath


@pytest.mark.asyncio
async def test_happy_path_code_has_realistic_content():
    """working_files contain actual code, not lorem ipsum or placeholders."""
    runner = RunnerFake(scenario="happy_path")
    state = create_initial_state(
        user_id="test-user",
        project_id="test-project",
        project_path="/tmp/test",
        goal="Build an inventory tracker",
    )

    result = await runner.run(state)

    # Check at least one file contains actual code patterns
    code_patterns_found = False
    for file_change in result["working_files"].values():
        content = file_change["new_content"]
        # Look for code indicators: def, class, function, import
        if any(keyword in content for keyword in ["def ", "class ", "function ", "import "]):
            code_patterns_found = True
            break

    assert code_patterns_found, "No realistic code found in working_files"


# =============================================================================
# LLM FAILURE SCENARIO TESTS
# =============================================================================


@pytest.mark.asyncio
async def test_llm_failure_run_raises_runtime_error():
    """RunnerFake('llm_failure').run() raises RuntimeError with API/rate limit message."""
    runner = RunnerFake(scenario="llm_failure")
    state = create_initial_state(
        user_id="test-user",
        project_id="test-project",
        project_path="/tmp/test",
        goal="Build something",
    )

    with pytest.raises(RuntimeError) as exc_info:
        await runner.run(state)

    error_msg = str(exc_info.value).lower()
    assert "rate limit" in error_msg or "api" in error_msg


@pytest.mark.asyncio
async def test_llm_failure_step_raises_runtime_error():
    """RunnerFake('llm_failure').step() raises RuntimeError."""
    runner = RunnerFake(scenario="llm_failure")
    state = create_initial_state(
        user_id="test-user",
        project_id="test-project",
        project_path="/tmp/test",
        goal="Build something",
    )

    with pytest.raises(RuntimeError) as exc_info:
        await runner.step(state, "architect")

    error_msg = str(exc_info.value).lower()
    assert "rate limit" in error_msg or "api" in error_msg


@pytest.mark.asyncio
async def test_llm_failure_generate_questions_raises():
    """RunnerFake('llm_failure').generate_questions() raises RuntimeError."""
    runner = RunnerFake(scenario="llm_failure")

    with pytest.raises(RuntimeError) as exc_info:
        await runner.generate_questions({"idea": "something"})

    error_msg = str(exc_info.value).lower()
    assert "rate limit" in error_msg or "api" in error_msg


# =============================================================================
# PARTIAL BUILD SCENARIO TESTS
# =============================================================================


@pytest.mark.asyncio
async def test_partial_build_run_returns_incomplete():
    """RunnerFake('partial_build').run() returns state with is_complete=False and errors."""
    runner = RunnerFake(scenario="partial_build")
    state = create_initial_state(
        user_id="test-user",
        project_id="test-project",
        project_path="/tmp/test",
        goal="Build something",
    )

    result = await runner.run(state)

    assert result["is_complete"] is False
    assert len(result["active_errors"]) > 0
    assert result["last_command_exit_code"] == 1


@pytest.mark.asyncio
async def test_partial_build_has_plan_and_code():
    """partial_build scenario still generates plan and code, but tests fail."""
    runner = RunnerFake(scenario="partial_build")
    state = create_initial_state(
        user_id="test-user",
        project_id="test-project",
        project_path="/tmp/test",
        goal="Build something",
    )

    result = await runner.run(state)

    # Plan and code were generated
    assert len(result["plan"]) > 0
    assert len(result["working_files"]) > 0
    # But execution failed
    assert result["is_complete"] is False


# =============================================================================
# RATE LIMITED SCENARIO TESTS
# =============================================================================


@pytest.mark.asyncio
async def test_rate_limited_run_raises_with_wait_info():
    """RunnerFake('rate_limited').run() raises RuntimeError with capacity/wait info."""
    runner = RunnerFake(scenario="rate_limited")
    state = create_initial_state(
        user_id="test-user",
        project_id="test-project",
        project_path="/tmp/test",
        goal="Build something",
    )

    with pytest.raises(RuntimeError) as exc_info:
        await runner.run(state)

    error_msg = str(exc_info.value).lower()
    assert "capacity" in error_msg or "wait" in error_msg


@pytest.mark.asyncio
async def test_rate_limited_step_raises():
    """RunnerFake('rate_limited').step() raises RuntimeError."""
    runner = RunnerFake(scenario="rate_limited")
    state = create_initial_state(
        user_id="test-user",
        project_id="test-project",
        project_path="/tmp/test",
        goal="Build something",
    )

    with pytest.raises(RuntimeError) as exc_info:
        await runner.step(state, "architect")

    error_msg = str(exc_info.value).lower()
    assert "capacity" in error_msg or "wait" in error_msg


# =============================================================================
# CROSS-SCENARIO TESTS
# =============================================================================


def test_invalid_scenario_raises_value_error():
    """RunnerFake('nonexistent') raises ValueError."""
    with pytest.raises(ValueError) as exc_info:
        RunnerFake(scenario="nonexistent")

    assert "nonexistent" in str(exc_info.value).lower()


def test_runner_fake_satisfies_protocol():
    """isinstance(RunnerFake(), Runner) is True."""
    runner = RunnerFake()
    assert isinstance(runner, Runner)


@pytest.mark.asyncio
async def test_all_scenarios_return_instantly():
    """All scenarios complete in <100ms (no real LLM calls)."""
    runner = RunnerFake(scenario="happy_path")
    state = create_initial_state(
        user_id="test-user",
        project_id="test-project",
        project_path="/tmp/test",
        goal="Build something",
    )

    start = time.time()
    result = await runner.run(state)
    duration_ms = (time.time() - start) * 1000

    assert duration_ms < 100, f"RunnerFake took {duration_ms:.2f}ms (expected <100ms)"


@pytest.mark.asyncio
async def test_step_with_invalid_stage_raises_value_error():
    """RunnerFake.step() with invalid stage name raises ValueError."""
    runner = RunnerFake(scenario="happy_path")
    state = create_initial_state(
        user_id="test-user",
        project_id="test-project",
        project_path="/tmp/test",
        goal="Build something",
    )

    with pytest.raises(ValueError) as exc_info:
        await runner.step(state, "invalid_stage")

    assert "invalid_stage" in str(exc_info.value).lower() or "stage" in str(exc_info.value).lower()


@pytest.mark.asyncio
@pytest.mark.parametrize("stage", ["architect", "coder", "executor", "debugger", "reviewer", "git_manager"])
async def test_step_accepts_all_valid_stages(stage):
    """RunnerFake.step() accepts all 6 valid stage names."""
    runner = RunnerFake(scenario="happy_path")
    state = create_initial_state(
        user_id="test-user",
        project_id="test-project",
        project_path="/tmp/test",
        goal="Build something",
    )

    result = await runner.step(state, stage)

    # Should not raise, and should update current_node
    assert result["current_node"] == stage
