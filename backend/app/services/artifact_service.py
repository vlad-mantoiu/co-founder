"""ArtifactService: Orchestrates artifact generation, versioning, editing, and retrieval.

Follows existing patterns from OnboardingService:
- Constructor dependency injection (generator, session_factory)
- User isolation via clerk_user_id filtering on project
- JSONB state management with flag_modified
- 404 pattern for unauthorized/not found
"""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm.attributes import flag_modified

from app.artifacts.generator import ArtifactGenerator
from app.db.graph.strategy_graph import get_strategy_graph
from app.db.models.artifact import Artifact
from app.db.models.project import Project
from app.schemas.artifacts import GENERATION_ORDER, ArtifactType
from app.services.graph_service import GraphService


class ArtifactService:
    """Orchestrates artifact generation, versioning, editing, and retrieval.

    Follows existing patterns from OnboardingService:
    - Constructor dependency injection (generator, session_factory)
    - User isolation via clerk_user_id filtering on project
    - JSONB state management with flag_modified
    """

    def __init__(self, generator: ArtifactGenerator, session_factory: async_sessionmaker[AsyncSession]):
        """Initialize with ArtifactGenerator and session factory.

        Args:
            generator: ArtifactGenerator instance (with Runner dependency)
            session_factory: SQLAlchemy async session factory for database access
        """
        self.generator = generator
        self.session_factory = session_factory

    async def generate_all(
        self,
        project_id: UUID,
        user_id: str,
        onboarding_data: dict,
        tier: str,
    ) -> tuple[list[UUID], list[str]]:
        """Generate all artifacts for a project via cascade.

        Returns: (artifact_ids, failed_types)

        Steps:
        1. Verify project belongs to user (404 pattern)
        2. Check if artifacts already exist (for retry: pass existing to generator)
        3. Set generation_status="generating" on all artifacts
        4. Call generator.generate_cascade()
        5. For each completed artifact: upsert with ON CONFLICT (project_id, artifact_type)
        6. Filter content by tier before persisting (locked decision)
        7. Set generation_status="idle" on completed, "failed" on failed
        8. Return artifact IDs and failed types

        Args:
            project_id: Project UUID
            user_id: Clerk user ID for authorization
            onboarding_data: From onboarding session (idea, answers)
            tier: Subscription tier (bootstrapper, partner, cto_scale)

        Returns:
            Tuple of (artifact_ids list, failed_types list)

        Raises:
            None - returns empty list and all failed on project not found
        """
        async with self.session_factory() as session:
            # Verify project belongs to user (404 pattern)
            result = await session.execute(
                select(Project).where(
                    Project.id == project_id,
                    Project.clerk_user_id == user_id,
                )
            )
            project = result.scalar_one_or_none()
            if project is None:
                # 404 pattern - return empty results
                return ([], [at.value for at in GENERATION_ORDER])

            # Check for existing artifacts (for retry)
            result = await session.execute(select(Artifact).where(Artifact.project_id == project_id))
            existing_artifacts_rows = result.scalars().all()
            existing_artifacts = {}
            for artifact_row in existing_artifacts_rows:
                if artifact_row.current_content is not None:
                    artifact_type = ArtifactType(artifact_row.artifact_type)
                    existing_artifacts[artifact_type] = artifact_row.current_content

            # Inject tier into onboarding_data so it reaches generate_artifacts
            onboarding_data_with_tier = {**onboarding_data, "_tier": tier}

            # Generate cascade
            completed, failed = await self.generator.generate_cascade(
                onboarding_data=onboarding_data_with_tier,
                existing_artifacts=existing_artifacts if existing_artifacts else None,
            )

            # Persist completed artifacts
            artifact_ids = []
            for artifact_type, content in completed.items():
                # Filter by tier before persisting
                filtered_content = self.generator.filter_by_tier(
                    tier=tier, artifact_type=artifact_type, content=content
                )

                # Upsert artifact (ON CONFLICT DO UPDATE pattern)
                result = await session.execute(
                    select(Artifact).where(
                        Artifact.project_id == project_id,
                        Artifact.artifact_type == artifact_type.value,
                    )
                )
                artifact = result.scalar_one_or_none()

                if artifact is None:
                    # Create new artifact
                    artifact = Artifact(
                        project_id=project_id,
                        artifact_type=artifact_type.value,
                        current_content=filtered_content,
                        version_number=1,
                        schema_version=filtered_content.get("_schema_version", 1),
                        generation_status="idle",
                        has_user_edits=False,
                    )
                    session.add(artifact)
                else:
                    # Update existing (shouldn't happen in normal flow, but handles retry)
                    artifact.current_content = filtered_content
                    artifact.generation_status = "idle"
                    flag_modified(artifact, "current_content")

                await session.flush()
                artifact_ids.append(artifact.id)

            # Mark failed artifacts (create with generation_status="failed")
            for failed_type_str in failed:
                failed_type = ArtifactType(failed_type_str)
                # Only create if doesn't already exist
                result = await session.execute(
                    select(Artifact).where(
                        Artifact.project_id == project_id,
                        Artifact.artifact_type == failed_type.value,
                    )
                )
                artifact = result.scalar_one_or_none()

                if artifact is None:
                    artifact = Artifact(
                        project_id=project_id,
                        artifact_type=failed_type.value,
                        current_content=None,
                        version_number=1,
                        schema_version=1,
                        generation_status="failed",
                        has_user_edits=False,
                    )
                    session.add(artifact)
                else:
                    artifact.generation_status = "failed"

            await session.commit()

            # Sync completed artifacts to Neo4j strategy graph (non-fatal)
            graph_service = GraphService(get_strategy_graph())
            for artifact_type, content in completed.items():
                result = await session.execute(
                    select(Artifact).where(
                        Artifact.project_id == project_id,
                        Artifact.artifact_type == artifact_type.value,
                    )
                )
                artifact = result.scalar_one_or_none()
                if artifact:
                    await graph_service.sync_artifact_to_graph(artifact, str(project_id))

            # Create edges: each artifact FOLLOWS the previous in generation order
            synced_ids = []
            for at in GENERATION_ORDER:
                result = await session.execute(
                    select(Artifact).where(
                        Artifact.project_id == project_id,
                        Artifact.artifact_type == at.value,
                    )
                )
                artifact = result.scalar_one_or_none()
                if artifact and artifact.generation_status == "idle":
                    synced_ids.append(str(artifact.id))

            for i in range(1, len(synced_ids)):
                await graph_service.create_decision_edge(synced_ids[i - 1], synced_ids[i], "LEADS_TO")

            return (artifact_ids, failed)

    async def get_artifact(self, artifact_id: UUID, user_id: str) -> Artifact | None:
        """Get artifact by ID with user isolation via project ownership.

        Args:
            artifact_id: Artifact UUID
            user_id: Clerk user ID for authorization

        Returns:
            Artifact if found and authorized, None otherwise (404 pattern)
        """
        async with self.session_factory() as session:
            # Join with Project to enforce user isolation
            result = await session.execute(
                select(Artifact)
                .join(Project, Artifact.project_id == Project.id)
                .where(
                    Artifact.id == artifact_id,
                    Project.clerk_user_id == user_id,
                )
            )
            artifact = result.scalar_one_or_none()
            return artifact

    async def get_project_artifacts(self, project_id: UUID, user_id: str) -> list[Artifact]:
        """Get all artifacts for a project.

        Returns empty list if project not found or unauthorized.

        Args:
            project_id: Project UUID
            user_id: Clerk user ID for authorization

        Returns:
            List of Artifact objects (empty if not found/unauthorized)
        """
        async with self.session_factory() as session:
            # Verify project ownership first
            result = await session.execute(
                select(Project).where(
                    Project.id == project_id,
                    Project.clerk_user_id == user_id,
                )
            )
            project = result.scalar_one_or_none()
            if project is None:
                return []

            # Get all artifacts for project
            result = await session.execute(select(Artifact).where(Artifact.project_id == project_id))
            artifacts = result.scalars().all()
            return list(artifacts)

    async def regenerate_artifact(
        self,
        artifact_id: UUID,
        user_id: str,
        onboarding_data: dict,
        tier: str,
        force: bool = False,
    ) -> tuple[Artifact, bool]:
        """Regenerate a single artifact.

        Per locked decisions:
        - Move current_content -> previous_content
        - Increment version_number
        - Clear has_user_edits and edited_sections
        - Use row-level lock (SELECT FOR UPDATE) per research pitfall 6
        - If force=False and has_user_edits, return (artifact, True) to signal UI warning needed

        Args:
            artifact_id: Artifact UUID
            user_id: Clerk user ID for authorization
            onboarding_data: From onboarding session (idea, answers)
            tier: Subscription tier (for filtering)
            force: If True, regenerate even with edits. If False and has edits, return warning signal.

        Returns:
            Tuple of (updated_artifact, had_edits)
        """
        async with self.session_factory() as session:
            # Load artifact with user isolation and row-level lock
            result = await session.execute(
                select(Artifact)
                .join(Project, Artifact.project_id == Project.id)
                .where(
                    Artifact.id == artifact_id,
                    Project.clerk_user_id == user_id,
                )
                .with_for_update()  # Row-level lock
            )
            artifact = result.scalar_one_or_none()

            if artifact is None:
                # Return None for not found (caller handles 404)
                # But type signature says we return tuple, so we need to handle this better
                # For now, raise an exception (will be caught by API layer)
                raise ValueError("Artifact not found or unauthorized")

            # Check for user edits
            had_edits = artifact.has_user_edits

            if had_edits and not force:
                # Return without regenerating - signal warning needed
                return (artifact, True)

            # Get artifact type
            artifact_type = ArtifactType(artifact.artifact_type)

            # Generate new content (single artifact, not cascade)
            # Need to get prior artifacts for context
            project_id = artifact.project_id
            result = await session.execute(select(Artifact).where(Artifact.project_id == project_id))
            all_artifacts = result.scalars().all()

            prior_artifacts = {}
            for other_artifact in all_artifacts:
                if other_artifact.artifact_type != artifact.artifact_type and other_artifact.current_content:
                    other_type = ArtifactType(other_artifact.artifact_type)
                    prior_artifacts[other_type.value] = other_artifact.current_content

            # Generate new content
            new_content = await self.generator.generate_artifact(
                artifact_type=artifact_type,
                onboarding_data=onboarding_data,
                prior_artifacts=prior_artifacts if prior_artifacts else None,
            )

            # Filter by tier
            filtered_content = self.generator.filter_by_tier(
                tier=tier, artifact_type=artifact_type, content=new_content
            )

            # Version rotation
            artifact.previous_content = artifact.current_content
            artifact.current_content = filtered_content
            artifact.version_number += 1
            artifact.has_user_edits = False
            artifact.edited_sections = None
            artifact.generation_status = "idle"

            flag_modified(artifact, "current_content")
            flag_modified(artifact, "previous_content")

            await session.commit()
            await session.refresh(artifact)

            return (artifact, had_edits)

    async def edit_section(
        self,
        artifact_id: UUID,
        user_id: str,
        section_path: str,
        new_value: str | dict,
    ) -> Artifact:
        """Edit a section of artifact content inline.

        Per locked decision: founders can inline-edit artifact content.
        Updates current_content JSONB at section_path.
        Sets has_user_edits=True, adds section_path to edited_sections.
        Uses flag_modified for SQLAlchemy JSONB tracking.

        Args:
            artifact_id: Artifact UUID
            user_id: Clerk user ID for authorization
            section_path: Field name to edit (e.g., "problem_statement")
            new_value: New value for the field

        Returns:
            Updated Artifact

        Raises:
            ValueError: If artifact not found or unauthorized
        """
        async with self.session_factory() as session:
            # Load artifact with user isolation
            result = await session.execute(
                select(Artifact)
                .join(Project, Artifact.project_id == Project.id)
                .where(
                    Artifact.id == artifact_id,
                    Project.clerk_user_id == user_id,
                )
            )
            artifact = result.scalar_one_or_none()

            if artifact is None:
                raise ValueError("Artifact not found or unauthorized")

            # Update content
            if artifact.current_content is None:
                artifact.current_content = {}

            artifact.current_content[section_path] = new_value
            flag_modified(artifact, "current_content")

            # Track edit
            artifact.has_user_edits = True
            if artifact.edited_sections is None:
                artifact.edited_sections = []
            if section_path not in artifact.edited_sections:
                artifact.edited_sections.append(section_path)
                flag_modified(artifact, "edited_sections")

            await session.commit()
            await session.refresh(artifact)

            return artifact

    async def add_annotation(
        self,
        artifact_id: UUID,
        user_id: str,
        section_id: str,
        note: str,
    ) -> Artifact:
        """Add annotation to artifact (separate from content per research).

        Appends to annotations JSONB array.

        Args:
            artifact_id: Artifact UUID
            user_id: Clerk user ID for authorization
            section_id: Section ID being annotated
            note: Annotation text

        Returns:
            Updated Artifact

        Raises:
            ValueError: If artifact not found or unauthorized
        """
        async with self.session_factory() as session:
            # Load artifact with user isolation
            result = await session.execute(
                select(Artifact)
                .join(Project, Artifact.project_id == Project.id)
                .where(
                    Artifact.id == artifact_id,
                    Project.clerk_user_id == user_id,
                )
            )
            artifact = result.scalar_one_or_none()

            if artifact is None:
                raise ValueError("Artifact not found or unauthorized")

            # Initialize annotations if None
            if artifact.annotations is None:
                artifact.annotations = []

            # Add annotation
            annotation = {
                "section_id": section_id,
                "note": note,
                "created_at": datetime.now(UTC).isoformat(),
            }
            artifact.annotations.append(annotation)
            flag_modified(artifact, "annotations")

            await session.commit()
            await session.refresh(artifact)

            return artifact

    async def check_has_edits(self, artifact_id: UUID, user_id: str) -> list[str] | None:
        """Check if artifact has user edits (for regeneration warning).

        Returns list of edited section names, or None if no edits.
        Per locked decision: warn before overwriting edits.

        Args:
            artifact_id: Artifact UUID
            user_id: Clerk user ID for authorization

        Returns:
            List of edited section names, or None if no edits

        Raises:
            ValueError: If artifact not found or unauthorized
        """
        async with self.session_factory() as session:
            # Load artifact with user isolation
            result = await session.execute(
                select(Artifact)
                .join(Project, Artifact.project_id == Project.id)
                .where(
                    Artifact.id == artifact_id,
                    Project.clerk_user_id == user_id,
                )
            )
            artifact = result.scalar_one_or_none()

            if artifact is None:
                raise ValueError("Artifact not found or unauthorized")

            if not artifact.has_user_edits:
                return None

            return artifact.edited_sections if artifact.edited_sections else []
