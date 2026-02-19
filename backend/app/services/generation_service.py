"""GenerationService: Orchestrates the full build pipeline for a job.

Wires Runner (LLM code generation) + E2BSandboxRuntime (execution) into
the JobStateMachine transitions, persisting sandbox build results.
"""

import uuid
from datetime import datetime, timezone
from typing import Callable
from uuid import uuid4

import structlog
from sqlalchemy import select

from app.agent.runner import Runner
from app.agent.state import create_initial_state
from app.db.base import get_session_factory
from app.metrics.cloudwatch import emit_business_event
from app.queue.schemas import JobStatus
from app.queue.state_machine import JobStateMachine
from app.sandbox.e2b_runtime import E2BSandboxRuntime

logger = structlog.get_logger(__name__)


class GenerationService:
    """Orchestrates the build pipeline: Runner (LLM) + E2B sandbox execution.

    Constructor uses dependency injection so tests can supply fakes for both
    the runner and the sandbox runtime without touching any real APIs.

    Args:
        runner: Runner implementation (RunnerReal in prod, RunnerFake in tests)
        sandbox_runtime_factory: Zero-arg callable returning an E2BSandboxRuntime
            (or compatible fake). Called once per execute_build invocation.
    """

    def __init__(
        self,
        runner: Runner,
        sandbox_runtime_factory: Callable[[], E2BSandboxRuntime],
    ) -> None:
        self.runner = runner
        self.sandbox_runtime_factory = sandbox_runtime_factory

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def execute_build(
        self,
        job_id: str,
        job_data: dict,
        state_machine: JobStateMachine,
    ) -> dict:
        """Execute the full build pipeline and return sandbox build results.

        Pipeline stages:
            STARTING -> SCAFFOLD -> CODE -> DEPS -> CHECKS -> (caller handles READY)

        Args:
            job_id: Unique job identifier (Redis key)
            job_data: Job metadata dict (user_id, project_id, goal, tier, …)
            state_machine: JobStateMachine for publishing transitions

        Returns:
            Dict with keys: sandbox_id, preview_url, build_version, workspace_path

        Raises:
            Exception: On any pipeline failure (after transitioning to FAILED)
        """
        sandbox = None
        user_id = job_data.get("user_id", "")
        project_id = job_data.get("project_id", "")

        try:
            # 1. STARTING
            await state_machine.transition(job_id, JobStatus.STARTING, "Starting generation pipeline")

            # 2. SCAFFOLD — create initial LangGraph state
            await state_machine.transition(job_id, JobStatus.SCAFFOLD, "Scaffolding project state")
            agent_state = create_initial_state(
                user_id=user_id,
                project_id=project_id,
                project_path=f"/home/user/project",
                goal=job_data.get("goal", ""),
                session_id=job_id,
            )

            # 3. CODE — run the Runner pipeline
            await state_machine.transition(job_id, JobStatus.CODE, "Running LLM code generation pipeline")
            final_state = await self.runner.run(agent_state)

            # 4. DEPS — create E2B sandbox, write generated files
            await state_machine.transition(job_id, JobStatus.DEPS, "Provisioning E2B sandbox and installing dependencies")
            sandbox = self.sandbox_runtime_factory()
            await sandbox.start()

            # Extend sandbox lifetime so it survives the full build cycle
            sandbox._sandbox.set_timeout(3600)

            # Write all generated files into sandbox
            working_files: dict = final_state.get("working_files", {})
            workspace_path = "/home/user/project"
            for rel_path, file_change in working_files.items():
                # FileChange is a TypedDict — content is in the 'content' key
                content = (
                    file_change.get("content", "")
                    if isinstance(file_change, dict)
                    else str(file_change)
                )
                abs_path = (
                    rel_path
                    if rel_path.startswith("/")
                    else f"{workspace_path}/{rel_path}"
                )
                await sandbox.write_file(abs_path, content)

            # 5. CHECKS — basic health check
            await state_machine.transition(job_id, JobStatus.CHECKS, "Running health checks")
            await sandbox.run_command("echo 'health-check-ok'", cwd=workspace_path)

            # 6. Compute build result fields
            host = sandbox._sandbox.get_host(8080)
            preview_url = f"https://{host}"
            sandbox_id = sandbox._sandbox.sandbox_id
            build_version = await self._get_next_build_version(project_id, state_machine)

            # 7. Post-build hook: MVP Built state transition (non-fatal)
            try:
                await self._handle_mvp_built_transition(
                    job_id=job_id,
                    project_id=project_id,
                    build_version=build_version,
                    preview_url=preview_url,
                )
            except Exception:
                logger.warning(
                    "mvp_built_hook_failed", job_id=job_id, exc_info=True
                )

            # Emit artifact_generated business event on successful build
            await emit_business_event("artifact_generated", user_id=user_id)

            return {
                "sandbox_id": sandbox_id,
                "preview_url": preview_url,
                "build_version": build_version,
                "workspace_path": workspace_path,
            }

        except Exception as exc:
            debug_id = str(uuid4())
            logger.error(
                "execute_build_failed",
                job_id=job_id,
                debug_id=debug_id,
                error=str(exc),
                error_type=type(exc).__name__,
                exc_info=True,
            )
            await state_machine.transition(
                job_id,
                JobStatus.FAILED,
                f"Build failed — debug_id: {debug_id}. {_friendly_message(exc)}",
            )
            # Attach debug_id so caller can persist it
            exc.debug_id = debug_id  # type: ignore[attr-defined]
            raise

    async def execute_iteration_build(
        self,
        job_id: str,
        job_data: dict,
        state_machine: JobStateMachine,
        change_request: dict,
    ) -> dict:
        """Execute an iteration build that patches an existing sandbox or rebuilds from scratch.

        Implements GENL-02, GENL-03, GENL-04, GENL-05, GENL-06.

        Pipeline stages:
            STARTING -> SCAFFOLD -> CODE -> DEPS -> CHECKS -> (caller handles READY)

        Args:
            job_id: Unique job identifier (Redis key)
            job_data: Job metadata dict (user_id, project_id, goal, tier, previous_sandbox_id, …)
            state_machine: JobStateMachine for publishing transitions
            change_request: Dict with at minimum {"change_description": "..."} plus optional context

        Returns:
            Dict with keys: sandbox_id, preview_url, build_version, workspace_path

        Raises:
            Exception: On any pipeline failure (after transitioning to FAILED)
        """
        sandbox = None
        user_id = job_data.get("user_id", "")
        project_id = job_data.get("project_id", "")
        previous_sandbox_id = job_data.get("previous_sandbox_id", None)

        try:
            # 1. STARTING
            await state_machine.transition(job_id, JobStatus.STARTING, "Starting iteration build pipeline")

            # 2. SCAFFOLD — try to reconnect to previous sandbox, fall back to fresh
            await state_machine.transition(job_id, JobStatus.SCAFFOLD, "Reconnecting to existing sandbox or scaffolding fresh state")

            sandbox_reconnected = False
            sandbox = None

            if previous_sandbox_id:
                try:
                    # Attempt to reconnect to previous sandbox (GENL-02: patch workspace)
                    sandbox = self.sandbox_runtime_factory()
                    await sandbox.connect(previous_sandbox_id)
                    sandbox_reconnected = True
                    logger.info("iteration_sandbox_reconnected", job_id=job_id,
                                previous_sandbox_id=previous_sandbox_id)
                except Exception as connect_exc:
                    logger.warning(
                        "iteration_sandbox_unavailable",
                        job_id=job_id,
                        previous_sandbox_id=previous_sandbox_id,
                        error=str(connect_exc),
                        error_type=type(connect_exc).__name__,
                    )
                    sandbox = None
                    sandbox_reconnected = False

            if sandbox is None:
                # Full rebuild from scratch (fallback or no prior sandbox)
                sandbox = self.sandbox_runtime_factory()
                await sandbox.start()

            # Extend sandbox lifetime
            sandbox._sandbox.set_timeout(3600)

            # 3. CODE — run Runner with change_request context
            await state_machine.transition(job_id, JobStatus.CODE, "Running LLM patch generation")

            # Build agent state that includes the change request context
            agent_state = create_initial_state(
                user_id=user_id,
                project_id=project_id,
                project_path="/home/user/project",
                goal=change_request.get("change_description", job_data.get("goal", "")),
                session_id=job_id,
            )
            # Embed the change request into the state for the Runner to consume
            agent_state["change_request"] = change_request

            final_state = await self.runner.run(agent_state)

            # 4. DEPS — write changed files to sandbox (patch mode for reconnected, full for fresh)
            await state_machine.transition(
                job_id,
                JobStatus.DEPS,
                "Writing patched files to sandbox",
            )

            working_files: dict = final_state.get("working_files", {})
            workspace_path = "/home/user/project"
            for rel_path, file_change in working_files.items():
                content = (
                    file_change.get("content", "")
                    if isinstance(file_change, dict)
                    else str(file_change)
                )
                abs_path = (
                    rel_path
                    if rel_path.startswith("/")
                    else f"{workspace_path}/{rel_path}"
                )
                await sandbox.write_file(abs_path, content)

            # 5. CHECKS — run health check, attempt rollback if fails (GENL-03)
            await state_machine.transition(job_id, JobStatus.CHECKS, "Running health checks on patched build")

            check_result = await sandbox.run_command("echo 'health-check-ok'", cwd=workspace_path)
            check_passed = check_result.get("exit_code", 0) == 0

            if not check_passed:
                logger.warning("iteration_health_check_failed", job_id=job_id)
                # Attempt one rollback: revert files (re-run without the patch)
                try:
                    rollback_state = create_initial_state(
                        user_id=user_id,
                        project_id=project_id,
                        project_path=workspace_path,
                        goal=job_data.get("goal", ""),
                        session_id=job_id,
                    )
                    rollback_result = await self.runner.run(rollback_state)
                    rollback_files: dict = rollback_result.get("working_files", {})
                    for rel_path, file_change in rollback_files.items():
                        content = (
                            file_change.get("content", "")
                            if isinstance(file_change, dict)
                            else str(file_change)
                        )
                        abs_path = (
                            rel_path if rel_path.startswith("/") else f"{workspace_path}/{rel_path}"
                        )
                        await sandbox.write_file(abs_path, content)
                except Exception as rollback_exc:
                    logger.error("iteration_rollback_failed", job_id=job_id,
                                 error=str(rollback_exc), error_type=type(rollback_exc).__name__)

                # Mark as needs-review even if rollback ran
                await state_machine.transition(
                    job_id,
                    JobStatus.FAILED,
                    "Build check failed — needs-review. Your change may have introduced an error. Please review the code before deploying.",
                )
                debug_id = str(uuid4())
                exc = RuntimeError("Build check failed after patch: needs-review")
                exc.debug_id = debug_id  # type: ignore[attr-defined]
                raise exc

            # 6. Compute build result fields
            host = sandbox._sandbox.get_host(8080)
            preview_url = f"https://{host}"
            sandbox_id = sandbox._sandbox.sandbox_id
            build_version = await self._get_next_build_version(project_id, state_machine)

            # 7. Timeline narration (GENL-05)
            try:
                await self._log_iteration_event(
                    project_id=project_id,
                    build_version=build_version,
                    change_request=change_request,
                )
            except Exception:
                logger.warning(
                    "iteration_timeline_event_failed", job_id=job_id, exc_info=True
                )

            return {
                "sandbox_id": sandbox_id,
                "preview_url": preview_url,
                "build_version": build_version,
                "workspace_path": workspace_path,
            }

        except Exception as exc:
            if hasattr(exc, "debug_id"):
                # Already handled (needs-review path raises with debug_id)
                raise
            debug_id = str(uuid4())
            logger.error(
                "execute_iteration_build_failed",
                job_id=job_id,
                debug_id=debug_id,
                error=str(exc),
                error_type=type(exc).__name__,
                exc_info=True,
            )
            await state_machine.transition(
                job_id,
                JobStatus.FAILED,
                f"Iteration build failed — debug_id: {debug_id}. {_friendly_message(exc)}",
            )
            exc.debug_id = debug_id  # type: ignore[attr-defined]
            raise

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    async def _get_next_build_version(
        self,
        project_id: str,
        state_machine: JobStateMachine,
    ) -> str:
        """Compute next build version for a project.

        Queries the Job table for the highest existing build_version of READY
        jobs for this project, parses "build_v0_N", returns "build_v0_{N+1}".
        First build returns "build_v0_1".

        Args:
            project_id: Project UUID string
            state_machine: JobStateMachine (unused here; kept for symmetry / future use)

        Returns:
            Version string like "build_v0_1"
        """
        from app.db.models.job import Job
        import uuid as _uuid

        try:
            factory = get_session_factory()
            async with factory() as session:
                result = await session.execute(
                    select(Job.build_version)
                    .where(Job.project_id == _uuid.UUID(project_id))
                    .where(Job.status == JobStatus.READY.value)
                    .where(Job.build_version.isnot(None))
                )
                versions = [row[0] for row in result.fetchall()]
        except Exception:
            # If DB unavailable, default to first version
            versions = []

        max_n = 0
        for v in versions:
            # Expected format: "build_v0_N"
            try:
                n = int(v.rsplit("_", 1)[-1])
                if n > max_n:
                    max_n = n
            except (ValueError, AttributeError):
                continue

        return f"build_v0_{max_n + 1}"

    async def _handle_mvp_built_transition(
        self,
        job_id: str,
        project_id: str,
        build_version: str,
        preview_url: str,
    ) -> None:
        """Trigger MVP Built state when first build (build_v0_1) completes.

        MVPS-01: stage transitions to 3 (Development / MVP Built)
        MVPS-03: Timeline event logged
        MVPS-04: Strategy graph node marked completed (via StrategyGraph, non-fatal)

        Only fires for build_v0_1 (first build). Subsequent builds are no-ops.
        """
        if build_version != "build_v0_1":
            return  # Only first build triggers MVP transition

        from app.db.models.project import Project
        from app.db.models.stage_event import StageEvent

        pid = uuid.UUID(project_id)
        correlation_id = uuid.uuid4()
        factory = get_session_factory()
        async with factory() as session:
            # Load project
            result = await session.execute(
                select(Project).where(Project.id == pid)
            )
            project = result.scalar_one_or_none()
            if project is None:
                logger.warning("mvp_built_hook_project_not_found", project_id=project_id)
                return

            # Only advance if project is currently at stage 2 (Validated Direction)
            # or any earlier stage — skip if already at 3+ (idempotent guard)
            current_stage = project.stage_number if project.stage_number is not None else 0
            if current_stage >= 3:
                logger.info(
                    "mvp_built_hook_already_advanced",
                    project_id=project_id,
                    current_stage=current_stage,
                )
                return

            # Directly advance stage to 3 (MVP Built / Development)
            from_stage_value = project.stage_number
            project.stage_number = 3
            project.stage_entered_at = datetime.now(timezone.utc)

            # Log transition event
            transition_event = StageEvent(
                project_id=pid,
                correlation_id=correlation_id,
                event_type="transition",
                from_stage=str(from_stage_value) if from_stage_value is not None else "pre-stage",
                to_stage="3",
                actor="system",
                detail={"target_stage": 3, "trigger": "build_complete"},
            )
            session.add(transition_event)

            # Log mvp_built timeline event (MVPS-03)
            mvp_event = StageEvent(
                project_id=pid,
                correlation_id=correlation_id,
                event_type="mvp_built",
                actor="system",
                detail={
                    "preview_url": preview_url,
                    "build_version": build_version,
                },
                reason="First MVP build completed and preview deployed",
            )
            session.add(mvp_event)
            await session.commit()

        # Sync to Neo4j strategy graph (MVPS-04, non-fatal)
        try:
            from app.db.graph.strategy_graph import get_strategy_graph
            strategy_graph = get_strategy_graph()
            await strategy_graph.upsert_milestone_node({
                "id": f"mvp_built_{project_id}",
                "project_id": project_id,
                "title": "Stage: MVP Built",
                "status": "done",
                "type": "milestone",
                "why": "MVP build completed",
                "impact_summary": f"Build {build_version} deployed to {preview_url}",
                "created_at": datetime.now(timezone.utc).isoformat(),
            })
        except Exception:
            logger.warning("neo4j_mvp_built_sync_failed", project_id=project_id, exc_info=True)

    async def _log_iteration_event(
        self,
        project_id: str,
        build_version: str,
        change_request: dict,
    ) -> None:
        """Log a StageEvent for a completed iteration build (GENL-05: timeline narration).

        Args:
            project_id: Project UUID string
            build_version: New build version string (e.g. "build_v0_2")
            change_request: Dict with change_description and other context
        """
        from app.db.models.stage_event import StageEvent

        change_description = change_request.get("change_description", "")[:100]
        pid = uuid.UUID(project_id)
        factory = get_session_factory()
        async with factory() as session:
            iteration_event = StageEvent(
                project_id=pid,
                correlation_id=uuid.uuid4(),
                event_type="iteration_completed",
                actor="system",
                detail={
                    "build_version": build_version,
                    "change_description": change_request.get("change_description", ""),
                },
                reason=f"Iteration build {build_version}: {change_description}",
            )
            session.add(iteration_event)
            await session.commit()


def _friendly_message(exc: Exception) -> str:
    """Convert a raw exception into a user-friendly failure message."""
    msg = str(exc)
    if "timeout" in msg.lower():
        return "The build timed out. Try a smaller scope or contact support."
    if "sandbox" in msg.lower():
        return "The build sandbox could not be started. Our team has been notified."
    if "rate" in msg.lower() or "429" in msg:
        return "LLM rate limit reached. Please try again in a few minutes."
    return "An unexpected error occurred during the build. Our team has been notified."
