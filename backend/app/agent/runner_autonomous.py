"""AutonomousRunner: TAOR (Think-Act-Observe-Repeat) loop implementation.

Replaces the LangGraph-based pipeline with a direct Anthropic SDK streaming
tool-use loop. Wires together:
- build_system_prompt() — assembles founder context into agent system prompt
- IterationGuard — iteration cap, repetition detection, tool result truncation
- InMemoryToolDispatcher — stateful tool stub (Phase 42 swaps to E2B)
- LogStreamer — writes narration to Redis Stream for SSE frontend delivery

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

        Returns:
            Dict with keys: status, project_id, phases_completed, result
            status values: "completed" | "iteration_limit_reached" | "repetition_detected" | "api_error"
        """
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

        # Initial user message — Anthropic requires at least one user turn
        messages: list[dict] = [  # type: ignore[type-arg]
            {"role": "user", "content": "Begin building the project per the build plan."}
        ]

        bound_logger.info("taor_loop_start", model=self._model)

        try:
            while True:
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

                # Track usage (Phase 43 budget daemon will act on these)
                _input_tokens = response.usage.input_tokens
                _output_tokens = response.usage.output_tokens
                bound_logger.debug(
                    "taor_loop_usage",
                    input_tokens=_input_tokens,
                    output_tokens=_output_tokens,
                )

                # ---- Check stop condition ----
                if response.stop_reason == "end_turn":
                    final_text = ""
                    for block in response.content:
                        if hasattr(block, "text"):
                            final_text += block.text
                    bound_logger.info("taor_loop_end_turn", result_length=len(final_text))
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

                    # Dispatch tool — capture errors as result string (loop continues)
                    try:
                        result = await dispatcher.dispatch(tool_name, tool_input)
                    except Exception as exc:
                        result = f"Error: {type(exc).__name__}: {str(exc)}"
                        bound_logger.warning(
                            "taor_tool_dispatch_error",
                            tool_name=tool_name,
                            error=str(exc),
                            iteration=iteration,
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
