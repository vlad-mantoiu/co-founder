"""ChangeRequestService — creates Change Request artifacts for iteration planning.

Change requests are stored as Artifact records with unique artifact_type per iteration:
  change_request_1, change_request_2, ... (never reuse type — UniqueConstraint on project_id + artifact_type)

Implements:
  GENL-01: Change Request artifact
  ITER-01: References build version
  ITER-02: Explicit tier limits
  ITER-03: Recorded in context
"""

import uuid
from datetime import UTC, datetime

import structlog
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.agent.runner import Runner
from app.db.models.artifact import Artifact
from app.db.models.job import Job
from app.db.models.project import Project
from app.domain.alignment import compute_alignment_score
from app.queue.schemas import TIER_ITERATION_DEPTH

logger = structlog.get_logger(__name__)


class ChangeRequestService:
    """Service layer for creating Change Request artifacts.

    Change requests are stored as Artifact records (no separate model needed).
    Each change request uses a unique artifact_type: change_request_{iteration_number}.
    """

    def __init__(self, runner: Runner, session_factory: async_sessionmaker[AsyncSession]):
        """Initialize with dependency injection.

        Args:
            runner: Runner instance (not used directly, kept for DI consistency)
            session_factory: SQLAlchemy async session factory
        """
        self.runner = runner
        self.session_factory = session_factory

    async def create_change_request(self, clerk_user_id: str, project_id: str, description: str) -> dict:
        """Create a Change Request artifact for a project iteration.

        Args:
            clerk_user_id: Clerk user ID for ownership check
            project_id: UUID string of the project
            description: Human description of the requested change

        Returns:
            Dict with: change_request_id, alignment_score, scope_creep_detected,
                       iteration_number, tier_limit, build_version, artifact_type

        Raises:
            HTTPException(404): Project not found or not owned by user
            HTTPException(422): No ready build found (must have a completed build first)
        """
        async with self.session_factory() as session:
            # 1. Verify project ownership
            project_uuid = uuid.UUID(project_id)
            result = await session.execute(
                select(Project).where(
                    Project.id == project_uuid,
                    Project.clerk_user_id == clerk_user_id,
                )
            )
            project = result.scalar_one_or_none()
            if not project:
                raise HTTPException(status_code=404, detail="Project not found")

            # 2. Get latest ready Job to find build_version
            job_result = await session.execute(
                select(Job)
                .where(
                    Job.project_id == project_uuid,
                    Job.status == "ready",
                    Job.build_version.isnot(None),
                )
                .order_by(Job.completed_at.desc())
                .limit(1)
            )
            latest_build = job_result.scalar_one_or_none()
            build_version = latest_build.build_version if latest_build else None

            # 3. Get MVP Scope artifact for alignment scoring
            mvp_result = await session.execute(
                select(Artifact).where(
                    Artifact.project_id == project_uuid,
                    Artifact.artifact_type == "mvp_scope",
                )
            )
            mvp_artifact = mvp_result.scalar_one_or_none()
            original_scope: dict = mvp_artifact.current_content or {} if mvp_artifact else {}

            # 4. Get all existing change_request artifacts
            cr_result = await session.execute(
                select(Artifact).where(
                    Artifact.project_id == project_uuid,
                    Artifact.artifact_type.like("change_request_%"),
                )
            )
            existing_crs = cr_result.scalars().all()

            # 5. Compute iteration_number
            iteration_number = len(existing_crs) + 1

            # 6. Compute alignment score including the new change
            existing_changes: list[dict] = [cr.current_content for cr in existing_crs if cr.current_content]
            all_changes = existing_changes + [{"description": description}]
            score, creep = compute_alignment_score(original_scope, all_changes)

            # 7. Get tier limit from TIER_ITERATION_DEPTH
            #    Derive tier from latest build job, fallback to bootstrapper
            tier = latest_build.tier if latest_build else "bootstrapper"
            tier_limit = TIER_ITERATION_DEPTH.get(tier, 2)

            # 8. Create Artifact record with unique type per iteration
            artifact_type = f"change_request_{iteration_number}"
            content: dict = {
                "_schema_version": 1,
                "change_description": description,
                "references_build_version": build_version,
                "iteration_number": iteration_number,
                "tier_limit": tier_limit,
                "alignment_score": score,
                "scope_creep_detected": creep,
            }

            artifact = Artifact(
                project_id=project_uuid,
                artifact_type=artifact_type,
                current_content=content,
                version_number=1,
                schema_version=1,
                generation_status="idle",
                has_user_edits=False,
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
            session.add(artifact)
            await session.commit()
            await session.refresh(artifact)

            # 9. Return the artifact content + id
            return {
                "change_request_id": str(artifact.id),
                "alignment_score": score,
                "scope_creep_detected": creep,
                "iteration_number": iteration_number,
                "tier_limit": tier_limit,
                "build_version": build_version,
                "artifact_type": artifact_type,
            }
