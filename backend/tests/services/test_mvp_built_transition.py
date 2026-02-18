"""Tests for the MVP Built post-build hook in GenerationService.

TDD coverage:
- test_first_build_transitions_to_mvp_built: build_v0_1 READY -> project.stage_number == 3
- test_second_build_does_not_re_transition: build_v0_2 does not re-fire the hook
- test_mvp_built_timeline_event_created: StageEvent with event_type="mvp_built" is persisted

Requires PostgreSQL running (TEST_DATABASE_URL env var or default localhost):
  docker run --rm -p 5432:5432 -e POSTGRES_PASSWORD=test -e POSTGRES_DB=cofounder_test postgres:16
"""

import os
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from app.db.base import Base
from app.db.models.project import Project
from app.db.models.stage_event import StageEvent
from app.services.generation_service import GenerationService

pytestmark = pytest.mark.integration


# ---------------------------------------------------------------------------
# DB fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def engine() -> AsyncEngine:
    """Create PostgreSQL test engine for MVP Built transition tests."""
    db_url = os.getenv(
        "TEST_DATABASE_URL",
        "postgresql+asyncpg://cofounder:cofounder@localhost:5432/cofounder_test",
    )
    engine = create_async_engine(db_url, echo=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def session(engine: AsyncEngine) -> AsyncSession:
    """Create an async session scoped to a single test."""
    session_factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    async with session_factory() as session:
        yield session


@pytest.fixture
async def test_project(session: AsyncSession) -> uuid.UUID:
    """Create a test project at stage 2 (Validated Direction) and return its UUID."""
    project = Project(
        clerk_user_id="test_mvp_user_001",
        name="MVP Transition Test Project",
        description="Testing MVP built state transition",
        status="active",
        stage_number=2,  # At Validated Direction, ready for MVP Built
    )
    session.add(project)
    await session.commit()
    await session.refresh(project)
    return project.id


# ---------------------------------------------------------------------------
# Helper to build a GenerationService with mocked DB factory
# ---------------------------------------------------------------------------


def _build_service_with_mocked_db(session: AsyncSession) -> GenerationService:
    """Return a GenerationService whose get_session_factory is mocked to use the test session."""
    from app.agent.runner_fake import RunnerFake

    class _FakeSandboxInner:
        sandbox_id = "fake-sandbox-mvp-001"

        def get_host(self, port: int) -> str:
            return f"{port}-fake-sandbox-mvp-001.e2b.app"

        def set_timeout(self, t: int) -> None:
            pass

    class _FakeSandbox:
        _sandbox = _FakeSandboxInner()
        _started = False

        async def start(self) -> None:
            self._started = True

        async def stop(self) -> None:
            pass

        async def write_file(self, path: str, content: str) -> None:
            pass

        async def run_command(self, cmd: str, **kwargs) -> dict:
            return {"stdout": "ok", "stderr": "", "exit_code": 0}

    return GenerationService(
        runner=RunnerFake(scenario="happy_path"),
        sandbox_runtime_factory=lambda: _FakeSandbox(),
    )


# ---------------------------------------------------------------------------
# Test 1: First build transitions project to stage 3
# ---------------------------------------------------------------------------


async def test_first_build_transitions_to_mvp_built(
    session: AsyncSession,
    test_project: uuid.UUID,
    engine: AsyncEngine,
):
    """build_v0_1 completion advances project stage to 3 (MVP Built).

    MVPS-01: stage transitions to 3
    Also asserts a 'transition' StageEvent is created with to_stage='3'.
    """
    service = _build_service_with_mocked_db(session)

    # Build a context manager that returns our test session
    mock_session_cm = MagicMock()
    mock_session_cm.__aenter__ = AsyncMock(return_value=session)
    mock_session_cm.__aexit__ = AsyncMock(return_value=None)
    mock_factory = MagicMock(return_value=mock_session_cm)

    with patch("app.services.generation_service.get_session_factory", return_value=mock_factory):
        # Also suppress Neo4j call (non-fatal, but avoids test env noise)
        with patch("app.db.graph.strategy_graph.get_strategy_graph") as mock_graph:
            mock_strategy = AsyncMock()
            mock_strategy.upsert_milestone_node = AsyncMock()
            mock_graph.return_value = mock_strategy

            await service._handle_mvp_built_transition(
                job_id="test-job-mvp-001",
                project_id=str(test_project),
                build_version="build_v0_1",
                preview_url="https://8080-fake-sandbox-mvp-001.e2b.app",
            )

    # Reload project in fresh query to verify stage change
    result = await session.execute(select(Project).where(Project.id == test_project))
    project = result.scalar_one()
    assert project.stage_number == 3, (
        f"Expected stage_number=3 after build_v0_1, got {project.stage_number}"
    )

    # Assert a 'transition' StageEvent exists with to_stage='3'
    result = await session.execute(
        select(StageEvent).where(
            StageEvent.project_id == test_project,
            StageEvent.event_type == "transition",
            StageEvent.to_stage == "3",
        )
    )
    transition_event = result.scalar_one_or_none()
    assert transition_event is not None, (
        "Expected a StageEvent with event_type='transition' and to_stage='3' after build_v0_1"
    )


# ---------------------------------------------------------------------------
# Test 2: Second build does not re-trigger the transition
# ---------------------------------------------------------------------------


async def test_second_build_does_not_re_transition(
    session: AsyncSession,
    test_project: uuid.UUID,
):
    """build_v0_2 does NOT re-fire the MVP Built hook (only build_v0_1 triggers it)."""
    service = _build_service_with_mocked_db(session)

    # Manually advance project to stage 3 (as if first build already ran)
    result = await session.execute(select(Project).where(Project.id == test_project))
    project = result.scalar_one()
    project.stage_number = 3
    await session.commit()

    mock_session_cm = MagicMock()
    mock_session_cm.__aenter__ = AsyncMock(return_value=session)
    mock_session_cm.__aexit__ = AsyncMock(return_value=None)
    mock_factory = MagicMock(return_value=mock_session_cm)

    with patch("app.services.generation_service.get_session_factory", return_value=mock_factory):
        with patch("app.db.graph.strategy_graph.get_strategy_graph") as mock_graph:
            mock_strategy = AsyncMock()
            mock_strategy.upsert_milestone_node = AsyncMock()
            mock_graph.return_value = mock_strategy

            await service._handle_mvp_built_transition(
                job_id="test-job-mvp-002",
                project_id=str(test_project),
                build_version="build_v0_2",  # Second build — should be a no-op
                preview_url="https://8080-fake-sandbox-mvp-002.e2b.app",
            )

    # Project remains at stage 3, no new events created
    result = await session.execute(select(Project).where(Project.id == test_project))
    project = result.scalar_one()
    assert project.stage_number == 3, (
        f"Stage should remain 3 after build_v0_2, got {project.stage_number}"
    )

    # No mvp_built events from second build (hook returns early for non-v0_1)
    result = await session.execute(
        select(StageEvent).where(
            StageEvent.project_id == test_project,
            StageEvent.event_type == "mvp_built",
        )
    )
    events = result.scalars().all()
    assert len(events) == 0, (
        f"Expected no mvp_built events from second build, got {len(events)}"
    )


# ---------------------------------------------------------------------------
# Test 3: MVP Built timeline event is persisted
# ---------------------------------------------------------------------------


async def test_mvp_built_timeline_event_created(
    session: AsyncSession,
    test_project: uuid.UUID,
):
    """After first build completes, StageEvent with event_type='mvp_built' is persisted.

    MVPS-03: Timeline event contains preview_url, build_version, and reason is not None.
    """
    service = _build_service_with_mocked_db(session)
    preview_url = "https://8080-fake-sandbox-mvp-003.e2b.app"
    build_version = "build_v0_1"

    mock_session_cm = MagicMock()
    mock_session_cm.__aenter__ = AsyncMock(return_value=session)
    mock_session_cm.__aexit__ = AsyncMock(return_value=None)
    mock_factory = MagicMock(return_value=mock_session_cm)

    with patch("app.services.generation_service.get_session_factory", return_value=mock_factory):
        with patch("app.db.graph.strategy_graph.get_strategy_graph") as mock_graph:
            mock_strategy = AsyncMock()
            mock_strategy.upsert_milestone_node = AsyncMock()
            mock_graph.return_value = mock_strategy

            await service._handle_mvp_built_transition(
                job_id="test-job-mvp-003",
                project_id=str(test_project),
                build_version=build_version,
                preview_url=preview_url,
            )

    # Query for the mvp_built timeline event
    result = await session.execute(
        select(StageEvent).where(
            StageEvent.project_id == test_project,
            StageEvent.event_type == "mvp_built",
        )
    )
    mvp_event = result.scalar_one_or_none()
    assert mvp_event is not None, "Expected a StageEvent with event_type='mvp_built'"

    # Verify detail contains preview_url and build_version keys
    assert "preview_url" in mvp_event.detail, "detail must contain 'preview_url'"
    assert "build_version" in mvp_event.detail, "detail must contain 'build_version'"
    assert mvp_event.detail["preview_url"] == preview_url
    assert mvp_event.detail["build_version"] == build_version

    # Verify reason is not None
    assert mvp_event.reason is not None, "reason must not be None"
    assert len(mvp_event.reason) > 0, "reason must be non-empty"
