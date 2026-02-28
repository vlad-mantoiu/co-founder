"""Unit tests for ErrorSignatureTracker state machine (AGNT-07).

Tests for:
- should_escalate_immediately() — NEVER_RETRY detection
- record_and_check() — state machine: attempts 1-4 return correct tuples
- global_threshold_exceeded() — fires at GLOBAL_ESCALATION_THRESHOLD escalations
- reset_signature() — clears retry count for a signature
- record_escalation() — non-fatal DB persistence (mocked)
- _build_retry_tool_result() — structured replanning injection
- _build_escalation_options() — category-appropriate options
"""

import pytest

from app.agent.error.classifier import ErrorCategory
from app.agent.error.tracker import (
    MAX_RETRIES_PER_SIGNATURE,
    GLOBAL_ESCALATION_THRESHOLD,
    ErrorSignatureTracker,
    _build_escalation_options,
    _build_retry_tool_result,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def make_tracker(retry_counts=None, db_session=None, session_id="sess-1", job_id="job-1"):
    """Create an ErrorSignatureTracker with default test values."""
    if retry_counts is None:
        retry_counts = {}
    return ErrorSignatureTracker(
        project_id="proj-test",
        retry_counts=retry_counts,
        db_session=db_session,
        session_id=session_id,
        job_id=job_id,
    )


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


class TestConstants:
    def test_max_retries_is_3(self):
        assert MAX_RETRIES_PER_SIGNATURE == 3

    def test_global_threshold_is_5(self):
        assert GLOBAL_ESCALATION_THRESHOLD == 5


# ---------------------------------------------------------------------------
# should_escalate_immediately
# ---------------------------------------------------------------------------


class TestShouldEscalateImmediately:
    def test_never_retry_error_returns_true(self):
        tracker = make_tracker()
        assert tracker.should_escalate_immediately("PermissionError", "access denied") is True

    def test_auth_error_returns_true(self):
        tracker = make_tracker()
        assert tracker.should_escalate_immediately("AuthError", "authentication failed") is True

    def test_code_error_returns_false(self):
        tracker = make_tracker()
        assert tracker.should_escalate_immediately("SyntaxError", "invalid syntax") is False

    def test_env_error_returns_false(self):
        tracker = make_tracker()
        assert tracker.should_escalate_immediately("ConnectionError", "connection refused") is False

    def test_unknown_error_returns_false(self):
        tracker = make_tracker()
        assert tracker.should_escalate_immediately("UnknownError", "something broke") is False


# ---------------------------------------------------------------------------
# record_and_check — state machine
# ---------------------------------------------------------------------------


class TestRecordAndCheck:
    def test_first_call_returns_false_attempt_1(self):
        tracker = make_tracker()
        should_escalate, attempt = tracker.record_and_check("SyntaxError", "bad code")
        assert should_escalate is False
        assert attempt == 1

    def test_second_call_returns_false_attempt_2(self):
        tracker = make_tracker()
        tracker.record_and_check("SyntaxError", "bad code")
        should_escalate, attempt = tracker.record_and_check("SyntaxError", "bad code")
        assert should_escalate is False
        assert attempt == 2

    def test_third_call_returns_false_attempt_3(self):
        tracker = make_tracker()
        tracker.record_and_check("SyntaxError", "bad code")
        tracker.record_and_check("SyntaxError", "bad code")
        should_escalate, attempt = tracker.record_and_check("SyntaxError", "bad code")
        assert should_escalate is False
        assert attempt == 3

    def test_fourth_call_returns_true_attempt_4(self):
        tracker = make_tracker()
        tracker.record_and_check("SyntaxError", "bad code")
        tracker.record_and_check("SyntaxError", "bad code")
        tracker.record_and_check("SyntaxError", "bad code")
        should_escalate, attempt = tracker.record_and_check("SyntaxError", "bad code")
        assert should_escalate is True
        assert attempt == 4

    def test_different_messages_tracked_separately(self):
        tracker = make_tracker()
        # Fill up first signature
        tracker.record_and_check("SyntaxError", "error A")
        tracker.record_and_check("SyntaxError", "error A")
        tracker.record_and_check("SyntaxError", "error A")
        # Different message gets fresh count
        should_escalate, attempt = tracker.record_and_check("SyntaxError", "error B")
        assert should_escalate is False
        assert attempt == 1

    def test_different_types_tracked_separately(self):
        tracker = make_tracker()
        tracker.record_and_check("SyntaxError", "bad code")
        tracker.record_and_check("SyntaxError", "bad code")
        tracker.record_and_check("SyntaxError", "bad code")
        # Different error type gets fresh count
        should_escalate, attempt = tracker.record_and_check("TypeError", "bad code")
        assert should_escalate is False
        assert attempt == 1

    def test_retry_counts_dict_mutated_in_place(self):
        """CRITICAL: tracker must mutate the shared dict reference, not a copy."""
        shared_counts = {}
        tracker = make_tracker(retry_counts=shared_counts)
        tracker.record_and_check("SyntaxError", "bad code")
        # shared_counts must reflect the update
        assert len(shared_counts) == 1
        assert list(shared_counts.values())[0] == 1

    def test_retry_counts_accumulate_across_calls(self):
        shared_counts = {}
        tracker = make_tracker(retry_counts=shared_counts)
        tracker.record_and_check("SyntaxError", "bad code")
        tracker.record_and_check("SyntaxError", "bad code")
        assert list(shared_counts.values())[0] == 2

    def test_escalation_increments_session_count(self):
        tracker = make_tracker()
        # Hit threshold
        tracker.record_and_check("SyntaxError", "bad code")
        tracker.record_and_check("SyntaxError", "bad code")
        tracker.record_and_check("SyntaxError", "bad code")
        tracker.record_and_check("SyntaxError", "bad code")
        assert tracker._session_escalation_count == 1

    def test_non_escalation_does_not_increment_session_count(self):
        tracker = make_tracker()
        tracker.record_and_check("SyntaxError", "bad code")
        tracker.record_and_check("SyntaxError", "bad code")
        assert tracker._session_escalation_count == 0

    def test_pre_populated_retry_counts_restored_correctly(self):
        """Simulates wake-from-checkpoint where retry_counts already has entries."""
        # Pre-populate to simulate 2 prior failures
        from app.agent.error.classifier import build_error_signature
        sig = build_error_signature("proj-test", "SyntaxError", "bad code")
        shared_counts = {sig: 2}
        tracker = make_tracker(retry_counts=shared_counts)
        # Third call should return (False, 3)
        should_escalate, attempt = tracker.record_and_check("SyntaxError", "bad code")
        assert should_escalate is False
        assert attempt == 3
        # Fourth call should escalate
        should_escalate, attempt = tracker.record_and_check("SyntaxError", "bad code")
        assert should_escalate is True
        assert attempt == 4


# ---------------------------------------------------------------------------
# global_threshold_exceeded
# ---------------------------------------------------------------------------


class TestGlobalThresholdExceeded:
    def test_returns_false_initially(self):
        tracker = make_tracker()
        assert tracker.global_threshold_exceeded() is False

    def test_returns_false_below_threshold(self):
        tracker = make_tracker()
        # 4 escalations (below threshold of 5)
        for i in range(4):
            tracker.record_and_check(f"Error{i}", "msg")
            tracker.record_and_check(f"Error{i}", "msg")
            tracker.record_and_check(f"Error{i}", "msg")
            tracker.record_and_check(f"Error{i}", "msg")  # escalation #i+1
        assert tracker._session_escalation_count == 4
        assert tracker.global_threshold_exceeded() is False

    def test_returns_true_at_threshold(self):
        tracker = make_tracker()
        # 5 escalations (exactly at threshold)
        for i in range(5):
            for _ in range(4):  # 4 calls to trigger escalation on 4th
                tracker.record_and_check(f"ErrorType{i}", f"unique message for error {i}")
        assert tracker._session_escalation_count == 5
        assert tracker.global_threshold_exceeded() is True

    def test_returns_true_above_threshold(self):
        tracker = make_tracker()
        # 6 escalations (above threshold)
        for i in range(6):
            for _ in range(4):
                tracker.record_and_check(f"ErrType{i}", f"msg variant {i}")
        assert tracker.global_threshold_exceeded() is True


# ---------------------------------------------------------------------------
# reset_signature
# ---------------------------------------------------------------------------


class TestResetSignature:
    def test_reset_clears_retry_count(self):
        tracker = make_tracker()
        tracker.record_and_check("SyntaxError", "bad code")
        tracker.record_and_check("SyntaxError", "bad code")
        # Should have 2 attempts stored
        assert len(tracker._retry_counts) == 1
        # Reset
        tracker.reset_signature("SyntaxError", "bad code")
        # Should be empty now
        assert len(tracker._retry_counts) == 0

    def test_reset_allows_fresh_attempts(self):
        tracker = make_tracker()
        # Fill to just before escalation
        tracker.record_and_check("SyntaxError", "bad code")
        tracker.record_and_check("SyntaxError", "bad code")
        tracker.record_and_check("SyntaxError", "bad code")
        # Reset (simulates founder input)
        tracker.reset_signature("SyntaxError", "bad code")
        # Fresh first attempt
        should_escalate, attempt = tracker.record_and_check("SyntaxError", "bad code")
        assert should_escalate is False
        assert attempt == 1

    def test_reset_nonexistent_signature_is_safe(self):
        tracker = make_tracker()
        # Should not raise even if signature doesn't exist
        tracker.reset_signature("SyntaxError", "nonexistent error")

    def test_reset_only_affects_target_signature(self):
        tracker = make_tracker()
        tracker.record_and_check("SyntaxError", "error A")
        tracker.record_and_check("TypeError", "error B")
        # Reset only the first
        tracker.reset_signature("SyntaxError", "error A")
        assert len(tracker._retry_counts) == 1
        # TypeError entry still exists
        assert list(tracker._retry_counts.values())[0] == 1

    def test_reset_mutates_shared_dict(self):
        shared_counts = {}
        tracker = make_tracker(retry_counts=shared_counts)
        tracker.record_and_check("SyntaxError", "bad code")
        assert len(shared_counts) == 1
        tracker.reset_signature("SyntaxError", "bad code")
        # Must be reflected in shared_counts
        assert len(shared_counts) == 0


# ---------------------------------------------------------------------------
# record_escalation — non-fatal DB persistence
# ---------------------------------------------------------------------------


class TestRecordEscalation:
    @pytest.mark.asyncio
    async def test_returns_none_when_no_db(self):
        tracker = make_tracker(db_session=None)
        result = await tracker.record_escalation(
            error_type="SyntaxError",
            error_message="bad code",
            attempts=["Tried approach A", "Tried approach B"],
            recommended_action="skip_feature",
            plain_english_problem="The code has a syntax issue",
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_on_db_failure(self):
        """Non-fatal: DB failure returns None, never raises."""
        from unittest.mock import AsyncMock, MagicMock

        db = AsyncMock()
        db.add = MagicMock()
        db.commit = AsyncMock(side_effect=Exception("DB connection error"))

        tracker = make_tracker(db_session=db)
        # Should not raise
        result = await tracker.record_escalation(
            error_type="SyntaxError",
            error_message="bad code",
            attempts=["Tried approach A"],
            recommended_action="skip_feature",
            plain_english_problem="The code has a syntax issue",
        )
        assert result is None


# ---------------------------------------------------------------------------
# _build_retry_tool_result
# ---------------------------------------------------------------------------


class TestBuildRetryToolResult:
    def test_includes_approach_failed_header(self):
        result = _build_retry_tool_result(
            error_type="SyntaxError",
            error_message="invalid syntax",
            attempt_num=1,
            original_intent="Create a login form",
        )
        assert "APPROACH 1 FAILED" in result

    def test_includes_error_type_and_message(self):
        result = _build_retry_tool_result(
            error_type="SyntaxError",
            error_message="invalid syntax",
            attempt_num=1,
            original_intent="Create a login form",
        )
        assert "SyntaxError" in result
        assert "invalid syntax" in result

    def test_includes_original_intent(self):
        result = _build_retry_tool_result(
            error_type="TypeError",
            error_message="bad types",
            attempt_num=2,
            original_intent="Create a login form",
        )
        assert "Create a login form" in result

    def test_includes_attempt_number(self):
        result = _build_retry_tool_result(
            error_type="TypeError",
            error_message="bad types",
            attempt_num=2,
            original_intent="Create a login form",
        )
        assert "2" in result

    def test_instructs_different_approach(self):
        result = _build_retry_tool_result(
            error_type="TypeError",
            error_message="bad types",
            attempt_num=3,
            original_intent="Build the API",
        )
        # Must instruct the model to try a different approach
        lowered = result.lower()
        assert any(phrase in lowered for phrase in ["different", "replan", "fundamentally", "not repeat"])

    def test_returns_string(self):
        result = _build_retry_tool_result("TypeError", "bad types", 1, "goal")
        assert isinstance(result, str)
        assert len(result) > 0


# ---------------------------------------------------------------------------
# _build_escalation_options
# ---------------------------------------------------------------------------


class TestBuildEscalationOptions:
    def test_never_retry_returns_credentials_and_skip(self):
        options = _build_escalation_options("PermissionError", ErrorCategory.NEVER_RETRY)
        values = [o["value"] for o in options]
        assert "provide_credentials" in values
        assert "skip_feature" in values

    def test_never_retry_has_2_options(self):
        options = _build_escalation_options("PermissionError", ErrorCategory.NEVER_RETRY)
        assert len(options) == 2

    def test_code_error_returns_3_options(self):
        options = _build_escalation_options("SyntaxError", ErrorCategory.CODE_ERROR)
        assert len(options) == 3

    def test_code_error_includes_skip_simpler_guidance(self):
        options = _build_escalation_options("SyntaxError", ErrorCategory.CODE_ERROR)
        values = [o["value"] for o in options]
        assert "skip_feature" in values
        assert "simpler_version" in values
        assert "provide_guidance" in values

    def test_env_error_returns_3_options(self):
        options = _build_escalation_options("ConnectionError", ErrorCategory.ENV_ERROR)
        assert len(options) == 3

    def test_env_error_includes_skip_simpler_guidance(self):
        options = _build_escalation_options("ConnectionError", ErrorCategory.ENV_ERROR)
        values = [o["value"] for o in options]
        assert "skip_feature" in values
        assert "simpler_version" in values
        assert "provide_guidance" in values

    def test_each_option_has_required_fields(self):
        options = _build_escalation_options("SyntaxError", ErrorCategory.CODE_ERROR)
        for option in options:
            assert "value" in option
            assert "label" in option
            assert "description" in option

    def test_options_are_non_empty_strings(self):
        options = _build_escalation_options("SyntaxError", ErrorCategory.CODE_ERROR)
        for option in options:
            assert len(option["value"]) > 0
            assert len(option["label"]) > 0
            assert len(option["description"]) > 0
