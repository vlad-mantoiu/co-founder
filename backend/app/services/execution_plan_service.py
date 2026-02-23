"""ExecutionPlanService — orchestrates execution plan generation, selection, and enforcement.

Provides methods for generating 2-3 execution plan options, selecting an option,
checking if selection has been made (for 409 enforcement), and regenerating with feedback.
"""

import uuid
from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.agent.runner import Runner
from app.db.models.artifact import Artifact
from app.db.models.project import Project
from app.schemas.artifacts import ArtifactType
from app.schemas.execution_plans import (
    ExecutionOption,
    GeneratePlansResponse,
    SelectPlanResponse,
)
from app.services.gate_service import GateService


class ExecutionPlanService:
    """Service layer for execution plan operations.

    Orchestrates execution plan generation, selection, and 409 enforcement.
    Integrates with GateService for gate blocking checks and Runner for LLM operations.
    """

    def __init__(self, runner: Runner, session_factory: async_sessionmaker[AsyncSession]):
        """Initialize with dependency injection.

        Args:
            runner: Runner instance for LLM operations
            session_factory: SQLAlchemy async session factory
        """
        self.runner = runner
        self.session_factory = session_factory

    async def generate_options(
        self, clerk_user_id: str, project_id: str, feedback: str | None = None
    ) -> GeneratePlansResponse:
        """Generate execution plan options for a project.

        Args:
            clerk_user_id: Clerk user ID for ownership check
            project_id: UUID string of the project
            feedback: Optional feedback on previous options (for regeneration)

        Returns:
            GeneratePlansResponse with 2-3 options and recommended option ID

        Raises:
            HTTPException(404): Project not found or not owned by user
            HTTPException(409): Decision Gate 1 not resolved or resolved as non-proceed
        """
        async with self.session_factory() as session:
            # Verify project ownership
            project_uuid = uuid.UUID(project_id)
            result = await session.execute(
                select(Project).where(Project.id == project_uuid, Project.clerk_user_id == clerk_user_id)
            )
            project = result.scalar_one_or_none()
            if not project:
                raise HTTPException(status_code=404, detail="Project not found")

            # Check gate blocking via GateService
            gate_service = GateService(self.runner, self.session_factory)
            is_blocking = await gate_service.check_gate_blocking(project_id)
            if is_blocking:
                raise HTTPException(
                    status_code=409,
                    detail="Decision Gate 1 must be resolved before generating execution plans",
                )

            # Check that gate was resolved with "proceed" decision
            # (Load the latest decided gate and verify decision == "proceed")
            from app.db.models.decision_gate import DecisionGate

            result = await session.execute(
                select(DecisionGate)
                .where(
                    DecisionGate.project_id == project_uuid,
                    DecisionGate.status == "decided",
                )
                .order_by(DecisionGate.decided_at.desc())
                .limit(1)
            )
            latest_gate = result.scalar_one_or_none()
            if latest_gate and latest_gate.decision != "proceed":
                raise HTTPException(
                    status_code=409,
                    detail=f"Cannot generate execution plans after '{latest_gate.decision}' decision. Gate must be resolved with 'proceed'.",
                )

            # Load Idea Brief artifact
            result = await session.execute(
                select(Artifact).where(
                    Artifact.project_id == project_uuid,
                    Artifact.artifact_type == ArtifactType.IDEA_BRIEF,
                )
            )
            brief_artifact = result.scalar_one_or_none()
            if not brief_artifact or not brief_artifact.current_content:
                raise HTTPException(
                    status_code=404,
                    detail="Idea Brief not found. Complete understanding interview first.",
                )

            # Generate options via Runner
            options_data = await self.runner.generate_execution_options(brief_artifact.current_content, feedback)

            # Store plan set as Artifact
            plan_set_id = str(uuid.uuid4())
            execution_plan_artifact = Artifact(
                project_id=project_uuid,
                artifact_type=ArtifactType.EXECUTION_PLAN,
                current_content={
                    "_schema_version": 1,
                    "plan_set_id": plan_set_id,
                    "options": options_data["options"],
                    "recommended_id": options_data["recommended_id"],
                    "generated_at": datetime.now(UTC).isoformat(),
                    "feedback_context": feedback,
                },
                version_number=1,
                generation_status="idle",
            )

            # Check if execution plan artifact already exists
            result = await session.execute(
                select(Artifact).where(
                    Artifact.project_id == project_uuid,
                    Artifact.artifact_type == ArtifactType.EXECUTION_PLAN,
                )
            )
            existing_plan = result.scalar_one_or_none()
            if existing_plan:
                # Version rotate
                existing_plan.previous_content = existing_plan.current_content
                existing_plan.current_content = execution_plan_artifact.current_content
                existing_plan.version_number += 1
                existing_plan.updated_at = datetime.now(UTC)
                await session.commit()
            else:
                # Create new
                session.add(execution_plan_artifact)
                await session.commit()

            return GeneratePlansResponse(
                plan_set_id=plan_set_id,
                options=[ExecutionOption(**opt) for opt in options_data["options"]],
                recommended_id=options_data["recommended_id"],
                generated_at=datetime.now(UTC).isoformat(),
            )

    async def select_option(self, clerk_user_id: str, project_id: str, option_id: str) -> SelectPlanResponse:
        """Select an execution plan option.

        Args:
            clerk_user_id: Clerk user ID for ownership check
            project_id: UUID string of the project
            option_id: ID of the selected option

        Returns:
            SelectPlanResponse with selected option details

        Raises:
            HTTPException(404): Project or execution plan not found, or option ID not found
        """
        async with self.session_factory() as session:
            # Verify project ownership
            project_uuid = uuid.UUID(project_id)
            result = await session.execute(
                select(Project).where(Project.id == project_uuid, Project.clerk_user_id == clerk_user_id)
            )
            project = result.scalar_one_or_none()
            if not project:
                raise HTTPException(status_code=404, detail="Project not found")

            # Load execution plan artifact
            result = await session.execute(
                select(Artifact).where(
                    Artifact.project_id == project_uuid,
                    Artifact.artifact_type == ArtifactType.EXECUTION_PLAN,
                )
            )
            plan_artifact = result.scalar_one_or_none()
            if not plan_artifact or not plan_artifact.current_content:
                raise HTTPException(status_code=404, detail="Execution plan not found")

            # Find option by ID
            options = plan_artifact.current_content.get("options", [])
            selected_option = None
            for opt in options:
                if opt["id"] == option_id:
                    selected_option = opt
                    break

            if not selected_option:
                raise HTTPException(
                    status_code=404,
                    detail=f"Option '{option_id}' not found in current plan set",
                )

            # Store selection in artifact — reassign dict to trigger SQLAlchemy
            # JSONB mutation detection (in-place dict mutation is not tracked)
            updated_content = {**plan_artifact.current_content}
            updated_content["selected_option_id"] = option_id
            updated_content["selected_at"] = datetime.now(UTC).isoformat()
            plan_artifact.current_content = updated_content
            plan_artifact.updated_at = datetime.now(UTC)
            await session.commit()

            return SelectPlanResponse(
                selected_option=ExecutionOption(**selected_option),
                plan_set_id=plan_artifact.current_content.get("plan_set_id", ""),
                message=f"Selected '{selected_option['name']}' execution plan. Ready to start building!",
            )

    async def get_selected_plan(self, clerk_user_id: str, project_id: str) -> ExecutionOption | None:
        """Get the selected execution plan option, if any.

        Args:
            clerk_user_id: Clerk user ID for ownership check
            project_id: UUID string of the project

        Returns:
            ExecutionOption if selected, None otherwise

        Raises:
            HTTPException(404): Project not found or not owned by user
        """
        async with self.session_factory() as session:
            # Verify project ownership
            project_uuid = uuid.UUID(project_id)
            result = await session.execute(
                select(Project).where(Project.id == project_uuid, Project.clerk_user_id == clerk_user_id)
            )
            project = result.scalar_one_or_none()
            if not project:
                raise HTTPException(status_code=404, detail="Project not found")

            # Load execution plan artifact
            result = await session.execute(
                select(Artifact).where(
                    Artifact.project_id == project_uuid,
                    Artifact.artifact_type == ArtifactType.EXECUTION_PLAN,
                )
            )
            plan_artifact = result.scalar_one_or_none()
            if not plan_artifact or not plan_artifact.current_content:
                return None

            selected_option_id = plan_artifact.current_content.get("selected_option_id")
            if not selected_option_id:
                return None

            # Find and return selected option
            options = plan_artifact.current_content.get("options", [])
            for opt in options:
                if opt["id"] == selected_option_id:
                    return ExecutionOption(**opt)

            return None

    async def check_plan_selected(self, project_id: str) -> bool:
        """Check if an execution plan has been selected.

        Used by build services to enforce PLAN-02 (409 if plan not selected).

        Args:
            project_id: UUID string of the project

        Returns:
            True if plan selected, False otherwise

        Note: Does not enforce user ownership (called by services that already verified)
        """
        async with self.session_factory() as session:
            project_uuid = uuid.UUID(project_id)
            result = await session.execute(
                select(Artifact).where(
                    Artifact.project_id == project_uuid,
                    Artifact.artifact_type == ArtifactType.EXECUTION_PLAN,
                )
            )
            plan_artifact = result.scalar_one_or_none()
            if not plan_artifact or not plan_artifact.current_content:
                return False

            selected_option_id = plan_artifact.current_content.get("selected_option_id")
            return selected_option_id is not None

    async def regenerate_options(self, clerk_user_id: str, project_id: str, feedback: str) -> GeneratePlansResponse:
        """Regenerate execution plan options with feedback.

        Args:
            clerk_user_id: Clerk user ID for ownership check
            project_id: UUID string of the project
            feedback: Feedback on why previous options weren't suitable

        Returns:
            GeneratePlansResponse with fresh options

        Raises:
            HTTPException(404): Project not found or not owned by user
            HTTPException(409): Decision Gate 1 not resolved
        """
        # Regeneration is the same as generation with feedback
        return await self.generate_options(clerk_user_id, project_id, feedback)
