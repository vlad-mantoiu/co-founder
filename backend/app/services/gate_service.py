"""GateService — orchestrates decision gate lifecycle with domain logic."""

import uuid
from datetime import UTC, datetime

import structlog
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm.attributes import flag_modified

from app.agent.runner import Runner
from app.db.models.artifact import Artifact
from app.db.models.decision_gate import DecisionGate
from app.db.models.onboarding_session import OnboardingSession
from app.db.models.project import Project
from app.db.models.understanding_session import UnderstandingSession
from app.schemas.decision_gates import (
    GATE_1_OPTIONS,
    GATE_2_OPTIONS,
    CreateGateResponse,
    GateStatusResponse,
    ResolveGateResponse,
)
from app.services.graph_service import GraphService
from app.services.journey import JourneyService

logger = structlog.get_logger(__name__)


class GateService:
    """Service layer for decision gate operations.

    Orchestrates gate creation, resolution, status checks, and blocking enforcement.
    Integrates with domain logic, Runner for LLM operations, and persistence.
    """

    def __init__(self, runner: Runner, session_factory: async_sessionmaker[AsyncSession]):
        """Initialize with dependency injection.

        Args:
            runner: Runner instance for LLM operations
            session_factory: SQLAlchemy async session factory
        """
        self.runner = runner
        self.session_factory = session_factory

    async def create_gate(self, clerk_user_id: str, project_id: str, gate_type: str) -> CreateGateResponse:
        """Create a decision gate for a project.

        Args:
            clerk_user_id: Clerk user ID for ownership check
            project_id: UUID string of the project
            gate_type: Type of gate (e.g., "direction" for Gate 1)

        Returns:
            CreateGateResponse with gate_id and options

        Raises:
            HTTPException(404): Project not found or not owned by user
            HTTPException(409): Pending gate already exists for this project+type
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

            # Check for existing pending gate
            result = await session.execute(
                select(DecisionGate).where(
                    DecisionGate.project_id == project_uuid,
                    DecisionGate.gate_type == gate_type,
                    DecisionGate.status == "pending",
                )
            )
            existing_gate = result.scalar_one_or_none()
            if existing_gate:
                raise HTTPException(
                    status_code=409,
                    detail=f"Pending {gate_type} gate already exists for this project",
                )

            # Get brief summary from Idea Brief artifact for context
            result = await session.execute(
                select(Artifact).where(
                    Artifact.project_id == project_uuid,
                    Artifact.artifact_type == "idea_brief",
                )
            )
            brief_artifact = result.scalar_one_or_none()
            brief_summary = ""
            if brief_artifact and brief_artifact.current_content:
                brief_summary = (
                    brief_artifact.current_content.get("problem_statement", "")
                    or brief_artifact.current_content.get("title", "")
                    or project.name
                )

            # Create gate using JourneyService
            journey_service = JourneyService(session)
            gate_id = await journey_service.create_gate(
                project_id=project_uuid,
                gate_type=gate_type,
                stage_number=project.stage_number or 1,
                context={"brief_summary": brief_summary},
            )

            # Return response with options (Gate 2 has different options than Gate 1)
            options_map = {"direction": GATE_1_OPTIONS, "solidification": GATE_2_OPTIONS}
            options = options_map.get(gate_type, GATE_1_OPTIONS)
            return CreateGateResponse(
                gate_id=str(gate_id),
                gate_type=gate_type,
                status="pending",
                options=options,
                created_at=datetime.now(UTC).isoformat(),
            )

    async def resolve_gate(
        self,
        clerk_user_id: str,
        gate_id: str,
        decision: str,
        action_text: str | None = None,
        park_note: str | None = None,
    ) -> ResolveGateResponse:
        """Resolve a pending gate with a decision.

        Args:
            clerk_user_id: Clerk user ID for ownership check
            gate_id: UUID string of the gate to resolve
            decision: Decision string ("proceed", "narrow", "pivot", "park")
            action_text: Description for narrow/pivot (required for those decisions)
            park_note: Optional note for park decision

        Returns:
            ResolveGateResponse with resolution summary and next action

        Raises:
            HTTPException(404): Gate not found or not owned by user
            HTTPException(409): Gate already decided
            HTTPException(422): Missing required action_text for narrow/pivot
        """
        async with self.session_factory() as session:
            # Load gate with ownership check
            gate_uuid = uuid.UUID(gate_id)
            result = await session.execute(select(DecisionGate).where(DecisionGate.id == gate_uuid))
            gate = result.scalar_one_or_none()
            if not gate:
                raise HTTPException(status_code=404, detail="Gate not found")

            # Verify project ownership
            result = await session.execute(
                select(Project).where(Project.id == gate.project_id, Project.clerk_user_id == clerk_user_id)
            )
            project = result.scalar_one_or_none()
            if not project:
                raise HTTPException(status_code=404, detail="Gate not found")

            # Check gate is pending
            if gate.status != "pending":
                raise HTTPException(status_code=409, detail=f"Gate already decided (status: {gate.status})")

            # Validate action_text for narrow/pivot
            if decision in ["narrow", "pivot"] and not action_text:
                raise HTTPException(
                    status_code=422,
                    detail=f"action_text is required for {decision} decision",
                )

            # Resolve gate via JourneyService
            journey_service = JourneyService(session)
            await journey_service.decide_gate(
                gate_id=gate_uuid, decision=decision, decided_by="founder", reason=action_text or park_note
            )

            # Handle decision-specific actions
            if gate.gate_type == "solidification":
                # Gate 2: compute alignment score and store in context (SOLD-02)
                score, creep = await self._compute_gate2_alignment(session, gate.project_id)
                gate.context = gate.context or {}
                gate.context["alignment_score"] = score
                gate.context["scope_creep_detected"] = creep
                from sqlalchemy.orm.attributes import flag_modified

                flag_modified(gate, "context")
                await session.commit()

                if decision == "iterate":
                    resolution_summary = f"Ready to iterate. Alignment: {score}%"
                    next_action = "Submit your change request"
                elif decision == "ship":
                    resolution_summary = "Ready to assess deploy readiness"
                    next_action = "We'll check your build for deploy readiness"
                else:  # park
                    resolution_summary = f"Project parked: {park_note or 'No note provided'}"
                    next_action = "You can revisit this project anytime from the Parked section"
            elif decision == "narrow":
                await self._handle_narrow(session, gate, project, action_text)
                resolution_summary = "Scope narrowed based on your input"
                next_action = "Review the updated Idea Brief, then proceed to execution planning"
            elif decision == "pivot":
                await self._handle_pivot(session, gate, project, action_text)
                resolution_summary = "New direction set based on your pivot"
                next_action = "Review the new Idea Brief, then proceed to execution planning"
            elif decision == "park":
                resolution_summary = f"Project parked: {park_note or 'No note provided'}"
                next_action = "You can revisit this project anytime from the Parked section"
            else:  # proceed
                resolution_summary = "Ready to proceed to execution planning"
                next_action = "We'll generate execution plan options for you to choose from"

            response = ResolveGateResponse(
                gate_id=str(gate_uuid),
                decision=decision,
                status="decided",
                resolution_summary=resolution_summary,
                next_action=next_action,
            )

            # Dual-write to Neo4j strategy graph (non-fatal)
            await self._sync_to_graph(gate, project.id)

            return response

    async def _compute_gate2_alignment(self, session: AsyncSession, project_id: uuid.UUID) -> tuple[int, bool]:
        """Compute alignment score for Gate 2 (solidification) using existing artifacts.

        Loads MVP Scope artifact as original scope and all change_request artifacts
        as requested changes. Falls back to neutral (75, False) when artifacts missing.

        Args:
            session: SQLAlchemy session
            project_id: Project UUID

        Returns:
            Tuple of (score: int, scope_creep_detected: bool)
        """
        from app.domain.alignment import compute_alignment_score

        # Load MVP Scope artifact for original scope
        mvp_result = await session.execute(
            select(Artifact).where(
                Artifact.project_id == project_id,
                Artifact.artifact_type == "mvp_scope",
            )
        )
        mvp_artifact = mvp_result.scalar_one_or_none()
        original_scope: dict = mvp_artifact.current_content or {} if mvp_artifact else {}

        # Load all existing change_request artifacts
        cr_result = await session.execute(
            select(Artifact).where(
                Artifact.project_id == project_id,
                Artifact.artifact_type.like("change_request_%"),
            )
        )
        change_request_artifacts = cr_result.scalars().all()
        requested_changes: list[dict] = [cr.current_content for cr in change_request_artifacts if cr.current_content]

        return compute_alignment_score(original_scope, requested_changes)

    async def _sync_to_graph(self, gate: DecisionGate, project_id: uuid.UUID) -> None:
        """Dual-write resolved gate to Neo4j strategy graph. Non-fatal."""
        try:
            from app.db.graph.strategy_graph import get_strategy_graph

            graph_service = GraphService(get_strategy_graph())
            await graph_service.sync_decision_to_graph(gate, str(project_id))
        except Exception:
            logger.warning("neo4j_sync_failed", entity="gate", gate_id=str(gate.id), exc_info=True)

    async def _handle_narrow(
        self, session: AsyncSession, gate: DecisionGate, project: Project, action_text: str
    ) -> None:
        """Handle narrow decision: regenerate brief with narrowed scope via Runner.

        Args:
            session: SQLAlchemy session
            gate: DecisionGate being resolved
            project: Project being narrowed
            action_text: Narrowing instructions from founder
        """
        # Store action_text in gate context
        gate.context = gate.context or {}
        gate.context["narrowing_instruction"] = action_text
        flag_modified(gate, "context")

        # Get existing Idea Brief
        result = await session.execute(
            select(Artifact).where(Artifact.project_id == project.id, Artifact.artifact_type == "idea_brief")
        )
        brief_artifact = result.scalar_one_or_none()
        if not brief_artifact:
            return  # No brief to update

        # Load OnboardingSession for idea_text context
        onboarding_result = await session.execute(
            select(OnboardingSession)
            .where(OnboardingSession.project_id == project.id)
            .order_by(OnboardingSession.created_at.desc())
            .limit(1)
        )
        onboarding = onboarding_result.scalar_one_or_none()

        # Load UnderstandingSession for questions/answers context
        understanding_result = await session.execute(
            select(UnderstandingSession)
            .where(UnderstandingSession.project_id == project.id)
            .order_by(UnderstandingSession.created_at.desc())
            .limit(1)
        )
        understanding = understanding_result.scalar_one_or_none()

        # Build narrowing context
        if onboarding:
            narrowed_idea = f"{onboarding.idea_text}\n\n[NARROWING INSTRUCTION]: {action_text}"
        else:
            narrowed_idea = f"{project.name}: {project.description}\n\n[NARROWING INSTRUCTION]: {action_text}"

        questions = understanding.questions if understanding else []
        answers = understanding.answers if understanding else {}

        # Regenerate full brief with narrowing context via Runner
        new_brief_content = await self.runner.generate_idea_brief(
            idea=narrowed_idea, questions=questions, answers=answers
        )

        # Rotate versions
        brief_artifact.previous_content = brief_artifact.current_content
        brief_artifact.current_content = new_brief_content
        flag_modified(brief_artifact, "current_content")
        flag_modified(brief_artifact, "previous_content")
        brief_artifact.version_number += 1
        brief_artifact.has_user_edits = False
        brief_artifact.updated_at = datetime.now(UTC)

        await session.commit()

    async def _handle_pivot(
        self, session: AsyncSession, gate: DecisionGate, project: Project, action_text: str
    ) -> None:
        """Handle pivot decision: regenerate brief with new direction via Runner.

        Args:
            session: SQLAlchemy session
            gate: DecisionGate being resolved
            project: Project being pivoted
            action_text: Pivot description from founder
        """
        # Store action_text in gate context
        gate.context = gate.context or {}
        gate.context["pivot_description"] = action_text
        flag_modified(gate, "context")

        # Get existing Idea Brief
        result = await session.execute(
            select(Artifact).where(Artifact.project_id == project.id, Artifact.artifact_type == "idea_brief")
        )
        brief_artifact = result.scalar_one_or_none()
        if not brief_artifact:
            return  # No brief to update

        # Load OnboardingSession for original idea context
        onboarding_result = await session.execute(
            select(OnboardingSession)
            .where(OnboardingSession.project_id == project.id)
            .order_by(OnboardingSession.created_at.desc())
            .limit(1)
        )
        onboarding = onboarding_result.scalar_one_or_none()

        # Load UnderstandingSession for questions/answers context
        understanding_result = await session.execute(
            select(UnderstandingSession)
            .where(UnderstandingSession.project_id == project.id)
            .order_by(UnderstandingSession.created_at.desc())
            .limit(1)
        )
        understanding = understanding_result.scalar_one_or_none()

        # Build pivot context — action_text IS the new direction
        original_idea = onboarding.idea_text if onboarding else project.name
        pivoted_idea = f"[PIVOT — NEW DIRECTION]: {action_text}\n\nOriginal idea: {original_idea}"

        questions = understanding.questions if understanding else []
        answers = understanding.answers if understanding else {}

        # Regenerate full brief with pivot context via Runner
        new_brief_content = await self.runner.generate_idea_brief(
            idea=pivoted_idea, questions=questions, answers=answers
        )

        # Rotate versions
        brief_artifact.previous_content = brief_artifact.current_content
        brief_artifact.current_content = new_brief_content
        flag_modified(brief_artifact, "current_content")
        flag_modified(brief_artifact, "previous_content")
        brief_artifact.version_number += 1
        brief_artifact.has_user_edits = False
        brief_artifact.updated_at = datetime.now(UTC)

        await session.commit()

    async def get_gate_status(self, clerk_user_id: str, gate_id: str) -> GateStatusResponse:
        """Get status of a decision gate.

        Args:
            clerk_user_id: Clerk user ID for ownership check
            gate_id: UUID string of the gate

        Returns:
            GateStatusResponse with current state

        Raises:
            HTTPException(404): Gate not found or not owned by user
        """
        async with self.session_factory() as session:
            # Load gate with ownership check
            gate_uuid = uuid.UUID(gate_id)
            result = await session.execute(select(DecisionGate).where(DecisionGate.id == gate_uuid))
            gate = result.scalar_one_or_none()
            if not gate:
                raise HTTPException(status_code=404, detail="Gate not found")

            # Verify project ownership
            result = await session.execute(
                select(Project).where(Project.id == gate.project_id, Project.clerk_user_id == clerk_user_id)
            )
            project = result.scalar_one_or_none()
            if not project:
                raise HTTPException(status_code=404, detail="Gate not found")

            options_map = {"direction": GATE_1_OPTIONS, "solidification": GATE_2_OPTIONS}
            options = options_map.get(gate.gate_type, GATE_1_OPTIONS) if gate.status == "pending" else []
            return GateStatusResponse(
                gate_id=str(gate.id),
                gate_type=gate.gate_type,
                status=gate.status,
                decision=gate.decision,
                decided_at=gate.decided_at.isoformat() if gate.decided_at else None,
                options=options,
            )

    async def get_pending_gate(self, clerk_user_id: str, project_id: str) -> GateStatusResponse | None:
        """Get pending gate for a project, if any.

        Args:
            clerk_user_id: Clerk user ID for ownership check
            project_id: UUID string of the project

        Returns:
            GateStatusResponse if pending gate exists, None otherwise

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

            # Query for pending gate
            result = await session.execute(
                select(DecisionGate)
                .where(DecisionGate.project_id == project_uuid, DecisionGate.status == "pending")
                .order_by(DecisionGate.created_at.desc())
                .limit(1)
            )
            gate = result.scalar_one_or_none()
            if not gate:
                return None

            options_map = {"direction": GATE_1_OPTIONS, "solidification": GATE_2_OPTIONS}
            options = options_map.get(gate.gate_type, GATE_1_OPTIONS)
            return GateStatusResponse(
                gate_id=str(gate.id),
                gate_type=gate.gate_type,
                status=gate.status,
                decision=None,
                decided_at=None,
                options=options,
            )

    async def check_gate_blocking(self, project_id: str) -> bool:
        """Check if there's a pending gate blocking operations.

        Args:
            project_id: UUID string of the project

        Returns:
            True if pending gate exists, False otherwise

        Note: Does not enforce user ownership (used by other services that already checked)
        """
        async with self.session_factory() as session:
            project_uuid = uuid.UUID(project_id)
            result = await session.execute(
                select(DecisionGate)
                .where(DecisionGate.project_id == project_uuid, DecisionGate.status == "pending")
                .limit(1)
            )
            gate = result.scalar_one_or_none()
            return gate is not None
