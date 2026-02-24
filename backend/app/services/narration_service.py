"""NarrationService — Claude Haiku stage narration with safety filter.

Architecture:
- Direct anthropic.AsyncAnthropic call with claude-3-5-haiku-20241022 (NOT LangChain)
- asyncio.wait_for(timeout=NARRATION_TIMEOUT_SECONDS) wraps the API call
- One retry with 2.5s backoff on RateLimitError, APITimeoutError, asyncio.TimeoutError
- Emits enriched build.stage.started SSE event per stage via JobStateMachine.publish_event()
- Safety filter reuses _SAFETY_PATTERNS from doc_generation_service (no duplication)
- narrate() NEVER raises — safe for asyncio.create_task() fire-and-forget
- Fallback narration emitted on any failure — build is never blocked

Phase 36 plan 01: TDD implementation.
"""

import asyncio

import anthropic
import structlog

from app.core.config import get_settings
from app.queue.state_machine import JobStateMachine, SSEEventType
from app.services.doc_generation_service import _SAFETY_PATTERNS

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

NARRATION_MODEL: str = "claude-3-5-haiku-20241022"
NARRATION_MAX_TOKENS: int = 80
NARRATION_TIMEOUT_SECONDS: float = 10.0
_RETRY_BACKOFF_SECONDS: float = 2.5

STAGE_AGENT_ROLES: dict[str, str] = {
    "scaffold": "Architect",
    "code": "Coder",
    "deps": "Coder",
    "checks": "Reviewer",
    "ready": "Reviewer",
}

STAGE_TIME_ESTIMATES: dict[str, str] = {
    "scaffold": "~15s",
    "code": "~60s",
    "deps": "~45s",
    "checks": "~20s",
    "ready": "~5s",
}

_FALLBACK_NARRATIONS: dict[str, str] = {
    "scaffold": "We're setting up your project structure.",
    "code": "We're writing the code for your application.",
    "deps": "We're installing the dependencies.",
    "checks": "We're running the final checks.",
    "ready": "Your build is ready.",
}

# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT: str = (
    "You are a calm, expert technical co-founder giving a brief status update. "
    "Use 'we' (not 'I'). Write exactly ONE sentence, 10-20 words. "
    "Reference the product's actual features when possible. "
    "Always sound confident — never apologize or acknowledge delays. "
    "Do NOT include code, file paths, framework names, or technical jargon."
)


# ---------------------------------------------------------------------------
# NarrationService
# ---------------------------------------------------------------------------


class NarrationService:
    """Generates one Claude Haiku sentence per build stage transition.

    Public API:
        narrate(job_id, stage, spec, redis) -> None

    Never raises. Falls back to generic sentence on any failure.
    Always emits a build.stage.started SSE event (real narration or fallback).
    """

    async def narrate(
        self,
        job_id: str,
        stage: str,
        spec: str,
        redis: object,
    ) -> None:
        """Generate stage narration and emit enriched build.stage.started SSE event.

        Never raises. Falls back to _FALLBACK_NARRATIONS[stage] on any failure.
        Always emits the SSE event even when Claude call fails.

        Args:
            job_id: Build job identifier — used for SSE event targeting
            stage:  Build stage name (scaffold / code / deps / checks / ready)
            spec:   Founder's product spec (truncated to 300 chars internally)
            redis:  Async Redis client
        """
        try:
            truncated_spec = spec[:300]
            try:
                narration_text = await asyncio.wait_for(
                    self._call_claude(stage, truncated_spec),
                    timeout=NARRATION_TIMEOUT_SECONDS,
                )
                narration_text = self._apply_safety_filter(narration_text)
            except Exception:
                narration_text = _FALLBACK_NARRATIONS.get(
                    stage, "We're making progress on your build."
                )

            state_machine = JobStateMachine(redis)  # type: ignore[arg-type]
            await state_machine.publish_event(
                job_id,
                {
                    "type": SSEEventType.BUILD_STAGE_STARTED,
                    "stage": stage,
                    "narration": narration_text,
                    "agent_role": STAGE_AGENT_ROLES.get(stage, "Engineer"),
                    "time_estimate": STAGE_TIME_ESTIMATES.get(stage, "~30s"),
                },
            )
        except Exception as exc:
            logger.warning(
                "narration_failed",
                job_id=job_id,
                stage=stage,
                error=str(exc),
                error_type=type(exc).__name__,
            )

        return None

    async def _call_claude(self, stage: str, spec: str) -> str:
        """Call Claude Haiku with one retry on transient failures.

        Args:
            stage: Build stage name for context
            spec:  Truncated product spec (max 300 chars)

        Returns:
            Stripped narration sentence from Claude

        Raises:
            Exception on second consecutive failure (caller handles in narrate())
        """
        from anthropic._exceptions import APITimeoutError, RateLimitError

        settings = get_settings()
        system_prompt, messages = self._build_prompt(stage, spec)

        for attempt in range(2):
            try:
                client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
                response = await asyncio.wait_for(
                    client.messages.create(
                        model=NARRATION_MODEL,
                        max_tokens=NARRATION_MAX_TOKENS,
                        system=system_prompt,
                        messages=messages,
                    ),
                    timeout=NARRATION_TIMEOUT_SECONDS,
                )
                return response.content[0].text.strip()

            except (TimeoutError, RateLimitError, APITimeoutError) as exc:
                if attempt == 0:
                    logger.warning(
                        "narration_retrying",
                        stage=stage,
                        attempt=attempt,
                        error_type=type(exc).__name__,
                    )
                    await asyncio.sleep(_RETRY_BACKOFF_SECONDS)
                    continue
                raise

        # Unreachable — loop always raises or returns on attempt=1
        raise RuntimeError("narration_exhausted_retries")  # pragma: no cover

    def _build_prompt(self, stage: str, spec: str) -> tuple[str, list[dict]]:
        """Build system prompt and messages list for narration generation.

        Args:
            stage: Build stage name for context
            spec:  Truncated product spec (max 300 chars)

        Returns:
            Tuple of (system_prompt, messages_list)
        """
        user_content = (
            f"Stage: {stage}\n"
            f"Product: {spec[:300]}\n"
            "Write one sentence describing what we're doing in this stage."
        )
        messages = [{"role": "user", "content": user_content}]
        return _SYSTEM_PROMPT, messages

    def _apply_safety_filter(self, text: str) -> str:
        """Apply regex-based content safety filter to narration text.

        Reuses _SAFETY_PATTERNS from doc_generation_service — no duplication.
        Strips paths, framework names, PascalCase filenames, code blocks.

        Args:
            text: Raw narration text from Claude

        Returns:
            Filtered, whitespace-normalized text string
        """
        for pattern, replacement in _SAFETY_PATTERNS:
            text = pattern.sub(replacement, text)
        return text.strip()


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

_narration_service = NarrationService()
