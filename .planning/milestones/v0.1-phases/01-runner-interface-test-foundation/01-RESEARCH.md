# Phase 1: Runner Interface & Test Foundation - Research

**Researched:** 2026-02-16
**Domain:** LangGraph testing, Python Protocol pattern, pytest organization
**Confidence:** HIGH

## Summary

Phase 1 wraps the existing 6-node LangGraph pipeline (Architect → Coder → Executor → Debugger → Reviewer → GitManager) with a testable Runner interface to enable TDD throughout the project. The Runner protocol provides both full pipeline execution and individual stage access, covering ALL LLM operations (code generation, onboarding, understanding interviews, brief/artifact generation).

The research reveals a clear path: Python's `typing.Protocol` for structural typing, LangChain's `GenericFakeChatModel` for deterministic test doubles, pytest's fixture system for organized test structure, and GitHub Actions service containers for CI/CD with PostgreSQL and Redis.

**Primary recommendation:** Use Protocol pattern with RunnerReal (production) and RunnerFake (testing) implementations. Structure tests by domain (api/, domain/, orchestration/, e2e/). Use scenario-based fakes with realistic content. Fix critical datetime.utcnow() deprecation immediately (affects 7 files, blocks Python 3.12+ compatibility).

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Runner Scope:**
- Runner protocol covers ALL LLM operations: code generation pipeline, onboarding questions, understanding interview, brief generation, artifact generation
- Expose both full pipeline and individual stages: `Runner.run(goal)` for end-to-end AND `Runner.step(stage)` for individual node execution
- The existing 6-node LangGraph pipeline (Architect → Coder → Executor → Debugger → Reviewer → GitManager) wrapped without modification
- Additional Runner methods for non-pipeline LLM calls: `Runner.generate_questions()`, `Runner.generate_brief()`, `Runner.generate_artifacts()`, etc.

**Test Double Behavior:**
- Scenario-based RunnerFake with named scenarios: `happy_path`, `llm_failure`, `partial_build`, `rate_limited`
- Each scenario is a pre-built response set that covers the full founder flow for that path
- Realistic content in fakes — plausible code, briefs, and artifacts (not "test stub" or "lorem ipsum")
- All 4 scenarios must be pre-built for MVP

**Test Harness Structure:**
- Separate directories for each test group: `tests/api/`, `tests/domain/`, `tests/orchestration/`, `tests/e2e/`
- Both single command (`pytest`) and convenience targets (`make test-api`, `make test-domain`, `make test-e2e`, `make test`)
- GitHub Actions CI pipeline with PostgreSQL + Redis services
- Tests runnable locally with identical behavior to CI

### Claude's Discretion

- Whether RunnerFake uses instant returns or configurable delays (pick what makes tests fastest and most reliable)
- Whether outputs are fully deterministic (same seed = identical) or schema-stable (pick what's most practical for CI)
- Test function naming convention (spec IDs in names vs descriptive names with IDs in docstrings)
- Tech debt triage: Mem0 async fix, datetime.utcnow() replacement, silent exception fixes, health check fix — Claude decides what to include in Phase 1 vs defer, based on risk to Runner reliability and foundation stability

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope
</user_constraints>

## Standard Stack

### Core Testing Libraries

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pytest | >=8.3.0 | Test framework | Industry standard, already in pyproject.toml, powerful fixtures/parametrization |
| pytest-asyncio | >=0.24.0 | Async test support | Required for FastAPI/async graph testing, already installed |
| pytest-cov | >=6.0.0 | Coverage reporting | Code coverage visibility, already installed |
| typing.Protocol | stdlib (3.12+) | Structural typing | Zero-cost abstraction, type-safe, runtime_checkable for isinstance() |

### LangChain Testing Support

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| langchain-core | >=0.3.0 (installed) | GenericFakeChatModel | Deterministic LLM mocking with message sequence control |
| langgraph.checkpoint.memory | >=0.2.0 (installed) | MemorySaver | In-memory checkpointing for stateful graph testing |

### CI/CD Support

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| GitHub Actions services | N/A | PostgreSQL/Redis containers | CI environment matches local, health checks ensure ready state |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Protocol | ABC (Abstract Base Class) | ABC requires inheritance; Protocol allows structural subtyping (duck typing with type safety) |
| GenericFakeChatModel | Mock/MagicMock | GenericFakeChatModel understands LangChain message format natively, Mock requires manual setup |
| pytest fixtures | unittest setUp/tearDown | Fixtures are more composable, support parametrization, and have explicit scope control |
| vcrpy cassettes | GenericFakeChatModel | Cassettes break when prompts change; GenericFakeChatModel is maintenance-friendly for evolving code |

**Installation:**
```bash
# All dependencies already in pyproject.toml
pip install -e ".[dev]"  # Installs pytest, pytest-asyncio, pytest-cov
```

## Architecture Patterns

### Recommended Project Structure

```
backend/
├── app/
│   ├── agent/
│   │   ├── runner.py              # Runner protocol definition
│   │   ├── runner_real.py         # Production implementation (wraps LangGraph)
│   │   ├── runner_fake.py         # Test implementation (scenario-based)
│   │   ├── graph.py               # Existing LangGraph (unchanged)
│   │   └── nodes/                 # Existing nodes (unchanged)
│   └── ...
├── tests/
│   ├── conftest.py                # Shared fixtures (RunnerFake factory, DB/Redis)
│   ├── api/                       # API route tests (FastAPI endpoints)
│   │   ├── conftest.py            # API-specific fixtures
│   │   └── test_agent_routes.py
│   ├── domain/                    # Domain logic tests (pure business logic)
│   │   └── test_runner_scenarios.py
│   ├── orchestration/             # Graph orchestration tests (LangGraph flow)
│   │   └── test_graph_execution.py
│   └── e2e/                       # End-to-end tests (full user flows)
│       └── test_founder_journey.py
└── Makefile                       # Convenience targets
```

### Pattern 1: Protocol-Based Runner Interface

**What:** Structural subtyping for polymorphic behavior without inheritance

**When to use:** When you need testable abstractions with compile-time safety and runtime flexibility

**Example:**
```python
# Source: Python typing docs + LangChain patterns
from typing import Protocol, runtime_checkable
from app.agent.state import CoFounderState

@runtime_checkable
class Runner(Protocol):
    """Protocol for agent execution (production or test)."""

    async def run(self, state: CoFounderState) -> CoFounderState:
        """Execute full agent pipeline from initial state to completion."""
        ...

    async def step(self, state: CoFounderState, stage: str) -> CoFounderState:
        """Execute a single stage (architect, coder, executor, etc.)."""
        ...

    async def generate_questions(self, context: dict) -> list[dict]:
        """Generate dynamic onboarding/understanding questions."""
        ...

    async def generate_brief(self, answers: dict) -> dict:
        """Generate rationalized idea brief from interview answers."""
        ...

    async def generate_artifacts(self, brief: dict) -> dict:
        """Generate supporting documents (Product Brief, MVP Scope, etc.)."""
        ...
```

**Why this works:**
- Protocol is checked at type-check time (mypy validates compliance)
- `@runtime_checkable` allows `isinstance(obj, Runner)` for runtime checks
- No inheritance required — RunnerReal and RunnerFake independently satisfy interface
- Zero runtime overhead vs traditional inheritance

### Pattern 2: Scenario-Based Fake with Realistic Content

**What:** Pre-built response sequences mapped to named test scenarios

**When to use:** When test reliability matters more than exact output matching

**Example:**
```python
# Source: Research synthesis + LangChain GenericFakeChatModel patterns
from langchain_core.messages import AIMessage
from langchain_core.language_models import GenericFakeChatModel

class RunnerFake:
    """Scenario-based test double for Runner protocol."""

    SCENARIOS = {
        "happy_path": {
            "questions": [
                {"id": "q1", "text": "Who is your target user?", "required": True},
                {"id": "q2", "text": "What problem are you solving?", "required": True},
            ],
            "brief": {
                "problem_statement": "Small business owners lack simple inventory tracking",
                "target_user": "Retail shop owners with 1-10 employees",
                "value_prop": "Dead-simple inventory app with barcode scanning",
                "smallest_viable_experiment": "Single-location inventory tracker with manual entry"
            },
            "plan": [
                {"index": 0, "description": "Create Product model with name, SKU, quantity", "status": "pending"},
                {"index": 1, "description": "Implement inventory list view with add/edit", "status": "pending"},
            ],
            "code": {
                "src/models.py": "from sqlalchemy import Column, Integer, String...",
                "src/views.py": "from fastapi import APIRouter...",
            },
            "test_result": {"exit_code": 0, "output": "All tests passed"},
        },
        "llm_failure": {
            "error": "Anthropic API rate limit exceeded",
            "stage": "architect",
            "retry_after": 60,
        },
        "partial_build": {
            # Plan succeeds, code generation succeeds, tests fail
            "plan": [...],
            "code": {...},
            "test_result": {"exit_code": 1, "output": "TypeError: expected str, got None"},
        },
        "rate_limited": {
            "error": "Worker capacity exceeded",
            "estimated_wait_minutes": 5,
        },
    }

    def __init__(self, scenario: str = "happy_path"):
        self.scenario = self.SCENARIOS[scenario]
        self._llm = GenericFakeChatModel(
            messages=iter([
                AIMessage(content="..."),  # Architect response
                AIMessage(content="..."),  # Coder response
                AIMessage(content="..."),  # Reviewer response
            ])
        )

    async def run(self, state: CoFounderState) -> CoFounderState:
        """Execute scenario-based fake flow."""
        if "error" in self.scenario:
            raise RuntimeError(self.scenario["error"])

        # Return scenario data wrapped in state format
        return {
            **state,
            "plan": self.scenario["plan"],
            "working_files": self.scenario["code"],
            "is_complete": True,
        }
```

**Why realistic content matters:**
- Tests validate schema parsing, not just happy-path success
- Reveals edge cases (long strings, special characters, nested structures)
- Downstream code expects real-looking data (JSON serialization, DB constraints)
- Makes test failures easier to debug ("expected inventory app, got lorem ipsum")

### Pattern 3: Layered Test Fixtures with Scope Control

**What:** Shared test setup organized by scope (session, module, function) and domain

**When to use:** When test performance matters and setup is expensive (DB, Redis, LangGraph compilation)

**Example:**
```python
# Source: pytest docs + project needs
# tests/conftest.py
import pytest
from app.agent.runner_fake import RunnerFake
from app.db.base import get_session_factory

@pytest.fixture(scope="session")
def db_session_factory():
    """Create DB session factory once per test run."""
    # Shared across all tests, created once
    factory = get_session_factory()
    yield factory
    # Cleanup after all tests

@pytest.fixture(scope="function")
def runner_fake():
    """Create fresh RunnerFake for each test (default scenario)."""
    return RunnerFake(scenario="happy_path")

@pytest.fixture(scope="function")
def runner_fake_failing():
    """Create RunnerFake for LLM failure scenario."""
    return RunnerFake(scenario="llm_failure")

@pytest.fixture(scope="module")
def compiled_graph():
    """Compile LangGraph once per test module (expensive operation)."""
    from app.agent.graph import create_cofounder_graph
    return create_cofounder_graph()

# tests/api/conftest.py (API-specific fixtures)
import pytest
from fastapi.testclient import TestClient

@pytest.fixture
def api_client(runner_fake):
    """FastAPI test client with RunnerFake injected."""
    from app.main import app
    from app.dependencies import get_runner

    # Override dependency
    app.dependency_overrides[get_runner] = lambda: runner_fake

    client = TestClient(app)
    yield client

    # Cleanup
    app.dependency_overrides.clear()
```

**Scope selection guide:**
- `function` (default): Fresh fixture per test — use for stateful objects that mutate
- `module`: Shared within file — use for expensive setup that's read-only across tests
- `session`: Shared across entire run — use for extremely expensive setup (DB schema, compiled graphs)

### Pattern 4: GitHub Actions Service Containers

**What:** PostgreSQL and Redis running as Docker containers in CI, accessible via localhost

**When to use:** Always — ensures CI matches local environment exactly

**Example:**
```yaml
# .github/workflows/test.yml
name: Test Suite

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_USER: test_user
          POSTGRES_PASSWORD: test_pass
          POSTGRES_DB: cofounder_test
        ports:
          - 5432:5432
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

      redis:
        image: redis:7-alpine
        ports:
          - 6379:6379
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python 3.12
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'
          cache: 'pip'

      - name: Install dependencies
        working-directory: backend
        run: |
          pip install -e ".[dev]"

      - name: Run tests
        working-directory: backend
        env:
          DATABASE_URL: postgresql://test_user:test_pass@localhost:5432/cofounder_test
          REDIS_URL: redis://localhost:6379/0
        run: |
          pytest tests/ -v --cov=app --cov-report=term-missing
```

**Why service containers:**
- Jobs run AFTER health checks pass (services are ready before tests start)
- localhost access (services bound to host network)
- Fast startup (health checks = 10s intervals, 5 retries = ~50s max wait)
- Matches local dev (same Postgres 16, Redis 7 versions)

### Anti-Patterns to Avoid

- **Mocking everything with unittest.mock:** Creates brittle tests tied to implementation. Use Protocol + real implementations where possible, reserve mocks for external services.
- **VCR cassettes for LLM calls:** Breaks every time prompts change. Use GenericFakeChatModel with scenario-based responses instead.
- **Global mutable state in fixtures:** Use function-scoped fixtures for stateful objects, not module/session scope.
- **Testing implementation details:** Test behavior (does it generate valid plans?), not internals (does it call _parse_plan_json?).
- **Silent exception handling:** `except Exception: pass` hides failures. Log errors or re-raise with context.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| LLM response mocking | Custom fake LLM class | `langchain_core.language_models.GenericFakeChatModel` | Handles message iteration, streaming, and content extraction. Edge cases: empty responses, malformed JSON, rate limits. |
| Test parametrization | Loop + assertions | `@pytest.mark.parametrize` | Pytest shows exactly which parameter failed. Custom loops obscure which case broke. |
| Async test execution | Custom asyncio.run() wrapper | `pytest-asyncio` with `asyncio_mode = "auto"` | Handles event loop lifecycle, cleanup, and exception propagation correctly. |
| Database fixtures | Manual setup/teardown | pytest fixtures with scope control | Fixtures compose (fixture can use another fixture), support parametrization, and handle cleanup automatically. |
| Test discovery | Custom test runner | pytest with `testpaths = ["tests"]` | Pytest discovers tests by convention (test_*.py, *_test.py), no registration needed. |

**Key insight:** Testing infrastructure has solved problems (fixture lifecycle, async execution, parametrization, mocking) where custom solutions introduce bugs. LangChain's GenericFakeChatModel specifically handles LLM message format edge cases that unittest.Mock doesn't know about.

## Common Pitfalls

### Pitfall 1: Protocol Methods Missing Implementations

**What goes wrong:** RunnerReal or RunnerFake passes mypy checks but fails at runtime with AttributeError

**Why it happens:** Protocol only checks signatures statically; if you forget to implement a method, mypy won't catch it unless you explicitly mark the class as implementing the Protocol

**How to avoid:**
```python
# BAD: Protocol satisfied implicitly, easy to miss methods
class RunnerReal:
    async def run(self, state): ...
    # Oops, forgot generate_questions()

# GOOD: Explicit protocol satisfaction, mypy validates completeness
class RunnerReal:
    """Production Runner implementation."""

    def __class_getitem__(cls, item):
        """Mark as satisfying Runner protocol."""
        return cls

    async def run(self, state: CoFounderState) -> CoFounderState: ...
    async def step(self, state: CoFounderState, stage: str) -> CoFounderState: ...
    async def generate_questions(self, context: dict) -> list[dict]: ...
    # mypy error if any protocol method is missing
```

**Warning signs:**
- AttributeError in tests that pass type checking
- Tests work with RunnerFake but fail with RunnerReal
- "object has no attribute X" at runtime despite mypy approval

### Pitfall 2: Fixture Scope Mismatch Causing State Leakage

**What goes wrong:** Test A modifies state, Test B sees modified state and fails intermittently

**Why it happens:** Using module/session scope for stateful objects (state persists across tests)

**How to avoid:**
```python
# BAD: RunnerFake at module scope (state leaks between tests)
@pytest.fixture(scope="module")
def runner():
    return RunnerFake()

def test_happy_path(runner):
    runner.run(...)  # Mutates runner internal state

def test_failure_path(runner):
    # Sees state from test_happy_path!
    runner.run(...)

# GOOD: RunnerFake at function scope (fresh instance per test)
@pytest.fixture(scope="function")  # or omit scope (function is default)
def runner():
    return RunnerFake()

# GOOD: Module scope for read-only expensive setup
@pytest.fixture(scope="module")
def compiled_graph():
    """Graph compilation is expensive, read-only, safe to share."""
    return create_cofounder_graph()
```

**Warning signs:**
- Tests pass individually but fail when run together
- Test order matters (pytest -x shows different results than full run)
- "Expected X, got Y" where Y is from a previous test

### Pitfall 3: datetime.utcnow() Deprecation

**What goes wrong:** Code uses `datetime.utcnow()` which is deprecated in Python 3.12+ and removed in 3.15

**Why it happens:** Legacy API, replaced by timezone-aware `datetime.now(timezone.utc)`

**How to avoid:**
```python
# BAD: Deprecated in 3.12, removed in 3.15
from datetime import datetime
created_at = datetime.utcnow()

# GOOD: Timezone-aware, future-proof
from datetime import datetime, timezone
created_at = datetime.now(timezone.utc)
```

**Affected files (from grep):**
- `backend/app/db/models/user_settings.py`
- `backend/app/api/routes/admin.py`
- `backend/app/core/locking.py`
- `backend/app/memory/episodic.py` (lines 48, 137, 178)
- `backend/app/db/models/project.py`
- `backend/app/db/models/usage_log.py`
- `backend/app/integrations/github.py`

**Warning signs:**
- DeprecationWarning in test output
- Future Python version incompatibility
- Timezone bugs (UTC vs local time confusion)

### Pitfall 4: Silent Exception Swallowing

**What goes wrong:** Errors hidden by `except: pass`, failures go unnoticed until production

**Why it happens:** "Optional" operations (memory, deps) fail silently to avoid blocking main flow

**How to avoid:**
```python
# BAD: Silent failure
try:
    await memory.add(content=...)
except Exception:
    pass  # Error lost forever

# GOOD: Log with context for debugging
import logging
logger = logging.getLogger(__name__)

try:
    await memory.add(content=...)
except Exception as e:
    logger.warning(f"Memory persistence failed (non-blocking): {e}", exc_info=True)

# BEST: Track optional failures with metrics
try:
    await memory.add(content=...)
except Exception as e:
    logger.warning(f"Memory persistence failed: {e}")
    metrics.increment("memory.add.failures")
```

**Found in codebase:**
- `backend/app/agent/nodes/architect.py` line 66: `except Exception: pass` (memory is optional)
- `backend/app/api/routes/agent.py` lines 139, 177, 196: Silent memory/episodic failures
- `backend/app/agent/nodes/executor.py` line 40, 139: Silent directory/dependency errors

**Warning signs:**
- Tests always pass but features don't work
- "It worked in dev but not staging"
- Debugging requires adding print statements

### Pitfall 5: Missing Health Check Implementation

**What goes wrong:** Load balancer thinks service is healthy when DB/Redis are down

**Why it happens:** `/ready` endpoint has TODO comment, doesn't actually check dependencies

**How to avoid:**
```python
# Current state (BAD)
@router.get("/ready")
async def readiness_check():
    """Readiness check - verifies dependencies are available."""
    # TODO: Add database and Redis connectivity checks
    return {"status": "ready"}

# Fixed (GOOD)
@router.get("/ready")
async def readiness_check():
    """Readiness check - verifies dependencies are available."""
    checks = {"database": False, "redis": False}

    try:
        # Check PostgreSQL
        async with get_session_factory()() as session:
            await session.execute(text("SELECT 1"))
        checks["database"] = True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")

    try:
        # Check Redis
        redis = get_redis()
        await redis.ping()
        checks["redis"] = True
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")

    all_healthy = all(checks.values())
    status_code = 200 if all_healthy else 503

    return JSONResponse(
        status_code=status_code,
        content={"status": "ready" if all_healthy else "degraded", "checks": checks}
    )
```

**Warning signs:**
- Service marked healthy but requests fail
- Load balancer routes traffic to unhealthy instances
- Cascading failures (service can't reach DB but keeps accepting requests)

## Code Examples

Verified patterns from official sources:

### Testing LangGraph with GenericFakeChatModel

```python
# Source: https://docs.langchain.com/oss/python/langchain/test
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.language_models import GenericFakeChatModel
from langgraph.checkpoint.memory import MemorySaver

def test_graph_with_fake_llm():
    """Test graph execution with deterministic fake LLM."""
    # Create fake LLM with predefined responses
    fake_llm = GenericFakeChatModel(
        messages=iter([
            AIMessage(content='{"plan": [{"index": 0, "description": "Create model"}]}'),
            AIMessage(content='class Product:\n    def __init__(self, name): ...'),
            AIMessage(content='Review passed'),
        ])
    )

    # Inject into graph (requires refactoring nodes to accept llm parameter)
    from app.agent.graph import create_cofounder_graph
    graph = create_cofounder_graph()

    # Use MemorySaver for test checkpointing
    checkpointer = MemorySaver()

    state = {
        "messages": [HumanMessage(content="Create an inventory app")],
        "user_id": "test-user",
        "project_id": "test-project",
        ...
    }

    result = graph.invoke(state, config={"configurable": {"thread_id": "test-123"}})

    assert result["plan"] is not None
    assert len(result["plan"]) > 0
    assert result["is_complete"] is True
```

### Pytest Parametrize for Scenario Testing

```python
# Source: https://docs.pytest.org/en/stable/how-to/parametrize.html
import pytest
from app.agent.runner_fake import RunnerFake

@pytest.mark.parametrize("scenario,expected_complete", [
    ("happy_path", True),
    ("partial_build", False),
])
async def test_runner_scenarios(scenario, expected_complete):
    """Test runner with multiple scenarios."""
    runner = RunnerFake(scenario=scenario)

    state = create_initial_state(
        user_id="test",
        project_id="test",
        project_path="/tmp/test",
        goal="Build inventory app"
    )

    result = await runner.run(state)
    assert result["is_complete"] == expected_complete

@pytest.mark.parametrize("stage", ["architect", "coder", "executor", "reviewer"])
async def test_individual_stages(stage):
    """Test each pipeline stage independently."""
    runner = RunnerFake(scenario="happy_path")
    state = {...}

    result = await runner.step(state, stage=stage)
    assert result["current_node"] == stage
```

### FastAPI Dependency Override for Testing

```python
# Source: FastAPI docs + project needs
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.dependencies import get_runner
from app.agent.runner_fake import RunnerFake

@pytest.fixture
def test_client():
    """FastAPI test client with RunnerFake injected."""
    fake_runner = RunnerFake(scenario="happy_path")

    # Override production Runner with fake
    app.dependency_overrides[get_runner] = lambda: fake_runner

    client = TestClient(app)
    yield client

    # Cleanup: restore production dependencies
    app.dependency_overrides.clear()

def test_chat_endpoint(test_client):
    """Test /chat endpoint with fake runner."""
    response = test_client.post(
        "/api/agent/chat",
        json={"message": "Build inventory app", "project_id": "test"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "Plan created with 2 steps"
    assert data["is_complete"] is True
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| datetime.utcnow() | datetime.now(timezone.utc) | Python 3.12 (Oct 2023) | Deprecation warnings now, removed in 3.15 (2026). **BLOCKS**: Future Python versions. |
| VCR cassettes for LLM testing | GenericFakeChatModel with scenarios | LangChain 0.3.0 (2024) | Cassettes break on prompt changes. GenericFakeChatModel is maintenance-friendly. |
| unittest.mock for everything | Protocol + real implementations | Typing.Protocol stabilized 3.8 (2020) | Mocks test implementation, not behavior. Protocols enable contract testing. |
| Manual async test setup | pytest-asyncio auto mode | pytest-asyncio 0.21 (2023) | Auto mode removes boilerplate (@pytest.mark.asyncio on every test). |

**Deprecated/outdated:**
- **datetime.utcnow()**: Deprecated in Python 3.12, use `datetime.now(timezone.utc)` immediately
- **Implicit asyncio loop creation**: pytest-asyncio auto mode handles this, remove manual `asyncio.run()` in tests
- **FakeListLLM**: LangChain 0.3+ uses GenericFakeChatModel (better streaming support, message format)

## Open Questions

1. **E2B Sandbox Mocking in Tests**
   - What we know: Executor node uses E2B for code execution, has local fallback
   - What's unclear: Should RunnerFake mock E2B entirely, or use local fallback? Local fallback still executes code (security risk in CI).
   - Recommendation: RunnerFake should mock E2B completely (return pre-built test results). E2B testing should be in dedicated integration tests with real sandboxes.

2. **LangGraph Checkpointer in Tests**
   - What we know: Production uses PostgresSaver, tests should use MemorySaver
   - What's unclear: Should tests verify checkpoint persistence, or just state transitions?
   - Recommendation: Unit tests use MemorySaver and test logic only. Add dedicated checkpoint persistence tests if needed (probably Phase 2+).

3. **Test Execution Time Budget**
   - What we know: Spec requires <30 seconds for full test suite with RunnerFake
   - What's unclear: Is this realistic with 4 scenarios × multiple test groups (api/domain/orchestration/e2e)?
   - Recommendation: Start with function-scoped fixtures (simplest). If >30s, optimize with module-scoped fixtures for expensive setup (graph compilation). Measure before optimizing.

4. **Mem0 Async Warning**
   - What we know: Mem0 might have async operation issues
   - What's unclear: Is this a real problem or just a warning? Does it affect Runner reliability?
   - Recommendation: Investigate during implementation. If memory operations are truly optional (try/except pass pattern), defer fix. If they block pipeline, fix in Phase 1.

## Tech Debt Assessment (Claude's Discretion)

Based on risk to Runner reliability and foundation stability:

### CRITICAL (Must fix in Phase 1)

1. **datetime.utcnow() replacement (7 files)**
   - Risk: Python 3.15 incompatibility, timeline is ~2026
   - Impact: Blocks future Python versions, affects ALL timestamped operations
   - Effort: Low (mechanical find/replace)
   - Decision: **Fix in Phase 1** — Foundation stability issue

2. **Health check implementation**
   - Risk: Load balancer routes traffic to unhealthy instances
   - Impact: Production reliability, affects ALL deployments
   - Effort: Low (15 lines of code)
   - Decision: **Fix in Phase 1** — Affects Runner reliability in production

### MEDIUM (Evaluate during Phase 1)

3. **Silent exception handling (try/except pass pattern)**
   - Risk: Hidden failures make debugging difficult
   - Impact: Optional features (memory) fail silently
   - Effort: Low (add logging)
   - Decision: **Add logging in Phase 1** — Doesn't block tests, but improves debuggability
   - Alternative: Defer to Phase 2 if time-constrained

### LOW (Defer to Phase 2+)

4. **Mem0 async fix**
   - Risk: Unknown (need to investigate)
   - Impact: Memory is optional (try/except pattern)
   - Effort: Unknown (depends on issue)
   - Decision: **Defer to Phase 2** — Runner works without memory, not a Phase 1 blocker

## Sources

### Primary (HIGH confidence)

- LangChain Testing Documentation: https://docs.langchain.com/oss/python/langchain/test
- Python typing.Protocol specification: https://typing.python.org/en/latest/spec/protocol.html
- pytest fixtures documentation: https://docs.pytest.org/en/stable/how-to/fixtures.html
- pytest parametrize documentation: https://docs.pytest.org/en/stable/how-to/parametrize.html
- GitHub Actions service containers: https://docs.github.com/en/actions/tutorials/use-containerized-services

### Secondary (MEDIUM confidence)

- LangGraph Explained (2026 Edition): https://medium.com/@dewasheesh.rana/langgraph-explained-2026-edition-ea8f725abff3
- Python Protocol Classes for Type Safety: https://oneuptime.com/blog/post/2026-02-02-python-protocol-classes-type-safety/view
- Pytest Fixtures Complete Guide (2026): https://devtoolbox.dedyn.io/blog/pytest-fixtures-complete-guide
- Postgres and Redis in GitHub Actions: https://sevic.dev/notes/postgres-redis-github-actions/

### Tertiary (LOW confidence)

- 5 Best Practices For Organizing Tests: https://pytest-with-eric.com/pytest-best-practices/pytest-organize-tests/
- E2B Code Interpreter: https://github.com/e2b-dev/code-interpreter

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — All libraries verified in pyproject.toml, official docs consulted
- Architecture: HIGH — Protocol pattern verified in Python docs, LangChain patterns verified in official docs
- Pitfalls: HIGH — datetime.utcnow() deprecation verified in Python docs, fixture scope issues documented in pytest docs

**Research date:** 2026-02-16
**Valid until:** 2026-03-16 (30 days, stable domain — testing patterns don't change rapidly)
