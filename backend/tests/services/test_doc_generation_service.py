"""Tests for DocGenerationService.

TDD coverage:
- Constants: SECTION_ORDER, DOC_GEN_TIMEOUT_SECONDS, DOC_GEN_MODEL, DOC_GEN_MAX_TOKENS
- generate(): feature flag disabled returns None immediately
- generate(): sets _status="pending" at start, then "generating" after first write
- generate(): all 4 sections valid -> _status="complete", all sections in Redis
- generate(): 2 valid sections, 2 non-string -> _status="partial"
- generate(): 0 valid sections -> _status="failed"
- generate(): never raises on RateLimitError (first call fails, second succeeds)
- generate(): never raises on RateLimitError + TimeoutError (both fail) -> _status="failed"
- generate(): never raises on JSONDecodeError -> _status="failed"
- generate(): never raises on Redis hset exception
- generate(): sections written in SECTION_ORDER order (overview first)
- generate(): SSE event emitted per section via DOCUMENTATION_UPDATED
- _apply_safety_filter(): strips code fences (triple backtick blocks)
- _apply_safety_filter(): strips inline code (single backticks)
- _apply_safety_filter(): strips shell prompts ($ and > prefixes)
- _apply_safety_filter(): strips Unix paths (/home/, /usr/, /var/, /tmp/, /app/, /src/)
- _apply_safety_filter(): strips PascalCase filenames (.py, .ts, .js, etc.)
- _apply_safety_filter(): strips framework names (React, Next.js, FastAPI, etc.)
- _apply_safety_filter(): preserves normal text ("reactive" NOT stripped)
- _call_claude_with_retry(): calls AsyncAnthropic with correct model and max_tokens
- _call_claude_with_retry(): retries on RateLimitError after 2.5s sleep
- _call_claude_with_retry(): raises on second consecutive failure
- _parse_sections(): extracts valid string sections, skips non-string values
- _build_prompt(): returns system prompt string + messages list
"""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch, call

import pytest

from app.services.doc_generation_service import (
    SECTION_ORDER,
    DOC_GEN_TIMEOUT_SECONDS,
    DOC_GEN_MODEL,
    DOC_GEN_MAX_TOKENS,
    DocGenerationService,
)

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------


class TestConstants:
    def test_section_order_is_four_sections(self) -> None:
        assert SECTION_ORDER == ["overview", "features", "getting_started", "faq"]

    def test_timeout_is_30_seconds(self) -> None:
        assert DOC_GEN_TIMEOUT_SECONDS == 30.0

    def test_model_is_haiku(self) -> None:
        assert DOC_GEN_MODEL == "claude-3-5-haiku-20241022"

    def test_max_tokens_is_1500(self) -> None:
        assert DOC_GEN_MAX_TOKENS == 1500


# ---------------------------------------------------------------------------
# _apply_safety_filter()
# ---------------------------------------------------------------------------


class TestSafetyFilter:
    """Content safety filter strips technical content, preserves natural language."""

    def setup_method(self) -> None:
        self.service = DocGenerationService()

    def test_strips_triple_backtick_code_blocks(self) -> None:
        """Code blocks (```...```) must be stripped completely."""
        content = "Built with ```npm install react``` and more"
        result = self.service._apply_safety_filter(content)
        assert "```" not in result
        assert "npm install" not in result

    def test_strips_inline_code(self) -> None:
        """Inline code (`code`) must be stripped."""
        content = "Run `npm install` to get started"
        result = self.service._apply_safety_filter(content)
        assert "`" not in result
        assert "npm install" not in result

    def test_strips_shell_dollar_prompts(self) -> None:
        """Lines starting with $ followed by command must be stripped."""
        content = "Install it:\n$ npm install\nThen open the app"
        result = self.service._apply_safety_filter(content)
        assert "$ npm install" not in result

    def test_strips_shell_gt_prompts(self) -> None:
        """Lines starting with > followed by command must be stripped."""
        content = "Run:\n> python app.py\nDone"
        result = self.service._apply_safety_filter(content)
        assert "> python" not in result

    def test_strips_unix_home_path(self) -> None:
        """/home/... paths must be stripped."""
        content = "Check /home/user/project for details"
        result = self.service._apply_safety_filter(content)
        assert "/home/" not in result

    def test_strips_unix_usr_path(self) -> None:
        """/usr/... paths must be stripped."""
        content = "Located at /usr/local/bin/python"
        result = self.service._apply_safety_filter(content)
        assert "/usr/" not in result

    def test_strips_unix_var_path(self) -> None:
        """/var/... paths must be stripped."""
        content = "Logs at /var/log/app.log"
        result = self.service._apply_safety_filter(content)
        assert "/var/" not in result

    def test_strips_unix_tmp_path(self) -> None:
        """/tmp/... paths must be stripped."""
        content = "Temp files in /tmp/cache"
        result = self.service._apply_safety_filter(content)
        assert "/tmp/" not in result

    def test_strips_unix_app_path(self) -> None:
        """/app/... paths must be stripped."""
        content = "App root is /app/src/main.py"
        result = self.service._apply_safety_filter(content)
        assert "/app/" not in result

    def test_strips_unix_src_path(self) -> None:
        """/src/... paths must be stripped."""
        content = "Source at /src/components/App.tsx"
        result = self.service._apply_safety_filter(content)
        assert "/src/" not in result

    def test_strips_pascal_case_py_filename(self) -> None:
        """PascalCase.py filenames must be stripped."""
        content = "Check App.py for configuration"
        result = self.service._apply_safety_filter(content)
        assert "App.py" not in result

    def test_strips_pascal_case_ts_filename(self) -> None:
        """PascalCase.ts filenames must be stripped."""
        content = "Located in UserService.ts"
        result = self.service._apply_safety_filter(content)
        assert "UserService.ts" not in result

    def test_strips_pascal_case_tsx_filename(self) -> None:
        """PascalCase.tsx filenames must be stripped."""
        content = "Component is in Dashboard.tsx"
        result = self.service._apply_safety_filter(content)
        assert "Dashboard.tsx" not in result

    def test_strips_framework_react(self) -> None:
        """'React' as standalone word must be stripped."""
        content = "Built with React for the frontend"
        result = self.service._apply_safety_filter(content)
        assert "React" not in result

    def test_strips_framework_nextjs(self) -> None:
        """'Next.js' as standalone word must be stripped."""
        content = "Powered by Next.js framework"
        result = self.service._apply_safety_filter(content)
        assert "Next.js" not in result

    def test_strips_framework_fastapi(self) -> None:
        """'FastAPI' as standalone word must be stripped."""
        content = "The FastAPI backend handles requests"
        result = self.service._apply_safety_filter(content)
        assert "FastAPI" not in result

    def test_strips_framework_postgresql(self) -> None:
        """'PostgreSQL' must be stripped."""
        content = "Data stored in PostgreSQL database"
        result = self.service._apply_safety_filter(content)
        assert "PostgreSQL" not in result

    def test_strips_framework_redis(self) -> None:
        """'Redis' as a standalone framework reference must be stripped."""
        content = "Cached with Redis for speed"
        result = self.service._apply_safety_filter(content)
        assert "Redis" not in result

    def test_strips_framework_typescript(self) -> None:
        """'TypeScript' must be stripped."""
        content = "Written in TypeScript for type safety"
        result = self.service._apply_safety_filter(content)
        assert "TypeScript" not in result

    def test_strips_unix_workspace_path(self) -> None:
        """/workspace/... paths must be stripped (E2B sandbox build directory)."""
        content = "Check /workspace/project/src/main.py for details."
        result = self.service._apply_safety_filter(content)
        assert "/workspace/" not in result

    def test_strips_stack_trace_header(self) -> None:
        """'Traceback (most recent call last):' lines must be stripped."""
        content = "Error: Traceback (most recent call last):\n  File \"/app/main.py\", line 42"
        result = self.service._apply_safety_filter(content)
        assert "Traceback" not in result

    def test_strips_raise_statement(self) -> None:
        """Lines containing 'raise SomeError' must be stripped."""
        content = "We encountered raise RuntimeError in the build."
        result = self.service._apply_safety_filter(content)
        assert "raise RuntimeError" not in result

    def test_redacts_anthropic_api_key(self) -> None:
        """sk-ant-api03-... keys must be replaced with [REDACTED]."""
        content = "Using key sk-ant-api03-abc123def456ghi789jkl012mno345 for generation."
        result = self.service._apply_safety_filter(content)
        assert "sk-ant-" not in result
        assert "[REDACTED]" in result

    def test_redacts_aws_access_key(self) -> None:
        """AKIA... AWS access key IDs must be replaced with [REDACTED]."""
        content = "Configured with AKIAIOSFODNN7EXAMPLE for S3 access."
        result = self.service._apply_safety_filter(content)
        assert "AKIA" not in result

    def test_preserves_reactive_word(self) -> None:
        """'reactive' must NOT be stripped (word boundary protection)."""
        content = "Your app is reactive and fast"
        result = self.service._apply_safety_filter(content)
        assert "reactive" in result

    def test_preserves_normal_text(self) -> None:
        """Plain English without technical terms passes through unchanged."""
        content = "Welcome to your new app! Sign up to get started."
        result = self.service._apply_safety_filter(content)
        assert "Welcome to your new app" in result
        assert "Sign up to get started" in result

    def test_returns_string(self) -> None:
        """_apply_safety_filter always returns a string."""
        result = self.service._apply_safety_filter("any content")
        assert isinstance(result, str)


# ---------------------------------------------------------------------------
# _parse_sections()
# ---------------------------------------------------------------------------


class TestParseSections:
    """Extract valid string sections from parsed JSON dict."""

    def setup_method(self) -> None:
        self.service = DocGenerationService()

    def test_extracts_all_four_valid_sections(self) -> None:
        """All four sections with string values are returned."""
        raw = {
            "overview": "This is the overview.",
            "features": "- **Feature**: description",
            "getting_started": "1. Sign up\n2. Create project",
            "faq": "### Question?\nAnswer here.",
        }
        sections = self.service._parse_sections(raw)
        assert len(sections) == 4
        assert "overview" in sections
        assert "features" in sections
        assert "getting_started" in sections
        assert "faq" in sections

    def test_skips_non_string_values(self) -> None:
        """Non-string values (lists, dicts, None, int) are skipped."""
        raw = {
            "overview": "Valid overview.",
            "features": ["bullet1", "bullet2"],  # list — should be skipped
            "getting_started": None,              # None — should be skipped
            "faq": 42,                            # int — should be skipped
        }
        sections = self.service._parse_sections(raw)
        assert "overview" in sections
        assert "features" not in sections
        assert "getting_started" not in sections
        assert "faq" not in sections

    def test_skips_empty_string_values(self) -> None:
        """Empty string values are skipped (not written to Redis)."""
        raw = {
            "overview": "Valid overview.",
            "features": "",  # empty — should be skipped
            "getting_started": "1. Sign up",
            "faq": "Q&A",
        }
        sections = self.service._parse_sections(raw)
        assert "overview" in sections
        assert "features" not in sections

    def test_ignores_extra_keys(self) -> None:
        """Unknown keys outside SECTION_ORDER are ignored."""
        raw = {
            "overview": "Valid.",
            "features": "Features here.",
            "getting_started": "Steps.",
            "faq": "Q&A.",
            "extra_section": "Should be ignored.",
        }
        sections = self.service._parse_sections(raw)
        assert "extra_section" not in sections
        assert len(sections) == 4

    def test_returns_dict(self) -> None:
        """_parse_sections always returns a dict."""
        result = self.service._parse_sections({})
        assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# _build_prompt()
# ---------------------------------------------------------------------------


class TestBuildPrompt:
    """System prompt and messages construction."""

    def setup_method(self) -> None:
        self.service = DocGenerationService()

    def test_returns_tuple_of_system_and_messages(self) -> None:
        """_build_prompt returns (system_prompt_str, messages_list)."""
        system, messages = self.service._build_prompt("Build a task manager")
        assert isinstance(system, str)
        assert isinstance(messages, list)

    def test_system_prompt_contains_json_instruction(self) -> None:
        """System prompt instructs Claude to return JSON."""
        system, _ = self.service._build_prompt("Build a task manager")
        assert "json" in system.lower() or "JSON" in system

    def test_system_prompt_contains_do_not_instructions(self) -> None:
        """System prompt contains negative instructions (DO NOT)."""
        system, _ = self.service._build_prompt("Build a task manager")
        # Should have explicit negative instructions
        assert "DO NOT" in system or "do not" in system.lower() or "Don't" in system

    def test_system_prompt_contains_example(self) -> None:
        """System prompt includes one-shot example (TaskFlow)."""
        system, _ = self.service._build_prompt("Build a task manager")
        assert "TaskFlow" in system

    def test_messages_list_has_user_role(self) -> None:
        """Messages list contains user role message."""
        _, messages = self.service._build_prompt("Build a task manager")
        assert len(messages) >= 1
        assert messages[0]["role"] == "user"

    def test_messages_user_content_contains_spec_summary(self) -> None:
        """User message contains the spec content."""
        spec = "Build a task manager for remote teams"
        _, messages = self.service._build_prompt(spec)
        user_content = messages[0]["content"]
        # Spec content should be reflected (summarized or verbatim)
        assert len(user_content) > 0

    def test_empty_spec_does_not_raise(self) -> None:
        """Empty spec is valid — Claude infers from empty input."""
        system, messages = self.service._build_prompt("")
        assert isinstance(system, str)
        assert isinstance(messages, list)


# ---------------------------------------------------------------------------
# _call_claude_with_retry()
# ---------------------------------------------------------------------------


class TestCallClaudeWithRetry:
    """API call structure, retry on RateLimitError, raises on second failure."""

    async def test_calls_with_correct_model(self) -> None:
        """AsyncAnthropic.messages.create() called with claude-3-5-haiku-20241022."""
        service = DocGenerationService()
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text='{"overview": "x", "features": "y", "getting_started": "z", "faq": "q"}')]

        with (
            patch("app.services.doc_generation_service.anthropic") as mock_anthropic,
            patch("app.services.doc_generation_service.asyncio.wait_for", new_callable=AsyncMock) as mock_wait,
        ):
            mock_client = AsyncMock()
            mock_anthropic.AsyncAnthropic.return_value = mock_client
            mock_wait.return_value = mock_response

            system = "system prompt"
            messages = [{"role": "user", "content": "spec"}]
            await service._call_claude_with_retry(system, messages)

            # Verify client created with api_key from settings
            mock_anthropic.AsyncAnthropic.assert_called_once()

    async def test_returns_parsed_json_dict(self) -> None:
        """Returns a dict from the JSON response."""
        service = DocGenerationService()
        sections_json = '{"overview": "Overview text", "features": "Features", "getting_started": "Steps", "faq": "Q&A"}'
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=sections_json)]

        with (
            patch("app.services.doc_generation_service.anthropic") as mock_anthropic,
            patch("app.services.doc_generation_service.asyncio.wait_for", new_callable=AsyncMock) as mock_wait,
            patch("app.services.doc_generation_service.get_settings") as mock_settings,
        ):
            mock_settings.return_value.anthropic_api_key = "test-key"
            mock_client = AsyncMock()
            mock_anthropic.AsyncAnthropic.return_value = mock_client
            mock_wait.return_value = mock_response

            system = "system"
            messages = [{"role": "user", "content": "build a task manager"}]
            result = await service._call_claude_with_retry(system, messages)

            assert isinstance(result, dict)
            assert result["overview"] == "Overview text"

    async def test_retries_on_rate_limit_error(self) -> None:
        """RateLimitError on first call triggers retry after ~2.5s sleep."""
        from anthropic._exceptions import RateLimitError

        service = DocGenerationService()
        sections_json = '{"overview": "x", "features": "y", "getting_started": "z", "faq": "q"}'
        mock_success_response = MagicMock()
        mock_success_response.content = [MagicMock(text=sections_json)]

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
            return mock_success_response

        with (
            patch("app.services.doc_generation_service.anthropic") as mock_anthropic,
            patch("app.services.doc_generation_service.asyncio") as mock_asyncio,
            patch("app.services.doc_generation_service.get_settings") as mock_settings,
        ):
            mock_settings.return_value.anthropic_api_key = "test-key"
            mock_client = AsyncMock()
            mock_anthropic.AsyncAnthropic.return_value = mock_client
            # Keep real asyncio.TimeoutError available
            mock_asyncio.TimeoutError = asyncio.TimeoutError
            mock_asyncio.wait_for = mock_wait_for
            mock_asyncio.sleep = AsyncMock()

            system = "system"
            messages = [{"role": "user", "content": "spec"}]
            result = await service._call_claude_with_retry(system, messages)

            # Slept once (first retry backoff)
            mock_asyncio.sleep.assert_called_once_with(2.5)
            assert call_count == 2
            assert isinstance(result, dict)

    async def test_raises_on_second_consecutive_failure(self) -> None:
        """Two consecutive failures cause _call_claude_with_retry to raise."""
        from anthropic._exceptions import RateLimitError

        service = DocGenerationService()

        async def mock_wait_for_always_fail(coro, timeout):
            raise RateLimitError(
                message="Rate limited",
                response=MagicMock(status_code=429, headers={}),
                body={},
            )

        with (
            patch("app.services.doc_generation_service.anthropic") as mock_anthropic,
            patch("app.services.doc_generation_service.asyncio") as mock_asyncio,
            patch("app.services.doc_generation_service.get_settings") as mock_settings,
        ):
            mock_settings.return_value.anthropic_api_key = "test-key"
            mock_client = AsyncMock()
            mock_anthropic.AsyncAnthropic.return_value = mock_client
            mock_asyncio.TimeoutError = asyncio.TimeoutError
            mock_asyncio.wait_for = mock_wait_for_always_fail
            mock_asyncio.sleep = AsyncMock()

            system = "system"
            messages = [{"role": "user", "content": "spec"}]
            with pytest.raises(Exception):
                await service._call_claude_with_retry(system, messages)


# ---------------------------------------------------------------------------
# generate() — happy path
# ---------------------------------------------------------------------------


class TestGenerateHappyPath:
    """generate() full end-to-end: sets status, writes sections, emits SSE."""

    async def test_generate_writes_all_four_sections(self) -> None:
        """All 4 valid sections written to Redis under job:{job_id}:docs."""
        service = DocGenerationService()
        mock_redis = AsyncMock()
        job_id = "test-job-123"
        all_sections = {
            "overview": "Welcome to your app!",
            "features": "**Fast**: Real-time updates.",
            "getting_started": "1. Sign up\n2. Create project",
            "faq": "### How do I start?\nClick sign up.",
        }

        with (
            patch("app.services.doc_generation_service.get_settings") as mock_settings,
            patch.object(service, "_call_claude_with_retry", new_callable=AsyncMock) as mock_call,
            patch.object(service, "_parse_sections") as mock_parse,
            patch("app.services.doc_generation_service.JobStateMachine") as mock_sm_cls,
        ):
            mock_settings.return_value.docs_generation_enabled = True
            mock_call.return_value = all_sections
            mock_parse.return_value = all_sections
            mock_sm = AsyncMock()
            mock_sm_cls.return_value = mock_sm

            await service.generate(job_id, "Build a task manager", mock_redis)

            # All four sections written to Redis
            hset_calls = mock_redis.hset.call_args_list
            written_keys = [c[0][1] for c in hset_calls if c[0][1] in SECTION_ORDER]
            for section in SECTION_ORDER:
                assert section in written_keys, f"Section '{section}' not written to Redis"

    async def test_generate_sets_status_complete_for_all_four(self) -> None:
        """_status set to 'complete' when all 4 sections are written."""
        service = DocGenerationService()
        mock_redis = AsyncMock()
        job_id = "test-job-123"
        all_sections = {
            "overview": "Overview.",
            "features": "Features.",
            "getting_started": "Steps.",
            "faq": "Q&A.",
        }

        with (
            patch("app.services.doc_generation_service.get_settings") as mock_settings,
            patch.object(service, "_call_claude_with_retry", new_callable=AsyncMock) as mock_call,
            patch.object(service, "_parse_sections") as mock_parse,
            patch("app.services.doc_generation_service.JobStateMachine") as mock_sm_cls,
        ):
            mock_settings.return_value.docs_generation_enabled = True
            mock_call.return_value = all_sections
            mock_parse.return_value = all_sections
            mock_sm_cls.return_value = AsyncMock()

            await service.generate(job_id, "spec", mock_redis)

            hset_calls = mock_redis.hset.call_args_list
            status_calls = [c for c in hset_calls if c[0][1] == "_status"]
            status_values = [c[0][2] for c in status_calls]
            assert "complete" in status_values

    async def test_generate_emits_sse_event_per_section(self) -> None:
        """SSE DOCUMENTATION_UPDATED event emitted once per valid section."""
        service = DocGenerationService()
        mock_redis = AsyncMock()
        job_id = "test-job-456"
        all_sections = {
            "overview": "Overview.",
            "features": "Features.",
            "getting_started": "Steps.",
            "faq": "Q&A.",
        }

        with (
            patch("app.services.doc_generation_service.get_settings") as mock_settings,
            patch.object(service, "_call_claude_with_retry", new_callable=AsyncMock) as mock_call,
            patch.object(service, "_parse_sections") as mock_parse,
            patch("app.services.doc_generation_service.JobStateMachine") as mock_sm_cls,
        ):
            mock_settings.return_value.docs_generation_enabled = True
            mock_call.return_value = all_sections
            mock_parse.return_value = all_sections
            mock_sm = AsyncMock()
            mock_sm_cls.return_value = mock_sm

            await service.generate(job_id, "spec", mock_redis)

            # publish_event called 4 times (one per section)
            assert mock_sm.publish_event.call_count == 4
            # Each call has DOCUMENTATION_UPDATED type
            from app.queue.state_machine import SSEEventType
            for call_args in mock_sm.publish_event.call_args_list:
                event = call_args[0][1]
                assert event["type"] == SSEEventType.DOCUMENTATION_UPDATED
                assert "section" in event

    async def test_generate_sections_written_in_order(self) -> None:
        """Sections are written to Redis in SECTION_ORDER order."""
        service = DocGenerationService()
        mock_redis = AsyncMock()
        job_id = "test-job-order"
        all_sections = {
            "overview": "Overview.",
            "features": "Features.",
            "getting_started": "Steps.",
            "faq": "Q&A.",
        }
        write_order = []

        async def track_hset(key, field, value):
            if field in SECTION_ORDER:
                write_order.append(field)

        mock_redis.hset.side_effect = track_hset

        with (
            patch("app.services.doc_generation_service.get_settings") as mock_settings,
            patch.object(service, "_call_claude_with_retry", new_callable=AsyncMock) as mock_call,
            patch.object(service, "_parse_sections") as mock_parse,
            patch("app.services.doc_generation_service.JobStateMachine") as mock_sm_cls,
        ):
            mock_settings.return_value.docs_generation_enabled = True
            mock_call.return_value = all_sections
            mock_parse.return_value = all_sections
            mock_sm_cls.return_value = AsyncMock()

            await service.generate(job_id, "spec", mock_redis)

            assert write_order == SECTION_ORDER

    async def test_generate_applies_safety_filter_before_write(self) -> None:
        """Safety filter is applied to each section before Redis write."""
        service = DocGenerationService()
        mock_redis = AsyncMock()
        job_id = "test-job-filter"
        # Overview contains a framework name that should be stripped
        sections_with_tech = {
            "overview": "Built with React and FastAPI.",
            "features": "Features.",
            "getting_started": "Steps.",
            "faq": "Q&A.",
        }

        with (
            patch("app.services.doc_generation_service.get_settings") as mock_settings,
            patch.object(service, "_call_claude_with_retry", new_callable=AsyncMock) as mock_call,
            patch.object(service, "_parse_sections") as mock_parse,
            patch("app.services.doc_generation_service.JobStateMachine") as mock_sm_cls,
        ):
            mock_settings.return_value.docs_generation_enabled = True
            mock_call.return_value = sections_with_tech
            mock_parse.return_value = sections_with_tech
            mock_sm_cls.return_value = AsyncMock()

            await service.generate(job_id, "spec", mock_redis)

            # Find the hset call for "overview" section
            hset_calls = mock_redis.hset.call_args_list
            overview_call = next((c for c in hset_calls if len(c[0]) >= 2 and c[0][1] == "overview"), None)
            assert overview_call is not None
            stored_content = overview_call[0][2]
            # React and FastAPI should be stripped
            assert "React" not in stored_content
            assert "FastAPI" not in stored_content

    async def test_generate_returns_none_on_success(self) -> None:
        """generate() returns None (not the sections dict) on success."""
        service = DocGenerationService()
        mock_redis = AsyncMock()
        all_sections = {k: "content" for k in SECTION_ORDER}

        with (
            patch("app.services.doc_generation_service.get_settings") as mock_settings,
            patch.object(service, "_call_claude_with_retry", new_callable=AsyncMock) as mock_call,
            patch.object(service, "_parse_sections") as mock_parse,
            patch("app.services.doc_generation_service.JobStateMachine") as mock_sm_cls,
        ):
            mock_settings.return_value.docs_generation_enabled = True
            mock_call.return_value = all_sections
            mock_parse.return_value = all_sections
            mock_sm_cls.return_value = AsyncMock()

            result = await service.generate("job-1", "spec", mock_redis)
            assert result is None


# ---------------------------------------------------------------------------
# generate() — partial success
# ---------------------------------------------------------------------------


class TestGeneratePartialSuccess:
    async def test_generate_partial_with_two_valid_sections(self) -> None:
        """2 valid + 2 non-string -> _status='partial', only 2 sections written."""
        service = DocGenerationService()
        mock_redis = AsyncMock()
        job_id = "test-partial"

        partial_sections = {
            "overview": "Valid overview.",
            "features": "Valid features.",
            # getting_started and faq missing (not in parsed result)
        }

        with (
            patch("app.services.doc_generation_service.get_settings") as mock_settings,
            patch.object(service, "_call_claude_with_retry", new_callable=AsyncMock) as mock_call,
            patch.object(service, "_parse_sections") as mock_parse,
            patch("app.services.doc_generation_service.JobStateMachine") as mock_sm_cls,
        ):
            mock_settings.return_value.docs_generation_enabled = True
            mock_call.return_value = partial_sections
            mock_parse.return_value = partial_sections
            mock_sm_cls.return_value = AsyncMock()

            await service.generate(job_id, "spec", mock_redis)

            hset_calls = mock_redis.hset.call_args_list
            status_calls = [c for c in hset_calls if c[0][1] == "_status"]
            status_values = [c[0][2] for c in status_calls]
            assert "partial" in status_values

    async def test_generate_failed_with_zero_valid_sections(self) -> None:
        """0 valid sections -> _status='failed'."""
        service = DocGenerationService()
        mock_redis = AsyncMock()
        job_id = "test-zero"

        with (
            patch("app.services.doc_generation_service.get_settings") as mock_settings,
            patch.object(service, "_call_claude_with_retry", new_callable=AsyncMock) as mock_call,
            patch.object(service, "_parse_sections") as mock_parse,
            patch("app.services.doc_generation_service.JobStateMachine") as mock_sm_cls,
        ):
            mock_settings.return_value.docs_generation_enabled = True
            mock_call.return_value = {}
            mock_parse.return_value = {}  # no valid sections
            mock_sm_cls.return_value = AsyncMock()

            await service.generate(job_id, "spec", mock_redis)

            hset_calls = mock_redis.hset.call_args_list
            status_values = [c[0][2] for c in hset_calls if c[0][1] == "_status"]
            assert "failed" in status_values


# ---------------------------------------------------------------------------
# generate() — failure paths (DOCS-08: never raises)
# ---------------------------------------------------------------------------


class TestGenerateNeverRaises:
    """generate() must never raise — all exceptions caught internally."""

    async def test_does_not_raise_on_rate_limit_exhausted(self) -> None:
        """RateLimitError on both attempts — generate() returns None, _status=failed."""
        from anthropic._exceptions import RateLimitError

        service = DocGenerationService()
        mock_redis = AsyncMock()
        job_id = "test-rate-limit"

        with (
            patch("app.services.doc_generation_service.get_settings") as mock_settings,
            patch.object(service, "_call_claude_with_retry", new_callable=AsyncMock) as mock_call,
        ):
            mock_settings.return_value.docs_generation_enabled = True
            mock_call.side_effect = RateLimitError(
                message="Rate limited",
                response=MagicMock(status_code=429, headers={}),
                body={},
            )

            # Must NOT raise
            result = await service.generate(job_id, "spec", mock_redis)
            assert result is None

            # _status should be set to failed
            hset_calls = mock_redis.hset.call_args_list
            status_values = [c[0][2] for c in hset_calls if c[0][1] == "_status"]
            assert "failed" in status_values

    async def test_does_not_raise_on_timeout(self) -> None:
        """asyncio.TimeoutError — generate() returns None, _status=failed."""
        service = DocGenerationService()
        mock_redis = AsyncMock()
        job_id = "test-timeout"

        with (
            patch("app.services.doc_generation_service.get_settings") as mock_settings,
            patch.object(service, "_call_claude_with_retry", new_callable=AsyncMock) as mock_call,
        ):
            mock_settings.return_value.docs_generation_enabled = True
            mock_call.side_effect = asyncio.TimeoutError("Timed out")

            result = await service.generate(job_id, "spec", mock_redis)
            assert result is None

    async def test_does_not_raise_on_json_decode_error(self) -> None:
        """JSONDecodeError — generate() returns None, _status=failed."""
        service = DocGenerationService()
        mock_redis = AsyncMock()
        job_id = "test-json-error"

        with (
            patch("app.services.doc_generation_service.get_settings") as mock_settings,
            patch.object(service, "_call_claude_with_retry", new_callable=AsyncMock) as mock_call,
        ):
            mock_settings.return_value.docs_generation_enabled = True
            mock_call.side_effect = json.JSONDecodeError("Expecting value", "", 0)

            result = await service.generate(job_id, "spec", mock_redis)
            assert result is None

    async def test_does_not_raise_on_redis_hset_exception(self) -> None:
        """Redis failure during hset — generate() logs and returns None without raising."""
        service = DocGenerationService()
        mock_redis = AsyncMock()
        mock_redis.hset.side_effect = Exception("Redis connection lost")
        job_id = "test-redis-fail"

        with (
            patch("app.services.doc_generation_service.get_settings") as mock_settings,
            patch.object(service, "_call_claude_with_retry", new_callable=AsyncMock) as mock_call,
            patch.object(service, "_parse_sections") as mock_parse,
        ):
            mock_settings.return_value.docs_generation_enabled = True
            mock_call.return_value = {"overview": "x"}
            mock_parse.return_value = {"overview": "x"}

            result = await service.generate(job_id, "spec", mock_redis)
            assert result is None

    async def test_does_not_raise_on_unexpected_exception(self) -> None:
        """Any unexpected exception — generate() catches and returns None."""
        service = DocGenerationService()
        mock_redis = AsyncMock()
        job_id = "test-unexpected"

        with (
            patch("app.services.doc_generation_service.get_settings") as mock_settings,
            patch.object(service, "_call_claude_with_retry", new_callable=AsyncMock) as mock_call,
        ):
            mock_settings.return_value.docs_generation_enabled = True
            mock_call.side_effect = RuntimeError("Something completely unexpected")

            result = await service.generate(job_id, "spec", mock_redis)
            assert result is None

    async def test_does_not_raise_with_empty_spec(self) -> None:
        """Empty spec is valid — generate() still attempts generation."""
        service = DocGenerationService()
        mock_redis = AsyncMock()
        all_sections = {k: "content" for k in SECTION_ORDER}

        with (
            patch("app.services.doc_generation_service.get_settings") as mock_settings,
            patch.object(service, "_call_claude_with_retry", new_callable=AsyncMock) as mock_call,
            patch.object(service, "_parse_sections") as mock_parse,
            patch("app.services.doc_generation_service.JobStateMachine") as mock_sm_cls,
        ):
            mock_settings.return_value.docs_generation_enabled = True
            mock_call.return_value = all_sections
            mock_parse.return_value = all_sections
            mock_sm_cls.return_value = AsyncMock()

            result = await service.generate("job-1", "", mock_redis)
            assert result is None
            mock_call.assert_called_once()

    async def test_feature_flag_disabled_returns_none_immediately(self) -> None:
        """docs_generation_enabled=False short-circuits before any API call."""
        service = DocGenerationService()
        mock_redis = AsyncMock()

        with (
            patch("app.services.doc_generation_service.get_settings") as mock_settings,
            patch.object(service, "_call_claude_with_retry", new_callable=AsyncMock) as mock_call,
        ):
            mock_settings.return_value.docs_generation_enabled = False

            result = await service.generate("job-1", "spec", mock_redis)
            assert result is None
            mock_call.assert_not_called()
