"""API-specific test fixtures."""

import os
from contextlib import asynccontextmanager

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from app.db.base import Base

# Shared test database URL
_TEST_DB_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://cofounder:cofounder@localhost:5432/cofounder_test",
)


@pytest.fixture
async def engine() -> AsyncEngine:
    """Create PostgreSQL test engine (supports JSONB).

    Creates/drops tables and sets the global session factory in the
    pytest-asyncio event loop. Tests using AsyncClient (in-process)
    share this loop and can use get_session_factory(). Tests using
    TestClient (api_client) reset the global in their own loop.
    """
    import app.db.base as db_mod

    engine = create_async_engine(_TEST_DB_URL, echo=False)

    # Import all models so metadata is populated
    import app.db.models  # noqa: F401

    # Create all tables (includes latest model changes)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    # Set global factory in the pytest-asyncio loop for in-process tests
    db_mod._engine = engine
    db_mod._session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    # Seed plan tiers
    from app.db.seed import seed_plan_tiers

    await seed_plan_tiers()

    yield engine

    # Cleanup: drop all tables, reset globals
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    db_mod._engine = None
    db_mod._session_factory = None
    await engine.dispose()


@pytest.fixture
async def db_session(engine: AsyncEngine) -> AsyncSession:
    """Create an async session bound to the pytest-asyncio event loop.

    Uses the engine directly — NOT the global factory from init_db,
    which may be bound to a different loop (TestClient's).
    """
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session


@pytest.fixture
def api_client(engine):
    """FastAPI test client with test database.

    Initializes the global database via init_db inside the TestClient's
    own event loop so route handlers can use get_session_factory().
    The engine fixture ensures tables exist before this runs.
    """
    from fastapi import HTTPException
    from fastapi.middleware.cors import CORSMiddleware

    from app.api.routes import api_router
    from app.core.config import get_settings
    from app.db import close_db, init_db
    from app.db.seed import seed_plan_tiers
    from app.main import generic_exception_handler, http_exception_handler

    @asynccontextmanager
    async def test_lifespan(app: FastAPI):
        """Test lifespan - initialize DB in TestClient's event loop."""
        # Reset global so init_db creates a fresh engine in THIS loop
        import app.db.base as db_mod

        db_mod._engine = None
        db_mod._session_factory = None
        await init_db(_TEST_DB_URL)
        await seed_plan_tiers()
        yield
        await close_db()

    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        description="AI Technical Co-Founder - Test Client",
        version="0.1.0",
        lifespan=test_lifespan,
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Exception handlers (needed for debug_id testing)
    app.exception_handler(HTTPException)(http_exception_handler)
    app.exception_handler(Exception)(generic_exception_handler)

    # Include API routes
    app.include_router(api_router, prefix="/api")

    with TestClient(app) as client:
        yield client
