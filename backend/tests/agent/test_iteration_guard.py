"""Unit tests for IterationGuard safety guards (AGNT-06).

Tests cover:
- Iteration cap: raises IterationCapError at max+1
- Repetition detection: raises RepetitionError on 3rd identical call in 10-call window
- Truncation: middle-truncates text >1000 words, preserving first 500 and last 500

All tests are async (pytest-asyncio auto mode).
"""

import pytest
from app.agent.loop.safety import IterationGuard, IterationCapError, RepetitionError


# ---------------------------------------------------------------------------
# Iteration cap tests
# ---------------------------------------------------------------------------


def test_iteration_cap_allows_within_limit():
    """5 calls on a guard with max=5 should not raise."""
    guard = IterationGuard(max_tool_calls=5)
    for _ in range(5):
        guard.check_iteration_cap()  # Should not raise


def test_iteration_cap_raises_on_exceed():
    """6th call on a guard with max=5 must raise IterationCapError containing '5'."""
    guard = IterationGuard(max_tool_calls=5)
    for _ in range(5):
        guard.check_iteration_cap()

    with pytest.raises(IterationCapError, match="5"):
        guard.check_iteration_cap()


# ---------------------------------------------------------------------------
# Repetition detection tests
# ---------------------------------------------------------------------------


def test_repetition_detection_allows_two_identical():
    """Two identical calls in a row should NOT raise."""
    guard = IterationGuard()
    guard.check_repetition("bash", {"command": "ls"})
    guard.check_repetition("bash", {"command": "ls"})  # Should not raise


def test_repetition_detection_raises_on_three_identical():
    """Third identical call must raise RepetitionError containing the tool name."""
    guard = IterationGuard()
    guard.check_repetition("bash", {"command": "ls"})
    guard.check_repetition("bash", {"command": "ls"})

    with pytest.raises(RepetitionError, match="bash"):
        guard.check_repetition("bash", {"command": "ls"})


def test_repetition_window_slides():
    """Window should slide past old entries.

    Pattern: 2 calls to tool A, then 8 different calls, then 1 call to tool A.
    The 10-slot window should have slid past the first 2 A calls, so only 1 A
    remains in window — no error should be raised.
    """
    guard = IterationGuard()
    # First 2 identical calls to A
    guard.check_repetition("tool_a", {"x": 1})
    guard.check_repetition("tool_a", {"x": 1})
    # 8 different calls that fill the 10-slot window, pushing out both A calls
    for i in range(8):
        guard.check_repetition(f"tool_{i}", {"i": i})
    # This A call is now alone in the window — should not raise
    guard.check_repetition("tool_a", {"x": 1})  # Should not raise


def test_repetition_different_args_not_detected():
    """Three calls with same tool name but different args should NOT raise."""
    guard = IterationGuard()
    guard.check_repetition("bash", {"command": "ls"})
    guard.check_repetition("bash", {"command": "pwd"})
    guard.check_repetition("bash", {"command": "cat"})  # Should not raise


# ---------------------------------------------------------------------------
# Truncation tests
# ---------------------------------------------------------------------------


def test_truncate_short_text_unchanged():
    """Text with 500 words should be returned unchanged."""
    guard = IterationGuard()
    text = " ".join(f"word{i}" for i in range(500))
    result = guard.truncate_tool_result(text)
    assert result == text


def test_truncate_long_text_middle_omitted():
    """Text with 2000 words should return first 500 + [1000 words omitted] + last 500."""
    guard = IterationGuard()
    words = [f"word{i}" for i in range(2000)]
    text = " ".join(words)
    result = guard.truncate_tool_result(text)

    # Should contain the omission marker
    assert "[1000 words omitted]" in result

    # Should start with the first 500 words
    expected_head = " ".join(words[:500])
    assert result.startswith(expected_head)

    # Should end with the last 500 words
    expected_tail = " ".join(words[-500:])
    assert result.endswith(expected_tail)


def test_truncate_exact_limit_unchanged():
    """Text with exactly 1000 words should be returned unchanged."""
    guard = IterationGuard()
    text = " ".join(f"word{i}" for i in range(1000))
    result = guard.truncate_tool_result(text)
    assert result == text
