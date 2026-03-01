"""Tests for Phase 46 SSE event types, helper functions, and REST endpoints.

Tests cover:
1.  test_human_tool_label_bash                — bash command label
2.  test_human_tool_label_write_file          — write_file label with path
3.  test_human_tool_label_edit_file           — edit_file label with path
4.  test_human_tool_label_read_file           — read_file label with path
5.  test_human_tool_label_grep               — grep label with pattern
6.  test_human_tool_label_glob               — glob label with pattern
7.  test_human_tool_label_take_screenshot    — take_screenshot label (no input)
8.  test_human_tool_label_narrate            — narrate label
9.  test_human_tool_label_document           — document label
10. test_human_tool_label_fallback           — unknown tool fallback
11. test_summarize_tool_result_short         — string within max_len not truncated
12. test_summarize_tool_result_truncates     — string exceeding max_len gets '...'
13. test_summarize_tool_result_vision_list   — vision list returns placeholder
14. test_sse_event_type_constants            — SSEEventType has all 4 new constants
15. test_get_job_phases_returns_sorted_list  — GET /api/jobs/{id}/phases returns sorted phases
16. test_get_job_phases_not_found            — missing job returns 404
17. test_agent_state_in_job_status           — agent_state field in GET /api/jobs/{id}
18. test_agent_state_null_when_no_redis_key  — agent_state is null when no Redis key
"""

import asyncio
import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fakeredis import FakeAsyncRedis
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.agent.runner_autonomous import _human_tool_label, _summarize_tool_result
from app.api.routes.jobs import router as jobs_router
from app.core.auth import ClerkUser, require_auth
from app.db.redis import get_redis
from app.queue.state_machine import JobStateMachine, SSEEventType

pytestmark = pytest.mark.unit

# ──────────────────────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────────────────────


@pytest.fixture
def fake_redis():
    """Provide fakeredis instance with decode_responses=True."""
    return FakeAsyncRedis(decode_responses=True)


@pytest.fixture
def test_user():
    """Test user for auth override."""
    return ClerkUser(user_id="user_phase46_test", claims={"sub": "user_phase46_test"})


def override_auth(user: ClerkUser):
    """Create auth dependency override for a specific user."""

    async def _override():
        return user

    return _override


@pytest.fixture
def app(fake_redis, test_user):
    """Minimal FastAPI app with only the jobs router — no full DB required."""
    _app = FastAPI()
    _app.include_router(jobs_router, prefix="/api/jobs")
    _app.dependency_overrides[require_auth] = override_auth(test_user)
    _app.dependency_overrides[get_redis] = lambda: fake_redis
    return _app


@pytest.fixture
def client(app):
    """Test client for the minimal app."""
    with TestClient(app) as c:
        yield c


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────


def _seed_job(fake_redis, job_id: str, user_id: str) -> None:
    """Synchronously create a minimal job in fakeredis."""
    state_machine = JobStateMachine(fake_redis)
    asyncio.run(
        state_machine.create_job(
            job_id,
            {
                "user_id": user_id,
                "project_id": str(uuid.uuid4()),
                "goal": "Build a test app",
                "tier": "bootstrapper",
            },
        )
    )


# ──────────────────────────────────────────────────────────────────────────────
# Tests 1–10: _human_tool_label()
# ──────────────────────────────────────────────────────────────────────────────


def test_human_tool_label_bash():
    """bash with command returns 'Ran command: ...' with command prefix."""
    label = _human_tool_label("bash", {"command": "npm install"})
    assert label == "Ran command: npm install"


def test_human_tool_label_bash_truncates_at_80():
    """bash command truncated to 80 chars in label."""
    long_cmd = "x" * 100
    label = _human_tool_label("bash", {"command": long_cmd})
    assert label == f"Ran command: {'x' * 80}"


def test_human_tool_label_write_file():
    """write_file with path returns 'Wrote {path}'."""
    label = _human_tool_label("write_file", {"path": "/src/app.py", "content": "..."})
    assert label == "Wrote /src/app.py"


def test_human_tool_label_edit_file():
    """edit_file with path returns 'Edited {path}'."""
    label = _human_tool_label("edit_file", {"path": "/src/config.py", "old_string": "a", "new_string": "b"})
    assert label == "Edited /src/config.py"


def test_human_tool_label_read_file():
    """read_file with path returns 'Read {path}'."""
    label = _human_tool_label("read_file", {"path": "/README.md"})
    assert label == "Read /README.md"


def test_human_tool_label_grep():
    """grep with pattern returns 'Searched for {pattern}'."""
    label = _human_tool_label("grep", {"pattern": "def authenticate", "path": "."})
    assert label == "Searched for 'def authenticate'"


def test_human_tool_label_glob():
    """glob with pattern returns 'Listed files matching {pattern}'."""
    label = _human_tool_label("glob", {"pattern": "**/*.py"})
    assert label == "Listed files matching '**/*.py'"


def test_human_tool_label_take_screenshot():
    """take_screenshot returns 'Captured screenshot'."""
    label = _human_tool_label("take_screenshot", {})
    assert label == "Captured screenshot"


def test_human_tool_label_narrate():
    """narrate returns 'Narrated progress'."""
    label = _human_tool_label("narrate", {"message": "I'm setting up auth"})
    assert label == "Narrated progress"


def test_human_tool_label_document():
    """document returns 'Generated documentation'."""
    label = _human_tool_label("document", {"section": "overview", "content": "..."})
    assert label == "Generated documentation"


def test_human_tool_label_fallback():
    """Unknown tool name returns 'Used {tool_name}'."""
    label = _human_tool_label("custom_tool", {"some": "input"})
    assert label == "Used custom_tool"


# ──────────────────────────────────────────────────────────────────────────────
# Tests 11–13: _summarize_tool_result()
# ──────────────────────────────────────────────────────────────────────────────


def test_summarize_tool_result_short():
    """String within max_len is returned unchanged."""
    result = _summarize_tool_result("short output", max_len=200)
    assert result == "short output"


def test_summarize_tool_result_truncates():
    """String exceeding max_len is truncated with '...' suffix."""
    long_result = "a" * 300
    result = _summarize_tool_result(long_result, max_len=200)
    assert len(result) == 203  # 200 chars + "..."
    assert result.endswith("...")
    assert result[:200] == "a" * 200


def test_summarize_tool_result_exactly_at_limit():
    """String exactly at max_len is not truncated."""
    result = _summarize_tool_result("x" * 200, max_len=200)
    assert result == "x" * 200
    assert not result.endswith("...")


def test_summarize_tool_result_vision_list():
    """Vision content list returns '[vision content]' placeholder."""
    vision_list = [{"type": "image", "source": {"data": "base64..."}}]
    result = _summarize_tool_result(vision_list)
    assert result == "[vision content]"


# ──────────────────────────────────────────────────────────────────────────────
# Test 14: SSEEventType constants
# ──────────────────────────────────────────────────────────────────────────────


def test_sse_event_type_constants():
    """SSEEventType class has all 4 new Phase 46 constants with correct values."""
    assert SSEEventType.AGENT_THINKING == "agent.thinking"
    assert SSEEventType.AGENT_TOOL_CALLED == "agent.tool.called"
    assert SSEEventType.GSD_PHASE_STARTED == "gsd.phase.started"
    assert SSEEventType.GSD_PHASE_COMPLETED == "gsd.phase.completed"


# ──────────────────────────────────────────────────────────────────────────────
# Test 15: GET /api/jobs/{job_id}/phases endpoint
# ──────────────────────────────────────────────────────────────────────────────


def test_get_job_phases_returns_sorted_list(client: TestClient, fake_redis, test_user):
    """GET /api/jobs/{job_id}/phases returns phases sorted by started_at from Redis hash."""
    job_id = f"test-phases-{uuid.uuid4().hex[:8]}"
    _seed_job(fake_redis, job_id, test_user.user_id)

    # Seed two phases in Redis hash (out of order to test sorting)
    phase_a_id = str(uuid.uuid4())
    phase_b_id = str(uuid.uuid4())
    phase_a = {
        "phase_id": phase_a_id,
        "phase_name": "Authentication Setup",
        "status": "completed",
        "started_at": "2026-03-01T10:00:00+00:00",
    }
    phase_b = {
        "phase_id": phase_b_id,
        "phase_name": "Database Schema",
        "status": "in_progress",
        "started_at": "2026-03-01T11:00:00+00:00",
    }
    asyncio.run(fake_redis.hset(f"job:{job_id}:phases", phase_b_id, json.dumps(phase_b)))
    asyncio.run(fake_redis.hset(f"job:{job_id}:phases", phase_a_id, json.dumps(phase_a)))

    response = client.get(f"/api/jobs/{job_id}/phases")

    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.json()}"
    data = response.json()
    assert "phases" in data
    phases = data["phases"]
    assert len(phases) == 2
    # Sorted by started_at — Authentication Setup first
    assert phases[0]["phase_name"] == "Authentication Setup"
    assert phases[1]["phase_name"] == "Database Schema"


def test_get_job_phases_empty_when_no_phases(client: TestClient, fake_redis, test_user):
    """GET /api/jobs/{job_id}/phases returns empty list when no phases in Redis."""
    job_id = f"test-phases-empty-{uuid.uuid4().hex[:8]}"
    _seed_job(fake_redis, job_id, test_user.user_id)

    response = client.get(f"/api/jobs/{job_id}/phases")

    assert response.status_code == 200
    data = response.json()
    assert data["phases"] == []


def test_get_job_phases_not_found(client: TestClient, fake_redis):
    """GET /api/jobs/{job_id}/phases returns 404 for non-existent job."""
    job_id = f"nonexistent-phases-{uuid.uuid4().hex[:8]}"

    response = client.get(f"/api/jobs/{job_id}/phases")

    assert response.status_code == 404
    assert "Job not found" in response.json()["detail"]


# ──────────────────────────────────────────────────────────────────────────────
# Tests 17–18: agent_state in GET /api/jobs/{job_id}
# ──────────────────────────────────────────────────────────────────────────────


def test_agent_state_in_job_status(client: TestClient, fake_redis, test_user):
    """GET /api/jobs/{job_id} returns agent_state field from Redis."""
    from app.queue.schemas import UsageCounters

    job_id = f"test-agent-state-{uuid.uuid4().hex[:8]}"
    _seed_job(fake_redis, job_id, test_user.user_id)

    # Set agent state in Redis (key pattern from runner_autonomous.py: session_id=job_id)
    asyncio.run(fake_redis.set(f"cofounder:agent:{job_id}:state", "working"))

    # get_job_status calls get_or_create_user_settings (DB) and UsageTracker
    # Patch both to avoid needing a live database
    mock_settings = MagicMock()
    mock_settings.plan_tier.slug = "bootstrapper"
    with (
        patch("app.api.routes.jobs.get_or_create_user_settings", new=AsyncMock(return_value=mock_settings)),
        patch("app.api.routes.jobs.UsageTracker") as mock_tracker_cls,
    ):
        mock_tracker = MagicMock()
        mock_tracker.get_usage_counters = AsyncMock(
            return_value=UsageCounters(
                jobs_used=0,
                jobs_remaining=5,
                iterations_used=0,
                iterations_remaining=10,
                daily_limit_resets_at="2026-03-02T00:00:00+00:00",
            )
        )
        mock_tracker_cls.return_value = mock_tracker

        response = client.get(f"/api/jobs/{job_id}")

    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.json()}"
    data = response.json()
    assert "agent_state" in data
    assert data["agent_state"] == "working"


def test_agent_state_null_when_no_redis_key(client: TestClient, fake_redis, test_user):
    """GET /api/jobs/{job_id} returns agent_state=null when no Redis key exists."""
    from app.queue.schemas import UsageCounters

    job_id = f"test-agent-state-null-{uuid.uuid4().hex[:8]}"
    _seed_job(fake_redis, job_id, test_user.user_id)
    # No cofounder:agent:{job_id}:state key set

    mock_settings = MagicMock()
    mock_settings.plan_tier.slug = "bootstrapper"
    with (
        patch("app.api.routes.jobs.get_or_create_user_settings", new=AsyncMock(return_value=mock_settings)),
        patch("app.api.routes.jobs.UsageTracker") as mock_tracker_cls,
    ):
        mock_tracker = MagicMock()
        mock_tracker.get_usage_counters = AsyncMock(
            return_value=UsageCounters(
                jobs_used=0,
                jobs_remaining=5,
                iterations_used=0,
                iterations_remaining=10,
                daily_limit_resets_at="2026-03-02T00:00:00+00:00",
            )
        )
        mock_tracker_cls.return_value = mock_tracker

        response = client.get(f"/api/jobs/{job_id}")

    assert response.status_code == 200
    data = response.json()
    assert "agent_state" in data
    assert data["agent_state"] is None


def test_agent_state_sleeping_includes_wake_at(client: TestClient, fake_redis, test_user):
    """GET /api/jobs/{job_id} returns wake_at when agent is sleeping."""
    from app.queue.schemas import UsageCounters

    job_id = f"test-sleeping-{uuid.uuid4().hex[:8]}"
    _seed_job(fake_redis, job_id, test_user.user_id)

    asyncio.run(fake_redis.set(f"cofounder:agent:{job_id}:state", "sleeping"))
    asyncio.run(fake_redis.set(f"cofounder:agent:{job_id}:wake_at", "2026-03-02T00:00:00+00:00"))

    mock_settings = MagicMock()
    mock_settings.plan_tier.slug = "bootstrapper"
    with (
        patch("app.api.routes.jobs.get_or_create_user_settings", new=AsyncMock(return_value=mock_settings)),
        patch("app.api.routes.jobs.UsageTracker") as mock_tracker_cls,
    ):
        mock_tracker = MagicMock()
        mock_tracker.get_usage_counters = AsyncMock(
            return_value=UsageCounters(
                jobs_used=0,
                jobs_remaining=5,
                iterations_used=0,
                iterations_remaining=10,
                daily_limit_resets_at="2026-03-02T00:00:00+00:00",
            )
        )
        mock_tracker_cls.return_value = mock_tracker

        response = client.get(f"/api/jobs/{job_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["agent_state"] == "sleeping"
    assert data["wake_at"] == "2026-03-02T00:00:00+00:00"
