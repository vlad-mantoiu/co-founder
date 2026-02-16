"""Artifact API routes — generation, retrieval, editing, annotation endpoints."""

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from uuid import UUID

from app.agent.runner import Runner
from app.agent.runner_fake import RunnerFake
from app.artifacts.generator import ArtifactGenerator
from app.core.auth import ClerkUser, require_auth
from app.core.llm_config import get_or_create_user_settings
from app.db.base import get_session_factory
from app.db.models.artifact import Artifact
from app.db.models.onboarding_session import OnboardingSession
from app.db.models.project import Project
from app.schemas.artifacts import (
    AnnotateRequest,
    ArtifactResponse,
    EditSectionRequest,
    GenerateArtifactsRequest,
    RegenerateArtifactRequest,
)
from app.services.artifact_service import ArtifactService
from pydantic import BaseModel
from sqlalchemy import select

router = APIRouter()


def get_runner() -> Runner:
    """Dependency that provides Runner instance.

    Returns RunnerFake for now (will swap to RunnerReal later).
    Override this dependency in tests via app.dependency_overrides.
    """
    return RunnerFake()


class GenerateArtifactsResponse(BaseModel):
    """Response model for generate artifacts endpoint."""

    generation_id: str
    artifact_count: int
    status: str


class RegenerateWarningResponse(BaseModel):
    """Response when regeneration encounters user edits."""

    warning: bool
    edited_sections: list[str]
    id: UUID
    artifact_type: str


class GenerationStatusResponse(BaseModel):
    """Response for generation status endpoint."""

    generation_status: str
    version_number: int
    updated_at: str


async def _background_generate_artifacts(
    project_id: UUID,
    user_id: str,
    tier: str,
    runner: Runner,
):
    """Background task to generate all artifacts for a project.

    Steps:
    1. Fetch onboarding data
    2. Create ArtifactService and ArtifactGenerator
    3. Call generate_all() which handles cascade generation
    4. Each artifact is persisted individually (live preview)
    """
    session_factory = get_session_factory()
    generator = ArtifactGenerator(runner)
    service = ArtifactService(generator, session_factory)

    # Fetch onboarding data
    async with session_factory() as session:
        result = await session.execute(
            select(Project).where(
                Project.id == project_id,
                Project.clerk_user_id == user_id,
            )
        )
        project = result.scalar_one_or_none()
        if project is None:
            return

        # Get onboarding session (OnboardingSession has project_id FK to Project)
        result = await session.execute(
            select(OnboardingSession).where(
                OnboardingSession.project_id == project_id
            )
        )
        onboarding_session = result.scalar_one_or_none()
        if onboarding_session is None:
            return

        onboarding_data = {
            "idea": onboarding_session.idea_text,
            "answers": onboarding_session.answers,
            "thesis_snapshot": onboarding_session.thesis_snapshot,
        }

    # Generate artifacts
    await service.generate_all(
        project_id=project_id,
        user_id=user_id,
        onboarding_data=onboarding_data,
        tier=tier,
    )


@router.post("/generate", status_code=202, response_model=GenerateArtifactsResponse)
async def generate_artifacts(
    request: GenerateArtifactsRequest,
    background_tasks: BackgroundTasks,
    user: ClerkUser = Depends(require_auth),
    runner: Runner = Depends(get_runner),
):
    """Trigger artifact generation for a project.

    Per locked decisions:
    - Returns 202 Accepted immediately (generation runs in background)
    - Cascade generates Brief -> MVP Scope -> Milestones -> Risk Log -> How It Works
    - Each artifact appears as soon as it's done (live preview)

    Returns: {generation_id, artifact_count: 5, status: "generating"}

    Raises:
        HTTPException(404): If project not found or unauthorized
        HTTPException(409): If generation already in progress
    """
    session_factory = get_session_factory()

    # Verify project belongs to user
    async with session_factory() as session:
        result = await session.execute(
            select(Project).where(
                Project.id == request.project_id,
                Project.clerk_user_id == user.user_id,
            )
        )
        project = result.scalar_one_or_none()
        if project is None:
            raise HTTPException(status_code=404, detail="Project not found")

        # Check no generation already in progress
        result = await session.execute(
            select(Artifact).where(
                Artifact.project_id == request.project_id,
                Artifact.generation_status == "generating",
            )
        )
        generating = result.scalar_one_or_none()
        if generating is not None:
            raise HTTPException(status_code=409, detail="Generation already in progress")

    # Get user's tier
    user_settings = await get_or_create_user_settings(user.user_id)
    tier_slug = user_settings.plan_tier.slug

    # Add background task for generation
    background_tasks.add_task(
        _background_generate_artifacts,
        project_id=request.project_id,
        user_id=user.user_id,
        tier=tier_slug,
        runner=runner,
    )

    return GenerateArtifactsResponse(
        generation_id=str(request.project_id),  # Use project_id as generation_id
        artifact_count=5,
        status="generating",
    )


@router.get("/{artifact_id}", response_model=ArtifactResponse)
async def get_artifact(
    artifact_id: UUID,
    user: ClerkUser = Depends(require_auth),
):
    """Get artifact by ID with user isolation.

    Returns 404 if not found or unauthorized.

    Raises:
        HTTPException(404): If artifact not found or unauthorized
    """
    session_factory = get_session_factory()
    runner = get_runner()
    generator = ArtifactGenerator(runner)
    service = ArtifactService(generator, session_factory)

    artifact = await service.get_artifact(artifact_id, user.user_id)
    if artifact is None:
        raise HTTPException(status_code=404, detail="Artifact not found")

    return ArtifactResponse(
        id=artifact.id,
        project_id=artifact.project_id,
        artifact_type=artifact.artifact_type,
        version_number=artifact.version_number,
        current_content=artifact.current_content or {},
        previous_content=artifact.previous_content,
        has_user_edits=artifact.has_user_edits,
        edited_sections=artifact.edited_sections,
        annotations=[
            {
                "section_id": ann["section_id"],
                "note": ann["note"],
                "created_at": ann["created_at"],
            }
            for ann in (artifact.annotations or [])
        ],
        generation_status=artifact.generation_status,
        schema_version=artifact.schema_version,
        created_at=artifact.created_at,
        updated_at=artifact.updated_at,
    )


@router.get("/project/{project_id}", response_model=list[ArtifactResponse])
async def list_project_artifacts(
    project_id: UUID,
    user: ClerkUser = Depends(require_auth),
):
    """List all artifacts for a project.

    Returns [] for empty/unauthorized projects.
    """
    session_factory = get_session_factory()
    runner = get_runner()
    generator = ArtifactGenerator(runner)
    service = ArtifactService(generator, session_factory)

    artifacts = await service.get_project_artifacts(project_id, user.user_id)

    return [
        ArtifactResponse(
            id=artifact.id,
            project_id=artifact.project_id,
            artifact_type=artifact.artifact_type,
            version_number=artifact.version_number,
            current_content=artifact.current_content or {},
            previous_content=artifact.previous_content,
            has_user_edits=artifact.has_user_edits,
            edited_sections=artifact.edited_sections,
            annotations=[
                {
                    "section_id": ann["section_id"],
                    "note": ann["note"],
                    "created_at": ann["created_at"],
                }
                for ann in (artifact.annotations or [])
            ],
            generation_status=artifact.generation_status,
            schema_version=artifact.schema_version,
            created_at=artifact.created_at,
            updated_at=artifact.updated_at,
        )
        for artifact in artifacts
    ]


@router.post("/{artifact_id}/regenerate")
async def regenerate_artifact(
    artifact_id: UUID,
    request: RegenerateArtifactRequest,
    background_tasks: BackgroundTasks,
    user: ClerkUser = Depends(require_auth),
    runner: Runner = Depends(get_runner),
):
    """Regenerate a single artifact.

    Per locked decisions:
    - If has_user_edits and force=False: return {warning: true, edited_sections: [...]}
    - If force=True or no edits: regenerate, move current->previous, bump version
    - Returns updated artifact or warning

    Raises:
        HTTPException(404): If artifact not found or unauthorized
    """
    session_factory = get_session_factory()
    generator = ArtifactGenerator(runner)
    service = ArtifactService(generator, session_factory)

    # Get user's tier
    user_settings = await get_or_create_user_settings(user.user_id)
    tier_slug = user_settings.plan_tier.slug

    # Get onboarding data
    async with session_factory() as session:
        result = await session.execute(
            select(Artifact)
            .join(Project, Artifact.project_id == Project.id)
            .where(
                Artifact.id == artifact_id,
                Project.clerk_user_id == user.user_id,
            )
        )
        artifact = result.scalar_one_or_none()
        if artifact is None:
            raise HTTPException(status_code=404, detail="Artifact not found")

        # Get onboarding session (OnboardingSession has project_id FK to Project)
        result = await session.execute(
            select(OnboardingSession).where(
                OnboardingSession.project_id == artifact.project_id
            )
        )
        onboarding_session = result.scalar_one_or_none()
        if onboarding_session is None:
            raise HTTPException(status_code=404, detail="Onboarding session not found")

        onboarding_data = {
            "idea": onboarding_session.idea_text,
            "answers": onboarding_session.answers,
            "thesis_snapshot": onboarding_session.thesis_snapshot,
        }

    # Attempt regeneration
    try:
        regenerated_artifact, had_edits = await service.regenerate_artifact(
            artifact_id=artifact_id,
            user_id=user.user_id,
            onboarding_data=onboarding_data,
            tier=tier_slug,
            force=request.force,
        )
    except ValueError:
        raise HTTPException(status_code=404, detail="Artifact not found")

    # If had edits and force=False, return warning
    if had_edits and not request.force:
        return RegenerateWarningResponse(
            warning=True,
            edited_sections=regenerated_artifact.edited_sections or [],
            id=regenerated_artifact.id,
            artifact_type=regenerated_artifact.artifact_type,
        )

    # Return regenerated artifact
    return ArtifactResponse(
        id=regenerated_artifact.id,
        project_id=regenerated_artifact.project_id,
        artifact_type=regenerated_artifact.artifact_type,
        version_number=regenerated_artifact.version_number,
        current_content=regenerated_artifact.current_content or {},
        previous_content=regenerated_artifact.previous_content,
        has_user_edits=regenerated_artifact.has_user_edits,
        edited_sections=regenerated_artifact.edited_sections,
        annotations=[
            {
                "section_id": ann["section_id"],
                "note": ann["note"],
                "created_at": ann["created_at"],
            }
            for ann in (regenerated_artifact.annotations or [])
        ],
        generation_status=regenerated_artifact.generation_status,
        schema_version=regenerated_artifact.schema_version,
        created_at=regenerated_artifact.created_at,
        updated_at=regenerated_artifact.updated_at,
    )


@router.patch("/{artifact_id}/edit", response_model=ArtifactResponse)
async def edit_artifact_section(
    artifact_id: UUID,
    request: EditSectionRequest,
    user: ClerkUser = Depends(require_auth),
):
    """Edit a section of artifact content inline.

    Per locked decision: founders can inline-edit content.
    Sets has_user_edits=True, tracks edited section.

    Raises:
        HTTPException(404): If artifact not found or unauthorized
    """
    session_factory = get_session_factory()
    runner = get_runner()
    generator = ArtifactGenerator(runner)
    service = ArtifactService(generator, session_factory)

    try:
        artifact = await service.edit_section(
            artifact_id=artifact_id,
            user_id=user.user_id,
            section_path=request.section_path,
            new_value=request.new_value,
        )
    except ValueError:
        raise HTTPException(status_code=404, detail="Artifact not found")

    return ArtifactResponse(
        id=artifact.id,
        project_id=artifact.project_id,
        artifact_type=artifact.artifact_type,
        version_number=artifact.version_number,
        current_content=artifact.current_content or {},
        previous_content=artifact.previous_content,
        has_user_edits=artifact.has_user_edits,
        edited_sections=artifact.edited_sections,
        annotations=[
            {
                "section_id": ann["section_id"],
                "note": ann["note"],
                "created_at": ann["created_at"],
            }
            for ann in (artifact.annotations or [])
        ],
        generation_status=artifact.generation_status,
        schema_version=artifact.schema_version,
        created_at=artifact.created_at,
        updated_at=artifact.updated_at,
    )


@router.post("/{artifact_id}/annotate", response_model=ArtifactResponse)
async def annotate_artifact(
    artifact_id: UUID,
    request: AnnotateRequest,
    user: ClerkUser = Depends(require_auth),
):
    """Add annotation to artifact section.

    Per locked decision: founders can annotate (comments/notes).
    Stored separately from content (research recommendation).

    Raises:
        HTTPException(404): If artifact not found or unauthorized
    """
    session_factory = get_session_factory()
    runner = get_runner()
    generator = ArtifactGenerator(runner)
    service = ArtifactService(generator, session_factory)

    try:
        artifact = await service.add_annotation(
            artifact_id=artifact_id,
            user_id=user.user_id,
            section_id=request.section_id,
            note=request.note,
        )
    except ValueError:
        raise HTTPException(status_code=404, detail="Artifact not found")

    return ArtifactResponse(
        id=artifact.id,
        project_id=artifact.project_id,
        artifact_type=artifact.artifact_type,
        version_number=artifact.version_number,
        current_content=artifact.current_content or {},
        previous_content=artifact.previous_content,
        has_user_edits=artifact.has_user_edits,
        edited_sections=artifact.edited_sections,
        annotations=[
            {
                "section_id": ann["section_id"],
                "note": ann["note"],
                "created_at": ann["created_at"],
            }
            for ann in (artifact.annotations or [])
        ],
        generation_status=artifact.generation_status,
        schema_version=artifact.schema_version,
        created_at=artifact.created_at,
        updated_at=artifact.updated_at,
    )


@router.get("/{artifact_id}/status", response_model=GenerationStatusResponse)
async def get_generation_status(
    artifact_id: UUID,
    user: ClerkUser = Depends(require_auth),
):
    """Check generation status of an artifact (for polling during live preview).

    Returns: {generation_status: "idle"|"generating"|"failed", version_number, updated_at}

    Raises:
        HTTPException(404): If artifact not found or unauthorized
    """
    session_factory = get_session_factory()
    runner = get_runner()
    generator = ArtifactGenerator(runner)
    service = ArtifactService(generator, session_factory)

    artifact = await service.get_artifact(artifact_id, user.user_id)
    if artifact is None:
        raise HTTPException(status_code=404, detail="Artifact not found")

    return GenerationStatusResponse(
        generation_status=artifact.generation_status,
        version_number=artifact.version_number,
        updated_at=artifact.updated_at.isoformat(),
    )
