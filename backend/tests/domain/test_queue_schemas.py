"""Test queue schemas — JobStatus enum and Pydantic models."""

import pytest
from pydantic import ValidationError

from app.queue.schemas import (
    GLOBAL_QUEUE_CAP,
    TIER_BOOST,
    TIER_CONCURRENT_PROJECT,
    TIER_CONCURRENT_USER,
    TIER_DAILY_LIMIT,
    TIER_ITERATION_DEPTH,
    JobRecord,
    JobRequest,
    JobStatus,
    UsageCounters,
)

pytestmark = pytest.mark.unit


def test_job_status_has_9_states():
    """JobStatus enum must have exactly 9 states."""
    expected = {
        "queued",
        "starting",
        "scaffold",
        "code",
        "deps",
        "checks",
        "ready",
        "failed",
        "scheduled",
    }
    actual = {status.value for status in JobStatus}
    assert actual == expected, f"JobStatus values mismatch. Expected {expected}, got {actual}"


def test_job_request_validates_required_fields():
    """JobRequest must require project_id, user_id, tier, and goal."""
    # Valid request
    valid = JobRequest(
        project_id="proj-123",
        user_id="user-456",
        tier="bootstrapper",
        goal="Build a todo app",
    )
    assert valid.project_id == "proj-123"
    assert valid.user_id == "user-456"
    assert valid.tier == "bootstrapper"
    assert valid.goal == "Build a todo app"

    # Missing required field
    with pytest.raises(ValidationError):
        JobRequest(project_id="proj-123", user_id="user-456", tier="bootstrapper")


def test_job_record_includes_all_fields():
    """JobRecord must include job_id, project_id, user_id, tier, status, enqueued_at, position, score."""
    record = JobRecord(
        job_id="job-789",
        project_id="proj-123",
        user_id="user-456",
        tier="partner",
        status=JobStatus.QUEUED,
        enqueued_at="2026-02-16T20:00:00Z",
        position=3,
        score=998000000000042.0,
    )

    assert record.job_id == "job-789"
    assert record.project_id == "proj-123"
    assert record.user_id == "user-456"
    assert record.tier == "partner"
    assert record.status == JobStatus.QUEUED
    assert record.enqueued_at == "2026-02-16T20:00:00Z"
    assert record.position == 3
    assert record.score == 998000000000042.0


def test_usage_counters_includes_all_fields():
    """UsageCounters must include jobs_used, jobs_remaining, iterations_used, iterations_remaining, daily_limit_resets_at."""
    counters = UsageCounters(
        jobs_used=3,
        jobs_remaining=2,
        iterations_used=7,
        iterations_remaining=8,
        daily_limit_resets_at="2026-02-17T00:00:00Z",
    )

    assert counters.jobs_used == 3
    assert counters.jobs_remaining == 2
    assert counters.iterations_used == 7
    assert counters.iterations_remaining == 8
    assert counters.daily_limit_resets_at == "2026-02-17T00:00:00Z"


def test_tier_constants_match_locked_decisions():
    """Verify tier capacity constants match LOCKED decisions from research."""
    assert TIER_BOOST == {"cto_scale": 5, "partner": 2, "bootstrapper": 0}
    assert TIER_CONCURRENT_USER == {"bootstrapper": 2, "partner": 3, "cto_scale": 10}
    assert TIER_CONCURRENT_PROJECT == {"bootstrapper": 2, "partner": 3, "cto_scale": 5}
    assert TIER_DAILY_LIMIT == {"bootstrapper": 5, "partner": 50, "cto_scale": 200}
    assert TIER_ITERATION_DEPTH == {"bootstrapper": 2, "partner": 3, "cto_scale": 5}
    assert GLOBAL_QUEUE_CAP == 100
