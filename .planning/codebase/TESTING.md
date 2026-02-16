# Testing Patterns

**Analysis Date:** 2026-02-16

## Test Framework

**Python Runner:**
- Framework: Pytest 8.3.0+
- Async support: pytest-asyncio 0.24.0+
- Coverage: pytest-cov 6.0.0+
- Config: `backend/pyproject.toml` [tool.pytest.ini_options]
  ```toml
  [tool.pytest.ini_options]
  asyncio_mode = "auto"
  testpaths = ["tests"]
  ```

**TypeScript/Frontend:**
- No test framework installed or configured (no Jest, Vitest, etc.)
- No test files present in frontend codebase

**Run Commands (Python):**
```bash
pytest                    # Run all tests in tests/ directory
pytest -v                 # Verbose output with test names
pytest -k test_auth       # Run tests matching pattern "test_auth"
pytest --cov=app         # Run with coverage report
pytest -s                 # Show print statements
pytest -x                 # Stop at first failure
```

## Test File Organization

**Location:**
- Python: `backend/tests/` directory (separate from source)
- Follows structure: `backend/tests/test_*.py`
- Current files: `test_agent.py`, `test_auth.py`

**Naming Convention:**
- Test files: `test_*.py` (required by pytest discovery)
- Test classes: `Test*` (e.g., `TestCoFounderState`, `TestExtractFrontendApiDomain`)
- Test functions: `test_*` (e.g., `test_create_initial_state`, `test_valid_token`)

**Structure:**
```
backend/tests/
├── __init__.py          # Empty; marks directory as package
├── test_agent.py        # Tests for agent module
└── test_auth.py         # Tests for auth module
```

## Test Structure

**Typical Test Class:**
```python
class TestCoFounderState:
    """Tests for CoFounderState creation and management."""

    def test_create_initial_state(self):
        """Test that initial state is created with correct defaults."""
        state = create_initial_state(
            user_id="test-user",
            project_id="test-project",
            project_path="/tmp/test",
            goal="Create a hello world app",
        )

        assert state["user_id"] == "test-user"
        assert state["project_id"] == "test-project"
        # ... more assertions
```

**Patterns:**
- One test class per module/feature being tested
- Descriptive docstrings on both class and test method
- Arrange-Act-Assert pattern (implicit; not commented)
- Use fixtures or helper functions for repeated setup
- Test one behavior per test function

**Async Test Pattern:**
```python
@pytest.mark.asyncio
async def test_graph_entry_point():
    """Test that the graph starts at architect node."""
    graph = create_cofounder_graph()
    initial_state = create_initial_state(...)
    # assertions
```

## Mocking

**Framework:**
- Built-in: `unittest.mock.MagicMock`, `patch`
- Pattern: Context manager with `with patch(...)`

**Example Pattern:**
```python
from unittest.mock import MagicMock, patch

@dataclass
class _FakeSigningKey:
    key: object

def _mock_jwks_client():
    client = MagicMock()
    client.get_signing_key_from_jwt.return_value = _FakeSigningKey(key=_public_key)
    return client

# Usage in test:
with patch("app.core.auth.get_jwks_client", _mock_jwks_client):
    user = decode_clerk_jwt(token)
```

**Multiple Patches:**
```python
with (
    patch("app.core.auth.get_jwks_client", _mock_jwks_client),
    patch("app.core.auth.get_settings", _mock_settings),
):
    user = await require_auth(credentials=creds)
```

**What to Mock:**
- External services: Clerk JWKS, Stripe API
- Configuration: `get_settings()`, environment variables
- Database: Return mock objects instead of real queries

**What NOT to Mock:**
- Internal business logic (let real functions run)
- Core authentication/validation logic
- State/data structures

## Fixtures and Factories

**Test Data Creation:**
```python
# Module-level fixture for RSA keypair
_private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
_public_key = _private_key.public_key()

# Helper factory function
def _sign_jwt(payload: dict, kid: str = "test-kid") -> str:
    """Sign a JWT with the test RSA private key."""
    return pyjwt.encode(payload, _private_pem, algorithm="RS256", headers={"kid": kid})

# Usage in test
now = int(time.time())
token = _sign_jwt({
    "sub": "user_abc",
    "iat": now - 10,
    "exp": now + 300,
    "nbf": now - 10,
})
```

**Location:**
- Fixture helpers defined at module level in test file
- Shared fixtures: Use pytest fixtures (not yet implemented in codebase)
- Test data: Hardcoded or generated in helper functions

## Coverage

**Requirements:** No coverage targets enforced

**View Coverage:**
```bash
pytest --cov=app --cov-report=html    # Generate HTML report
pytest --cov=app --cov-report=term    # Terminal report
```

## Test Types

**Unit Tests (primary):**
- Scope: Single function or class method
- Isolation: Mock external dependencies
- Location: `backend/tests/test_*.py`
- Examples:
  - `test_create_initial_state()` - Tests state initialization
  - `test_parses_test_publishable_key()` - Tests key parsing
  - `test_valid_token()` - Tests JWT decoding
  - `test_expired_token_raises()` - Tests error handling

**Integration Tests:**
- Not yet implemented; tests currently are unit tests only
- Would test: Database operations, full authentication flow, agent graph execution
- Could use: pytest fixtures with real database or SQLite in-memory

**E2E Tests:**
- Not implemented
- Framework not configured

## Common Patterns

**Async Testing:**
```python
@pytest.mark.asyncio
async def test_graph_entry_point():
    """Async test using pytest-asyncio."""
    graph = create_cofounder_graph()
    initial_state = create_initial_state(...)
    # Assertions on async results
```

**Error Testing:**
```python
def test_invalid_key_raises(self):
    """Test that invalid input raises ValueError."""
    from app.core.auth import _extract_frontend_api_domain

    with pytest.raises(ValueError, match="Invalid Clerk publishable key"):
        _extract_frontend_api_domain("not-a-valid-key")

# With specific status codes
@pytest.mark.asyncio
async def test_missing_credentials_raises_401(self):
    """Test that missing credentials raise 401."""
    from app.core.auth import require_auth

    with pytest.raises(HTTPException) as exc_info:
        await require_auth(credentials=None)
    assert exc_info.value.status_code == 401
```

**Parametrized Tests (pattern not yet used):**
- Could use `@pytest.mark.parametrize` for testing multiple inputs
- Example pattern:
  ```python
  @pytest.mark.parametrize("plan_slug,interval,expected_price_id", [
      ("bootstrapper", "monthly", "price_123"),
      ("partner", "annual", "price_456"),
  ])
  def test_price_mapping(plan_slug, interval, expected_price_id):
      # Test with multiple inputs
  ```

## Test Configuration Details

**asyncio_mode: "auto"**
- Pytest-asyncio automatically handles async test function detection
- No need for `@pytest.mark.asyncio` wrapping (though it's used for clarity)
- Async fixtures not yet used

**testpaths: ["tests"]**
- Only runs tests in `backend/tests/` directory
- Prevents discovery of test templates or other files

## Assertion Style

**Pattern:**
- Simple `assert` statements (not fluent/chained)
- Direct attribute/dict key access
- Example from tests:
  ```python
  assert state["user_id"] == "test-user"
  assert state["project_id"] == "test-project"
  assert state["plan"] == []
  assert state["current_step_index"] == 0
  ```

- For exception testing: `pytest.raises` context manager with optional `match` for message checking

## Dependencies

**Installed (in pyproject.toml [project.optional-dependencies.dev]):**
- pytest >= 8.3.0
- pytest-asyncio >= 0.24.0
- pytest-cov >= 6.0.0
- ruff >= 0.8.0 (linting/formatting)
- mypy >= 1.13.0 (type checking)

---

*Testing analysis: 2026-02-16*
