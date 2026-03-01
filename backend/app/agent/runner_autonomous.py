"""AutonomousRunner: TAOR (Think-Act-Observe-Repeat) loop implementation.

Replaces the LangGraph-based pipeline with a direct Anthropic SDK streaming
tool-use loop. Wires together:
- build_system_prompt() — assembles founder context into agent system prompt
- IterationGuard — iteration cap, repetition detection, tool result truncation
- InMemoryToolDispatcher — stateful tool stub (Phase 42 swaps to E2B)
- LogStreamer — writes narration to Redis Stream for SSE frontend delivery
- BudgetService — per-call cost tracking + graceful/hard circuit breakers (Phase 43)
- CheckpointService — PostgreSQL checkpoint persistence after each iteration (Phase 43)
- WakeDaemon — asyncio.Event sleep/wake lifecycle (Phase 43)

All 13 pre-existing Runner protocol methods (onboarding, brief, artifacts, etc.)
remain as NotImplementedError stubs — they are for the pre-existing pipeline
and are not used by the autonomous agent path.
"""

from __future__ import annotations

import anthropic
import structlog

from app.agent.loop.safety import IterationCapError, IterationGuard, RepetitionError
from app.agent.loop.system_prompt import build_system_prompt
from app.agent.state import CoFounderState
from app.agent.tools.definitions import AGENT_TOOLS
from app.agent.tools.dispatcher import InMemoryToolDispatcher
from app.core.config import get_settings
from app.services.log_streamer import LogStreamer

logger = structlog.get_logger(__name__)


# ──────────────────────────────────────────────────────────────────────────────
# Pure helper functions — no I/O, no side effects (Phase 46 — UI Integration)
# ──────────────────────────────────────────────────────────────────────────────


def _human_tool_label(tool_name: str, tool_input: dict) -> str:  # type: ignore[type-arg]
    """Return a human-readable label for a tool call.

    Used by the UI to display what the agent is doing in real time.
    Pure function: no I/O, no side effects.

    Args:
        tool_name: The tool's registered name (e.g. "write_file").
        tool_input: The tool's input dict from the Anthropic response.

    Returns:
        A short human-readable label string.
    """
    if tool_name == "bash":
        cmd = tool_input.get("command", "")[:80]
        return f"Ran command: {cmd}"
    if tool_name == "write_file":
        path = tool_input.get("path", "file")
        return f"Wrote {path}"
    if tool_name == "edit_file":
        path = tool_input.get("path", "file")
        return f"Edited {path}"
    if tool_name == "read_file":
        path = tool_input.get("path", "file")
        return f"Read {path}"
    if tool_name == "grep":
        pattern = tool_input.get("pattern", "")
        return f"Searched for '{pattern}'"
    if tool_name == "glob":
        pattern = tool_input.get("pattern", "")
        return f"Listed files matching '{pattern}'"
    if tool_name == "take_screenshot":
        return "Captured screenshot"
    if tool_name == "narrate":
        return "Narrated progress"
    if tool_name == "document":
        return "Generated documentation"
    return f"Used {tool_name}"


def _summarize_tool_result(result: str | list, max_len: int = 200) -> str:  # type: ignore[type-arg]
    """Truncate a tool result to max_len characters with '...' suffix.

    Vision content lists (list[dict]) are converted to a short placeholder.
    Pure function: no I/O, no side effects.

    Args:
        result: Tool result — either a string or a vision content list.
        max_len: Maximum character length before truncation.

    Returns:
        A string, truncated to max_len + '...' if needed.
    """
    if isinstance(result, list):
        return "[vision content]"
    text = str(result)
    if len(text) <= max_len:
        return text
    return text[:max_len] + "..."


class AutonomousRunner:
    """TAOR agent runner using Anthropic streaming tool-use API.

    Implements the Runner protocol. The core method is ``run_agent_loop()``
    which executes the autonomous Think-Act-Observe-Repeat cycle.

    All other protocol methods (generate_questions, generate_brief, etc.) remain
    as NotImplementedError stubs — those are for the pre-existing onboarding and
    brief generation pipeline handled by RunnerReal.
    """

    def __init__(
        self,
        model: str = "claude-sonnet-4-20250514",
        api_key: str | None = None,
    ) -> None:
        settings = get_settings()
        self._model = model
        self._client = anthropic.AsyncAnthropic(
            api_key=api_key or settings.anthropic_api_key
        )

    # ------------------------------------------------------------------
    # Core TAOR loop
    # ------------------------------------------------------------------

    async def run_agent_loop(self, context: dict) -> dict:  # type: ignore[type-arg]
        """Execute the autonomous TAOR agent loop for a build session.

        Args:
            context: Dict with required keys:
                - project_id: str
                - user_id: str
                - job_id: str
                - idea_brief: dict
                - understanding_qna: list[dict]
                - build_plan: dict
                - redis: Redis connection (optional — skip streaming if absent)
                - max_tool_calls: int (optional, default 150)
                - dispatcher: ToolDispatcher (optional — for testing)
                - budget_service: BudgetService (optional — skip budget if absent)
                - checkpoint_service: CheckpointService (optional — skip checkpoints if absent)
                - db_session: AsyncSession (optional — required for budget/checkpoint ops)
                - wake_daemon: WakeDaemon (optional — sleep/wake lifecycle)
                - session_id: str (optional — defaults to job_id)
                - tier: str (optional — defaults to "bootstrapper")
                - sandbox_id: str (optional — for checkpoint state)
                - current_phase: str (optional — for checkpoint state)
                - retry_counts: dict (optional — for checkpoint state; shared with ErrorSignatureTracker)
                - state_machine: JobStateMachine (optional — for SSE budget events)
                - error_tracker: ErrorSignatureTracker (optional — routes tool dispatch errors)

        Returns:
            Dict with keys: status, project_id, phases_completed, result
            status values: "completed" | "iteration_limit_reached" | "repetition_detected"
                          | "api_error" | "budget_exceeded" | "escalation_threshold_exceeded"
        """
        from app.agent.budget.service import BudgetExceededError

        project_id = context.get("project_id")
        job_id = context.get("job_id", "unknown")
        bound_logger = logger.bind(job_id=job_id, project_id=project_id)

        # --- Setup ---
        system = build_system_prompt(
            context["idea_brief"],
            context["understanding_qna"],
            context.get("build_plan", {}),
        )

        guard = IterationGuard(max_tool_calls=context.get("max_tool_calls", 150))

        # Use injected dispatcher (for testing) or default InMemoryToolDispatcher
        dispatcher = context.get("dispatcher") or InMemoryToolDispatcher()

        # Create LogStreamer only if redis is provided
        redis = context.get("redis")
        streamer: LogStreamer | None = None
        if redis is not None:
            streamer = LogStreamer(redis=redis, job_id=job_id, phase="agent")

        # ---- Integration Point 1: Session Start ----
        budget_service = context.get("budget_service")
        checkpoint_service = context.get("checkpoint_service")
        db_session = context.get("db_session")
        user_id = context.get("user_id", "")
        session_id = context.get("session_id", job_id)
        state_machine = context.get("state_machine")
        wake_daemon = context.get("wake_daemon")
        snapshot_service = context.get("snapshot_service")
        sandbox_runtime = context.get("sandbox_runtime")
        error_tracker = context.get("error_tracker")
        # Shared retry_counts dict — same reference held by ErrorSignatureTracker and CheckpointService
        retry_counts = context.get("retry_counts", {})

        daily_budget: int = 0
        session_cost: int = 0
        graceful_wind_down = False

        if budget_service and db_session:
            daily_budget = await budget_service.calc_daily_budget(user_id, db_session)

        if db_session:
            from app.db.models.agent_session import AgentSession
            agent_session = AgentSession(
                id=session_id,
                job_id=job_id,
                clerk_user_id=user_id,
                tier=context.get("tier", "bootstrapper"),
                model_used=self._model,
                daily_budget_microdollars=daily_budget,
            )
            db_session.add(agent_session)
            try:
                await db_session.commit()
            except Exception as exc:
                bound_logger.warning("agent_session_create_failed", error=str(exc))

        # Initial user message — Anthropic requires at least one user turn
        messages: list[dict] = [  # type: ignore[type-arg]
            {"role": "user", "content": "Begin building the project per the build plan."}
        ]
        iteration_count = 0

        # Check for existing checkpoint — restore if found
        if checkpoint_service and db_session:
            try:
                existing = await checkpoint_service.restore(session_id, db_session)
                if existing is not None and existing.message_history:
                    messages = existing.message_history
                    iteration_count = existing.iteration_number
                    guard._count = iteration_count
                    bound_logger.info(
                        "taor_loop_checkpoint_restored",
                        iteration=iteration_count,
                    )
            except Exception as exc:
                bound_logger.warning("taor_loop_restore_failed", error=str(exc))

        bound_logger.info("taor_loop_start", model=self._model)

        # GSD phase tracking (Phase 46 — UI Integration)
        # Tracks the in-progress phase so we can emit gsd.phase.completed before the next one starts.
        _current_phase_id: str | None = None

        try:
            while True:
                # ---- THINK: emit agent.thinking before each stream call ----
                if state_machine:
                    from datetime import UTC, datetime as _dt
                    from app.queue.state_machine import SSEEventType as _SSEEventType
                    await state_machine.publish_event(
                        job_id,
                        {"type": _SSEEventType.AGENT_THINKING},
                    )

                # ---- THINK: stream response from Anthropic ----
                async with self._client.messages.stream(
                    model=self._model,
                    system=system,
                    messages=messages,
                    tools=AGENT_TOOLS,
                    max_tokens=4096,
                ) as stream:
                    # Accumulate narration text — flush on sentence boundaries
                    # to avoid per-token Redis writes
                    accumulated_text = ""
                    async for chunk in stream.text_stream:
                        accumulated_text += chunk
                        if accumulated_text.rstrip().endswith((".", "!", "?", "\n")):
                            line = accumulated_text.strip()
                            if line and streamer:
                                await streamer.write_event(line, source="agent")
                            accumulated_text = ""

                    # Flush any remaining text after stream exhausted
                    if accumulated_text.strip() and streamer:
                        await streamer.write_event(accumulated_text.strip(), source="agent")

                    # Get the full message snapshot AFTER consuming text_stream
                    response = await stream.get_final_message()

                # Track usage (Phase 43 budget daemon acts on these)
                _input_tokens = response.usage.input_tokens
                _output_tokens = response.usage.output_tokens
                bound_logger.debug(
                    "taor_loop_usage",
                    input_tokens=_input_tokens,
                    output_tokens=_output_tokens,
                )

                # ---- Integration Point 2: After each streaming response ----
                if budget_service:
                    session_cost = await budget_service.record_call_cost(
                        session_id,
                        user_id,
                        self._model,
                        _input_tokens,
                        _output_tokens,
                        context.get("redis"),
                    )
                    budget_pct = await budget_service.get_budget_percentage(
                        session_id,
                        user_id,
                        daily_budget,
                        context.get("redis"),
                    )
                    if state_machine:
                        await state_machine.publish_event(
                            job_id,
                            {
                                "type": "agent.budget_updated",
                                "budget_pct": int(budget_pct * 100),
                            },
                        )
                    # Write budget_pct Redis key for REST bootstrap (UIAG-04)
                    if redis:
                        await redis.set(
                            f"cofounder:agent:{session_id}:budget_pct",
                            int(budget_pct * 100),
                            ex=90,  # 90s TTL — matches SSE heartbeat window
                        )
                    # Hard circuit breaker — BudgetExceededError propagates to outer try
                    await budget_service.check_runaway(
                        session_id, user_id, daily_budget, context.get("redis")
                    )
                    # Graceful threshold — finish current dispatch, no new iterations
                    if budget_service.is_at_graceful_threshold(session_cost, daily_budget):
                        graceful_wind_down = True

                # ---- Check stop condition ----
                if response.stop_reason == "end_turn":
                    final_text = ""
                    for block in response.content:
                        if hasattr(block, "text"):
                            final_text += block.text
                    bound_logger.info("taor_loop_end_turn", result_length=len(final_text))

                    # ---- Integration Point 4: Sleep/Wake on graceful wind-down ----
                    if graceful_wind_down:
                        if state_machine:
                            await state_machine.publish_event(
                                job_id,
                                {
                                    "type": "agent.sleeping",
                                    "message": "Agent paused until budget refresh",
                                    "budget_pct": 100,
                                },
                            )
                        if redis:
                            await redis.set(
                                f"cofounder:agent:{session_id}:state",
                                "sleeping",
                                ex=90_000,
                            )
                        # Write wake_at Redis key for REST bootstrap countdown timer (UIAG-04)
                        if redis:
                            from datetime import UTC, datetime as _dt_wake, timedelta as _td_wake
                            _now_utc = _dt_wake.now(UTC)
                            _next_midnight = (_now_utc.replace(hour=0, minute=0, second=0, microsecond=0)
                                              + _td_wake(days=1))
                            _sleep_seconds = max(1, int((_next_midnight - _now_utc).total_seconds()))
                            await redis.set(
                                f"cofounder:agent:{session_id}:wake_at",
                                _next_midnight.isoformat(),
                                ex=_sleep_seconds,  # TTL matches sleep duration
                            )
                        if checkpoint_service and db_session:
                            await checkpoint_service.save(
                                session_id=session_id,
                                job_id=job_id,
                                message_history=messages,
                                sandbox_id=context.get("sandbox_id"),
                                current_phase=context.get("current_phase"),
                                retry_counts=retry_counts,
                                session_cost_microdollars=session_cost,
                                daily_budget_microdollars=daily_budget,
                                iteration_number=guard._count,
                                agent_state="sleeping",
                                db=db_session,
                            )
                        # Forced S3 sync before sleep — prevent work loss during long sleep periods (MIGR-04)
                        if snapshot_service and sandbox_runtime:
                            try:
                                await snapshot_service.sync(
                                    runtime=sandbox_runtime,
                                    project_id=context.get("project_id", ""),
                                )
                            except Exception:
                                logger.warning("pre_sleep_snapshot_failed", session_id=session_id, exc_info=True)
                        if wake_daemon:
                            await wake_daemon.wake_event.wait()
                            wake_daemon.wake_event.clear()
                        if state_machine:
                            await state_machine.publish_event(
                                job_id,
                                {
                                    "type": "agent.waking",
                                    "message": "Resuming — budget refreshed. Continuing from last task.",
                                },
                            )
                        if redis:
                            await redis.set(
                                f"cofounder:agent:{session_id}:state",
                                "working",
                                ex=90_000,
                            )
                        if budget_service and db_session:
                            daily_budget = await budget_service.calc_daily_budget(
                                user_id, db_session
                            )
                        graceful_wind_down = False
                        session_cost = 0
                        # Continue the TAOR loop — do NOT return
                        continue

                    return {
                        "status": "completed",
                        "project_id": project_id,
                        "phases_completed": [],
                        "result": final_text,
                    }

                # ---- ACT: find tool_use blocks ----
                tool_use_blocks = [b for b in response.content if b.type == "tool_use"]
                if not tool_use_blocks:
                    # No tool calls and not end_turn — treat as implicit completion
                    final_text = ""
                    for block in response.content:
                        if hasattr(block, "text"):
                            final_text += block.text
                    bound_logger.info("taor_loop_implicit_end", result_length=len(final_text))
                    return {
                        "status": "completed",
                        "project_id": project_id,
                        "phases_completed": [],
                        "result": final_text,
                    }

                # Append assistant turn to history BEFORE processing tool calls
                # (Anthropic API requires assistant turn before tool_result user turn)
                messages.append({"role": "assistant", "content": response.content})

                # ---- OBSERVE: dispatch each tool call ----
                tool_results: list[dict] = []  # type: ignore[type-arg]
                steered = False  # Flag: first-strike repetition steering injected

                for tool_block in tool_use_blocks:
                    iteration = guard._count + 1
                    tool_name = tool_block.name
                    tool_input = tool_block.input

                    # Safety checks before dispatch
                    try:
                        guard.check_iteration_cap()
                        guard.check_repetition(tool_name, tool_input)
                    except IterationCapError:
                        stop_msg = (
                            f"I've reached my action limit of {guard._max} tool calls. "
                            "Here's what I completed and what's remaining..."
                        )
                        if streamer:
                            await streamer.write_event(stop_msg, source="agent")
                        bound_logger.warning("taor_loop_iteration_cap", max=guard._max)
                        return {
                            "status": "iteration_limit_reached",
                            "project_id": project_id,
                            "phases_completed": [],
                            "result": stop_msg,
                        }
                    except RepetitionError as e:
                        # Two-strike repetition handling:
                        # First strike → steer, continue loop
                        # Second strike → terminate
                        if not guard._had_repetition_warning:
                            guard._had_repetition_warning = True
                            steer_msg = (
                                "I noticed I'm repeating myself. "
                                "Let me try a different approach."
                            )
                            if streamer:
                                await streamer.write_event(steer_msg, source="agent")
                            # Clear the repetition window so guard doesn't re-fire immediately
                            guard._window.clear()
                            # Inject steering tool_result as user turn to redirect model
                            messages.append({
                                "role": "user",
                                "content": [{
                                    "type": "tool_result",
                                    "tool_use_id": tool_block.id,
                                    "content": (
                                        "SYSTEM: You repeated the same tool call 3 times. "
                                        "Please try a completely different approach to achieve the same goal."
                                    ),
                                }],
                            })
                            steered = True
                            bound_logger.warning(
                                "taor_loop_repetition_first_strike",
                                tool_name=tool_name,
                            )
                            break  # Break inner tool dispatch loop; outer while continues
                        else:
                            # Second repetition — terminate
                            stop_msg = (
                                f"Hit a repeated action pattern twice. {str(e)}. "
                                "Stopping to avoid a loop."
                            )
                            if streamer:
                                await streamer.write_event(stop_msg, source="agent")
                            bound_logger.error(
                                "taor_loop_repetition_second_strike",
                                tool_name=tool_name,
                            )
                            return {
                                "status": "repetition_detected",
                                "project_id": project_id,
                                "phases_completed": [],
                                "result": stop_msg,
                            }

                    # Narrate before tool call (per CONTEXT.md: narrate before AND after)
                    if streamer:
                        await streamer.write_event(
                            f"Running `{tool_name}` ...", source="agent"
                        )

                    # Dispatch tool — route errors through ErrorSignatureTracker
                    try:
                        result = await dispatcher.dispatch(tool_name, tool_input)
                    except Exception as exc:
                        # Guard: Anthropic API errors must NOT reach the error tracker
                        # They are handled by the outer except anthropic.APIError block
                        if isinstance(exc, anthropic.APIError):
                            raise  # Re-raise to outer handler

                        error_type_name = type(exc).__name__
                        error_message = str(exc)

                        if error_tracker:
                            # Step 1: Check never-retry first (auth/permission errors escalate immediately)
                            if error_tracker.should_escalate_immediately(error_type_name, error_message):
                                escalation_id = await error_tracker.record_escalation(
                                    error_type=error_type_name,
                                    error_message=error_message,
                                    attempts=["Immediate escalation — this error type cannot be retried"],
                                    recommended_action="This requires manual configuration or credentials",
                                    plain_english_problem=f"I encountered a permissions or configuration issue: {error_type_name}",
                                )
                                result = (
                                    f"ESCALATED TO FOUNDER: {error_type_name} — this cannot be retried automatically. "
                                    f"I've asked the founder for help. Move on to other tasks while waiting."
                                )
                                if state_machine:
                                    await state_machine.publish_event(
                                        job_id,
                                        {"type": "agent.waiting_for_input", "escalation_id": str(escalation_id) if escalation_id else None},
                                    )
                            else:
                                # Step 2: Record and check retry budget for CODE_ERROR / ENV_ERROR
                                should_escalate, attempt_num = error_tracker.record_and_check(error_type_name, error_message)
                                if should_escalate:
                                    escalation_id = await error_tracker.record_escalation(
                                        error_type=error_type_name,
                                        error_message=error_message,
                                        attempts=[f"Attempt {i}: different approach tried" for i in range(1, attempt_num)],
                                        recommended_action="I've tried multiple approaches. The founder can skip this feature, try a simpler version, or provide guidance.",
                                        plain_english_problem=f"I tried {attempt_num - 1} different approaches but kept hitting the same issue: {error_type_name}",
                                    )
                                    result = (
                                        f"ESCALATED TO FOUNDER after {attempt_num - 1} attempts: {error_type_name}: {error_message}. "
                                        f"I've asked the founder for help. Move on to other unblocked tasks."
                                    )
                                    if state_machine:
                                        await state_machine.publish_event(
                                            job_id,
                                            {"type": "agent.waiting_for_input", "escalation_id": str(escalation_id) if escalation_id else None},
                                        )
                                    # Check global threshold — pause build if too many escalations
                                    if error_tracker.global_threshold_exceeded():
                                        if state_machine:
                                            await state_machine.publish_event(
                                                job_id,
                                                {"type": "agent.build_paused", "reason": "Too many unresolvable issues encountered"},
                                            )
                                        bound_logger.error("taor_loop_global_threshold_exceeded", session_id=session_id)
                                        return {
                                            "status": "escalation_threshold_exceeded",
                                            "project_id": project_id,
                                            "phases_completed": [],
                                            "reason": f"Global escalation threshold ({error_tracker._session_escalation_count}) exceeded",
                                        }
                                else:
                                    # Retry allowed — inject replanning context so model takes a different approach
                                    from app.agent.error.tracker import _build_retry_tool_result
                                    result = _build_retry_tool_result(
                                        error_type_name,
                                        error_message,
                                        attempt_num,
                                        original_intent=context.get("current_task_intent", "building the project"),
                                    )
                                    if state_machine:
                                        await state_machine.publish_event(
                                            job_id,
                                            {"type": "agent.retrying", "attempt": attempt_num, "error_type": error_type_name},
                                        )
                        else:
                            # Fallback: no error tracker — bare error string (backward compatible)
                            result = f"Error: {error_type_name}: {error_message}"

                        bound_logger.warning(
                            "taor_tool_dispatch_error",
                            tool_name=tool_name,
                            error=str(exc),
                            iteration=iteration,
                        )

                    # ---- Phase 46: GSD phase tracking via narrate(phase_name=...) ----
                    # When the agent narrates with a phase_name, emit gsd.phase.started
                    # and complete the previous phase if one was in progress.
                    if tool_name == "narrate" and state_machine:
                        from datetime import UTC, datetime as _dt2
                        from app.queue.state_machine import SSEEventType as _SSEEventType2
                        import uuid as _uuid_mod
                        phase_name = tool_input.get("phase_name")
                        if phase_name:
                            _ts = _dt2.now(UTC).isoformat()
                            # Complete any previous in-progress phase
                            if _current_phase_id is not None:
                                completed_data = {
                                    "phase_id": _current_phase_id,
                                    "status": "completed",
                                    "completed_at": _ts,
                                }
                                await state_machine.publish_event(
                                    job_id,
                                    {"type": _SSEEventType2.GSD_PHASE_COMPLETED, **completed_data},
                                )
                                if redis:
                                    import json as _json
                                    # Update existing entry status to completed
                                    existing_raw = await redis.hget(f"job:{job_id}:phases", _current_phase_id)
                                    if existing_raw:
                                        existing_entry = _json.loads(existing_raw)
                                        existing_entry["status"] = "completed"
                                        existing_entry["completed_at"] = _ts
                                        await redis.hset(f"job:{job_id}:phases", _current_phase_id, _json.dumps(existing_entry))
                            # Start new phase
                            new_phase_id = str(_uuid_mod.uuid4())
                            _current_phase_id = new_phase_id
                            phase_data = {
                                "phase_id": new_phase_id,
                                "phase_name": phase_name,
                                "status": "in_progress",
                                "started_at": _ts,
                            }
                            await state_machine.publish_event(
                                job_id,
                                {"type": _SSEEventType2.GSD_PHASE_STARTED, **phase_data},
                            )
                            if redis:
                                import json as _json2
                                await redis.hset(f"job:{job_id}:phases", new_phase_id, _json2.dumps(phase_data))

                    # ---- Phase 46: Emit agent.tool.called after successful dispatch ----
                    if state_machine:
                        from datetime import UTC, datetime as _dt3
                        from app.queue.state_machine import SSEEventType as _SSEEventType3
                        await state_machine.publish_event(
                            job_id,
                            {
                                "type": _SSEEventType3.AGENT_TOOL_CALLED,
                                "tool_name": tool_name,
                                "tool_label": _human_tool_label(tool_name, tool_input),
                                "tool_summary": _summarize_tool_result(result),
                            },
                        )

                    # Middle-truncate large string results before appending to history.
                    # Vision content lists (list[dict]) are passed through as-is —
                    # they contain base64 images which must not be truncated.
                    if isinstance(result, str):
                        result = guard.truncate_tool_result(result)

                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tool_block.id,
                        "content": result,
                    })

                # ---- REPEAT: append tool results, continue loop ----
                # Skip normal append if steering already injected the user turn
                if steered:
                    # Outer while-loop continues with steering message already in messages
                    continue

                messages.append({"role": "user", "content": tool_results})

                # ---- Integration Point 3: After each full TAOR iteration ----
                if checkpoint_service and db_session:
                    await checkpoint_service.save(
                        session_id=session_id,
                        job_id=job_id,
                        message_history=messages,
                        sandbox_id=context.get("sandbox_id"),
                        current_phase=context.get("current_phase"),
                        retry_counts=retry_counts,
                        session_cost_microdollars=session_cost if budget_service else 0,
                        daily_budget_microdollars=daily_budget if budget_service else 0,
                        iteration_number=guard._count,
                        agent_state="working",
                        db=db_session,
                    )
                    # S3 snapshot at checkpoint boundary — approximates phase commit (MIGR-04)
                    # Per locked decision: batch at boundaries, not per write_file/edit_file
                    if snapshot_service and sandbox_runtime:
                        try:
                            await snapshot_service.sync(
                                runtime=sandbox_runtime,
                                project_id=context.get("project_id", ""),
                            )
                        except Exception:
                            logger.warning("checkpoint_snapshot_failed", session_id=session_id, exc_info=True)

        except BudgetExceededError:
            # Hard circuit breaker fired — set Redis state, emit SSE, save checkpoint
            # CRITICAL: must NOT propagate — job status must NOT become FAILED
            bound_logger.error("taor_loop_budget_exceeded", session_id=session_id)
            if state_machine:
                await state_machine.publish_event(
                    job_id,
                    {
                        "type": "agent.budget_exceeded",
                        "message": "Agent stopped — daily budget exceeded",
                    },
                )
            if redis:
                await redis.set(
                    f"cofounder:agent:{session_id}:state",
                    "budget_exceeded",
                    ex=90_000,
                )
            if checkpoint_service and db_session:
                await checkpoint_service.save(
                    session_id=session_id,
                    job_id=job_id,
                    message_history=messages,
                    sandbox_id=context.get("sandbox_id"),
                    current_phase=context.get("current_phase"),
                    retry_counts=retry_counts,
                    session_cost_microdollars=session_cost,
                    daily_budget_microdollars=daily_budget,
                    iteration_number=guard._count,
                    agent_state="budget_exceeded",
                    db=db_session,
                )
            return {
                "status": "budget_exceeded",
                "project_id": project_id,
                "phases_completed": [],
                "reason": "Daily budget exceeded by >10%",
            }
        except anthropic.APIError as exc:
            error_msg = f"Anthropic API error: {type(exc).__name__}: {str(exc)}"
            bound_logger.error("taor_loop_api_error", error=str(exc))
            return {
                "status": "api_error",
                "project_id": project_id,
                "phases_completed": [],
                "result": error_msg,
            }

    # ------------------------------------------------------------------
    # Runner protocol stubs (pre-existing pipeline — not used by autonomous agent)
    # ------------------------------------------------------------------

    async def run(self, state: CoFounderState) -> CoFounderState:
        """Execute the full pipeline.

        Raises:
            NotImplementedError: Not used by autonomous agent path — Phase 41
        """
        raise NotImplementedError("AutonomousRunner.run() not yet implemented — Phase 41")

    async def step(self, state: CoFounderState, stage: str) -> CoFounderState:
        """Execute a single named node from the pipeline.

        Raises:
            NotImplementedError: Not used by autonomous agent path — Phase 41
        """
        raise NotImplementedError("AutonomousRunner.step() not yet implemented — Phase 41")

    async def generate_questions(self, context: dict) -> list[dict]:  # type: ignore[type-arg]
        """Generate onboarding questions tailored to the user's idea context.

        Raises:
            NotImplementedError: Not used by autonomous agent path — Phase 41
        """
        raise NotImplementedError("AutonomousRunner.generate_questions() not yet implemented — Phase 41")

    async def generate_brief(self, answers: dict) -> dict:  # type: ignore[type-arg]
        """Generate a structured product brief from onboarding answers.

        Raises:
            NotImplementedError: Not used by autonomous agent path — Phase 41
        """
        raise NotImplementedError("AutonomousRunner.generate_brief() not yet implemented — Phase 41")

    async def generate_artifacts(self, brief: dict) -> dict:  # type: ignore[type-arg]
        """Generate documentation artifacts from the product brief.

        Raises:
            NotImplementedError: Not used by autonomous agent path — Phase 41
        """
        raise NotImplementedError("AutonomousRunner.generate_artifacts() not yet implemented — Phase 41")

    async def generate_understanding_questions(self, context: dict) -> list[dict]:  # type: ignore[type-arg]
        """Generate adaptive understanding questions (deeper than onboarding).

        Raises:
            NotImplementedError: Not used by autonomous agent path — Phase 41
        """
        raise NotImplementedError("AutonomousRunner.generate_understanding_questions() not yet implemented — Phase 41")

    async def generate_idea_brief(self, idea: str, questions: list[dict], answers: dict) -> dict:  # type: ignore[type-arg]
        """Generate Rationalised Idea Brief from understanding interview answers.

        Raises:
            NotImplementedError: Not used by autonomous agent path — Phase 41
        """
        raise NotImplementedError("AutonomousRunner.generate_idea_brief() not yet implemented — Phase 41")

    async def check_question_relevance(
        self, idea: str, answered: list[dict], answers: dict, remaining: list[dict]
    ) -> dict:  # type: ignore[type-arg]
        """Check if remaining questions are still relevant after an answer edit.

        Raises:
            NotImplementedError: Not used by autonomous agent path — Phase 41
        """
        raise NotImplementedError("AutonomousRunner.check_question_relevance() not yet implemented — Phase 41")

    async def assess_section_confidence(self, section_key: str, content: str) -> str:
        """Assess confidence level for a brief section.

        Raises:
            NotImplementedError: Not used by autonomous agent path — Phase 41
        """
        raise NotImplementedError("AutonomousRunner.assess_section_confidence() not yet implemented — Phase 41")

    async def generate_execution_options(self, brief: dict, feedback: str | None = None) -> dict:  # type: ignore[type-arg]
        """Generate 2-3 execution plan options from the Idea Brief.

        Raises:
            NotImplementedError: Not used by autonomous agent path — Phase 41
        """
        raise NotImplementedError("AutonomousRunner.generate_execution_options() not yet implemented — Phase 41")

    async def generate_strategy_graph(self, idea: str, brief: dict, onboarding_answers: dict) -> dict:  # type: ignore[type-arg]
        """Generate Strategy Graph artifact from idea brief and onboarding data.

        Raises:
            NotImplementedError: Not used by autonomous agent path — Phase 41
        """
        raise NotImplementedError("AutonomousRunner.generate_strategy_graph() not yet implemented — Phase 41")

    async def generate_mvp_timeline(self, idea: str, brief: dict, tier: str) -> dict:  # type: ignore[type-arg]
        """Generate MVP Timeline artifact with relative-week milestones.

        Raises:
            NotImplementedError: Not used by autonomous agent path — Phase 41
        """
        raise NotImplementedError("AutonomousRunner.generate_mvp_timeline() not yet implemented — Phase 41")

    async def generate_app_architecture(self, idea: str, brief: dict, tier: str) -> dict:  # type: ignore[type-arg]
        """Generate App Architecture artifact with component diagram and cost estimates.

        Raises:
            NotImplementedError: Not used by autonomous agent path — Phase 41
        """
        raise NotImplementedError("AutonomousRunner.generate_app_architecture() not yet implemented — Phase 41")
