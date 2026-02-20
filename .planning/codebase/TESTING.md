# Testing Patterns

**Analysis Date:** 2026-02-20

## Test Framework

**Backend (Python):**
- Runner: pytest 8.3.0+
- Async support: pytest-asyncio 0.24.0+ with `asyncio_mode = "auto"`
- Coverage: pytest-cov 6.0.0+
- Config: `backend/pyproject.toml` under `[tool.pytest.ini_options]`

**Frontend (TypeScript):**
- Not yet implemented—no test framework installed
- When implementing: Jest or Vitest recommended (compatible with Next.js)

**Run Commands (Backend):**
```bash
pytest tests                      # Run all tests
pytest tests -v                   # Verbose output with test names
pytest tests -k unit              # Run only unit tests (using markers)
pytest tests::TestClass::test_method  # Run specific test
pytest tests --cov=app            # Run with coverage report
pytest tests -m unit              # Run tests marked with @pytest.mark.unit
```

## Test File Organization

**Backend:**

**Location:** Test files alongside source or in parallel `tests/` directory
```
backend/
├── app/                    # Source code
├── tests/                  # Test root
│   ├── __init__.py
│   ├── conftest.py        # Shared fixtures
│   ├── api/               # API route tests
│   │   ├── conftest.py    # API-specific fixtures (database setup)
│   │   ├── test_auth.py
│   │   ├── test_onboarding_api.py
│   │   └── test_generation_routes.py
│   ├── agent/             # Agent tests
│   │   ├── test_llm_retry.py
│   │   ├── test_runner_real.py
│   │   └── test_local_path_safety.py
│   ├── e2e/               # End-to-end tests
│   │   ├── conftest.py    # E2E-specific fixtures
│   │   └── test_*.py
│   └── test_llm_helpers.py
```

**Naming Patterns:**
- File names: `test_<module>.py` (matches source module name)
- Test classes: `Test<Feature>` (e.g., `TestDecodeClerkJwt`)
- Test methods: `test_<scenario>` (e.g., `test_expired_token_raises`)
- Helper functions: `_helper_name()` (underscore prefix)

## Test Structure and Markers

**Pytest Configuration:**
```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
asyncio_default_fixture_loop_scope = "function"
testpaths = ["tests"]
markers = [
    "unit: Unit tests - no external services required (fakeredis OK)",
    "integration: Integration tests - require real database and Redis",
]
addopts = "--strict-markers"
```

**Test Markers:**

Use `@pytest.mark.unit` or `@pytest.mark.integration` to categorize tests.

**Unit Tests:**
- No external services (no real database, no real Redis)
- Mock all dependencies
- Focus: function logic, error handling, validation
- Examples from codebase:
  - `tests/api/test_auth.py` — uses `@pytest.mark.unit` (no DB needed)
  - `tests/agent/test_llm_retry.py` — mocks LLM calls, no real API

**Integration Tests:**
- Require real PostgreSQL test database
- Use TestClient against full FastAPI app
- Database state initialized fresh per test
- Examples from codebase:
  - `tests/api/test_onboarding_api.py` — uses `@pytest.mark.integration` (requires DB)
  - `tests/e2e/` — full stack tests with real database

**E2E Tests:**
- Simulation of FakeSandboxRuntime instead of real E2B Cloud
- Full API path from request to response
- Database state persists across related tests
- Markers: `@pytest.mark.e2e` (not yet observed but pattern clear)

## Fixture Patterns

**Root Fixtures (`tests/conftest.py`):**
```python
@pytest.fixture
def runner_fake():
    """Fresh RunnerFake with happy_path scenario (default)."""
    return RunnerFake(scenario="happy_path")

@pytest.fixture
def sample_state():
    """Create a sample initial state for testing."""
    return create_initial_state(
        user_id="test-user-001",
        project_id="test-project-001",
        project_path="/tmp/test-project",
        goal="Build a simple inventory tracking app",
        session_id="test-session-001",
    )
```

**API Fixtures (`tests/api/conftest.py`):**

**Database Setup:**
```python
@pytest.fixture
async def engine() -> AsyncEngine:
    """Create PostgreSQL test engine (supports JSONB).

    Note: Uses Base.metadata.create_all instead of migrations for test simplicity.
    Ensures all model columns are created including latest additions.
    """
    db_url = os.getenv("TEST_DATABASE_URL", "postgresql+asyncpg://cofounder:cofounder@localhost:5432/cofounder_test")
    engine = create_async_engine(db_url, echo=False)

    # Import models to populate metadata
    import app.db.models  # noqa: F401

    # Create fresh schema
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Cleanup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()
```

**TestClient Setup:**
```python
@pytest.fixture
def api_client(engine):
    """FastAPI test client with test database.

    Initializes the global database with test database URL so routes can access it.
    """
    @asynccontextmanager
    async def test_lifespan(app: FastAPI):
        await init_db(test_db_url)
        await seed_plan_tiers()
        yield
        await close_db()

    app = FastAPI(lifespan=test_lifespan)

    # Add middleware and routes
    app.add_middleware(CORSMiddleware, ...)
    app.exception_handler(HTTPException)(http_exception_handler)
    app.include_router(api_router, prefix="/api")

    with TestClient(app) as client:
        yield client
```

**E2E Fixtures (`tests/e2e/conftest.py`):**

FakeSandboxRuntime for E2B simulation:
```python
class FakeSandboxRuntime:
    """Test double for E2BSandboxRuntime — no real E2B API calls."""

    def __init__(self, template: str = "base"):
        self.template = template
        self.files: dict[str, str] = {}
        self._started = False

    @asynccontextmanager
    async def session(self):
        await self.start()
        try:
            yield self
        finally:
            await self.stop()

    async def write_file(self, path: str, content: str):
        abs_path = path if path.startswith("/") else f"/home/user/{path}"
        self.files[abs_path] = content

    async def run_command(self, command: str, timeout: int = 120, cwd: str | None = None) -> dict:
        return {"stdout": "ok", "stderr": "", "exit_code": 0}
```

## Test Structure Examples

**Unit Test Structure (From `tests/api/test_auth.py`):**

```python
"""Tests for Clerk JWT authentication."""

import time
from dataclasses import dataclass
from unittest.mock import AsyncMock, MagicMock, patch

import jwt as pyjwt
import pytest
from fastapi import HTTPException

pytestmark = pytest.mark.unit  # Marker at module level

# Module-level setup (RSA key generation for all tests)
_private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
_public_key = _private_key.public_key()

def _sign_jwt(payload: dict, kid: str = "test-kid") -> str:
    """Helper to sign test JWTs."""
    return pyjwt.encode(payload, _private_pem, algorithm="RS256", headers={"kid": kid})

class TestExtractFrontendApiDomain:
    """Grouped tests for related functionality."""

    def test_parses_test_publishable_key(self):
        from app.core.auth import _extract_frontend_api_domain

        domain = _extract_frontend_api_domain(_TEST_CLERK_PK)
        assert domain == "superb-tick-45.clerk.accounts.dev"

    def test_parses_live_publishable_key(self):
        # Simulate a live key...
        assert domain == "example.clerk.accounts.dev"

    def test_invalid_key_raises(self):
        with pytest.raises(ValueError, match="Invalid Clerk publishable key"):
            _extract_frontend_api_domain("not-a-valid-key")

class TestDecodeClerkJwt:
    """More grouped tests."""

    def test_valid_token(self):
        # Arrange: create a valid token
        now = int(time.time())
        token = _sign_jwt({"sub": "user_abc", ...})

        # Act: decode the token
        with patch("app.core.auth.get_jwks_client", _mock_jwks_client):
            user = decode_clerk_jwt(token)

        # Assert: verify result
        assert user.user_id == "user_abc"

class TestRequireAuth:
    """Async tests marked explicitly."""

    @pytest.mark.asyncio
    async def test_valid_bearer_token(self):
        # Setup
        mock_request = MagicMock()
        mock_request.state = MagicMock()
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

        # Act + Assert
        with patch("app.core.auth.get_jwks_client", _mock_jwks_client):
            user = await require_auth(request=mock_request, credentials=creds)

        assert user.user_id == "user_xyz"
```

**Integration Test Structure (From `tests/api/test_onboarding_api.py`):**

```python
"""Integration tests for onboarding API endpoints.

Tests cover:
- Session start with questions
- Empty/whitespace idea rejection
- Answer submission and index advancement
- User isolation (404 for other user's sessions)
- ThesisSnapshot generation with tier filtering
- Required answer validation
- Tier session limits
- Session abandonment
- Session resumption
- Inline thesis editing
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.auth import ClerkUser, require_auth

pytestmark = pytest.mark.integration  # All tests in file are integration

@pytest.fixture
def user_a():
    """Test user A."""
    return ClerkUser(user_id="user_a", claims={"sub": "user_a"})

@pytest.fixture
def user_b():
    """Test user B."""
    return ClerkUser(user_id="user_b", claims={"sub": "user_b"})

def override_auth(user: ClerkUser):
    """Create auth override for a specific user."""
    async def _override():
        return user
    return _override

def test_start_onboarding_returns_questions(api_client: TestClient, mock_runner, user_a):
    """Test that POST /api/onboarding/start returns session with 5-7 questions."""
    # Arrange: setup dependency overrides
    app: FastAPI = api_client.app
    app.dependency_overrides[require_auth] = override_auth(user_a)
    app.dependency_overrides[get_runner] = lambda: mock_runner

    # Act: make request
    response = api_client.post("/api/onboarding/start", json={"idea": "A marketplace for local artisans"})

    # Assert: verify response structure
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "in_progress"
    assert data["current_question_index"] == 0
    assert len(data["questions"]) == 6

    # Cleanup: clear overrides
    app.dependency_overrides.clear()

def test_submit_answer_to_other_users_session_returns_404(api_client: TestClient, mock_runner, user_a, user_b):
    """Test that User B cannot answer User A's session (ONBD-05)."""
    app: FastAPI = api_client.app

    # User A starts session
    app.dependency_overrides[require_auth] = override_auth(user_a)
    app.dependency_overrides[get_runner] = lambda: mock_runner

    start_response = api_client.post("/api/onboarding/start", json={"idea": "A task manager for teams"})
    assert start_response.status_code == 200
    session_id = start_response.json()["id"]

    # User B tries to answer
    app.dependency_overrides[require_auth] = override_auth(user_b)

    answer_response = api_client.post(
        f"/api/onboarding/{session_id}/answer",
        json={"question_id": first_question_id, "answer": "Stolen answer"}
    )

    assert answer_response.status_code == 404
    app.dependency_overrides.clear()
```

## Mocking Patterns

**Mock Framework:** `unittest.mock` (stdlib)

**Common Patterns:**

**MagicMock for Sync Objects:**
```python
from unittest.mock import MagicMock

mock_settings = MagicMock()
mock_settings.clerk_publishable_key = _TEST_CLERK_PK
mock_settings.clerk_allowed_origins = ["http://localhost:3000"]
```

**AsyncMock for Async Functions:**
```python
from unittest.mock import AsyncMock

mock_llm = AsyncMock()
mock_llm.ainvoke = AsyncMock(return_value=response)
```

**Patching at Call Site:**
```python
with patch("app.core.auth.get_jwks_client", _mock_jwks_client):
    user = decode_clerk_jwt(token)
```

**Side Effects for Multi-Step Tests:**
```python
mock_llm.ainvoke = AsyncMock(side_effect=[
    _make_overloaded_error(),  # First call raises
    response,                   # Second call succeeds
])
```

**Dependency Override Pattern (FastAPI):**
```python
app.dependency_overrides[require_auth] = override_auth(user_a)
# ... test ...
app.dependency_overrides.clear()
```

**What to Mock:**
- External services (LLM, Clerk, E2B Cloud)
- Database calls (unless testing integration)
- HTTP requests
- File I/O
- Credentials and secrets

**What NOT to Mock:**
- Business logic being tested
- Pydantic validation
- Database models themselves (mock at session level instead)
- HTTP status codes and response structures (test them real)

## Fixtures and Test Doubles

**Test Doubles from Codebase:**

**RunnerFake (`app/agent/runner_fake.py`):**
```python
from app.agent.runner_fake import RunnerFake

@pytest.fixture
def runner_fake():
    """Fresh RunnerFake with happy_path scenario (default)."""
    return RunnerFake(scenario="happy_path")

@pytest.fixture
def runner_fake_failing():
    """RunnerFake with llm_failure scenario."""
    return RunnerFake(scenario="llm_failure")

@pytest.fixture
def runner_fake_partial():
    """RunnerFake with partial_build scenario."""
    return RunnerFake(scenario="partial_build")

@pytest.fixture
def runner_fake_rate_limited():
    """RunnerFake with rate_limited scenario."""
    return RunnerFake(scenario="rate_limited")
```

**FakeSandboxRuntime (`tests/e2e/conftest.py`):**
- Simulates E2B Cloud without actual API calls
- Methods: `write_file()`, `read_file()`, `run_command()`, `install_packages()`
- Used in E2E tests to avoid real sandbox costs

**Sample State Creation:**
```python
@pytest.fixture
def sample_state():
    """Create a sample initial state for testing."""
    return create_initial_state(
        user_id="test-user-001",
        project_id="test-project-001",
        project_path="/tmp/test-project",
        goal="Build a simple inventory tracking app",
        session_id="test-session-001",
    )
```

## Coverage

**Requirements:** Not enforced at CI level (no coverage threshold configured)

**View Coverage:**
```bash
pytest tests --cov=app --cov-report=html
# Opens htmlcov/index.html in browser
```

**Current Coverage (Approximate):**
- Backend: ~13,500 LOC of tests across 346 test files
- Unit test heavy (most tests use `@pytest.mark.unit`)
- Integration tests for critical paths (onboarding, auth, generation)
- E2E tests use fake implementations, not real services

## Test Types and Examples

**Unit Test Example (Auth decoding):**

From `tests/api/test_auth.py`:
- No database required
- Mocks JWKS client
- Tests JWT parsing, expiration, audience validation
- Isolated from HTTP layer

**Integration Test Example (Onboarding flow):**

From `tests/api/test_onboarding_api.py`:
- Real database (fresh schema)
- Real TestClient against full FastAPI app
- Tests full request→response cycle
- Includes session management, user isolation, thesis generation
- ~24 test methods covering the complete onboarding surface

**Async Pattern:**
```python
class TestRequireAuth:
    @pytest.mark.asyncio
    async def test_valid_bearer_token(self):
        # Async test body
        user = await require_auth(request=mock_request, credentials=creds)
        assert user.user_id == "user_xyz"
```

**Parametrized Test Example:**
```python
@pytest.mark.parametrize("stage", ["architect", "coder", "executor", "debugger", "reviewer", "git_manager"])
def test_all_stages_start(stage):
    # Test each stage
    assert stage in VALID_STAGES
```

## Database Testing

**Test Database:**
- PostgreSQL with asyncpg driver
- URL: `postgresql+asyncpg://cofounder:cofounder@localhost:5432/cofounder_test`
- Configurable via `TEST_DATABASE_URL` env var

**Schema Setup:**
- Fresh schema created per test file (in conftest fixtures)
- No migrations—uses `Base.metadata.create_all()` for speed
- Includes all model columns including latest additions

**Session Management:**
```python
@pytest.fixture
async def db_session(engine: AsyncEngine, api_client) -> AsyncSession:
    """Create an async session for tests."""
    from app.db import get_session_factory

    factory = get_session_factory()
    async with factory() as session:
        yield session
```

## Frontend Testing (Not Implemented)

**Setup When Ready:**

When adding frontend tests:
1. Choose framework: Jest or Vitest (both compatible with Next.js 15)
2. Install: `npm install --save-dev jest @testing-library/react`
3. Configure: `jest.config.js` in `/frontend`
4. Create test files: `__tests__/` or `.test.tsx` co-located with components
5. Test patterns: Use React Testing Library (not enzyme or snapshot tests)
6. Commands:
   ```bash
   npm test                    # Run all tests
   npm test -- --watch        # Watch mode
   npm test -- --coverage     # Coverage report
   ```

**Convention When Implemented:**
- Component tests: Focus on behavior, not implementation
- Hook tests: Use `@testing-library/react` hooks testing library
- Integration: TestClient for API calls to backend
- No snapshot tests (brittle, hard to maintain)

---

*Testing analysis: 2026-02-20*
