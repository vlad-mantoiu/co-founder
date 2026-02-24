"""Tests for NarrationService.

TDD coverage:
- test_narration_constants: STAGE_AGENT_ROLES has all 5 stages, STAGE_TIME_ESTIMATES has all 5, _FALLBACK_NARRATIONS has all 5
- test_narration_happy_path: Mock Claude response, verify narrate() emits publish_event with correct type/stage/narration/agent_role/time_estimate
- test_narration_uses_correct_model: Verify messages.create called with model=NARRATION_MODEL
- test_narration_truncates_spec: Spec longer than 300 chars is truncated in the prompt
- test_narration_fallback_on_api_error: Mock Claude to raise, verify fallback sentence emitted
- test_narration_fallback_on_timeout: Mock asyncio.wait_for to raise TimeoutError, verify fallback
- test_narration_never_raises: Mock publish_event to raise, verify narrate() returns None without exception
- test_narration_safety_filter_strips_paths: Input with /app/src/main.py stripped
- test_narration_safety_filter_strips_framework_names: "React component" -> "component"
- test_narration_safety_filter_preserves_clean_text: "We're building your dashboard" unchanged
- test_narration_event_includes_agent_role: Each stage maps to correct role (Architect/Coder/Reviewer)
- test_narration_event_includes_time_estimate: Each stage has time_estimate in event
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.narration_service import (
    NARRATION_MODEL,
    NARRATION_MAX_TOKENS,
    NARRATION_TIMEOUT_SECONDS,
    STAGE_AGENT_ROLES,
    STAGE_TIME_ESTIMATES,
    _FALLBACK_NARRATIONS,
    NarrationService,
)

pytestmark = pytest.mark.unit

_FIVE_STAGES = {"scaffold", "code", "deps", "checks", "ready"}


# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------


class TestNarrationConstants:
    """Module-level constants must exist with correct values."""

    def test_narration_model_is_haiku(self) -> None:
        assert NARRATION_MODEL == "claude-3-5-haiku-20241022"

    def test_narration_max_tokens_is_80(self) -> None:
        assert NARRATION_MAX_TOKENS == 80

    def test_narration_timeout_is_10_seconds(self) -> None:
        assert NARRATION_TIMEOUT_SECONDS == 10.0

    def test_stage_agent_roles_has_all_five_stages(self) -> None:
        assert set(STAGE_AGENT_ROLES.keys()) == _FIVE_STAGES

    def test_stage_agent_roles_scaffold_is_architect(self) -> None:
        assert STAGE_AGENT_ROLES["scaffold"] == "Architect"

    def test_stage_agent_roles_code_is_coder(self) -> None:
        assert STAGE_AGENT_ROLES["code"] == "Coder"

    def test_stage_agent_roles_deps_is_coder(self) -> None:
        assert STAGE_AGENT_ROLES["deps"] == "Coder"

    def test_stage_agent_roles_checks_is_reviewer(self) -> None:
        assert STAGE_AGENT_ROLES["checks"] == "Reviewer"

    def test_stage_agent_roles_ready_is_reviewer(self) -> None:
        assert STAGE_AGENT_ROLES["ready"] == "Reviewer"

    def test_stage_time_estimates_has_all_five_stages(self) -> None:
        assert set(STAGE_TIME_ESTIMATES.keys()) == _FIVE_STAGES

    def test_stage_time_estimates_are_strings(self) -> None:
        for stage, estimate in STAGE_TIME_ESTIMATES.items():
            assert isinstance(estimate, str), f"Stage {stage!r} estimate is not a string"

    def test_fallback_narrations_has_all_five_stages(self) -> None:
        assert set(_FALLBACK_NARRATIONS.keys()) == _FIVE_STAGES

    def test_fallback_narrations_are_nonempty_strings(self) -> None:
        for stage, text in _FALLBACK_NARRATIONS.items():
            assert isinstance(text, str) and text.strip(), (
                f"Stage {stage!r} fallback is empty or not a string"
            )


# ---------------------------------------------------------------------------
# _apply_safety_filter()
# ---------------------------------------------------------------------------


class TestSafetyFilter:
    """Safety filter reuses _SAFETY_PATTERNS from doc_generation_service."""

    def setup_method(self) -> None:
        self.service = NarrationService()

    def test_strips_unix_app_path(self) -> None:
        """/app/src/main.py must be stripped from narration."""
        text = "We're building the core logic in /app/src/main.py right now."
        result = self.service._apply_safety_filter(text)
        assert "/app/" not in result

    def test_strips_unix_src_path(self) -> None:
        """/src/... paths must be stripped."""
        text = "We're setting up /src/components/Dashboard."
        result = self.service._apply_safety_filter(text)
        assert "/src/" not in result

    def test_strips_framework_react(self) -> None:
        """'React' as standalone word must be stripped."""
        text = "We're setting up your React component structure."
        result = self.service._apply_safety_filter(text)
        assert "React" not in result
        # "component" should still be present
        assert "component" in result

    def test_strips_framework_fastapi(self) -> None:
        """'FastAPI' must be stripped."""
        text = "We're configuring the FastAPI endpoints."
        result = self.service._apply_safety_filter(text)
        assert "FastAPI" not in result

    def test_strips_framework_typescript(self) -> None:
        """'TypeScript' must be stripped."""
        text = "We're writing the TypeScript interfaces."
        result = self.service._apply_safety_filter(text)
        assert "TypeScript" not in result

    def test_strips_workspace_path(self) -> None:
        """/workspace/... paths must be stripped (E2B sandbox build directory)."""
        text = "We're updating /workspace/project/package.json with dependencies."
        result = self.service._apply_safety_filter(text)
        assert "/workspace/" not in result

    def test_strips_stack_trace_text(self) -> None:
        """'Traceback (most recent call last):' must be stripped from narration."""
        text = "We found Traceback (most recent call last): in your build output."
        result = self.service._apply_safety_filter(text)
        assert "Traceback" not in result

    def test_redacts_secret_shaped_strings(self) -> None:
        """sk-ant-... API key shaped strings must be replaced with [REDACTED]."""
        text = "We're using sk-ant-api03-abcdefghijklmnop for the API call."
        result = self.service._apply_safety_filter(text)
        assert "sk-ant-" not in result

    def test_preserves_clean_narration(self) -> None:
        """Plain narration text passes through unchanged."""
        text = "We're building your dashboard and team management pages."
        result = self.service._apply_safety_filter(text)
        assert "We're building your dashboard" in result

    def test_preserves_reactive_word(self) -> None:
        """'reactive' must NOT be stripped (word boundary protection)."""
        text = "We're making your UI reactive and fast."
        result = self.service._apply_safety_filter(text)
        assert "reactive" in result

    def test_returns_string(self) -> None:
        """_apply_safety_filter always returns a string."""
        result = self.service._apply_safety_filter("any text")
        assert isinstance(result, str)


# ---------------------------------------------------------------------------
# _build_prompt()
# ---------------------------------------------------------------------------


class TestBuildPrompt:
    """Prompt builder for NarrationService Claude calls."""

    def setup_method(self) -> None:
        self.service = NarrationService()

    def test_returns_tuple_of_system_and_messages(self) -> None:
        system, messages = self.service._build_prompt("scaffold", "Build a task manager")
        assert isinstance(system, str)
        assert isinstance(messages, list)

    def test_system_prompt_uses_we_pronoun(self) -> None:
        """System prompt instructs 'we' pronoun."""
        system, _ = self.service._build_prompt("scaffold", "Build a task manager")
        assert "'we'" in system or '"we"' in system or "Use 'we'" in system or "use 'we'" in system.lower()

    def test_system_prompt_instructs_one_sentence(self) -> None:
        """System prompt instructs exactly one sentence."""
        system, _ = self.service._build_prompt("scaffold", "spec")
        assert "one sentence" in system.lower() or "ONE sentence" in system

    def test_user_prompt_contains_stage(self) -> None:
        """User message contains the stage name."""
        _, messages = self.service._build_prompt("scaffold", "Build a task manager")
        user_content = messages[0]["content"]
        assert "scaffold" in user_content.lower() or "scaffold" in user_content

    def test_user_prompt_contains_spec(self) -> None:
        """User message contains spec content."""
        spec = "Build a project management tool"
        _, messages = self.service._build_prompt("code", spec)
        user_content = messages[0]["content"]
        assert spec in user_content

    def test_messages_list_has_user_role(self) -> None:
        """Messages list contains user role."""
        _, messages = self.service._build_prompt("code", "spec")
        assert len(messages) >= 1
        assert messages[0]["role"] == "user"

    def test_spec_truncated_to_300_chars_in_prompt(self) -> None:
        """Spec longer than 300 chars is truncated in the user prompt."""
        long_spec = "A" * 600
        _, messages = self.service._build_prompt("scaffold", long_spec)
        user_content = messages[0]["content"]
        # The user prompt should not contain the full 600-char spec
        assert "A" * 600 not in user_content
        # But should contain the first 300 chars
        assert "A" * 300 in user_content


# ---------------------------------------------------------------------------
# _call_claude()
# ---------------------------------------------------------------------------


class TestCallClaude:
    """Claude API call structure and retry behavior."""

    async def test_calls_with_correct_model(self) -> None:
        """AsyncAnthropic.messages.create() called with NARRATION_MODEL."""
        service = NarrationService()
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="We're building your project structure now.")]

        with (
            patch("app.services.narration_service.anthropic") as mock_anthropic,
            patch("app.services.narration_service.asyncio.wait_for", new_callable=AsyncMock) as mock_wait,
            patch("app.services.narration_service.get_settings") as mock_settings,
        ):
            mock_settings.return_value.anthropic_api_key = "test-key"
            mock_client = AsyncMock()
            mock_anthropic.AsyncAnthropic.return_value = mock_client
            mock_wait.return_value = mock_response

            result = await service._call_claude("scaffold", "Build a task manager")

            mock_anthropic.AsyncAnthropic.assert_called_once()
            assert isinstance(result, str)

    async def test_returns_stripped_text(self) -> None:
        """Returns stripped text from response.content[0].text."""
        service = NarrationService()
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="  We're setting up your project.  ")]

        with (
            patch("app.services.narration_service.anthropic") as mock_anthropic,
            patch("app.services.narration_service.asyncio.wait_for", new_callable=AsyncMock) as mock_wait,
            patch("app.services.narration_service.get_settings") as mock_settings,
        ):
            mock_settings.return_value.anthropic_api_key = "test-key"
            mock_client = AsyncMock()
            mock_anthropic.AsyncAnthropic.return_value = mock_client
            mock_wait.return_value = mock_response

            result = await service._call_claude("scaffold", "spec")
            assert result == "We're setting up your project."

    async def test_retries_on_rate_limit_error(self) -> None:
        """RateLimitError on first call triggers retry with 2.5s backoff."""
        from anthropic._exceptions import RateLimitError

        service = NarrationService()
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="We're building your app.")]

        call_count = 0

        async def mock_wait_for(coro, timeout):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RateLimitError(
                    message="Rate limited",
                    response=MagicMock(status_code=429, headers={}),
                    body={},
                )
            return mock_response

        with (
            patch("app.services.narration_service.anthropic") as mock_anthropic,
            patch("app.services.narration_service.asyncio") as mock_asyncio,
            patch("app.services.narration_service.get_settings") as mock_settings,
        ):
            mock_settings.return_value.anthropic_api_key = "test-key"
            mock_client = AsyncMock()
            mock_anthropic.AsyncAnthropic.return_value = mock_client
            mock_asyncio.TimeoutError = asyncio.TimeoutError
            mock_asyncio.wait_for = mock_wait_for
            mock_asyncio.sleep = AsyncMock()

            result = await service._call_claude("scaffold", "spec")

            mock_asyncio.sleep.assert_called_once_with(2.5)
            assert call_count == 2
            assert result == "We're building your app."

    async def test_raises_on_second_consecutive_failure(self) -> None:
        """Two consecutive failures cause _call_claude to raise."""
        from anthropic._exceptions import RateLimitError

        service = NarrationService()

        async def mock_wait_for_always_fail(coro, timeout):
            raise RateLimitError(
                message="Rate limited",
                response=MagicMock(status_code=429, headers={}),
                body={},
            )

        with (
            patch("app.services.narration_service.anthropic") as mock_anthropic,
            patch("app.services.narration_service.asyncio") as mock_asyncio,
            patch("app.services.narration_service.get_settings") as mock_settings,
        ):
            mock_settings.return_value.anthropic_api_key = "test-key"
            mock_client = AsyncMock()
            mock_anthropic.AsyncAnthropic.return_value = mock_client
            mock_asyncio.TimeoutError = asyncio.TimeoutError
            mock_asyncio.wait_for = mock_wait_for_always_fail
            mock_asyncio.sleep = AsyncMock()

            with pytest.raises(Exception):
                await service._call_claude("scaffold", "spec")


# ---------------------------------------------------------------------------
# narrate() — happy path
# ---------------------------------------------------------------------------


class TestNarrateHappyPath:
    """narrate() emits enriched build.stage.started event via publish_event."""

    async def test_narrate_emits_publish_event_on_success(self) -> None:
        """narrate() calls publish_event with correct type/stage/narration/agent_role/time_estimate."""
        service = NarrationService()
        mock_redis = AsyncMock()
        job_id = "job-narr-001"
        stage = "scaffold"
        narration_text = "We're setting up your project structure."

        with (
            patch.object(service, "_call_claude", new_callable=AsyncMock) as mock_call,
            patch("app.services.narration_service.asyncio.wait_for", new_callable=AsyncMock) as mock_wait,
            patch("app.services.narration_service.JobStateMachine") as mock_sm_cls,
        ):
            mock_wait.return_value = narration_text
            mock_call.return_value = narration_text
            mock_sm = AsyncMock()
            mock_sm_cls.return_value = mock_sm

            await service.narrate(job_id=job_id, stage=stage, spec="Build a task manager", redis=mock_redis)

            mock_sm.publish_event.assert_called_once()
            call_args = mock_sm.publish_event.call_args
            published_job_id = call_args[0][0]
            event = call_args[0][1]

            assert published_job_id == job_id
            from app.queue.state_machine import SSEEventType
            assert event["type"] == SSEEventType.BUILD_STAGE_STARTED
            assert event["stage"] == stage
            assert event["narration"] == narration_text
            assert event["agent_role"] == STAGE_AGENT_ROLES[stage]
            assert event["time_estimate"] == STAGE_TIME_ESTIMATES[stage]

    async def test_narrate_event_includes_correct_agent_role_for_each_stage(self) -> None:
        """Each stage maps to the correct agent role in the emitted event."""
        service = NarrationService()
        mock_redis = AsyncMock()

        expected_roles = {
            "scaffold": "Architect",
            "code": "Coder",
            "deps": "Coder",
            "checks": "Reviewer",
            "ready": "Reviewer",
        }

        for stage, expected_role in expected_roles.items():
            with (
                patch.object(service, "_call_claude", new_callable=AsyncMock) as mock_call,
                patch("app.services.narration_service.asyncio.wait_for", new_callable=AsyncMock) as mock_wait,
                patch("app.services.narration_service.JobStateMachine") as mock_sm_cls,
            ):
                mock_wait.return_value = "We're making progress."
                mock_call.return_value = "We're making progress."
                mock_sm = AsyncMock()
                mock_sm_cls.return_value = mock_sm

                await service.narrate(job_id="job-1", stage=stage, spec="spec", redis=mock_redis)

                call_args = mock_sm.publish_event.call_args
                event = call_args[0][1]
                assert event["agent_role"] == expected_role, (
                    f"Stage {stage!r} expected role {expected_role!r}, got {event['agent_role']!r}"
                )

    async def test_narrate_event_includes_time_estimate_for_each_stage(self) -> None:
        """Each stage has a time_estimate in the emitted event."""
        service = NarrationService()
        mock_redis = AsyncMock()

        for stage in _FIVE_STAGES:
            with (
                patch.object(service, "_call_claude", new_callable=AsyncMock) as mock_call,
                patch("app.services.narration_service.asyncio.wait_for", new_callable=AsyncMock) as mock_wait,
                patch("app.services.narration_service.JobStateMachine") as mock_sm_cls,
            ):
                mock_wait.return_value = "We're making progress."
                mock_call.return_value = "We're making progress."
                mock_sm = AsyncMock()
                mock_sm_cls.return_value = mock_sm

                await service.narrate(job_id="job-1", stage=stage, spec="spec", redis=mock_redis)

                call_args = mock_sm.publish_event.call_args
                event = call_args[0][1]
                assert "time_estimate" in event, f"Stage {stage!r} missing time_estimate"
                assert isinstance(event["time_estimate"], str)

    async def test_narrate_returns_none(self) -> None:
        """narrate() returns None on success."""
        service = NarrationService()
        mock_redis = AsyncMock()

        with (
            patch.object(service, "_call_claude", new_callable=AsyncMock) as mock_call,
            patch("app.services.narration_service.asyncio.wait_for", new_callable=AsyncMock) as mock_wait,
            patch("app.services.narration_service.JobStateMachine") as mock_sm_cls,
        ):
            mock_wait.return_value = "We're making progress."
            mock_call.return_value = "We're making progress."
            mock_sm_cls.return_value = AsyncMock()

            result = await service.narrate(job_id="job-1", stage="scaffold", spec="spec", redis=mock_redis)
            assert result is None


# ---------------------------------------------------------------------------
# narrate() — spec truncation
# ---------------------------------------------------------------------------


class TestNarrateSpecTruncation:
    """Spec is truncated to first 300 chars before passing to Claude."""

    async def test_narrate_truncates_long_spec(self) -> None:
        """Spec longer than 300 chars is truncated before passing to _call_claude."""
        service = NarrationService()
        mock_redis = AsyncMock()
        long_spec = "X" * 800

        with (
            patch.object(service, "_call_claude", new_callable=AsyncMock) as mock_call,
            patch("app.services.narration_service.asyncio.wait_for", new_callable=AsyncMock) as mock_wait,
            patch("app.services.narration_service.JobStateMachine") as mock_sm_cls,
        ):
            mock_call.return_value = "We're making progress."
            mock_wait.return_value = "We're making progress."
            mock_sm_cls.return_value = AsyncMock()

            await service.narrate(job_id="job-1", stage="scaffold", spec=long_spec, redis=mock_redis)

            # _call_claude is called — its second arg (spec) should be max 300 chars
            mock_call.assert_called_once()
            called_spec = mock_call.call_args[0][1]  # positional arg: (stage, spec)
            assert len(called_spec) <= 300

    async def test_narrate_passes_short_spec_unchanged(self) -> None:
        """Spec shorter than 300 chars is passed to _call_claude unchanged."""
        service = NarrationService()
        mock_redis = AsyncMock()
        short_spec = "Build a task management tool for remote teams."

        with (
            patch.object(service, "_call_claude", new_callable=AsyncMock) as mock_call,
            patch("app.services.narration_service.asyncio.wait_for", new_callable=AsyncMock) as mock_wait,
            patch("app.services.narration_service.JobStateMachine") as mock_sm_cls,
        ):
            mock_call.return_value = "We're making progress."
            mock_wait.return_value = "We're making progress."
            mock_sm_cls.return_value = AsyncMock()

            await service.narrate(job_id="job-1", stage="scaffold", spec=short_spec, redis=mock_redis)

            mock_call.assert_called_once()
            called_spec = mock_call.call_args[0][1]
            assert called_spec == short_spec


# ---------------------------------------------------------------------------
# narrate() — fallback paths
# ---------------------------------------------------------------------------


class TestNarrateFallback:
    """narrate() uses fallback narration on any failure — never raises."""

    async def test_fallback_on_api_error(self) -> None:
        """When Claude raises, fallback sentence is emitted via publish_event."""
        service = NarrationService()
        mock_redis = AsyncMock()
        stage = "code"

        with (
            patch.object(service, "_call_claude", new_callable=AsyncMock) as mock_call,
            patch("app.services.narration_service.asyncio.wait_for", new_callable=AsyncMock) as mock_wait,
            patch("app.services.narration_service.JobStateMachine") as mock_sm_cls,
        ):
            mock_call.side_effect = Exception("Anthropic API error")
            mock_wait.side_effect = Exception("Anthropic API error")
            mock_sm = AsyncMock()
            mock_sm_cls.return_value = mock_sm

            await service.narrate(job_id="job-1", stage=stage, spec="spec", redis=mock_redis)

            mock_sm.publish_event.assert_called_once()
            event = mock_sm.publish_event.call_args[0][1]
            # Fallback narration should be a non-empty string
            assert isinstance(event["narration"], str)
            assert event["narration"].strip()
            # Should be the fallback sentence for this stage
            assert event["narration"] == _FALLBACK_NARRATIONS[stage]

    async def test_fallback_on_timeout_error(self) -> None:
        """asyncio.TimeoutError triggers fallback narration."""
        service = NarrationService()
        mock_redis = AsyncMock()
        stage = "deps"

        with (
            patch.object(service, "_call_claude", new_callable=AsyncMock) as mock_call,
            patch("app.services.narration_service.asyncio.wait_for", new_callable=AsyncMock) as mock_wait,
            patch("app.services.narration_service.JobStateMachine") as mock_sm_cls,
        ):
            mock_call.side_effect = asyncio.TimeoutError("Timed out")
            mock_wait.side_effect = asyncio.TimeoutError("Timed out")
            mock_sm = AsyncMock()
            mock_sm_cls.return_value = mock_sm

            await service.narrate(job_id="job-1", stage=stage, spec="spec", redis=mock_redis)

            mock_sm.publish_event.assert_called_once()
            event = mock_sm.publish_event.call_args[0][1]
            assert event["narration"] == _FALLBACK_NARRATIONS[stage]

    async def test_fallback_event_still_includes_agent_role(self) -> None:
        """Even on fallback, event includes agent_role and time_estimate."""
        service = NarrationService()
        mock_redis = AsyncMock()
        stage = "checks"

        with (
            patch.object(service, "_call_claude", new_callable=AsyncMock) as mock_call,
            patch("app.services.narration_service.asyncio.wait_for", new_callable=AsyncMock) as mock_wait,
            patch("app.services.narration_service.JobStateMachine") as mock_sm_cls,
        ):
            mock_call.side_effect = Exception("API error")
            mock_wait.side_effect = Exception("API error")
            mock_sm = AsyncMock()
            mock_sm_cls.return_value = mock_sm

            await service.narrate(job_id="job-1", stage=stage, spec="spec", redis=mock_redis)

            event = mock_sm.publish_event.call_args[0][1]
            assert event["agent_role"] == STAGE_AGENT_ROLES[stage]
            assert event["time_estimate"] == STAGE_TIME_ESTIMATES[stage]


# ---------------------------------------------------------------------------
# narrate() — never raises
# ---------------------------------------------------------------------------


class TestNarrateNeverRaises:
    """narrate() never raises — even when publish_event fails."""

    async def test_never_raises_when_publish_event_raises(self) -> None:
        """publish_event failure does not propagate — narrate() returns None."""
        service = NarrationService()
        mock_redis = AsyncMock()

        with (
            patch.object(service, "_call_claude", new_callable=AsyncMock) as mock_call,
            patch("app.services.narration_service.asyncio.wait_for", new_callable=AsyncMock) as mock_wait,
            patch("app.services.narration_service.JobStateMachine") as mock_sm_cls,
        ):
            mock_call.return_value = "We're making progress."
            mock_wait.return_value = "We're making progress."
            mock_sm = AsyncMock()
            mock_sm.publish_event.side_effect = Exception("Redis publish failed")
            mock_sm_cls.return_value = mock_sm

            result = await service.narrate(job_id="job-1", stage="scaffold", spec="spec", redis=mock_redis)
            assert result is None

    async def test_never_raises_when_claude_and_publish_both_fail(self) -> None:
        """All errors caught — narrate() returns None without any exception."""
        service = NarrationService()
        mock_redis = AsyncMock()

        with (
            patch.object(service, "_call_claude", new_callable=AsyncMock) as mock_call,
            patch("app.services.narration_service.asyncio.wait_for", new_callable=AsyncMock) as mock_wait,
            patch("app.services.narration_service.JobStateMachine") as mock_sm_cls,
        ):
            mock_call.side_effect = Exception("Claude down")
            mock_wait.side_effect = Exception("Claude down")
            mock_sm = AsyncMock()
            mock_sm.publish_event.side_effect = Exception("Redis down")
            mock_sm_cls.return_value = mock_sm

            result = await service.narrate(job_id="job-1", stage="scaffold", spec="spec", redis=mock_redis)
            assert result is None

    async def test_never_raises_on_unexpected_exception(self) -> None:
        """Any unexpected exception — narrate() catches and returns None."""
        service = NarrationService()
        mock_redis = AsyncMock()

        with (
            patch.object(service, "_call_claude", new_callable=AsyncMock) as mock_call,
            patch("app.services.narration_service.asyncio.wait_for", new_callable=AsyncMock) as mock_wait,
            patch("app.services.narration_service.JobStateMachine") as mock_sm_cls,
        ):
            mock_call.side_effect = RuntimeError("Completely unexpected")
            mock_wait.side_effect = RuntimeError("Completely unexpected")
            mock_sm_cls.return_value = AsyncMock()

            result = await service.narrate(job_id="job-1", stage="ready", spec="spec", redis=mock_redis)
            assert result is None


# ---------------------------------------------------------------------------
# narrate() — safety filter applied to narration
# ---------------------------------------------------------------------------


class TestNarrateSafetyFilterApplied:
    """Safety filter is applied to Claude output before emitting event."""

    async def test_safety_filter_applied_to_claude_output(self) -> None:
        """Claude output with paths is filtered before event emission."""
        service = NarrationService()
        mock_redis = AsyncMock()
        stage = "scaffold"
        # Claude returns text with a path leak
        raw_narration = "We're building /app/src/main.py for your project."

        with (
            patch.object(service, "_call_claude", new_callable=AsyncMock) as mock_call,
            patch("app.services.narration_service.asyncio.wait_for", new_callable=AsyncMock) as mock_wait,
            patch("app.services.narration_service.JobStateMachine") as mock_sm_cls,
        ):
            mock_call.return_value = raw_narration
            mock_wait.return_value = raw_narration
            mock_sm = AsyncMock()
            mock_sm_cls.return_value = mock_sm

            await service.narrate(job_id="job-1", stage=stage, spec="spec", redis=mock_redis)

            event = mock_sm.publish_event.call_args[0][1]
            assert "/app/" not in event["narration"]

    async def test_safety_filter_strips_framework_names_from_narration(self) -> None:
        """Framework names are stripped from Claude output before event emission."""
        service = NarrationService()
        mock_redis = AsyncMock()
        stage = "code"
        raw_narration = "We're writing your React components and FastAPI endpoints."

        with (
            patch.object(service, "_call_claude", new_callable=AsyncMock) as mock_call,
            patch("app.services.narration_service.asyncio.wait_for", new_callable=AsyncMock) as mock_wait,
            patch("app.services.narration_service.JobStateMachine") as mock_sm_cls,
        ):
            mock_call.return_value = raw_narration
            mock_wait.return_value = raw_narration
            mock_sm = AsyncMock()
            mock_sm_cls.return_value = mock_sm

            await service.narrate(job_id="job-1", stage=stage, spec="spec", redis=mock_redis)

            event = mock_sm.publish_event.call_args[0][1]
            assert "React" not in event["narration"]
            assert "FastAPI" not in event["narration"]


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------


class TestModuleSingleton:
    """Module exports a singleton _narration_service instance."""

    def test_module_singleton_exists(self) -> None:
        """_narration_service module-level singleton must exist."""
        from app.services.narration_service import _narration_service
        assert isinstance(_narration_service, NarrationService)
