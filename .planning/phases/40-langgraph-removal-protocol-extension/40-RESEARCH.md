# Phase 40: LangGraph Removal + Protocol Extension - Research

**Researched:** 2026-02-24
**Domain:** Python dependency removal, Protocol extension, Feature flag routing, TDD stub patterns
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Transition behavior:**
- When `AUTONOMOUS_AGENT=true` and AutonomousRunner is a stub: return **501 Not Implemented**
- Frontend catches 501 and shows a **non-blocking "coming soon" banner** in the agent/build area only
- Banner copy: **"Your AI Co-Founder is being built"**
- Banner is **temporary** — removed once AutonomousRunner ships
- Default value: **true** (product is not live, no users to protect)
- The flag is a **migration-only switch** — once autonomous mode works, it's permanently on for all users
- RunnerReal becomes a **minimal non-LangGraph pass-through** (direct Anthropic API call, no streaming — single response OK)
- Once AutonomousRunner is stable: **delete RunnerReal entirely** (no legacy code)
- RunnerReal pass-through behavior: **Claude's discretion**

**Service removal scope:**
- **NarrationService** and **DocGenerationService**: extract to **standalone utilities** (not deleted, preserved for autonomous agent to use)
  - API simplification: Claude's discretion
  - File placement: Claude's discretion
  - Existing tests: **adapt** to match new standalone interface
- **6 LangGraph node files + graph.py**: **delete completely** — TAOR loop is a complete replacement, no behaviors preserved
- **LangGraph/LangChain Python dependencies**: **remove from pyproject.toml** in this phase
- **LangGraph checkpointer** (PostgresSaver/MemorySaver init in main.py): **remove entirely** — Phase 41 implements its own state management
- **generation_service.py** and **generation API routes**: Claude's discretion on what to strip vs delete
- **NOT deleted**: strategy_graph.py, knowledge_graph.py (Neo4j, unrelated to LangGraph)

**Feature flag design:**
- **Simple boolean**: `AUTONOMOUS_AGENT=true` or `false`
- Scope: **build/generation endpoints only** — understanding interview, idea brief, strategy graph unaffected
- Read location: Claude's discretion (startup DI vs per-request)
- No deprecation markers — **just delete the flag later** when no longer needed

**Protocol contract:**
- `run_agent_loop()` input types: **Claude's discretion** (typed dataclass vs raw dict)
- Return shape: **Claude's discretion** (async generator vs final result)
- RunnerFake stub design: **Claude's discretion** (deterministic vs configurable scenarios)
- Lifecycle methods (start/stop/health_check): **Claude's discretion** based on existing Runner protocol

**Branching strategy:**
- All Phase 40 work on branch: **`feature/autonomous-agent-migration`**
- **Single milestone branch** for all v0.7 phases — merge to main only when full milestone is done

### Claude's Discretion

- RunnerReal pass-through behavior (what the minimal direct Anthropic call actually does)
- NarrationService/DocGenerationService API simplification and file placement
- generation_service.py — what to strip vs delete
- Feature flag read location (startup DI vs per-request)
- run_agent_loop() input types and return shape
- RunnerFake stub design (deterministic vs configurable scenarios)
- Lifecycle methods on Runner protocol

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| MIGR-01 | LangGraph/LangChain deps atomically removed — all 6 node files, graph.py deleted; NarrationService/DocGenerationService extracted to standalone utilities | LangGraph import sites fully mapped; removal checklist below |
| MIGR-02 | Feature flag (AUTONOMOUS_AGENT env var) toggles between RunnerReal and AutonomousRunner for build/generation endpoints only | Settings pattern identified; existing flag infrastructure reusable |
| MIGR-03 | Runner protocol extended with run_agent_loop(); RunnerFake stubs it deterministically; AutonomousRunner stub returns 501 | Protocol extension pattern identified; existing test infrastructure ready |
</phase_requirements>

---

## Summary

Phase 40 is a surgical removal and extension operation with no new business logic. The scope is fully bounded: remove LangGraph imports from ~17 files, delete 7 files (6 nodes + graph.py), rewrite RunnerReal as a minimal direct-Anthropic pass-through, add `run_agent_loop()` to the Runner protocol, add a stub AutonomousRunner, and wire an env-var flag to route between them at the build/generation endpoint.

The codebase is well-structured for this operation. The Runner Protocol pattern with RunnerReal/RunnerFake is already established, test infrastructure uses `pytest` with `asyncio_mode = auto`, and all 536 unit tests currently pass. The LangGraph dependency is concentrated in specific files — the removal is discrete and traceable. The critical risk is test breakage: three test files directly import from `app.agent.graph` (which uses LangGraph), and `test_runner_real.py` tests use `SystemMessage`/`HumanMessage` from `langchain_core`.

**Primary recommendation:** Execute in strict TDD order — write tests for the new protocol method and stub first, then delete LangGraph code, then verify the full suite passes. The feature flag should be a Settings field (read once at startup via existing `get_settings()` pattern) for simplicity — no per-request overhead.

---

## Standard Stack

### Core (already installed)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| anthropic | >=0.40.0 | Direct Anthropic API for rewritten RunnerReal | Already in pyproject.toml; NarrationService/DocGenerationService already use it directly |
| pydantic-settings | >=2.6.0 | AUTONOMOUS_AGENT env var via Settings class | Existing pattern in `app/core/config.py` — all env vars go here |
| pytest + pytest-asyncio | >=8.3.0 / >=0.24.0 | TDD test framework | `asyncio_mode = auto`, 803 tests already collected |
| structlog | >=25.0.0 | Logging in new AutonomousRunner stub | Existing pattern throughout |

### To Remove

| Library | Remove From | Impact |
|---------|------------|--------|
| `langgraph>=0.2.0` | pyproject.toml | Deletes graph.py, 6 node files, RunnerReal LangGraph wiring |
| `langgraph-checkpoint-postgres>=2.0.0` | pyproject.toml | Removes AsyncPostgresSaver from main.py lifespan |
| `langchain-anthropic>=0.3.0` | pyproject.toml | Removes from runner_real.py (SystemMessage, HumanMessage) |
| `langchain-core>=0.3.0` | pyproject.toml | Removes from runner_real.py, llm_config.py, all 6 node files |

**Note:** `anthropic>=0.40.0` stays — used by NarrationService, DocGenerationService, and will be used by the rewritten RunnerReal and AutonomousRunner.

---

## Architecture Patterns

### Current LangGraph Dependency Map

All files that import from `langgraph` or `langchain`:

**DELETE (LangGraph-specific):**
- `backend/app/agent/graph.py` — `from langgraph.graph import StateGraph, END` + `from langgraph.checkpoint.memory import MemorySaver`
- `backend/app/agent/nodes/architect.py` — `from langchain_core.messages import HumanMessage, SystemMessage`
- `backend/app/agent/nodes/coder.py` — `from langchain_core.messages import HumanMessage, SystemMessage`
- `backend/app/agent/nodes/debugger.py` — `from langchain_core.messages import HumanMessage, SystemMessage`
- `backend/app/agent/nodes/reviewer.py` — `from langchain_core.messages import HumanMessage, SystemMessage`
- `backend/app/agent/nodes/git_manager.py` — likely same pattern
- `backend/app/agent/nodes/executor.py` — likely same pattern

**REWRITE (keep file, remove LangGraph imports):**
- `backend/app/agent/runner_real.py` — imports `from langchain_core.messages import HumanMessage, SystemMessage` + `from langgraph.checkpoint.memory import MemorySaver` + `from app.agent.graph import create_cofounder_graph` + node imports — ALL removed; replace with direct `anthropic` SDK calls
- `backend/app/core/llm_config.py` — `from langchain_anthropic import ChatAnthropic` + `from langchain_core.callbacks import AsyncCallbackHandler` + `from langchain_core.outputs import LLMResult` — rewrite to use `anthropic.AsyncAnthropic` directly
- `backend/app/main.py` — entire LangGraph checkpointer block (lines 92-127) removed

**KEEP (incidentally mentions LangGraph in comments only):**
- `backend/app/services/narration_service.py` — has comment "NOT LangChain", no actual import
- `backend/app/services/doc_generation_service.py` — has comment "NOT LangChain", no actual import
- `backend/app/services/generation_service.py` — no direct LangGraph import

**Tests to update:**
- `backend/tests/domain/test_agent.py` — imports `from app.agent.graph import create_cofounder_graph`; contains `TestCoFounderGraph` class with graph-structural tests — DELETE the graph tests, keep state tests
- `backend/tests/agent/test_runner_real.py` — tests `SystemMessage`/`HumanMessage` in prompt assertions — rewrite assertions for new direct-Anthropic format
- `backend/tests/api/test_artifact_export.py` — line 228 mentions "LangGraph agents" in fixture data string — update to reflect new architecture

### Pattern 1: Adding run_agent_loop() to Runner Protocol

The existing Runner Protocol in `app/agent/runner.py` is a `@runtime_checkable` Protocol with async methods. Adding a 14th method follows exactly the same pattern:

```python
# Source: app/agent/runner.py (current pattern)
@runtime_checkable
class Runner(Protocol):
    ...
    async def run_agent_loop(self, context: dict) -> dict:
        """Execute the autonomous agent TAOR loop.

        Args:
            context: Dict with project_id, user_id, idea_brief, and execution_plan

        Returns:
            Dict with status, result, and metadata — or raises NotImplementedError
        """
        ...
```

**Consequence:** Any class used as `Runner` via `isinstance()` check must implement `run_agent_loop()`. The existing `test_runner_protocol.py::test_runner_is_runtime_checkable` has a `CompleteRunner` dummy class — it will need `run_agent_loop()` added or that test will fail.

### Pattern 2: RunnerFake stub for run_agent_loop()

RunnerFake follows a scenario-dispatch pattern. The stub for `run_agent_loop()` should match:

```python
async def run_agent_loop(self, context: dict) -> dict:
    """Deterministic stub for TDD. Returns a fixed agent loop result."""
    if self.scenario == "llm_failure":
        raise RuntimeError("Anthropic API rate limit exceeded. Retry after 60 seconds.")
    if self.scenario == "rate_limited":
        raise RuntimeError("Worker capacity exceeded. Estimated wait: 5 minutes. Current queue depth: 12.")
    # happy_path and partial_build
    return {
        "status": "completed",
        "project_id": context.get("project_id", "test-project"),
        "phases_completed": 3,
        "result": "stub: autonomous agent loop completed",
    }
```

### Pattern 3: AutonomousRunner stub (501 behavior)

New file `backend/app/agent/runner_autonomous.py`:

```python
class AutonomousRunner:
    """Autonomous agent runner — stub returning 501 until Phase 41 implements it."""

    async def run(self, state: CoFounderState) -> CoFounderState:
        raise NotImplementedError("AutonomousRunner.run() not yet implemented")

    async def run_agent_loop(self, context: dict) -> dict:
        raise NotImplementedError("AutonomousRunner.run_agent_loop() not yet implemented")

    # ... all 14 Runner protocol methods raise NotImplementedError
```

The caller (generation route or worker) catches `NotImplementedError` and returns HTTP 501.

### Pattern 4: AUTONOMOUS_AGENT Feature Flag

**Read location recommendation:** Settings class (startup DI), not per-request. Rationale: it's a migration switch that never changes during runtime. Per-request reads via `get_settings()` would work but are unnecessary overhead.

Add to `backend/app/core/config.py`:
```python
# Feature flag for autonomous agent migration (Phase 40)
autonomous_agent: bool = True  # env: AUTONOMOUS_AGENT
```

Read in the runner factory function (already exists in generation.py and other routes):
```python
def _build_runner(request: Request) -> Runner:
    """Return AutonomousRunner or RunnerReal based on AUTONOMOUS_AGENT flag."""
    settings = get_settings()
    if settings.autonomous_agent:
        from app.agent.runner_autonomous import AutonomousRunner
        return AutonomousRunner()
    else:
        from app.agent.runner_real import RunnerReal
        return RunnerReal()
```

**Scope confirmation:** This factory is used in:
- `app/api/routes/generation.py` — `_build_runner()` at line 187 (build endpoint)
- `app/api/routes/understanding.py` — separate factory at line 41 (NOT scoped — leave unchanged)
- `app/api/routes/onboarding.py` — separate factory at line 41 (NOT scoped — leave unchanged)
- `app/api/routes/execution_plans.py` — line 29 (NOT scoped — leave unchanged)
- `app/api/routes/change_requests.py` — uses RunnerFake hardcoded (leave unchanged)

Only `generation.py` route factory gets the AUTONOMOUS_AGENT flag. Other routes continue using existing RunnerReal fallback (they handle onboarding/understanding interview, not the build).

### Pattern 5: Frontend 501 Banner

The build page is at `frontend/src/app/(dashboard)/projects/[id]/build/page.tsx`. The `POST /api/generation/start` call is where the 501 is returned. The frontend already handles error states via `setError()`. The banner should be:
- Non-blocking — other navigation remains functional
- In the build area only (PreBuildView component)
- Rendered when `error.status === 501` or response body indicates 501
- Copy: **"Your AI Co-Founder is being built"**

### Pattern 6: Rewriting RunnerReal as Direct Anthropic Pass-Through

RunnerReal currently uses `langchain_core.messages.HumanMessage/SystemMessage` as message wrappers for `llm.ainvoke()`. After removal, use `anthropic.AsyncAnthropic` directly with the messages list format:

```python
# Before (LangChain)
from langchain_core.messages import HumanMessage, SystemMessage
response = await _invoke_with_retry(llm, [SystemMessage(content=...), HumanMessage(content=...)])
text = response.content

# After (direct Anthropic)
import anthropic
client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
message = await client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=4096,
    system=system_content,
    messages=[{"role": "user", "content": human_content}],
)
text = message.content[0].text
```

**Key difference:** `_invoke_with_retry` uses LangChain's `ainvoke()` which expects message objects. After removal, retry logic wraps `client.messages.create()` directly. The `OverloadedError` import changes from `anthropic._exceptions` (already imported this way in `llm_helpers.py`) — no change needed there.

### Pattern 7: Rewriting llm_config.py

`llm_config.py` currently uses `ChatAnthropic` from `langchain_anthropic` and `AsyncCallbackHandler`/`LLMResult` from `langchain_core` for usage tracking. This is the main LangChain usage outside the agent nodes. After removal:

1. Replace `ChatAnthropic` with direct `anthropic.AsyncAnthropic` client
2. Replace LangChain callback handlers with explicit token counting from `anthropic` response `usage` object
3. `create_tracked_llm()` returns an `anthropic.AsyncAnthropic` client (or a thin wrapper that tracks usage)

The `runner_real.py` tests mock `create_tracked_llm` and assert on `ainvoke` calls — these tests will need to be rewritten to mock `anthropic.AsyncAnthropic` directly.

### Pattern 8: NarrationService and DocGenerationService as Standalone Utilities

Both services currently import from `app.queue.state_machine` for SSE event emission. They are already direct-Anthropic callers (no LangGraph). "Standalone utility" means:

- Move to a utility location (e.g., `app/utils/narration.py`, `app/utils/doc_generation.py`) OR keep in `app/services/` but simplify the constructor
- Remove dependency on `JobStateMachine` from their core logic (make it injectable/optional)
- Existing tests in `tests/services/test_narration_service.py` and `tests/services/test_doc_generation_service.py` should adapt to new interface

The existing tests pass 536/536 unit tests — minimal breakage expected since these services use direct Anthropic SDK (not LangGraph).

### Anti-Patterns to Avoid

- **Removing langchain imports from llm_helpers.py first:** `llm_helpers.py` contains `_invoke_with_retry` which takes an `llm` object with `.ainvoke()` — this is LangChain-specific. After removal, this function changes signature or is replaced. Remove LangGraph node dependencies BEFORE touching llm_helpers.
- **Forgetting test fixtures:** `test_runner_real.py` asserts on `SystemMessage` content. If RunnerReal no longer uses SystemMessage, these tests fail with AttributeError, not AssertionError. Rewrite tests before modifying RunnerReal.
- **Breaking onboarding/understanding routes:** The AUTONOMOUS_AGENT flag should ONLY affect `generation.py`. Other routes use RunnerReal for non-build operations (generate_questions, generate_brief, etc.) and must continue working.
- **Protocol isinstance() check failure:** After adding `run_agent_loop()` to Runner protocol, `isinstance(RunnerFake(), Runner)` will return False until RunnerFake implements the method. This will break `test_runner_fake_satisfies_protocol`. Add the method to RunnerFake first.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Env var boolean parsing | Custom parser | pydantic-settings bool field | Already handles `true/false/1/0/yes/no` |
| HTTP 501 response | Custom exception class | `raise HTTPException(status_code=501)` in FastAPI | Standard FastAPI pattern already used everywhere |
| Retry on Anthropic overload | Custom retry loop | tenacity in `llm_helpers._invoke_with_retry` | Already wired; just change what it wraps |
| Direct Anthropic client | Rebuild client init | `anthropic.AsyncAnthropic(api_key=...)` | SDK handles connection pooling, retries config |

---

## Common Pitfalls

### Pitfall 1: Protocol Runtime Check Breaks on Method Addition

**What goes wrong:** Adding `run_agent_loop()` to the Runner Protocol immediately breaks `isinstance(RunnerFake(), Runner)` — Python's `runtime_checkable` requires ALL protocol methods to exist on the concrete class for `isinstance()` to return True.
**Why it happens:** `@runtime_checkable` only checks that methods exist, not signatures. But if the method doesn't exist at all, isinstance returns False.
**How to avoid:** Add `run_agent_loop()` to RunnerFake AND RunnerReal (or the new pass-through RunnerReal) BEFORE adding it to the Protocol class — then add it to Protocol last. In TDD order: write the test, add to Protocol, add to RunnerFake, then tests go green.
**Warning signs:** `test_runner_fake_satisfies_protocol` fails with `AssertionError: assert False` after Protocol change.

### Pitfall 2: llm_config.py ChatAnthropic Dependency is Widespread

**What goes wrong:** `create_tracked_llm()` in `llm_config.py` returns a `ChatAnthropic` instance. Every method in RunnerReal calls `await create_tracked_llm(...)`. After removing langchain_anthropic, all 13 RunnerReal methods break simultaneously.
**Why it happens:** All LangChain message handling is centralized in llm_config.py — removing it breaks all callers at once.
**How to avoid:** Rewrite `create_tracked_llm()` first (to return a native anthropic client), then RunnerReal automatically works. The function signature stays the same; only the return type and internals change.
**Warning signs:** `ImportError: cannot import name 'ChatAnthropic' from 'langchain_anthropic'` on any import of llm_config.

### Pitfall 3: test_agent.py Graph Tests Import LangGraph at Module Level

**What goes wrong:** `tests/domain/test_agent.py` has `from app.agent.graph import create_cofounder_graph` at the top — this import fails at collection time after graph.py is deleted, breaking the entire test module (not just graph tests).
**Why it happens:** Python imports are module-level; any import failure prevents the entire test file from loading.
**How to avoid:** Delete or rewrite test_agent.py BEFORE deleting graph.py. The state tests (`TestCoFounderState`) are valuable and should be kept — only the `TestCoFounderGraph` class and `test_graph_entry_point` function are deleted.
**Warning signs:** `pytest --collect-only` fails with `ImportError` on test_agent.py.

### Pitfall 4: NarrationService Imports DocGenerationService's _SAFETY_PATTERNS

**What goes wrong:** `narration_service.py` imports `from app.services.doc_generation_service import _SAFETY_PATTERNS`. If DocGenerationService is moved to a utility location, this import breaks NarrationService.
**Why it happens:** The two services share a private constant via import (not a clean separation).
**How to avoid:** Either keep both in `app/services/`, or move `_SAFETY_PATTERNS` to a shared constants module and update both imports simultaneously.
**Warning signs:** `ImportError: cannot import name '_SAFETY_PATTERNS' from 'app.services.doc_generation_service'`.

### Pitfall 5: main.py Checkpointer Teardown Still References LangGraph

**What goes wrong:** Even after removing the checkpointer initialization, the teardown block (`app.state._checkpointer_cm.__aexit__`) still runs and tries to close something that was never initialized.
**Why it happens:** The lifespan function has symmetric try/finally blocks — removing the setup without removing the teardown causes AttributeError on shutdown.
**How to avoid:** Remove both the checkpointer initialization block AND the checkpointer teardown block from `lifespan()` in main.py together. Remove `app.state.checkpointer` references in both places.

### Pitfall 6: runner_real.py `run()` and `step()` Still Use graph and nodes After Rewrite

**What goes wrong:** The new RunnerReal (minimal pass-through) no longer has `run()` and `step()` in the traditional sense — the 6-node pipeline is gone. But the Runner Protocol requires these methods.
**Why it happens:** The protocol defines `run()` and `step()` for the old LangGraph graph execution. The new RunnerReal doesn't have a graph.
**How to avoid:** Keep `run()` and `step()` in RunnerReal but have them do a simple direct Anthropic call or just raise `NotImplementedError` (since AUTONOMOUS_AGENT=true routes to AutonomousRunner, RunnerReal is only used in AUTONOMOUS_AGENT=false mode). The "minimal pass-through" behavior for `run()` in RunnerReal can be a direct Anthropic call that generates a build plan response without executing it in E2B — this is throwaway code anyway.

---

## Code Examples

### Adding `run_agent_loop()` to Runner Protocol

```python
# Source: app/agent/runner.py — add after generate_app_architecture()
async def run_agent_loop(self, context: dict) -> dict:
    """Execute the autonomous TAOR agent loop for a build session.

    Args:
        context: Dict with keys:
            - project_id: str
            - user_id: str
            - idea_brief: dict (RationalisedIdeaBrief)
            - execution_plan: dict (selected ExecutionOption)

    Returns:
        Dict with keys: status, project_id, phases_completed, result
    """
    ...
```

### AUTONOMOUS_AGENT Setting in config.py

```python
# Add to class Settings in app/core/config.py
autonomous_agent: bool = True  # env: AUTONOMOUS_AGENT (migration switch for v0.7)
```

### Feature Flag Router in generation.py

```python
# Replace the existing _build_runner function in app/api/routes/generation.py
def _build_runner(request: Request) -> Runner:
    """Return AutonomousRunner or RunnerReal based on AUTONOMOUS_AGENT flag.

    Scope: build/generation endpoints only (generation.py).
    Understanding, onboarding, execution plans use RunnerReal directly.
    """
    settings = get_settings()
    if settings.autonomous_agent:
        from app.agent.runner_autonomous import AutonomousRunner
        return AutonomousRunner()
    else:
        from app.agent.runner_real import RunnerReal
        return RunnerReal()
```

### AutonomousRunner Stub

```python
# New file: app/agent/runner_autonomous.py
"""AutonomousRunner: Stub returning NotImplementedError — Phase 41 implements TAOR loop.

This class satisfies the Runner protocol. All build methods raise NotImplementedError.
The caller (generation route/worker) catches NotImplementedError and returns HTTP 501.
Non-build methods (generate_questions, generate_brief, etc.) delegate to RunnerReal
since AUTONOMOUS_AGENT flag is build-scoped only.
"""
import structlog
from app.agent.state import CoFounderState

logger = structlog.get_logger(__name__)


class AutonomousRunner:
    """Stub runner — placeholder until Phase 41 TAOR implementation."""

    async def run(self, state: CoFounderState) -> CoFounderState:
        raise NotImplementedError("AutonomousRunner.run() not yet implemented — Phase 41")

    async def step(self, state: CoFounderState, stage: str) -> CoFounderState:
        raise NotImplementedError("AutonomousRunner.step() not yet implemented — Phase 41")

    async def run_agent_loop(self, context: dict) -> dict:
        raise NotImplementedError("AutonomousRunner.run_agent_loop() not yet implemented — Phase 41")

    # All 13 other Runner protocol methods also raise NotImplementedError
    # (or delegate to a shared RunnerReal for non-build operations — Claude's discretion)
```

### HTTP 501 in generation route

```python
# In app/api/routes/generation.py POST /start handler
try:
    runner = _build_runner(request)
    # ... enqueue job ...
    background_tasks.add_task(process_next_job, runner=runner, redis=redis)
except NotImplementedError:
    raise HTTPException(
        status_code=501,
        detail="Autonomous agent coming soon. Your AI Co-Founder is being built.",
    )
```

**Alternative (cleaner):** Catch NotImplementedError in the worker's execute_build call and return 501 from there. Since the build is async (background task), returning 501 from the HTTP layer means the client must poll the job status. The cleaner approach is to return 501 immediately from the start endpoint before enqueueing. AutonomousRunner detection can be done at request time (check flag before enqueueing).

### RunnerFake.run_agent_loop() stub

```python
# Add to RunnerFake in app/agent/runner_fake.py
async def run_agent_loop(self, context: dict) -> dict:
    """Deterministic stub for TDD — returns synthetic agent loop result."""
    if self.scenario == "llm_failure":
        raise RuntimeError("Anthropic API rate limit exceeded. Retry after 60 seconds.")
    if self.scenario == "rate_limited":
        raise RuntimeError("Worker capacity exceeded. Estimated wait: 5 minutes. Current queue depth: 12.")
    return {
        "status": "completed",
        "project_id": context.get("project_id", "test-project"),
        "phases_completed": 3,
        "result": "stub: autonomous agent loop completed",
    }
```

### Direct Anthropic client (replacing LangChain in RunnerReal)

```python
# Pattern for new RunnerReal methods (replacing langchain_core.messages pattern)
import anthropic

async def generate_questions(self, context: dict) -> list[dict]:
    client = anthropic.AsyncAnthropic(api_key=get_settings().anthropic_api_key)
    message = await client.messages.create(
        model=get_settings().architect_model,
        max_tokens=2048,
        system=COFOUNDER_SYSTEM.format(task_instructions=task_instructions),
        messages=[{"role": "user", "content": human_content}],
    )
    return _parse_json_response(message.content[0].text)
```

---

## Deletion Checklist (Files to Delete)

| File | Reason |
|------|--------|
| `backend/app/agent/graph.py` | LangGraph StateGraph — replaced by AutonomousRunner TAOR loop in Phase 41 |
| `backend/app/agent/nodes/__init__.py` | Node registry — deleted with all nodes |
| `backend/app/agent/nodes/architect.py` | LangGraph node with langchain_core imports |
| `backend/app/agent/nodes/coder.py` | LangGraph node with langchain_core imports |
| `backend/app/agent/nodes/debugger.py` | LangGraph node with langchain_core imports |
| `backend/app/agent/nodes/executor.py` | LangGraph node with langchain_core imports |
| `backend/app/agent/nodes/reviewer.py` | LangGraph node with langchain_core imports |
| `backend/app/agent/nodes/git_manager.py` | LangGraph node with langchain_core imports |

**Do NOT delete:**
- `backend/app/agent/state.py` — CoFounderState TypedDict used by RunnerFake and protocol
- `backend/app/agent/llm_helpers.py` — `_strip_json_fences`, `_parse_json_response`, `_invoke_with_retry` — rewrite to use native anthropic
- `backend/app/agent/runner.py` — protocol definition (extended with run_agent_loop)
- `backend/app/agent/runner_fake.py` — test double (add run_agent_loop)
- `backend/app/agent/path_safety.py` — used by sandbox tools
- `backend/app/memory/knowledge_graph.py` — Neo4j, unrelated to LangGraph
- `backend/app/db/graph/strategy_graph.py` — Neo4j, unrelated to LangGraph

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.3.0 + pytest-asyncio 0.24.0 |
| Config file | `backend/pyproject.toml` (`[tool.pytest.ini_options]`) |
| Quick run command | `cd backend && python -m pytest tests/ -m unit -x -q` |
| Full suite command | `cd backend && python -m pytest tests/ -q` |
| Estimated runtime | ~5 seconds (unit), ~20 seconds (full suite with integration) |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| MIGR-01 | `import langgraph` raises ImportError | unit (import test) | `pytest tests/agent/test_langgraph_removal.py -x` | Wave 0 gap |
| MIGR-01 | `import langchain` raises ImportError | unit (import test) | `pytest tests/agent/test_langgraph_removal.py -x` | Wave 0 gap |
| MIGR-01 | Full pytest suite passes with no LangGraph references | integration | `pytest tests/ -q` | existing |
| MIGR-01 | NarrationService operates as standalone utility | unit | `pytest tests/services/test_narration_service.py -x` | existing (adapt) |
| MIGR-01 | DocGenerationService operates as standalone utility | unit | `pytest tests/services/test_doc_generation_service.py -x` | existing (adapt) |
| MIGR-02 | `AUTONOMOUS_AGENT=false` routes to RunnerReal behavior | unit | `pytest tests/agent/test_feature_flag_routing.py -x` | Wave 0 gap |
| MIGR-02 | `AUTONOMOUS_AGENT=true` routes to AutonomousRunner stub | unit | `pytest tests/agent/test_feature_flag_routing.py -x` | Wave 0 gap |
| MIGR-02 | `AUTONOMOUS_AGENT=true` returns 501 from /generation/start | unit | `pytest tests/api/test_generation_routes.py -x` | existing (extend) |
| MIGR-03 | `run_agent_loop()` exists in Runner protocol | unit | `pytest tests/domain/test_runner_protocol.py -x` | existing (extend) |
| MIGR-03 | `RunnerFake.run_agent_loop()` returns deterministic stub | unit | `pytest tests/domain/test_runner_fake.py -x` | existing (extend) |
| MIGR-03 | `isinstance(RunnerFake(), Runner)` still True after extension | unit | `pytest tests/domain/test_runner_fake.py::test_runner_fake_satisfies_protocol -x` | existing |
| MIGR-03 | `AutonomousRunner.run_agent_loop()` raises NotImplementedError | unit | `pytest tests/agent/test_autonomous_runner_stub.py -x` | Wave 0 gap |

### Nyquist Sampling Rate

- **Minimum sample interval:** After every committed task → run: `cd backend && python -m pytest tests/ -m unit -x -q`
- **Full suite trigger:** Before merging final task of any plan wave
- **Phase-complete gate:** Full suite green (803+ tests) before phase closes
- **Estimated feedback latency per task:** ~5 seconds

### Wave 0 Gaps (must be created before implementation)

- [ ] `tests/agent/test_langgraph_removal.py` — covers MIGR-01: verify langgraph/langchain produce ImportError
- [ ] `tests/agent/test_feature_flag_routing.py` — covers MIGR-02: flag routes to correct runner
- [ ] `tests/agent/test_autonomous_runner_stub.py` — covers MIGR-03: AutonomousRunner raises NotImplementedError

**Existing tests to extend (not create):**
- `tests/domain/test_runner_protocol.py` — add `run_agent_loop()` to `CompleteRunner` dummy + add method existence test
- `tests/domain/test_runner_fake.py` — add test for `RunnerFake.run_agent_loop()` stub behavior
- `tests/api/test_generation_routes.py` — add test for 501 response when AUTONOMOUS_AGENT=true

**Existing tests to fix/rewrite:**
- `tests/domain/test_agent.py` — delete `TestCoFounderGraph` class and `test_graph_entry_point` (LangGraph-specific); keep `TestCoFounderState` tests
- `tests/agent/test_runner_real.py` — rewrite SystemMessage/HumanMessage assertions to match direct Anthropic format; mock `anthropic.AsyncAnthropic` instead of `create_tracked_llm`

---

## Open Questions

1. **What does RunnerReal.run() do after removal?**
   - What we know: `run()` currently executes the 6-node LangGraph pipeline. After removal, there's no pipeline.
   - What's unclear: The CONTEXT says "minimal pass-through" — but what does `run()` return as CoFounderState? It cannot actually build anything without a sandbox.
   - Recommendation: Have RunnerReal.run() make a single Claude call that produces a mock plan in CoFounderState format. Since AUTONOMOUS_AGENT=true is the default and RunnerReal is only used when false, this path exists only for testing the flag itself. A simple "return state unchanged after one API call" is sufficient.

2. **Does AutonomousRunner need to implement ALL 13 existing Runner protocol methods or just run_agent_loop()?**
   - What we know: The Runner Protocol has 14 methods after Phase 40. The AUTONOMOUS_AGENT flag only scopes to build/generation endpoints. Non-build routes (understanding, onboarding) continue using RunnerReal.
   - What's unclear: If AutonomousRunner is used as a `Runner` via isinstance() check, it needs all 14 methods defined.
   - Recommendation: Implement all 14 methods with NotImplementedError in AutonomousRunner. The isinstance() check in the protocol test requires all methods present. This is cheap to write and avoids protocol compliance failures.

3. **Where exactly does 501 get surfaced to the user?**
   - What we know: The CONTEXT says "non-blocking banner in agent/build area only." The build starts via POST /generation/start.
   - What's unclear: Since the build is async (background task), should the 501 come from the start endpoint itself or from a status poll?
   - Recommendation: Return 501 directly from the start endpoint BEFORE enqueueing — AutonomousRunner is detected at request time (flag check), not during background execution. This gives instant feedback.

---

## Sources

### Primary (HIGH confidence)

- Codebase direct inspection — `backend/app/agent/runner.py`, `runner_real.py`, `runner_fake.py`, `graph.py`, all 6 node files, `main.py`, `config.py`, `llm_config.py`, `narration_service.py`, `doc_generation_service.py`, `generation_service.py`, `worker.py`, all 5 route files with runner factories
- `backend/pyproject.toml` — exact dependency versions confirmed
- `backend/tests/` — all test files inspected for LangGraph references and existing coverage
- `anthropic` SDK docs pattern — confirmed from NarrationService/DocGenerationService existing usage

### Secondary (MEDIUM confidence)

- Python `@runtime_checkable` Protocol behavior — verified against existing `test_runner_protocol.py` which already tests isinstance() behavior

### Tertiary (LOW confidence)

None

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all dependencies confirmed in pyproject.toml; removal list derived from direct grep
- Architecture: HIGH — deletion checklist and import map derived from full codebase inspection
- Pitfalls: HIGH — each pitfall derived from specific observed code patterns, not speculation

**Research date:** 2026-02-24
**Valid until:** Stable — this is a bounded migration with no external library dependencies changing
