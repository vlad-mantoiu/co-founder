"""Tests for RunnerReal with mocked LLM calls.

All tests mock create_tracked_llm to avoid real API calls.
These verify prompt construction, response parsing, and error handling.
"""
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.agent.runner_real import RunnerReal

pytestmark = pytest.mark.unit


def _mock_llm_response(content: str):
    """Create a mock LLM response with .content attribute."""
    response = MagicMock()
    response.content = content
    return response


def _mock_create_tracked_llm(response_content: str):
    """Create a mock create_tracked_llm that returns LLM with preset response."""
    mock_llm = AsyncMock()
    mock_llm.ainvoke = AsyncMock(return_value=_mock_llm_response(response_content))

    async def mock_factory(**kwargs):
        return mock_llm

    return mock_factory, mock_llm


@pytest.fixture
def runner():
    return RunnerReal()


class TestGenerateUnderstandingQuestions:
    @pytest.mark.asyncio
    async def test_returns_question_list(self, runner):
        questions = [
            {"id": "uq1", "text": "Who have we talked to?", "input_type": "textarea", "required": True, "options": None, "follow_up_hint": "Be specific"},
            {"id": "uq2", "text": "What's our biggest risk?", "input_type": "textarea", "required": True, "options": None, "follow_up_hint": None},
        ]
        factory, _ = _mock_create_tracked_llm(json.dumps(questions))

        with patch("app.agent.runner_real.create_tracked_llm", side_effect=factory):
            result = await runner.generate_understanding_questions({
                "idea_text": "An inventory tracker for small shops",
                "user_id": "user_123",
                "session_id": "sess_abc",
                "tier": "bootstrapper",
            })

        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]["id"] == "uq1"

    @pytest.mark.asyncio
    async def test_handles_fenced_json(self, runner):
        questions = [{"id": "uq1", "text": "Test?", "input_type": "text", "required": True, "options": None, "follow_up_hint": None}]
        fenced = f"```json\n{json.dumps(questions)}\n```"
        factory, _ = _mock_create_tracked_llm(fenced)

        with patch("app.agent.runner_real.create_tracked_llm", side_effect=factory):
            result = await runner.generate_understanding_questions({
                "idea_text": "test", "user_id": "u1", "session_id": "s1",
            })

        assert len(result) == 1


class TestGenerateIdeaBrief:
    @pytest.mark.asyncio
    async def test_returns_brief_with_confidence(self, runner):
        brief = {
            "problem_statement": "Small shops waste time on inventory",
            "target_user": "Retail shop owners",
            "value_prop": "Simple inventory tracking",
            "confidence_scores": {
                "problem_statement": "strong",
                "target_user": "moderate",
                "value_prop": "needs_depth",
            },
            "_schema_version": 1,
        }
        factory, _ = _mock_create_tracked_llm(json.dumps(brief))

        with patch("app.agent.runner_real.create_tracked_llm", side_effect=factory):
            result = await runner.generate_idea_brief(
                idea="Inventory tracker",
                questions=[{"id": "q1", "text": "Who?"}],
                answers={"q1": "Shop owners"},
            )

        assert "confidence_scores" in result
        assert result["confidence_scores"]["problem_statement"] == "strong"


class TestCheckQuestionRelevance:
    @pytest.mark.asyncio
    async def test_returns_relevance_dict(self, runner):
        relevance = {"needs_regeneration": False, "preserve_indices": [0, 1]}
        factory, _ = _mock_create_tracked_llm(json.dumps(relevance))

        with patch("app.agent.runner_real.create_tracked_llm", side_effect=factory):
            result = await runner.check_question_relevance(
                idea="Test idea",
                answered=[{"id": "q1", "text": "Q1"}],
                answers={"q1": "Answer 1"},
                remaining=[{"id": "q2", "text": "Q2"}],
            )

        assert "needs_regeneration" in result
        assert isinstance(result["preserve_indices"], list)


class TestAssessSectionConfidence:
    @pytest.mark.asyncio
    async def test_returns_strong(self, runner):
        factory, _ = _mock_create_tracked_llm("strong")

        with patch("app.agent.runner_real.create_tracked_llm", side_effect=factory):
            result = await runner.assess_section_confidence(
                "problem_statement",
                "We validated this through 12 customer interviews with specific data points.",
            )

        assert result == "strong"

    @pytest.mark.asyncio
    async def test_extracts_from_verbose_response(self, runner):
        factory, _ = _mock_create_tracked_llm("Based on the evidence, I would assess this as moderate confidence.")

        with patch("app.agent.runner_real.create_tracked_llm", side_effect=factory):
            result = await runner.assess_section_confidence("target_user", "Some vague description")

        assert result == "moderate"

    @pytest.mark.asyncio
    async def test_defaults_to_moderate(self, runner):
        factory, _ = _mock_create_tracked_llm("I'm not sure how to assess this.")

        with patch("app.agent.runner_real.create_tracked_llm", side_effect=factory):
            result = await runner.assess_section_confidence("value_prop", "Something")

        assert result == "moderate"


class TestGenerateExecutionOptions:
    @pytest.mark.asyncio
    async def test_returns_options(self, runner):
        options = {
            "options": [
                {"id": "fast-mvp", "name": "Fast MVP", "is_recommended": True, "risk_level": "low"},
                {"id": "full", "name": "Full Build", "is_recommended": False, "risk_level": "high"},
            ],
            "recommended_id": "fast-mvp",
        }
        factory, _ = _mock_create_tracked_llm(json.dumps(options))

        with patch("app.agent.runner_real.create_tracked_llm", side_effect=factory):
            result = await runner.generate_execution_options(
                brief={"problem_statement": "Test"},
            )

        assert "options" in result
        assert len(result["options"]) == 2
        assert result["recommended_id"] == "fast-mvp"


class TestGenerateArtifacts:
    @pytest.mark.asyncio
    async def test_returns_artifact_cascade(self, runner):
        artifacts = {
            "brief": {"problem_statement": "Test", "_schema_version": 1},
            "mvp_scope": {"core_features": []},
            "milestones": {"milestones": []},
            "risk_log": {"technical_risks": []},
            "how_it_works": {"user_journey": []},
        }
        factory, _ = _mock_create_tracked_llm(json.dumps(artifacts))

        with patch("app.agent.runner_real.create_tracked_llm", side_effect=factory):
            result = await runner.generate_artifacts(
                brief={"problem_statement": "Test"},
            )

        assert "brief" in result
        assert "mvp_scope" in result
        assert "milestones" in result
        assert "risk_log" in result
        assert "how_it_works" in result


class TestJsonRetryOnMalformedOutput:
    @pytest.mark.asyncio
    async def test_retries_with_strict_prompt_on_bad_json(self, runner):
        """First call returns bad JSON, second call returns valid JSON."""
        bad_response = _mock_llm_response("Here are the questions:\n{invalid json}")
        good_response = _mock_llm_response('[{"id": "q1", "text": "Test?", "input_type": "text", "required": true, "options": null, "follow_up_hint": null}]')

        mock_llm = AsyncMock()
        mock_llm.ainvoke = AsyncMock(side_effect=[bad_response, good_response])

        async def mock_factory(**kwargs):
            return mock_llm

        with patch("app.agent.runner_real.create_tracked_llm", side_effect=mock_factory):
            result = await runner.generate_understanding_questions({
                "idea_text": "test", "user_id": "u1", "session_id": "s1",
            })

        assert len(result) == 1
        assert mock_llm.ainvoke.call_count == 2


class TestTierDifferentiation:
    @pytest.mark.asyncio
    async def test_bootstrapper_gets_6_8_questions(self, runner):
        """Bootstrapper tier produces 6-8 question count in prompt."""
        questions = [{"id": f"uq{i}", "text": f"Q{i}?", "input_type": "textarea", "required": True, "options": None, "follow_up_hint": None} for i in range(7)]
        factory, mock_llm = _mock_create_tracked_llm(json.dumps(questions))

        with patch("app.agent.runner_real.create_tracked_llm", side_effect=factory):
            await runner.generate_understanding_questions({
                "idea_text": "test", "user_id": "u1", "session_id": "s1",
                "tier": "bootstrapper",
            })

        call_args = mock_llm.ainvoke.call_args[0][0]
        system_content = call_args[0].content
        assert "6-8" in system_content

    @pytest.mark.asyncio
    async def test_cto_scale_gets_14_16_questions(self, runner):
        """cto_scale tier produces 14-16 question count in prompt."""
        questions = [{"id": f"uq{i}", "text": f"Q{i}?", "input_type": "textarea", "required": True, "options": None, "follow_up_hint": None} for i in range(15)]
        factory, mock_llm = _mock_create_tracked_llm(json.dumps(questions))

        with patch("app.agent.runner_real.create_tracked_llm", side_effect=factory):
            await runner.generate_understanding_questions({
                "idea_text": "test", "user_id": "u1", "session_id": "s1",
                "tier": "cto_scale",
            })

        call_args = mock_llm.ainvoke.call_args[0][0]
        system_content = call_args[0].content
        assert "14-16" in system_content


class TestCofounderVoice:
    @pytest.mark.asyncio
    async def test_system_prompt_uses_we_voice(self, runner):
        """Verify system prompts contain co-founder voice markers."""
        factory, mock_llm = _mock_create_tracked_llm('[]')

        with patch("app.agent.runner_real.create_tracked_llm", side_effect=factory):
            await runner.generate_understanding_questions({
                "idea_text": "test", "user_id": "u1", "session_id": "s1",
            })

        # Check the system message content
        call_args = mock_llm.ainvoke.call_args[0][0]  # first positional arg (messages list)
        system_content = call_args[0].content  # first message is system
        assert "co-founder" in system_content.lower() or "we" in system_content.lower()
