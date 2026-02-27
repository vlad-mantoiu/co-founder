"""Unit tests for build_system_prompt() — RED phase.

Verifies that the system prompt builder assembles verbatim founder context
(Idea Brief + Understanding QnA + Build Plan) with the co-founder persona,
collaborative voice, narration instructions, and critical guardrails.
"""

import pytest

from app.agent.loop.system_prompt import build_system_prompt


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

MINIMAL_IDEA_BRIEF: dict = {"problem": "placeholder", "target_user": "placeholder"}
MINIMAL_QNA: list[dict] = []
MINIMAL_BUILD_PLAN: dict = {"phases": []}


# ---------------------------------------------------------------------------
# Test 1: Idea Brief injected verbatim
# ---------------------------------------------------------------------------


def test_idea_brief_in_prompt() -> None:
    """Both 'problem' and 'target_user' values appear verbatim in the output."""
    idea_brief = {
        "problem": "Founders waste time on boilerplate",
        "target_user": "Non-technical founders",
    }
    result = build_system_prompt(
        idea_brief=idea_brief,
        understanding_qna=[],
        build_plan={},
    )
    assert "Founders waste time on boilerplate" in result
    assert "Non-technical founders" in result


# ---------------------------------------------------------------------------
# Test 2: Understanding QnA injected verbatim
# ---------------------------------------------------------------------------


def test_qna_in_prompt() -> None:
    """All four strings (both questions and both answers) appear verbatim."""
    qna = [
        {"question": "What is your revenue model?", "answer": "SaaS subscriptions"},
        {"question": "Who is your competition?", "answer": "Bubble, Webflow"},
    ]
    result = build_system_prompt(
        idea_brief=MINIMAL_IDEA_BRIEF,
        understanding_qna=qna,
        build_plan={},
    )
    assert "What is your revenue model?" in result
    assert "SaaS subscriptions" in result
    assert "Who is your competition?" in result
    assert "Bubble, Webflow" in result


# ---------------------------------------------------------------------------
# Test 3: Empty QnA list does not crash
# ---------------------------------------------------------------------------


def test_empty_qna_no_crash() -> None:
    """Passing an empty QnA list returns a string without raising."""
    result = build_system_prompt(
        idea_brief=MINIMAL_IDEA_BRIEF,
        understanding_qna=[],
        build_plan={},
    )
    assert isinstance(result, str)
    assert len(result) > 0


# ---------------------------------------------------------------------------
# Test 4: Build plan content appears in prompt
# ---------------------------------------------------------------------------


def test_build_plan_in_prompt() -> None:
    """Phase names from the build plan appear in the returned string."""
    build_plan = {"phases": [{"name": "auth"}, {"name": "dashboard"}]}
    result = build_system_prompt(
        idea_brief=MINIMAL_IDEA_BRIEF,
        understanding_qna=[],
        build_plan=build_plan,
    )
    assert "auth" in result
    assert "dashboard" in result


# ---------------------------------------------------------------------------
# Test 5: Co-founder persona identity present
# ---------------------------------------------------------------------------


def test_persona_identity_present() -> None:
    """The returned string contains 'co-founder' (case-insensitive)."""
    result = build_system_prompt(
        idea_brief=MINIMAL_IDEA_BRIEF,
        understanding_qna=MINIMAL_QNA,
        build_plan=MINIMAL_BUILD_PLAN,
    )
    assert "co-founder" in result.lower()


# ---------------------------------------------------------------------------
# Test 6: Critical guardrails present
# ---------------------------------------------------------------------------


def test_guardrails_present() -> None:
    """The returned string contains 'Do not delete' or 'do not delete'."""
    result = build_system_prompt(
        idea_brief=MINIMAL_IDEA_BRIEF,
        understanding_qna=MINIMAL_QNA,
        build_plan=MINIMAL_BUILD_PLAN,
    )
    assert "do not delete" in result.lower()


# ---------------------------------------------------------------------------
# Test 7: Collaborative voice present
# ---------------------------------------------------------------------------


def test_collaborative_voice() -> None:
    """The returned string contains 'we' or 'us' — collaborative voice."""
    result = build_system_prompt(
        idea_brief=MINIMAL_IDEA_BRIEF,
        understanding_qna=MINIMAL_QNA,
        build_plan=MINIMAL_BUILD_PLAN,
    )
    assert "we" in result.lower() or "us" in result.lower()


# ---------------------------------------------------------------------------
# Test 8: Narration instructions present
# ---------------------------------------------------------------------------


def test_narration_instructions_present() -> None:
    """The returned string contains narration instructions and narrate() tool reference
    (Phase 44: narration via native tool call, not inline text)."""
    result = build_system_prompt(
        idea_brief=MINIMAL_IDEA_BRIEF,
        understanding_qna=MINIMAL_QNA,
        build_plan=MINIMAL_BUILD_PLAN,
    )
    # Phase 44: narration section still present, but now instructs agent to call narrate()
    assert "Narration" in result
    assert "narrate()" in result
