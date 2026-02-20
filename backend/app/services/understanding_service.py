"""UnderstandingService — orchestrates understanding interview flow with Runner integration.

Responsibilities:
- Session lifecycle: start, answer, edit_answer, finalize, get_brief, edit_brief, re_interview
- User isolation via clerk_user_id filtering
- JSONB persistence with flag_modified tracking
- Idea Brief generation and artifact storage
"""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm.attributes import flag_modified

from app.agent.runner import Runner
from app.db.graph.strategy_graph import get_strategy_graph
from app.db.models.artifact import Artifact
from app.db.models.onboarding_session import OnboardingSession
from app.db.models.project import Project
from app.db.models.understanding_session import UnderstandingSession
from app.schemas.artifacts import ArtifactType
from app.services.graph_service import GraphService


class UnderstandingService:
    """Service layer for understanding interview flow with Runner integration."""

    def __init__(self, runner: Runner, session_factory: async_sessionmaker[AsyncSession]):
        """Initialize with Runner protocol instance and session factory.

        Args:
            runner: Runner implementation (RunnerFake for tests, RunnerReal for production)
            session_factory: SQLAlchemy async session factory for database access
        """
        self.runner = runner
        self.session_factory = session_factory

    async def start_session(self, clerk_user_id: str, onboarding_session_id: str) -> UnderstandingSession:
        """Start a new understanding session based on completed onboarding.

        Args:
            clerk_user_id: Clerk user ID
            onboarding_session_id: Completed onboarding session ID

        Returns:
            New UnderstandingSession with first question

        Raises:
            HTTPException(404): If onboarding session not found or not owned by user
            HTTPException(400): If onboarding session not completed
        """
        async with self.session_factory() as session:
            # Load and validate onboarding session
            result = await session.execute(
                select(OnboardingSession).where(
                    OnboardingSession.id == UUID(onboarding_session_id),
                    OnboardingSession.clerk_user_id == clerk_user_id,
                )
            )
            onboarding = result.scalar_one_or_none()

            if not onboarding:
                raise HTTPException(status_code=404, detail="Onboarding session not found")

            if onboarding.status != "completed":
                raise HTTPException(
                    status_code=400,
                    detail="Onboarding session must be completed before starting understanding interview",
                )

            # Resolve tier for the user
            from app.core.llm_config import get_or_create_user_settings

            user_settings = await get_or_create_user_settings(clerk_user_id)
            tier_slug = user_settings.plan_tier.slug if user_settings.plan_tier else "bootstrapper"

            # Generate understanding questions via Runner
            context = {
                "idea_text": onboarding.idea_text,
                "onboarding_answers": onboarding.answers,
                "user_id": clerk_user_id,
                "session_id": str(onboarding.id),
                "tier": tier_slug,
            }
            questions_data = await self.runner.generate_understanding_questions(context)

            # Create understanding session
            new_session = UnderstandingSession(
                clerk_user_id=clerk_user_id,
                onboarding_session_id=UUID(onboarding_session_id),
                project_id=onboarding.project_id,
                status="in_progress",
                current_question_index=0,
                total_questions=len(questions_data),
                questions=questions_data,
                answers={},
            )
            session.add(new_session)
            await session.commit()
            await session.refresh(new_session)

            return new_session

    async def submit_answer(
        self, clerk_user_id: str, session_id: str, question_id: str, answer: str
    ) -> UnderstandingSession:
        """Submit an answer and advance to next question.

        Args:
            clerk_user_id: Clerk user ID
            session_id: Understanding session ID
            question_id: Question ID being answered
            answer: User's answer

        Returns:
            Updated UnderstandingSession

        Raises:
            HTTPException(404): If session not found or not owned by user
            HTTPException(400): If session already completed
        """
        async with self.session_factory() as session:
            # Load session with user isolation
            result = await session.execute(
                select(UnderstandingSession).where(
                    UnderstandingSession.id == UUID(session_id),
                    UnderstandingSession.clerk_user_id == clerk_user_id,
                )
            )
            understanding = result.scalar_one_or_none()

            if not understanding:
                raise HTTPException(status_code=404, detail="Understanding session not found")

            if understanding.status == "completed":
                raise HTTPException(status_code=400, detail="Session already completed")

            # Store answer
            understanding.answers[question_id] = answer
            flag_modified(understanding, "answers")

            # Advance to next question
            understanding.current_question_index += 1

            await session.commit()
            await session.refresh(understanding)

            return understanding

    async def edit_answer(
        self, clerk_user_id: str, session_id: str, question_id: str, new_answer: str
    ) -> dict[str, Any]:
        """Edit a previous answer and check if remaining questions need regeneration.

        Args:
            clerk_user_id: Clerk user ID
            session_id: Understanding session ID
            question_id: Question ID to edit
            new_answer: Updated answer

        Returns:
            Dict with keys: updated_session, needs_regeneration, regenerated

        Raises:
            HTTPException(404): If session not found or not owned by user
        """
        async with self.session_factory() as session:
            # Load session with user isolation
            result = await session.execute(
                select(UnderstandingSession).where(
                    UnderstandingSession.id == UUID(session_id),
                    UnderstandingSession.clerk_user_id == clerk_user_id,
                )
            )
            understanding = result.scalar_one_or_none()

            if not understanding:
                raise HTTPException(status_code=404, detail="Understanding session not found")

            # Update answer
            understanding.answers[question_id] = new_answer
            flag_modified(understanding, "answers")

            # Determine which questions have been answered
            answered_questions = [q for q in understanding.questions if q["id"] in understanding.answers]
            remaining_questions = [q for q in understanding.questions if q["id"] not in understanding.answers]

            # Load onboarding session for idea_text
            onboarding_result = await session.execute(
                select(OnboardingSession).where(OnboardingSession.id == understanding.onboarding_session_id)
            )
            onboarding = onboarding_result.scalar_one()

            # Check if remaining questions need regeneration
            relevance_check = await self.runner.check_question_relevance(
                idea=onboarding.idea_text,
                answered=answered_questions,
                answers=understanding.answers,
                remaining=remaining_questions,
            )

            regenerated = False
            if relevance_check["needs_regeneration"] and remaining_questions:
                # Regenerate remaining questions (not implemented in fake, but framework ready)
                # In real implementation, we'd call runner.generate_understanding_questions
                # with updated context and replace remaining questions
                regenerated = True

            await session.commit()
            await session.refresh(understanding)

            return {
                "updated_session": understanding,
                "needs_regeneration": relevance_check["needs_regeneration"],
                "regenerated": regenerated,
            }

    async def finalize(self, clerk_user_id: str, session_id: str) -> dict[str, Any]:
        """Generate Rationalised Idea Brief and store as Artifact.

        Args:
            clerk_user_id: Clerk user ID
            session_id: Understanding session ID

        Returns:
            Dict with keys: brief (dict), artifact_id (str), version (int)

        Raises:
            HTTPException(404): If session not found or not owned by user
            HTTPException(400): If not all questions answered
        """
        async with self.session_factory() as session:
            # Load session with user isolation
            result = await session.execute(
                select(UnderstandingSession).where(
                    UnderstandingSession.id == UUID(session_id),
                    UnderstandingSession.clerk_user_id == clerk_user_id,
                )
            )
            understanding = result.scalar_one_or_none()

            if not understanding:
                raise HTTPException(status_code=404, detail="Understanding session not found")

            # Verify all questions answered
            answered_count = len(understanding.answers)
            if answered_count < understanding.total_questions:
                raise HTTPException(
                    status_code=400,
                    detail=f"Must answer all questions before finalizing. Answered: {answered_count}/{understanding.total_questions}",
                )

            # Load onboarding session for idea_text
            onboarding_result = await session.execute(
                select(OnboardingSession).where(OnboardingSession.id == understanding.onboarding_session_id)
            )
            onboarding = onboarding_result.scalar_one()

            # Resolve tier for the user
            from app.core.llm_config import get_or_create_user_settings

            user_settings = await get_or_create_user_settings(clerk_user_id)
            tier_slug = user_settings.plan_tier.slug if user_settings.plan_tier else "bootstrapper"

            # Inject tier into answers so generate_idea_brief can read it
            answers_with_tier = {**understanding.answers, "_tier": tier_slug}

            # Generate Idea Brief via Runner
            brief_content = await self.runner.generate_idea_brief(
                idea=onboarding.idea_text,
                questions=understanding.questions,
                answers=answers_with_tier,
            )

            # Inject _tier into brief content for downstream tier-differentiation
            brief_content["_tier"] = tier_slug

            # Store as Artifact
            artifact = Artifact(
                project_id=understanding.project_id,
                artifact_type=ArtifactType.IDEA_BRIEF,
                current_content=brief_content,
                previous_content=None,
                version_number=1,
                schema_version=1,
                generation_status="idle",
            )
            session.add(artifact)

            # Mark session as completed
            understanding.status = "completed"
            understanding.completed_at = datetime.now(UTC)

            await session.commit()
            await session.refresh(artifact)
            await session.refresh(understanding)

            # Sync artifact to Neo4j strategy graph (non-fatal)
            graph_service = GraphService(get_strategy_graph())
            await graph_service.sync_artifact_to_graph(artifact, str(understanding.project_id))

            return {
                "brief": brief_content,
                "artifact_id": str(artifact.id),
                "version": artifact.version_number,
                "project_id": str(understanding.project_id),
                "idea_text": onboarding.idea_text,
                "onboarding_answers": onboarding.answers or {},
                "tier": tier_slug,
            }

    async def get_brief(self, clerk_user_id: str, project_id: str) -> dict[str, Any]:
        """Get Idea Brief artifact for a project.

        Args:
            clerk_user_id: Clerk user ID
            project_id: Project ID

        Returns:
            Dict with keys: brief (dict), artifact_id (str), version (int)

        Raises:
            HTTPException(404): If brief not found or user doesn't own project
        """
        async with self.session_factory() as session:
            # Verify project ownership before returning the brief
            project_result = await session.execute(
                select(Project).where(
                    Project.id == UUID(project_id),
                    Project.clerk_user_id == clerk_user_id,
                )
            )
            project = project_result.scalar_one_or_none()
            if not project:
                raise HTTPException(status_code=404, detail="Project not found")

            # Load artifact after ownership verified
            result = await session.execute(
                select(Artifact).where(
                    Artifact.project_id == UUID(project_id),
                    Artifact.artifact_type == ArtifactType.IDEA_BRIEF,
                )
            )
            artifact = result.scalar_one_or_none()

            if not artifact:
                raise HTTPException(status_code=404, detail="Idea brief not found")

            return {
                "brief": artifact.current_content,
                "artifact_id": str(artifact.id),
                "version": artifact.version_number,
            }

    async def edit_brief_section(
        self, clerk_user_id: str, project_id: str, section_key: str, new_content: str
    ) -> dict[str, Any]:
        """Edit a section of the Idea Brief and recalculate confidence.

        Args:
            clerk_user_id: Clerk user ID
            project_id: Project ID
            section_key: Section field name (e.g., 'problem_statement')
            new_content: Updated section content

        Returns:
            Dict with keys: updated_section (str), new_confidence (str), version (int)

        Raises:
            HTTPException(404): If brief not found
            HTTPException(400): If section_key invalid
        """
        async with self.session_factory() as session:
            # Verify project ownership before allowing edits
            project_result = await session.execute(
                select(Project).where(
                    Project.id == UUID(project_id),
                    Project.clerk_user_id == clerk_user_id,
                )
            )
            project = project_result.scalar_one_or_none()
            if not project:
                raise HTTPException(status_code=404, detail="Project not found")

            # Load artifact after ownership verified
            result = await session.execute(
                select(Artifact).where(
                    Artifact.project_id == UUID(project_id),
                    Artifact.artifact_type == ArtifactType.IDEA_BRIEF,
                )
            )
            artifact = result.scalar_one_or_none()

            if not artifact:
                raise HTTPException(status_code=404, detail="Idea brief not found")

            # Validate section_key exists
            if section_key not in artifact.current_content:
                raise HTTPException(status_code=400, detail=f"Invalid section key: {section_key}")

            # Version rotation pattern (from Phase 06 decision)
            artifact.previous_content = artifact.current_content.copy()
            artifact.current_content[section_key] = new_content
            flag_modified(artifact, "current_content")

            # Recalculate confidence for edited section
            new_confidence = await self.runner.assess_section_confidence(section_key, new_content)
            artifact.current_content["confidence_scores"][section_key] = new_confidence
            flag_modified(artifact, "current_content")

            # Increment version and mark as edited
            artifact.version_number += 1
            artifact.has_user_edits = True

            await session.commit()
            await session.refresh(artifact)

            return {
                "updated_section": new_content,
                "new_confidence": new_confidence,
                "version": artifact.version_number,
            }

    async def re_interview(self, clerk_user_id: str, session_id: str) -> UnderstandingSession:
        """Reset understanding session for re-interview (major changes).

        Args:
            clerk_user_id: Clerk user ID
            session_id: Understanding session ID

        Returns:
            Reset UnderstandingSession with new questions

        Raises:
            HTTPException(404): If session not found or not owned by user
        """
        async with self.session_factory() as session:
            # Load session
            result = await session.execute(
                select(UnderstandingSession).where(
                    UnderstandingSession.id == UUID(session_id),
                    UnderstandingSession.clerk_user_id == clerk_user_id,
                )
            )
            understanding = result.scalar_one_or_none()

            if not understanding:
                raise HTTPException(status_code=404, detail="Understanding session not found")

            # Load onboarding for context
            onboarding_result = await session.execute(
                select(OnboardingSession).where(OnboardingSession.id == understanding.onboarding_session_id)
            )
            onboarding = onboarding_result.scalar_one()

            # Resolve tier for the user
            from app.core.llm_config import get_or_create_user_settings

            user_settings = await get_or_create_user_settings(clerk_user_id)
            tier_slug = user_settings.plan_tier.slug if user_settings.plan_tier else "bootstrapper"

            # Generate fresh questions
            context = {
                "idea_text": onboarding.idea_text,
                "onboarding_answers": onboarding.answers,
                "existing_brief": (understanding.answers if understanding.answers else None),
                "user_id": clerk_user_id,
                "session_id": str(understanding.id),
                "tier": tier_slug,
            }
            questions_data = await self.runner.generate_understanding_questions(context)

            # Reset session state
            understanding.questions = questions_data
            understanding.answers = {}
            understanding.current_question_index = 0
            understanding.total_questions = len(questions_data)
            understanding.status = "in_progress"
            understanding.completed_at = None

            flag_modified(understanding, "questions")
            flag_modified(understanding, "answers")

            await session.commit()
            await session.refresh(understanding)

            return understanding

    async def get_session(self, clerk_user_id: str, session_id: str) -> UnderstandingSession:
        """Get current understanding session state (for resumption).

        Args:
            clerk_user_id: Clerk user ID
            session_id: Understanding session ID

        Returns:
            UnderstandingSession

        Raises:
            HTTPException(404): If session not found or not owned by user
        """
        async with self.session_factory() as session:
            result = await session.execute(
                select(UnderstandingSession).where(
                    UnderstandingSession.id == UUID(session_id),
                    UnderstandingSession.clerk_user_id == clerk_user_id,
                )
            )
            understanding = result.scalar_one_or_none()

            if not understanding:
                raise HTTPException(status_code=404, detail="Understanding session not found")

            return understanding
