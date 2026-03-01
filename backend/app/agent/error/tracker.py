"""ErrorSignatureTracker — per-error-signature retry tracking and escalation decisions (AGNT-07).

Provides:
- ErrorSignatureTracker: stateful service for retry/escalate decisions
- _build_retry_tool_result(): structured replanning prompt injection for CODE_ERROR/ENV_ERROR retries
- _build_escalation_options(): founder-facing multiple-choice options per error category

Design decisions (from STATE.md / CONTEXT.md):
- retry_counts dict is a MUTABLE reference shared with CheckpointService — never copy it
- MAX_RETRIES_PER_SIGNATURE = 3: agent gets 3 replanning attempts before escalating
- GLOBAL_ESCALATION_THRESHOLD = 5: pause build after 5 total escalations in one session
- record_escalation() is non-fatal: DB failures log and return None, never raise
- NEVER_RETRY errors bypass record_and_check() — should_escalate_immediately() is checked first
- Anthropic API errors (OverloadedError, RateLimitError) are handled by tenacity in llm_helpers;
  they MUST NOT reach this tracker
"""

from __future__ import annotations

import structlog

from app.agent.error.classifier import ErrorCategory, build_error_signature, classify_error

logger = structlog.get_logger(__name__)

MAX_RETRIES_PER_SIGNATURE: int = 3
GLOBAL_ESCALATION_THRESHOLD: int = 5  # pause build after N total session escalations


class ErrorSignatureTracker:
    """Tracks per-error-signature retry counts and decides retry vs escalate.

    Injected via context["error_tracker"] into the TAOR loop.
    The retry_counts dict is shared with CheckpointService so retry state
    persists across sleep/wake cycles — same object reference, never copied.

    State machine per signature:
        attempt 1 (count=1): (False, 1) — retry with replanning context
        attempt 2 (count=2): (False, 2) — retry with replanning context
        attempt 3 (count=3): (False, 3) — retry with replanning context
        attempt 4 (count=4): (True,  4) — escalate to founder

    Usage::

        tracker = ErrorSignatureTracker(
            project_id=project_id,
            retry_counts=retry_counts,  # same dict as CheckpointService receives
            db_session=db,
            session_id=session_id,
            job_id=job_id,
        )

        # In tool dispatch error handler:
        if tracker.should_escalate_immediately(error_type, error_message):
            esc_id = await tracker.record_escalation(...)
            result = _build_escalation_tool_result(...)
        else:
            should_escalate, attempt = tracker.record_and_check(error_type, error_message)
            if should_escalate:
                esc_id = await tracker.record_escalation(...)
                result = _build_escalation_tool_result(...)
            else:
                result = _build_retry_tool_result(error_type, error_message, attempt, intent)
    """

    def __init__(
        self,
        project_id: str,
        retry_counts: dict,  # mutable reference — shared with CheckpointService
        db_session=None,  # AsyncSession | None
        session_id: str = "",
        job_id: str = "",
    ) -> None:
        self._project_id = project_id
        self._retry_counts = retry_counts  # MUST hold the same reference, never copy
        self._db = db_session
        self._session_id = session_id
        self._job_id = job_id
        self._session_escalation_count: int = 0  # tracks global threshold for this session

    # ------------------------------------------------------------------
    # Classification helpers
    # ------------------------------------------------------------------

    def should_escalate_immediately(self, error_type: str, error_message: str) -> bool:
        """Return True if the error is in the NEVER_RETRY category.

        Call this BEFORE record_and_check() to short-circuit auth/permission errors.
        NEVER_RETRY errors should escalate immediately without consuming retry budget.

        Args:
            error_type: Exception class name
            error_message: Error message string

        Returns:
            True if category is NEVER_RETRY, False otherwise
        """
        category = classify_error(error_type, error_message)
        return category == ErrorCategory.NEVER_RETRY

    # ------------------------------------------------------------------
    # Retry state machine
    # ------------------------------------------------------------------

    def record_and_check(
        self,
        error_type: str,
        error_message: str,
    ) -> tuple[bool, int]:
        """Record a failure for this error signature and decide retry vs escalate.

        Increments the count in the shared retry_counts dict (mutates in-place so
        CheckpointService persists the updated state on next save).

        Args:
            error_type: Exception class name
            error_message: Error message string

        Returns:
            Tuple of (should_escalate: bool, attempt_number: int)
            - should_escalate is True when count > MAX_RETRIES_PER_SIGNATURE
            - attempt_number is the 1-indexed count of failures for this signature
        """
        sig = build_error_signature(self._project_id, error_type, error_message)
        current_count = self._retry_counts.get(sig, 0) + 1
        self._retry_counts[sig] = current_count

        should_escalate = current_count > MAX_RETRIES_PER_SIGNATURE
        if should_escalate:
            self._session_escalation_count += 1

        logger.info(
            "error_signature_recorded",
            signature=sig,
            attempt=current_count,
            should_escalate=should_escalate,
            session_escalations=self._session_escalation_count,
        )
        return should_escalate, current_count

    def global_threshold_exceeded(self) -> bool:
        """Return True if total escalations in this session reached GLOBAL_ESCALATION_THRESHOLD.

        When True, the TAOR loop should pause the build and notify the founder.
        A threshold of 5 means 15+ genuine tool failures — appropriate pause point.

        Returns:
            True when _session_escalation_count >= GLOBAL_ESCALATION_THRESHOLD
        """
        return self._session_escalation_count >= GLOBAL_ESCALATION_THRESHOLD

    def reset_signature(self, error_type: str, error_message: str) -> None:
        """Reset the retry count for an error signature (called after founder provides input).

        Founder input is new information — the agent gets 3 fresh attempts with
        the founder's guidance. Removes the key from retry_counts so count starts
        from zero on the next record_and_check() call.

        Mutates the shared retry_counts dict so the reset is persisted on next
        CheckpointService.save() call.

        Args:
            error_type: Exception class name
            error_message: Error message string
        """
        sig = build_error_signature(self._project_id, error_type, error_message)
        self._retry_counts.pop(sig, None)
        logger.info("error_signature_reset", signature=sig)

    # ------------------------------------------------------------------
    # Escalation persistence
    # ------------------------------------------------------------------

    async def record_escalation(
        self,
        error_type: str,
        error_message: str,
        attempts: list[str],
        recommended_action: str,
        plain_english_problem: str,
    ) -> str | None:
        """Persist an escalation record to PostgreSQL and return the escalation ID.

        Non-fatal: DB failures log a warning and return None. The TAOR loop
        must never crash because an escalation write failed.

        Args:
            error_type: Exception class name (stored for internal use, not shown to founder)
            error_message: Raw error message (stored for internal use, not shown to founder)
            attempts: List of human-readable attempt descriptions (plain English)
            recommended_action: Recommended option value from _build_escalation_options()
            plain_english_problem: LLM-generated or template plain English problem description

        Returns:
            Escalation UUID string if persisted, None if no db_session or on failure
        """
        if self._db is None:
            return None
        try:
            # Lazy import to avoid circular imports at module level (established project pattern)
            from app.db.models.agent_escalation import AgentEscalation

            category = classify_error(error_type, error_message)
            options = _build_escalation_options(error_type, category)
            escalation = AgentEscalation(
                session_id=self._session_id,
                job_id=self._job_id,
                project_id=self._project_id,
                error_type=error_type,
                error_signature=build_error_signature(self._project_id, error_type, error_message),
                plain_english_problem=plain_english_problem,
                attempts_summary=attempts,
                recommended_action=recommended_action,
                options=options,
            )
            self._db.add(escalation)
            await self._db.commit()
            await self._db.refresh(escalation)
            return str(escalation.id)
        except Exception as exc:
            logger.warning(
                "escalation_persist_failed",
                error=str(exc),
                error_type=type(exc).__name__,
            )
            return None


# ------------------------------------------------------------------
# Module-level helper functions
# ------------------------------------------------------------------


def _build_retry_tool_result(
    error_type: str,
    error_message: str,
    attempt_num: int,
    original_intent: str,
) -> str:
    """Build a structured replanning prompt injection for the tool_result content.

    This string is returned as the tool_result.content so the Claude model sees it
    as the outcome of its tool call and understands it must replan with a fundamentally
    different approach — not repeat the same call.

    Args:
        error_type: Exception class name
        error_message: Raw error message string
        attempt_num: 1-indexed attempt number (1-3 before escalation)
        original_intent: The original task intent/goal for context

    Returns:
        Structured string with APPROACH N FAILED header and replanning instruction
    """
    return (
        f"APPROACH {attempt_num} FAILED: {error_type}: {error_message}\n\n"
        f"Original goal: {original_intent}\n\n"
        f"INSTRUCTION: The approach you just tried did not work. "
        f"Do NOT repeat the same call. Replan this task from scratch. "
        f"Consider a fundamentally different implementation strategy, different libraries, "
        f"or a simpler alternative that achieves the same goal. "
        f"This is attempt {attempt_num} of {MAX_RETRIES_PER_SIGNATURE} before escalating to the founder."
    )


def _build_escalation_options(error_type: str, category: ErrorCategory) -> list[dict]:
    """Generate founder-facing multiple-choice options for an escalation.

    Returns 2 options for NEVER_RETRY (credentials vs skip) and 3 options for
    CODE_ERROR/ENV_ERROR (skip, simpler version, or provide guidance).

    All text is plain English — no code, no jargon, no stack traces.

    Args:
        error_type: Exception class name (used for future customization)
        category: ErrorCategory from classify_error()

    Returns:
        List of option dicts with "value", "label", and "description" fields
    """
    if category == ErrorCategory.NEVER_RETRY:
        return [
            {
                "value": "provide_credentials",
                "label": "Provide credentials",
                "description": "I'll add the missing API key or permission",
            },
            {
                "value": "skip_feature",
                "label": "Skip this feature",
                "description": "Skip this feature and continue with the rest of the build",
            },
        ]
    # CODE_ERROR or ENV_ERROR — agent tried 3 approaches, needs human guidance
    return [
        {
            "value": "skip_feature",
            "label": "Skip this feature",
            "description": "Skip this and continue building other parts",
        },
        {
            "value": "simpler_version",
            "label": "Try a simpler version",
            "description": "Build a simpler version without this specific functionality",
        },
        {
            "value": "provide_guidance",
            "label": "Give me specific guidance",
            "description": "I'll describe exactly what I want and you try again",
        },
    ]
