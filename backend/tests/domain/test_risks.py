"""Tests for system risk detection logic.

Tests enforce pure function behavior:
- No DB access
- Deterministic outputs given same inputs
- Injectable time for testability
"""
import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from app.domain.risks import detect_llm_risks, detect_system_risks

pytestmark = pytest.mark.unit


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


class TestDetectLlmRisks:
    @pytest.mark.asyncio
    async def test_high_usage_returns_risk(self):
        """When usage > 80% of daily limit, return high_token_usage risk."""
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=b"85000")

        mock_settings = MagicMock()
        mock_settings.plan_tier.max_tokens_per_day = 100000
        mock_settings.override_max_tokens_per_day = None

        with patch("app.domain.risks.get_redis", return_value=mock_redis), \
             patch("app.domain.risks.get_or_create_user_settings", return_value=mock_settings):
            risks = await detect_llm_risks("user_123", None)

        assert len(risks) == 1
        assert risks[0]["rule"] == "high_token_usage"
        assert "85%" in risks[0]["message"]

    @pytest.mark.asyncio
    async def test_normal_usage_returns_empty(self):
        """When usage < 80% of daily limit, return no risks."""
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=b"50000")

        mock_settings = MagicMock()
        mock_settings.plan_tier.max_tokens_per_day = 100000
        mock_settings.override_max_tokens_per_day = None

        with patch("app.domain.risks.get_redis", return_value=mock_redis), \
             patch("app.domain.risks.get_or_create_user_settings", return_value=mock_settings):
            risks = await detect_llm_risks("user_123", None)

        assert len(risks) == 0

    @pytest.mark.asyncio
    async def test_unlimited_plan_returns_empty(self):
        """When plan has unlimited tokens (-1), return no risks."""
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=b"999999")

        mock_settings = MagicMock()
        mock_settings.plan_tier.max_tokens_per_day = -1
        mock_settings.override_max_tokens_per_day = None

        with patch("app.domain.risks.get_redis", return_value=mock_redis), \
             patch("app.domain.risks.get_or_create_user_settings", return_value=mock_settings):
            risks = await detect_llm_risks("user_123", None)

        assert len(risks) == 0

    @pytest.mark.asyncio
    async def test_redis_failure_returns_empty(self):
        """When Redis fails, return empty list (non-blocking)."""
        with patch("app.domain.risks.get_redis", side_effect=Exception("Redis down")):
            risks = await detect_llm_risks("user_123", None)

        assert len(risks) == 0
