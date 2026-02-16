"""Integration tests for JourneyService using PostgreSQL test database.

Tests the full orchestration layer: domain logic + database persistence.

Requires PostgreSQL running locally or via Docker:
  docker run --rm -p 5432:5432 -e POSTGRES_PASSWORD=test -e POSTGRES_DB=cofounder_test postgres:16
"""

import os
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from app.db.base import Base
from app.db.models.decision_gate import DecisionGate
from app.db.models.project import Project
from app.db.models.stage_config import StageConfig
from app.db.models.stage_event import StageEvent
from app.services.journey import JourneyService


@pytest.fixture
async def engine() -> AsyncEngine:
    """Create PostgreSQL test engine (supports JSONB)."""
    # Use test database URL from env, or default to local postgres
    db_url = os.getenv(
        "TEST_DATABASE_URL",
        "postgresql+asyncpg://cofounder:cofounder@localhost:5432/cofounder_test"
    )

    engine = create_async_engine(
        db_url,
        echo=False,
    )

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Cleanup: drop all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def session(engine: AsyncEngine) -> AsyncSession:
    """Create an async session for tests."""
    session_factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    async with session_factory() as session:
        yield session


@pytest.fixture
async def journey_service(session: AsyncSession) -> JourneyService:
    """Create a JourneyService instance."""
    return JourneyService(session)


@pytest.fixture
async def sample_project(session: AsyncSession) -> uuid.UUID:
    """Create a sample project and return its UUID."""
    project = Project(
        clerk_user_id="test_user_123",
        name="Test Project",
        description="A test project",
        status="active",
        stage_number=None,  # Pre-stage
    )
    session.add(project)
    await session.commit()
    await session.refresh(project)
    return project.id


# Tests

async def test_initialize_journey_creates_stage_configs(
    journey_service: JourneyService, sample_project: uuid.UUID, session: AsyncSession
):
    """Test that initialize_journey creates StageConfig records for stages 1-5."""
    await journey_service.initialize_journey(sample_project)

    # Check that 5 StageConfig records exist
    result = await session.execute(
        select(StageConfig).where(StageConfig.project_id == sample_project)
    )
    configs = result.scalars().all()
    assert len(configs) == 5

    # Check stage numbers
    stage_numbers = [c.stage_number for c in configs]
    assert sorted(stage_numbers) == [1, 2, 3, 4, 5]

    # Check stage 1 has expected milestones from template
    stage_1_config = next(c for c in configs if c.stage_number == 1)
    assert "brief_generated" in stage_1_config.milestones
    assert stage_1_config.milestones["brief_generated"]["weight"] == 40
    assert stage_1_config.milestones["brief_generated"]["completed"] is False

    # Check project is still at pre-stage
    result = await session.execute(
        select(Project).where(Project.id == sample_project)
    )
    project = result.scalar_one()
    assert project.stage_number is None


async def test_initialize_journey_idempotent(
    journey_service: JourneyService, sample_project: uuid.UUID, session: AsyncSession
):
    """Test that initialize_journey is idempotent."""
    await journey_service.initialize_journey(sample_project)
    await journey_service.initialize_journey(sample_project)

    # Still only 5 StageConfig records
    result = await session.execute(
        select(StageConfig).where(StageConfig.project_id == sample_project)
    )
    configs = result.scalars().all()
    assert len(configs) == 5


async def test_create_gate_returns_gate_id(
    journey_service: JourneyService, sample_project: uuid.UUID, session: AsyncSession
):
    """Test that create_gate returns a UUID and creates a pending gate."""
    gate_id = await journey_service.create_gate(
        sample_project, "stage_advance", 1
    )

    assert isinstance(gate_id, uuid.UUID)

    # Check gate exists
    result = await session.execute(
        select(DecisionGate).where(DecisionGate.id == gate_id)
    )
    gate = result.scalar_one()
    assert gate.status == "pending"
    assert gate.gate_type == "stage_advance"
    assert gate.stage_number == 1


async def test_decide_gate_proceed_advances_stage(
    journey_service: JourneyService, sample_project: uuid.UUID, session: AsyncSession
):
    """Test that deciding a gate with 'proceed' advances the stage."""
    # Initialize journey
    await journey_service.initialize_journey(sample_project)

    # Create gate for stage 1 (to advance from pre-stage to stage 1)
    gate_id = await journey_service.create_gate(
        sample_project, "stage_advance", 0  # Gate at pre-stage to advance to 1
    )

    # Decide with proceed
    result = await journey_service.decide_gate(gate_id, "proceed")

    assert result["decision"] == "proceed"
    assert result["target_stage"] == 1

    # Check project is now at stage 1
    result = await session.execute(
        select(Project).where(Project.id == sample_project)
    )
    project = result.scalar_one()
    assert project.stage_number == 1
    assert project.stage_entered_at is not None


async def test_decide_gate_narrow_resets_milestones(
    journey_service: JourneyService, sample_project: uuid.UUID, session: AsyncSession
):
    """Test that deciding a gate with 'narrow' resets milestones."""
    # Initialize and advance to stage 1
    await journey_service.initialize_journey(sample_project)
    gate_id = await journey_service.create_gate(sample_project, "stage_advance", 0)
    await journey_service.decide_gate(gate_id, "proceed")

    # Complete a milestone
    await journey_service.complete_milestone(sample_project, 1, "brief_generated")

    # Verify milestone is completed
    result = await session.execute(
        select(StageConfig).where(
            StageConfig.project_id == sample_project,
            StageConfig.stage_number == 1
        )
    )
    config = result.scalar_one()
    assert config.milestones["brief_generated"]["completed"] is True

    # Create gate and decide with narrow
    gate_id = await journey_service.create_gate(sample_project, "direction", 1)
    result = await journey_service.decide_gate(gate_id, "narrow")

    # Check milestone is reset
    await session.refresh(config)
    assert config.milestones["brief_generated"]["completed"] is False


async def test_decide_gate_pivot_returns_to_earlier_stage(
    journey_service: JourneyService, sample_project: uuid.UUID, session: AsyncSession
):
    """Test that deciding a gate with 'pivot' returns to stage 1."""
    # Initialize and advance to stage 1, then stage 2
    await journey_service.initialize_journey(sample_project)

    # Advance to stage 1
    gate_id = await journey_service.create_gate(sample_project, "stage_advance", 0)
    await journey_service.decide_gate(gate_id, "proceed")

    # Advance to stage 2
    gate_id = await journey_service.create_gate(sample_project, "stage_advance", 1)
    await journey_service.decide_gate(gate_id, "proceed")

    # Verify at stage 2
    result = await session.execute(
        select(Project).where(Project.id == sample_project)
    )
    project = result.scalar_one()
    assert project.stage_number == 2

    # Create gate and decide with pivot
    gate_id = await journey_service.create_gate(sample_project, "pivot", 2)
    result = await journey_service.decide_gate(gate_id, "pivot")

    # Check returned to stage 1
    await session.refresh(project)
    assert project.stage_number == 1


async def test_decide_gate_park_changes_status(
    journey_service: JourneyService, sample_project: uuid.UUID, session: AsyncSession
):
    """Test that deciding a gate with 'park' changes status to parked."""
    # Initialize and advance to stage 1
    await journey_service.initialize_journey(sample_project)
    gate_id = await journey_service.create_gate(sample_project, "stage_advance", 0)
    await journey_service.decide_gate(gate_id, "proceed")

    # Create gate and decide with park
    gate_id = await journey_service.create_gate(sample_project, "park", 1)
    await journey_service.decide_gate(gate_id, "park")

    # Check status is parked and stage preserved
    result = await session.execute(
        select(Project).where(Project.id == sample_project)
    )
    project = result.scalar_one()
    assert project.status == "parked"
    assert project.stage_number == 1


async def test_unpark_restores_active_status(
    journey_service: JourneyService, sample_project: uuid.UUID, session: AsyncSession
):
    """Test that unpark restores active status."""
    # Initialize, advance, and park
    await journey_service.initialize_journey(sample_project)
    gate_id = await journey_service.create_gate(sample_project, "stage_advance", 0)
    await journey_service.decide_gate(gate_id, "proceed")
    gate_id = await journey_service.create_gate(sample_project, "park", 1)
    await journey_service.decide_gate(gate_id, "park")

    # Unpark
    await journey_service.unpark_project(sample_project)

    # Check status is active and stage unchanged
    result = await session.execute(
        select(Project).where(Project.id == sample_project)
    )
    project = result.scalar_one()
    assert project.status == "active"
    assert project.stage_number == 1


async def test_complete_milestone_updates_progress(
    journey_service: JourneyService, sample_project: uuid.UUID, session: AsyncSession
):
    """Test that completing a milestone updates progress."""
    # Initialize and advance to stage 1
    await journey_service.initialize_journey(sample_project)
    gate_id = await journey_service.create_gate(sample_project, "stage_advance", 0)
    await journey_service.decide_gate(gate_id, "proceed")

    # Complete a milestone
    stage_progress = await journey_service.complete_milestone(
        sample_project, 1, "brief_generated"
    )

    # Check stage progress
    assert stage_progress > 0

    # Check global progress
    result = await session.execute(
        select(Project).where(Project.id == sample_project)
    )
    project = result.scalar_one()
    assert project.progress_percent > 0


async def test_get_project_progress_computes_correctly(
    journey_service: JourneyService, sample_project: uuid.UUID, session: AsyncSession
):
    """Test that get_project_progress computes progress correctly."""
    # Initialize and advance to stage 1
    await journey_service.initialize_journey(sample_project)
    gate_id = await journey_service.create_gate(sample_project, "stage_advance", 0)
    await journey_service.decide_gate(gate_id, "proceed")

    # Complete some milestones
    await journey_service.complete_milestone(sample_project, 1, "brief_generated")
    await journey_service.complete_milestone(sample_project, 1, "gate_proceed")

    # Get progress
    progress = await journey_service.get_project_progress(sample_project)

    assert "global_progress" in progress
    assert "stages" in progress
    assert isinstance(progress["global_progress"], int)
    assert 0 <= progress["global_progress"] <= 100

    # Check stage 1 progress
    stage_1 = next(s for s in progress["stages"] if s["stage"] == 1)
    assert stage_1["progress"] > 0


async def test_all_mutations_create_stage_events(
    journey_service: JourneyService, sample_project: uuid.UUID, session: AsyncSession
):
    """Test that all state mutations create StageEvents."""
    # Perform multiple operations
    await journey_service.initialize_journey(sample_project)
    gate_id = await journey_service.create_gate(sample_project, "stage_advance", 0)
    await journey_service.decide_gate(gate_id, "proceed")
    await journey_service.complete_milestone(sample_project, 1, "brief_generated")

    # Get timeline
    timeline = await journey_service.get_timeline(sample_project)

    # Should have at least 4 events
    assert len(timeline) >= 4

    # Check event types
    event_types = {event["event_type"] for event in timeline}
    assert "journey_initialized" in event_types
    assert "gate_created" in event_types
    assert "gate_decided" in event_types
    assert "milestone" in event_types

    # Check all have correlation_ids
    assert all("correlation_id" in event for event in timeline)


async def test_multiple_gates_coexist(
    journey_service: JourneyService, sample_project: uuid.UUID, session: AsyncSession
):
    """Test that multiple gates can coexist for the same project."""
    await journey_service.initialize_journey(sample_project)

    # Create two gates
    gate_id_1 = await journey_service.create_gate(sample_project, "stage_advance", 0)
    gate_id_2 = await journey_service.create_gate(sample_project, "direction", 0)

    # Check both exist
    result = await session.execute(
        select(DecisionGate).where(DecisionGate.project_id == sample_project)
    )
    gates = result.scalars().all()
    assert len(gates) == 2
    assert all(g.status == "pending" for g in gates)


async def test_transition_while_parked_fails(
    journey_service: JourneyService, sample_project: uuid.UUID, session: AsyncSession
):
    """Test that transitions fail when project is parked."""
    # Initialize, advance, and park
    await journey_service.initialize_journey(sample_project)
    gate_id = await journey_service.create_gate(sample_project, "stage_advance", 0)
    await journey_service.decide_gate(gate_id, "proceed")
    gate_id = await journey_service.create_gate(sample_project, "park", 1)
    await journey_service.decide_gate(gate_id, "park")

    # Try to advance while parked
    gate_id = await journey_service.create_gate(sample_project, "stage_advance", 1)

    with pytest.raises(ValueError, match="Cannot transition while parked"):
        await journey_service.decide_gate(gate_id, "proceed")


async def test_get_blocking_risks_detects_stale_project(
    journey_service: JourneyService, sample_project: uuid.UUID, session: AsyncSession
):
    """Test that get_blocking_risks detects stale projects."""
    # Initialize project
    await journey_service.initialize_journey(sample_project)

    # Update project to have old last_activity
    result = await session.execute(
        select(Project).where(Project.id == sample_project)
    )
    project = result.scalar_one()
    project.updated_at = datetime.now(timezone.utc) - timedelta(days=15)
    await session.commit()

    # Get risks
    risks = await journey_service.get_blocking_risks(sample_project)

    # Should detect stale_project risk
    risk_rules = [r["rule"] for r in risks]
    assert "stale_project" in risk_rules


async def test_dismiss_risk_filters_from_results(
    journey_service: JourneyService, sample_project: uuid.UUID, session: AsyncSession
):
    """Test that dismissed risks are filtered from get_blocking_risks results."""
    # Initialize and advance
    await journey_service.initialize_journey(sample_project)
    gate_id = await journey_service.create_gate(sample_project, "stage_advance", 0)
    await journey_service.decide_gate(gate_id, "proceed")

    # Make project stale
    result = await session.execute(
        select(Project).where(Project.id == sample_project)
    )
    project = result.scalar_one()
    project.updated_at = datetime.now(timezone.utc) - timedelta(days=15)
    await session.commit()

    # Verify risk exists
    risks = await journey_service.get_blocking_risks(sample_project)
    assert any(r["rule"] == "stale_project" for r in risks)

    # Dismiss the risk
    await journey_service.dismiss_risk(sample_project, 1, "stale_project")

    # Verify risk is now filtered
    risks = await journey_service.get_blocking_risks(sample_project)
    assert not any(r["rule"] == "stale_project" for r in risks)
