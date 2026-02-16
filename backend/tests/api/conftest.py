"""API-specific test fixtures."""
import os
from contextlib import asynccontextmanager

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from app.db.base import Base
from app.db.models.plan_tier import PlanTier


@pytest.fixture
async def engine() -> AsyncEngine:
    """Create PostgreSQL test engine (supports JSONB).

    Note: Uses Base.metadata.create_all instead of migrations for test simplicity.
    Ensures all model columns are created including latest additions.
    """
    # Use test database URL from env, or default to local postgres
    db_url = os.getenv(
        "TEST_DATABASE_URL",
        "postgresql+asyncpg://cofounder:cofounder@localhost:5432/cofounder_test"
    )

    engine = create_async_engine(
        db_url,
        echo=False,
    )

    # Import all models so metadata is populated
    import app.db.models  # noqa: F401

    # Create all tables (includes latest model changes)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Cleanup: drop all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def db_session(engine: AsyncEngine, api_client) -> AsyncSession:
    """Create an async session for tests.

    Depends on api_client to ensure database is initialized and seeded.
    """
    from app.db import get_session_factory

    factory = get_session_factory()
    async with factory() as session:
        yield session


@pytest.fixture
def api_client(engine):
    """FastAPI test client with test database.

    Initializes the global database with test database URL so routes can access it.
    """
    import asyncio
    import os
    from app.api.routes import api_router
    from app.core.config import get_settings
    from app.db import init_db, close_db
    from app.db.seed import seed_plan_tiers
    from app.main import http_exception_handler, generic_exception_handler
    from fastapi import HTTPException
    from fastapi.middleware.cors import CORSMiddleware

    # Set test database URL in environment
    test_db_url = os.getenv(
        "TEST_DATABASE_URL",
        "postgresql+asyncpg://cofounder:cofounder@localhost:5432/cofounder_test"
    )

    @asynccontextmanager
    async def test_lifespan(app: FastAPI):
        """Test lifespan - initialize DB with test URL."""
        await init_db(test_db_url)
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
