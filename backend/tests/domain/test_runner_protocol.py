"""Tests for Runner protocol compliance and structural validation.

These tests verify:
1. The Runner protocol is properly runtime_checkable
2. All required methods exist with correct signatures
3. RunnerReal satisfies the Runner protocol
4. Incomplete implementations are correctly rejected
"""

import inspect
from typing import get_type_hints

from app.agent.runner import Runner
from app.agent.state import CoFounderState


def test_runner_is_runtime_checkable():
    """Verify Runner protocol can be used with isinstance checks at runtime."""
    # Test that the protocol works with isinstance by checking a complete implementation
    from typing import Protocol

    # Verify Runner is a Protocol subclass
    assert isinstance(Runner, type)
    assert issubclass(type(Runner), type(Protocol))

    # Test that isinstance works with a complete dummy class
    class CompleteRunner:
        async def run(self, state: CoFounderState) -> CoFounderState:
            return state

        async def step(self, state: CoFounderState, stage: str) -> CoFounderState:
            return state

        async def generate_questions(self, context: dict) -> list[dict]:
            return []

        async def generate_brief(self, answers: dict) -> dict:
            return {}

        async def generate_artifacts(self, brief: dict) -> dict:
            return {}

    complete = CompleteRunner()
    # If runtime_checkable is working, isinstance should return True
    assert isinstance(
        complete, Runner
    ), "Runner protocol must support isinstance checks (runtime_checkable)"


def test_runner_has_required_methods():
    """Verify Runner protocol defines all 5 required methods."""
    required_methods = {
        "run",
        "step",
        "generate_questions",
        "generate_brief",
        "generate_artifacts",
    }

    protocol_methods = {
        name
        for name, method in inspect.getmembers(Runner)
        if not name.startswith("_") and callable(method)
    }

    assert (
        required_methods <= protocol_methods
    ), f"Missing methods: {required_methods - protocol_methods}"


def test_runner_method_signatures():
    """Verify Runner protocol methods have correct signatures."""
    # Get the protocol's type hints
    run_hints = get_type_hints(Runner.run)
    assert "state" in run_hints
    assert run_hints["state"] == CoFounderState
    assert run_hints["return"] == CoFounderState

    step_hints = get_type_hints(Runner.step)
    assert "state" in step_hints
    assert "stage" in step_hints
    assert step_hints["state"] == CoFounderState
    assert step_hints["stage"] == str
    assert step_hints["return"] == CoFounderState

    questions_hints = get_type_hints(Runner.generate_questions)
    assert "context" in questions_hints
    assert questions_hints["context"] == dict
    assert questions_hints["return"] == list[dict]

    brief_hints = get_type_hints(Runner.generate_brief)
    assert "answers" in brief_hints
    assert brief_hints["answers"] == dict
    assert brief_hints["return"] == dict

    artifacts_hints = get_type_hints(Runner.generate_artifacts)
    assert "brief" in artifacts_hints
    assert artifacts_hints["brief"] == dict
    assert artifacts_hints["return"] == dict


def test_runner_real_satisfies_protocol():
    """Verify RunnerReal implements the Runner protocol correctly.

    This test MUST FAIL initially (RED) because RunnerReal doesn't exist yet.
    After implementing RunnerReal, this test MUST PASS (GREEN).
    """
    from app.agent.runner_real import RunnerReal

    # Create an instance
    runner = RunnerReal()

    # Verify it satisfies the protocol
    assert isinstance(
        runner, Runner
    ), "RunnerReal must satisfy the Runner protocol"

    # Verify it has all required methods
    assert hasattr(runner, "run")
    assert hasattr(runner, "step")
    assert hasattr(runner, "generate_questions")
    assert hasattr(runner, "generate_brief")
    assert hasattr(runner, "generate_artifacts")

    # Verify all methods are callable
    assert callable(runner.run)
    assert callable(runner.step)
    assert callable(runner.generate_questions)
    assert callable(runner.generate_brief)
    assert callable(runner.generate_artifacts)


def test_incomplete_class_does_not_satisfy_protocol():
    """Verify that a class missing required methods does NOT satisfy Runner protocol."""

    class IncompleteRunner:
        """A class that only implements some Runner methods."""

        async def run(self, state: CoFounderState) -> CoFounderState:
            return state

        async def step(self, state: CoFounderState, stage: str) -> CoFounderState:
            return state

        # Missing: generate_questions, generate_brief, generate_artifacts

    incomplete = IncompleteRunner()

    # This should NOT satisfy the protocol
    assert not isinstance(
        incomplete, Runner
    ), "Incomplete implementation should not satisfy Runner protocol"
