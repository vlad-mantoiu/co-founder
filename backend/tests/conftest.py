"""Shared test fixtures for all test groups."""

import pytest

from app.agent.runner_fake import RunnerFake
from app.agent.state import create_initial_state


@pytest.fixture
def runner_fake():
    """Fresh RunnerFake with happy_path scenario (default)."""
    return RunnerFake(scenario="happy_path")


@pytest.fixture
def runner_fake_failing():
    """RunnerFake with llm_failure scenario."""
    return RunnerFake(scenario="llm_failure")


@pytest.fixture
def runner_fake_partial():
    """RunnerFake with partial_build scenario."""
    return RunnerFake(scenario="partial_build")


@pytest.fixture
def runner_fake_rate_limited():
    """RunnerFake with rate_limited scenario."""
    return RunnerFake(scenario="rate_limited")


@pytest.fixture
def sample_state():
    """Create a sample initial state for testing."""
    return create_initial_state(
        user_id="test-user-001",
        project_id="test-project-001",
        project_path="/tmp/test-project",
        goal="Build a simple inventory tracking app",
        session_id="test-session-001",
    )
