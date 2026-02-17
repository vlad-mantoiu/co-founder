"""E2E test fixtures — FakeSandboxRuntime and e2e_api_client."""

import os
from contextlib import asynccontextmanager

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from app.db.base import Base


# ──────────────────────────────────────────────────────────────────────────────
# FakeSandboxRuntime
# ──────────────────────────────────────────────────────────────────────────────


class FakeSandboxRuntime:
    """Test double for E2BSandboxRuntime — no real E2B API calls."""

    def __init__(self, template: str = "base"):
        self.template = template
        self.files: dict[str, str] = {}
        self._started = False
        self._background_procs: dict[str, str] = {}

    @asynccontextmanager
    async def session(self):
        await self.start()
        try:
            yield self
        finally:
            await self.stop()

    async def start(self):
        self._started = True

    async def stop(self):
        self._started = False

    async def write_file(self, path: str, content: str):
        abs_path = path if path.startswith("/") else f"/home/user/{path}"
        self.files[abs_path] = content

    async def read_file(self, path: str) -> str:
        abs_path = path if path.startswith("/") else f"/home/user/{path}"
        return self.files.get(abs_path, "")

    async def list_files(self, path: str = "/") -> list[str]:
        return list(self.files.keys())

    async def make_dir(self, path: str):
        pass

    async def run_command(self, command: str, timeout: int = 120, cwd: str | None = None) -> dict:
        return {"stdout": "ok", "stderr": "", "exit_code": 0}

    async def run_background(self, command: str, cwd: str | None = None) -> str:
        pid = "fake-pid-001"
        self._background_procs[pid] = command
        return pid

    async def kill_process(self, pid: str):
        self._background_procs.pop(pid, None)

    async def install_packages(self, packages: list[str], manager: str = "pip") -> dict:
        return {"stdout": "installed", "stderr": "", "exit_code": 0}

    class _FakeSandbox:
        sandbox_id = "fake-sandbox-e2e-001"

        def get_host(self, port: int) -> str:
            return f"{port}-fake-sandbox-e2e-001.e2b.app"

        def set_timeout(self, t: int) -> None:
            pass

    @property
    def _sandbox(self):
        return self._FakeSandbox()


# ──────────────────────────────────────────────────────────────────────────────
# E2E fixtures
# ──────────────────────────────────────────────────────────────────────────────


@pytest.fixture
async def e2e_engine() -> AsyncEngine:
    """PostgreSQL test engine for E2E tests."""
    db_url = os.getenv(
        "TEST_DATABASE_URL",
        "postgresql+asyncpg://cofounder:cofounder@localhost:5432/cofounder_test",
    )
    engine = create_async_engine(db_url, echo=False)

    import app.db.models  # noqa: F401 — populate metadata

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
def api_client(e2e_engine):
    """Full-stack TestClient backed by test PostgreSQL — usable by E2E tests.

    Mirrors tests/api/conftest.py api_client fixture pattern.
    """
    from app.api.routes import api_router
    from app.core.config import get_settings
    from app.db import init_db, close_db
    from app.db.seed import seed_plan_tiers
    from app.main import http_exception_handler, generic_exception_handler

    test_db_url = os.getenv(
        "TEST_DATABASE_URL",
        "postgresql+asyncpg://cofounder:cofounder@localhost:5432/cofounder_test",
    )

    @asynccontextmanager
    async def test_lifespan(app: FastAPI):
        await init_db(test_db_url)
        await seed_plan_tiers()
        yield
        await close_db()

    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        description="E2E Test Client",
        version="0.1.0",
        lifespan=test_lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.exception_handler(HTTPException)(http_exception_handler)
    app.exception_handler(Exception)(generic_exception_handler)

    app.include_router(api_router, prefix="/api")

    with TestClient(app) as client:
        yield client
