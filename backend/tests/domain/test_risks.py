"""Tests for system risk detection logic.

Tests enforce pure function behavior:
- No DB access
- Deterministic outputs given same inputs
- Injectable time for testability
"""
from datetime import datetime, timedelta, timezone

from app.domain.risks import detect_llm_risks, detect_system_risks


def test_detect_system_risks_no_conditions_returns_empty():
    """When no risk conditions are met, return empty list."""
    now = datetime(2026, 2, 16, 12, 0, 0, tzinfo=timezone.utc)
    last_activity = now - timedelta(days=5)
    last_decision = now - timedelta(days=3)

    risks = detect_system_risks(
        last_gate_decision_at=last_decision,
        build_failure_count=1,
        last_activity_at=last_activity,
        now=now,
    )
    assert risks == []


def test_detect_system_risks_stale_decision_at_7_days():
    """Stale decision risk triggers at exactly 7 days."""
    now = datetime(2026, 2, 16, 12, 0, 0, tzinfo=timezone.utc)
    last_decision = now - timedelta(days=7)
    last_activity = now - timedelta(days=1)

    risks = detect_system_risks(
        last_gate_decision_at=last_decision,
        build_failure_count=0,
        last_activity_at=last_activity,
        now=now,
    )
    assert len(risks) == 1
    assert risks[0]["type"] == "system"
    assert risks[0]["rule"] == "stale_decision"
    assert "7 days" in risks[0]["message"] or "decision" in risks[0]["message"].lower()


def test_detect_system_risks_stale_decision_boundary_6_days():
    """Stale decision does not trigger at 6 days (boundary test)."""
    now = datetime(2026, 2, 16, 12, 0, 0, tzinfo=timezone.utc)
    last_decision = now - timedelta(days=6)
    last_activity = now - timedelta(days=1)

    risks = detect_system_risks(
        last_gate_decision_at=last_decision,
        build_failure_count=0,
        last_activity_at=last_activity,
        now=now,
    )
    assert risks == []


def test_detect_system_risks_stale_decision_none_returns_no_risk():
    """When last_gate_decision_at is None, no stale decision risk."""
    now = datetime(2026, 2, 16, 12, 0, 0, tzinfo=timezone.utc)
    last_activity = now - timedelta(days=1)

    risks = detect_system_risks(
        last_gate_decision_at=None,
        build_failure_count=0,
        last_activity_at=last_activity,
        now=now,
    )
    assert risks == []


def test_detect_system_risks_build_failures_at_3():
    """Build failures risk triggers at exactly 3 failures."""
    now = datetime(2026, 2, 16, 12, 0, 0, tzinfo=timezone.utc)
    last_activity = now - timedelta(days=1)

    risks = detect_system_risks(
        last_gate_decision_at=None,
        build_failure_count=3,
        last_activity_at=last_activity,
        now=now,
    )
    assert len(risks) == 1
    assert risks[0]["type"] == "system"
    assert risks[0]["rule"] == "build_failures"
    assert "3" in risks[0]["message"] or "build" in risks[0]["message"].lower()


def test_detect_system_risks_build_failures_boundary_2():
    """Build failures does not trigger at 2 failures (boundary test)."""
    now = datetime(2026, 2, 16, 12, 0, 0, tzinfo=timezone.utc)
    last_activity = now - timedelta(days=1)

    risks = detect_system_risks(
        last_gate_decision_at=None,
        build_failure_count=2,
        last_activity_at=last_activity,
        now=now,
    )
    assert risks == []


def test_detect_system_risks_stale_project_at_14_days():
    """Stale project risk triggers at exactly 14 days inactive."""
    now = datetime(2026, 2, 16, 12, 0, 0, tzinfo=timezone.utc)
    last_activity = now - timedelta(days=14)

    risks = detect_system_risks(
        last_gate_decision_at=None,
        build_failure_count=0,
        last_activity_at=last_activity,
        now=now,
    )
    assert len(risks) == 1
    assert risks[0]["type"] == "system"
    assert risks[0]["rule"] == "stale_project"
    assert "14 days" in risks[0]["message"] or "inactive" in risks[0]["message"].lower()


def test_detect_system_risks_stale_project_boundary_13_days():
    """Stale project does not trigger at 13 days inactive (boundary test)."""
    now = datetime(2026, 2, 16, 12, 0, 0, tzinfo=timezone.utc)
    last_activity = now - timedelta(days=13)

    risks = detect_system_risks(
        last_gate_decision_at=None,
        build_failure_count=0,
        last_activity_at=last_activity,
        now=now,
    )
    assert risks == []


def test_detect_system_risks_all_conditions_met():
    """Multiple risk conditions can fire simultaneously."""
    now = datetime(2026, 2, 16, 12, 0, 0, tzinfo=timezone.utc)
    last_activity = now - timedelta(days=14)
    last_decision = now - timedelta(days=7)

    risks = detect_system_risks(
        last_gate_decision_at=last_decision,
        build_failure_count=3,
        last_activity_at=last_activity,
        now=now,
    )
    assert len(risks) == 3
    rules = {r["rule"] for r in risks}
    assert rules == {"stale_decision", "build_failures", "stale_project"}
    for risk in risks:
        assert risk["type"] == "system"
        assert "message" in risk
        assert len(risk["message"]) > 0


def test_detect_system_risks_default_now_parameter():
    """When now parameter is not provided, uses current time."""
    # Test that function works without explicit now (uses default)
    # We can't test exact behavior without mocking, but can verify it doesn't crash
    last_activity = datetime.now(timezone.utc) - timedelta(days=1)
    risks = detect_system_risks(
        last_gate_decision_at=None,
        build_failure_count=0,
        last_activity_at=last_activity,
    )
    # Should return empty list for recent activity
    assert isinstance(risks, list)


def test_detect_llm_risks_returns_empty_list():
    """LLM risk detection stub always returns empty list."""
    risks = detect_llm_risks()
    assert risks == []


def test_detect_llm_risks_accepts_kwargs():
    """LLM risk detection stub accepts arbitrary kwargs for future use."""
    risks = detect_llm_risks(
        project_stage=1,
        milestones=[],
        code_quality="unknown",
    )
    assert risks == []
