"""OnboardingService — orchestrates onboarding flow with Runner integration.

Responsibilities:
- Session lifecycle: start, answer, resume, finalize, abandon
- Tier-based session limits (bootstrapper: 1, partner: 3, cto_scale: unlimited)
- User isolation via clerk_user_id filtering
- ThesisSnapshot tier filtering
- JSONB persistence with flag_modified tracking
"""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm.attributes import flag_modified

from app.agent.runner import Runner
from app.db.models.artifact import Artifact
from app.db.models.decision_gate import DecisionGate
from app.db.models.job import Job
from app.db.models.onboarding_session import OnboardingSession
from app.db.models.plan_tier import PlanTier
from app.db.models.project import Project
from app.db.models.stage_config import StageConfig
from app.db.models.stage_event import StageEvent
from app.db.models.understanding_session import UnderstandingSession
from app.db.models.user_settings import UserSettings

# Tier session limits (concurrent active sessions)
TIER_SESSION_LIMITS = {
    "bootstrapper": 1,
    "partner": 3,
    "cto_scale": -1,  # unlimited
}

LEGACY_STARTER_PROJECT_NAME = "My First Project"


class OnboardingService:
    """Service layer for onboarding flow with Runner integration."""

    def __init__(self, runner: Runner, session_factory: async_sessionmaker[AsyncSession]):
        """Initialize with Runner protocol instance and session factory.

        Args:
            runner: Runner implementation (RunnerFake for tests, RunnerReal for production)
            session_factory: SQLAlchemy async session factory for database access
        """
        self.runner = runner
        self.session_factory = session_factory

    async def start_session(self, user_id: str, idea: str, tier_slug: str) -> OnboardingSession:
        """Start a new onboarding session with LLM-generated questions.

        Args:
            user_id: Clerk user ID
            idea: User's idea text (must be non-empty after strip)
            tier_slug: User's plan tier (bootstrapper, partner, cto_scale)

        Returns:
            New OnboardingSession with questions populated

        Raises:
            HTTPException(403): If user has reached tier session limit
            HTTPException(400): If idea is empty after strip
        """
        # Validate idea is non-empty (defense in depth — Pydantic also validates)
        idea_stripped = idea.strip()
        if not idea_stripped:
            raise HTTPException(status_code=400, detail="Idea cannot be empty")

        # Check tier session limits
        max_sessions = TIER_SESSION_LIMITS.get(tier_slug, 1)

        async with self.session_factory() as session:
            if max_sessions != -1:
                result = await session.execute(
                    select(func.count(OnboardingSession.id)).where(
                        OnboardingSession.clerk_user_id == user_id,
                        OnboardingSession.status == "in_progress",
                    )
                )
                active_count = result.scalar() or 0
                if active_count >= max_sessions:
                    raise HTTPException(
                        status_code=403,
                        detail=f"Active session limit reached ({active_count}/{max_sessions}). Complete or abandon an existing session to start a new one.",
                    )

            # Generate questions via Runner
            questions_data = await self.runner.generate_questions({"idea": idea_stripped})

            # Create session
            new_session = OnboardingSession(
                clerk_user_id=user_id,
                idea_text=idea_stripped,
                questions=questions_data,
                total_questions=len(questions_data),
                answers={},
                status="in_progress",
                current_question_index=0,
            )
            session.add(new_session)
            await session.commit()
            await session.refresh(new_session)

            return new_session

    async def submit_answer(self, user_id: str, session_id: str, question_id: str, answer: str) -> OnboardingSession:
        """Submit an answer to a question and advance current_question_index.

        Args:
            user_id: Clerk user ID
            session_id: Onboarding session UUID
            question_id: Question ID from questions list
            answer: User's answer text

        Returns:
            Updated OnboardingSession

        Raises:
            HTTPException(404): If session not found or user mismatch
            HTTPException(400): If session is not in_progress
        """
        async with self.session_factory() as session:
            result = await session.execute(
                select(OnboardingSession).where(
                    OnboardingSession.id == session_id,
                    OnboardingSession.clerk_user_id == user_id,
                )
            )
            onboarding_session = result.scalar_one_or_none()

            if onboarding_session is None:
                raise HTTPException(status_code=404, detail="Session not found")

            if onboarding_session.status != "in_progress":
                raise HTTPException(status_code=400, detail="Cannot answer questions in completed or abandoned session")

            # Store answer
            onboarding_session.answers[question_id] = answer
            flag_modified(onboarding_session, "answers")

            # Advance current_question_index if this is the current question
            questions = onboarding_session.questions
            for i, q in enumerate(questions):
                if q["id"] == question_id and i == onboarding_session.current_question_index:
                    onboarding_session.current_question_index = min(i + 1, onboarding_session.total_questions)
                    break

            await session.commit()
            await session.refresh(onboarding_session)

            return onboarding_session

    async def get_sessions(self, user_id: str) -> list[OnboardingSession]:
        """Get all sessions for a user (ordered by created_at desc).

        Args:
            user_id: Clerk user ID

        Returns:
            List of OnboardingSession objects for the user
        """
        async with self.session_factory() as session:
            result = await session.execute(
                select(OnboardingSession)
                .where(OnboardingSession.clerk_user_id == user_id)
                .order_by(OnboardingSession.created_at.desc())
            )
            sessions = result.scalars().all()
            return list(sessions)

    async def get_session(self, user_id: str, session_id: str) -> OnboardingSession:
        """Get a specific session (with user isolation).

        Args:
            user_id: Clerk user ID
            session_id: Onboarding session UUID

        Returns:
            OnboardingSession

        Raises:
            HTTPException(404): If session not found or user mismatch
        """
        async with self.session_factory() as session:
            result = await session.execute(
                select(OnboardingSession).where(
                    OnboardingSession.id == session_id,
                    OnboardingSession.clerk_user_id == user_id,
                )
            )
            onboarding_session = result.scalar_one_or_none()

            if onboarding_session is None:
                raise HTTPException(status_code=404, detail="Session not found")

            return onboarding_session

    async def finalize_session(self, user_id: str, session_id: str, tier_slug: str) -> OnboardingSession:
        """Generate ThesisSnapshot (tier-filtered) and complete the session.

        Args:
            user_id: Clerk user ID
            session_id: Onboarding session UUID
            tier_slug: User's plan tier (bootstrapper, partner, cto_scale)

        Returns:
            Updated OnboardingSession with thesis_snapshot populated

        Raises:
            HTTPException(404): If session not found or user mismatch
            HTTPException(400): If required answers are missing
        """
        async with self.session_factory() as session:
            result = await session.execute(
                select(OnboardingSession).where(
                    OnboardingSession.id == session_id,
                    OnboardingSession.clerk_user_id == user_id,
                )
            )
            onboarding_session = result.scalar_one_or_none()

            if onboarding_session is None:
                raise HTTPException(status_code=404, detail="Session not found")

            # Verify all required answers present
            questions = onboarding_session.questions
            answers = onboarding_session.answers
            missing_required = []

            for q in questions:
                if q.get("required") and q["id"] not in answers:
                    missing_required.append(q["id"])

            if missing_required:
                raise HTTPException(
                    status_code=400,
                    detail=f"Missing required answers: {', '.join(missing_required)}",
                )

            # Generate ThesisSnapshot via Runner
            brief_data = await self.runner.generate_brief(answers)

            # Filter by tier
            filtered_snapshot = self._filter_thesis_by_tier(brief_data, tier_slug)

            # Store in session
            onboarding_session.thesis_snapshot = filtered_snapshot
            onboarding_session.status = "completed"
            onboarding_session.completed_at = datetime.now(UTC)
            flag_modified(onboarding_session, "thesis_snapshot")

            await session.commit()
            await session.refresh(onboarding_session)

            return onboarding_session

    async def edit_thesis_field(
        self, user_id: str, session_id: str, field_name: str, new_value: str
    ) -> OnboardingSession:
        """Edit a field in the thesis snapshot (inline edits are canonical).

        Args:
            user_id: Clerk user ID
            session_id: Onboarding session UUID
            field_name: Field name to edit (e.g., "problem", "target_user")
            new_value: New value for the field

        Returns:
            Updated OnboardingSession

        Raises:
            HTTPException(404): If session not found or user mismatch
        """
        async with self.session_factory() as session:
            result = await session.execute(
                select(OnboardingSession).where(
                    OnboardingSession.id == session_id,
                    OnboardingSession.clerk_user_id == user_id,
                )
            )
            onboarding_session = result.scalar_one_or_none()

            if onboarding_session is None:
                raise HTTPException(status_code=404, detail="Session not found")

            # Initialize thesis_edits if None
            if onboarding_session.thesis_edits is None:
                onboarding_session.thesis_edits = {}

            onboarding_session.thesis_edits[field_name] = new_value
            flag_modified(onboarding_session, "thesis_edits")

            await session.commit()
            await session.refresh(onboarding_session)

            return onboarding_session

    async def abandon_session(self, user_id: str, session_id: str) -> OnboardingSession:
        """Abandon a session (frees up session slot for tier limits).

        Args:
            user_id: Clerk user ID
            session_id: Onboarding session UUID

        Returns:
            Updated OnboardingSession

        Raises:
            HTTPException(404): If session not found or user mismatch
        """
        async with self.session_factory() as session:
            result = await session.execute(
                select(OnboardingSession).where(
                    OnboardingSession.id == session_id,
                    OnboardingSession.clerk_user_id == user_id,
                )
            )
            onboarding_session = result.scalar_one_or_none()

            if onboarding_session is None:
                raise HTTPException(status_code=404, detail="Session not found")

            onboarding_session.status = "abandoned"

            await session.commit()
            await session.refresh(onboarding_session)

            return onboarding_session

    async def create_project_from_session(self, user_id: str, session_id: str) -> tuple[OnboardingSession, Project]:
        """Create a Project from a completed onboarding session.

        Args:
            user_id: Clerk user ID
            session_id: Onboarding session UUID

        Returns:
            Tuple of (updated OnboardingSession, new Project)

        Raises:
            HTTPException(404): If session not found or user mismatch
            HTTPException(400): If session is not completed or project already created
            HTTPException(403): If user has reached tier project limit
        """
        async with self.session_factory() as session:
            # Load session with user isolation
            result = await session.execute(
                select(OnboardingSession).where(
                    OnboardingSession.id == session_id,
                    OnboardingSession.clerk_user_id == user_id,
                )
            )
            onboarding_session = result.scalar_one_or_none()

            if onboarding_session is None:
                raise HTTPException(status_code=404, detail="Session not found")

            # Verify session is completed
            if onboarding_session.status != "completed":
                raise HTTPException(
                    status_code=400,
                    detail="Session not completed. Finalize the session before creating a project.",
                )

            # Idempotent guard: verify project not already created
            if onboarding_session.project_id is not None:
                raise HTTPException(
                    status_code=400,
                    detail="Project already created from this session.",
                )

            # Check project limit from effective user settings (override or plan tier default).
            settings_result = await session.execute(
                select(UserSettings, PlanTier)
                .join(PlanTier, UserSettings.plan_tier_id == PlanTier.id)
                .where(UserSettings.clerk_user_id == user_id)
            )
            settings_row = settings_result.one_or_none()
            if settings_row is None:
                raise HTTPException(status_code=404, detail="User settings not found")

            user_settings, plan_tier = settings_row._tuple()
            max_projects = (
                user_settings.override_max_projects
                if user_settings.override_max_projects is not None
                else plan_tier.max_projects
            )

            # Compatibility cleanup: old accounts may still have a legacy auto-created starter
            # project that blocks first onboarding conversion.
            if not user_settings.onboarding_completed:
                await self._archive_legacy_starter_projects(session=session, user_id=user_id)

            if max_projects != -1:
                # Fetch active projects so we can return actionable context on limit errors.
                result = await session.execute(
                    select(Project)
                    .where(
                        Project.clerk_user_id == user_id,
                        Project.status == "active",
                    )
                    .order_by(Project.created_at.desc())
                )
                active_projects = list(result.scalars().all())
                active_count = len(active_projects)

                if active_count >= max_projects:
                    raise HTTPException(
                        status_code=403,
                        detail={
                            "code": "project_limit_reached",
                            "message": (
                                f"Project limit reached ({active_count}/{max_projects}). "
                                "Abandon a project or upgrade to continue."
                            ),
                            "active_count": active_count,
                            "max_projects": max_projects,
                            "upgrade_url": "/billing",
                            "projects_url": "/projects",
                            "active_projects": [
                                {
                                    "id": str(project.id),
                                    "name": project.name,
                                    "status": project.status,
                                    "created_at": project.created_at.isoformat(),
                                }
                                for project in active_projects
                            ],
                        },
                    )

            # Create Project from idea_text
            idea_text = onboarding_session.idea_text

            # Project name: first 50 chars of idea_text (truncated with "..." if longer)
            if len(idea_text) > 50:
                project_name = idea_text[:50] + "..."
            else:
                project_name = idea_text

            project = Project(
                clerk_user_id=user_id,
                name=project_name,
                description=idea_text,  # Full idea_text as description
                status="active",
                stage_number=1,  # Stage.THESIS_DEFINED from Phase 02
            )

            # Link session to project
            session.add(project)
            await session.flush()  # Get project.id before linking

            onboarding_session.project_id = project.id
            flag_modified(onboarding_session, "project_id")

            # Mark onboarding complete at user level for first-time funnel routing.
            if not user_settings.onboarding_completed:
                user_settings.onboarding_completed = True

            await session.commit()
            await session.refresh(onboarding_session)
            await session.refresh(project)

            return (onboarding_session, project)

    # =========================================================================
    # PRIVATE HELPERS
    # =========================================================================

    async def _archive_legacy_starter_projects(self, session: AsyncSession, user_id: str) -> None:
        """Archive inactive legacy starter projects from old auto-provisioning behavior."""
        result = await session.execute(
            select(Project).where(
                Project.clerk_user_id == user_id,
                Project.status == "active",
                Project.name == LEGACY_STARTER_PROJECT_NAME,
            )
        )
        legacy_projects = list(result.scalars().all())
        if not legacy_projects:
            return

        archived_any = False
        for project in legacy_projects:
            if await self._project_has_activity(session=session, project_id=project.id):
                continue
            project.status = "deleted"
            archived_any = True

        if archived_any:
            await session.flush()

    async def _project_has_activity(self, session: AsyncSession, project_id: UUID) -> bool:
        """Return True if project has generated/linked records and should not be auto-archived."""
        checks = (
            select(Artifact.id).where(Artifact.project_id == project_id).limit(1),
            select(DecisionGate.id).where(DecisionGate.project_id == project_id).limit(1),
            select(Job.id).where(Job.project_id == project_id).limit(1),
            select(StageConfig.id).where(StageConfig.project_id == project_id).limit(1),
            select(StageEvent.id).where(StageEvent.project_id == project_id).limit(1),
            select(UnderstandingSession.id).where(UnderstandingSession.project_id == project_id).limit(1),
            select(OnboardingSession.id).where(OnboardingSession.project_id == project_id).limit(1),
        )

        for check in checks:
            if (await session.execute(check)).scalar_one_or_none() is not None:
                return True
        return False

    def _filter_thesis_by_tier(self, brief_data: dict[str, Any], tier_slug: str) -> dict[str, Any]:
        """Filter ThesisSnapshot fields by tier.

        Args:
            brief_data: Full ThesisSnapshot data from Runner
            tier_slug: User's plan tier

        Returns:
            Filtered dict with tier-appropriate fields
        """
        # Core fields (always present)
        # LLM prompt uses "problem_statement" but schema expects "problem"
        filtered = {
            "problem": brief_data.get("problem") or brief_data.get("problem_statement", ""),
            "target_user": brief_data.get("target_user", ""),
            "value_prop": brief_data.get("value_prop") or brief_data.get("value_proposition", ""),
            "key_constraint": brief_data.get("key_constraint") or brief_data.get("key_constraints", ""),
        }

        # Business fields (Partner+)
        if tier_slug in ("partner", "cto_scale"):
            filtered["differentiation"] = brief_data.get("differentiation")
            filtered["monetization_hypothesis"] = brief_data.get("monetization_hypothesis")
        else:
            filtered["differentiation"] = None
            filtered["monetization_hypothesis"] = None

        # Strategic fields (CTO only)
        if tier_slug == "cto_scale":
            filtered["assumptions"] = brief_data.get("assumptions")
            filtered["risks"] = brief_data.get("risks")
            filtered["smallest_viable_experiment"] = brief_data.get("smallest_viable_experiment")
        else:
            filtered["assumptions"] = None
            filtered["risks"] = None
            filtered["smallest_viable_experiment"] = None

        return filtered
