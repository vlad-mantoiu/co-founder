"""Integration tests for ArtifactService.

Tests cover:
- Cascade generation creating 5 artifact records
- Version numbering and status management
- User isolation via project ownership
- Artifact retrieval and project artifacts list
- Regeneration with version rotation and edit clearing
- Inline section editing with flag tracking
- Annotation management
- Edit detection for regeneration warnings
"""

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.runner_fake import RunnerFake
from app.db.models.artifact import Artifact
from app.db.models.project import Project

pytestmark = pytest.mark.integration
from app.artifacts.generator import ArtifactGenerator
from app.schemas.artifacts import ArtifactType
from app.services.artifact_service import ArtifactService


@pytest.fixture
def runner_fake():
    """RunnerFake in happy_path scenario."""
    return RunnerFake(scenario="happy_path")


@pytest.fixture
def generator(runner_fake):
    """ArtifactGenerator with RunnerFake."""
    return ArtifactGenerator(runner=runner_fake)


@pytest.fixture
def artifact_service(generator, api_client):
    """ArtifactService with test database session factory.

    Depends on api_client to ensure database is initialized.
    """
    from app.db import get_session_factory

    factory = get_session_factory()
    return ArtifactService(generator=generator, session_factory=factory)


@pytest.fixture
def onboarding_data():
    """Sample onboarding data."""
    return {
        "idea": "Inventory tracking for small retail shops",
        "answers": {
            "q1": "Retail shop owners",
            "q2": "Manual inventory tracking is time-consuming",
        },
    }


async def create_test_project(db_session: AsyncSession, user_id: str = "user_test"):
    """Helper: Create a test project."""
    project = Project(
        clerk_user_id=user_id,
        name="Test Project",
        description="Test project for artifact generation",
        status="active",
        stage_number=1,
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)
    return project


@pytest.mark.asyncio
async def test_generate_artifacts_creates_five_records(artifact_service, onboarding_data, db_session):
    """Test that generate_all creates 5 Artifact rows."""
    test_project = await create_test_project(db_session)

    artifact_ids, failed = await artifact_service.generate_all(
        project_id=test_project.id,
        user_id="user_test",
        onboarding_data=onboarding_data,
        tier="cto_scale",
    )

    # Should create 5 artifacts
    assert len(artifact_ids) == 5
    assert len(failed) == 0

    # Verify in database
    result = await db_session.execute(select(Artifact).where(Artifact.project_id == test_project.id))
    artifacts = result.scalars().all()
    assert len(artifacts) == 5

    # Verify all artifact types present
    artifact_types = {a.artifact_type for a in artifacts}
    assert artifact_types == {
        ArtifactType.BRIEF.value,
        ArtifactType.MVP_SCOPE.value,
        ArtifactType.MILESTONES.value,
        ArtifactType.RISK_LOG.value,
        ArtifactType.HOW_IT_WORKS.value,
    }


@pytest.mark.asyncio
async def test_generate_artifacts_sets_version_1(artifact_service, onboarding_data, db_session):
    """Test that all created artifacts have version_number=1."""
    await artifact_service.generate_all(
        project_id=test_project.id,
        user_id="user_test",
        onboarding_data=onboarding_data,
        tier="cto_scale",
    )

    # Check all artifacts have version 1
    result = await db_session.execute(select(Artifact).where(Artifact.project_id == test_project.id))
    artifacts = result.scalars().all()
    for artifact in artifacts:
        assert artifact.version_number == 1
        assert artifact.previous_content is None  # No previous version


@pytest.mark.asyncio
async def test_generate_artifacts_sets_generation_status_idle_after_completion(
    artifact_service, onboarding_data, db_session
):
    """Test that generation_status is idle after successful generation."""
    await artifact_service.generate_all(
        project_id=test_project.id,
        user_id="user_test",
        onboarding_data=onboarding_data,
        tier="cto_scale",
    )

    # All artifacts should have idle status
    result = await db_session.execute(select(Artifact).where(Artifact.project_id == test_project.id))
    artifacts = result.scalars().all()
    for artifact in artifacts:
        assert artifact.generation_status == "idle"


@pytest.mark.asyncio
async def test_get_artifact_by_id_returns_content(artifact_service, onboarding_data, db_session):
    """Test that get_artifact returns artifact with current_content."""
    artifact_ids, _ = await artifact_service.generate_all(
        project_id=test_project.id,
        user_id="user_test",
        onboarding_data=onboarding_data,
        tier="cto_scale",
    )

    # Get first artifact
    artifact = await artifact_service.get_artifact(artifact_ids[0], "user_test")

    assert artifact is not None
    assert artifact.id == artifact_ids[0]
    assert artifact.current_content is not None
    assert artifact.project_id == test_project.id


@pytest.mark.asyncio
async def test_get_artifact_user_isolation(artifact_service, onboarding_data, db_session):
    """Test that get_artifact returns None for wrong user_id (404 pattern)."""
    artifact_ids, _ = await artifact_service.generate_all(
        project_id=test_project.id,
        user_id="user_test",
        onboarding_data=onboarding_data,
        tier="cto_scale",
    )

    # Try to access with different user
    artifact = await artifact_service.get_artifact(artifact_ids[0], "user_other")
    assert artifact is None  # 404 pattern - not found


@pytest.mark.asyncio
async def test_get_project_artifacts_returns_all_types(artifact_service, onboarding_data, db_session):
    """Test that get_project_artifacts returns list of 5 artifacts."""
    await artifact_service.generate_all(
        project_id=test_project.id,
        user_id="user_test",
        onboarding_data=onboarding_data,
        tier="cto_scale",
    )

    artifacts = await artifact_service.get_project_artifacts(project_id=test_project.id, user_id="user_test")

    assert len(artifacts) == 5
    artifact_types = {a.artifact_type for a in artifacts}
    assert len(artifact_types) == 5  # All unique types


@pytest.mark.asyncio
async def test_regenerate_artifact_bumps_version(artifact_service, onboarding_data, db_session):
    """Test that regenerate increments version_number to 2."""
    artifact_ids, _ = await artifact_service.generate_all(
        project_id=test_project.id,
        user_id="user_test",
        onboarding_data=onboarding_data,
        tier="cto_scale",
    )

    # Regenerate first artifact
    updated_artifact, had_edits = await artifact_service.regenerate_artifact(
        artifact_id=artifact_ids[0],
        user_id="user_test",
        onboarding_data=onboarding_data,
        tier="cto_scale",
        force=False,
    )

    assert updated_artifact.version_number == 2
    assert had_edits is False  # No edits initially


@pytest.mark.asyncio
async def test_regenerate_artifact_preserves_previous_content(artifact_service, onboarding_data, db_session):
    """Test that previous_content matches v1 current_content after regeneration."""
    artifact_ids, _ = await artifact_service.generate_all(
        project_id=test_project.id,
        user_id="user_test",
        onboarding_data=onboarding_data,
        tier="cto_scale",
    )

    # Get v1 content
    artifact_v1 = await artifact_service.get_artifact(artifact_ids[0], "user_test")
    v1_content = artifact_v1.current_content

    # Regenerate
    updated_artifact, _ = await artifact_service.regenerate_artifact(
        artifact_id=artifact_ids[0],
        user_id="user_test",
        onboarding_data=onboarding_data,
        tier="cto_scale",
        force=False,
    )

    # previous_content should match v1
    assert updated_artifact.previous_content == v1_content


@pytest.mark.asyncio
async def test_regenerate_clears_user_edits(artifact_service, onboarding_data, db_session):
    """Test that regenerate clears has_user_edits and edited_sections."""
    artifact_ids, _ = await artifact_service.generate_all(
        project_id=test_project.id,
        user_id="user_test",
        onboarding_data=onboarding_data,
        tier="cto_scale",
    )

    # Edit a section first
    await artifact_service.edit_section(
        artifact_id=artifact_ids[0],
        user_id="user_test",
        section_path="problem_statement",
        new_value="Updated problem statement",
    )

    # Regenerate with force=True
    updated_artifact, had_edits = await artifact_service.regenerate_artifact(
        artifact_id=artifact_ids[0],
        user_id="user_test",
        onboarding_data=onboarding_data,
        tier="cto_scale",
        force=True,
    )

    assert had_edits is True  # Had edits before regeneration
    assert updated_artifact.has_user_edits is False  # Cleared after regeneration
    assert updated_artifact.edited_sections is None or updated_artifact.edited_sections == []


@pytest.mark.asyncio
async def test_edit_artifact_section(artifact_service, onboarding_data, db_session):
    """Test that edit_section updates content and sets has_user_edits."""
    test_project = await create_test_project(db_session)

    artifact_ids, _ = await artifact_service.generate_all(
        project_id=test_project.id,
        user_id="user_test",
        onboarding_data=onboarding_data,
        tier="cto_scale",
    )

    # Edit section
    updated_artifact = await artifact_service.edit_section(
        artifact_id=artifact_ids[0],
        user_id="user_test",
        section_path="problem_statement",
        new_value="Custom problem statement",
    )

    assert updated_artifact.has_user_edits is True
    assert "problem_statement" in updated_artifact.edited_sections
    assert updated_artifact.current_content["problem_statement"] == "Custom problem statement"


@pytest.mark.asyncio
async def test_add_annotation(artifact_service, onboarding_data, db_session):
    """Test that add_annotation appends to annotations JSONB array."""
    test_project = await create_test_project(db_session)

    artifact_ids, _ = await artifact_service.generate_all(
        project_id=test_project.id,
        user_id="user_test",
        onboarding_data=onboarding_data,
        tier="cto_scale",
    )

    # Add annotation
    updated_artifact = await artifact_service.add_annotation(
        artifact_id=artifact_ids[0],
        user_id="user_test",
        section_id="problem_statement",
        note="This needs more detail",
    )

    assert updated_artifact.annotations is not None
    assert len(updated_artifact.annotations) == 1
    assert updated_artifact.annotations[0]["section_id"] == "problem_statement"
    assert updated_artifact.annotations[0]["note"] == "This needs more detail"


@pytest.mark.asyncio
async def test_check_edits_before_regenerate(artifact_service, onboarding_data, db_session):
    """Test that check_has_edits returns edited section names."""
    artifact_ids, _ = await artifact_service.generate_all(
        project_id=test_project.id,
        user_id="user_test",
        onboarding_data=onboarding_data,
        tier="cto_scale",
    )

    # No edits initially
    edited_sections = await artifact_service.check_has_edits(artifact_ids[0], "user_test")
    assert edited_sections is None

    # Edit two sections
    await artifact_service.edit_section(
        artifact_id=artifact_ids[0],
        user_id="user_test",
        section_path="problem_statement",
        new_value="Updated",
    )
    await artifact_service.edit_section(
        artifact_id=artifact_ids[0],
        user_id="user_test",
        section_path="target_user",
        new_value="Updated user",
    )

    # Check has edits
    edited_sections = await artifact_service.check_has_edits(artifact_ids[0], "user_test")
    assert edited_sections is not None
    assert len(edited_sections) == 2
    assert "problem_statement" in edited_sections
    assert "target_user" in edited_sections
