---
phase: 40-langgraph-removal-protocol-extension
plan: 03
subsystem: backend/agent-llm
tags: [langgraph-removal, anthropic-sdk, migration, cleanup, runner]
dependency_graph:
  requires: [40-01]
  provides: [LangGraph-free codebase, TrackedAnthropicClient, direct-SDK RunnerReal]
  affects:
    - backend/app/agent/runner_real.py
    - backend/app/agent/llm_helpers.py
    - backend/app/core/llm_config.py
    - backend/app/agent/__init__.py
    - backend/app/api/routes/agent.py
    - backend/app/main.py
    - backend/pyproject.toml
tech_stack:
  added: []
  patterns: [direct anthropic.AsyncAnthropic SDK, TrackedAnthropicClient wrapper, Anthropic message format]
key_files:
  created:
    - backend/tests/agent/test_langgraph_removal.py
  modified:
    - backend/app/core/llm_config.py
    - backend/app/agent/llm_helpers.py
    - backend/app/agent/runner_real.py
    - backend/app/agent/__init__.py
    - backend/app/api/routes/agent.py
    - backend/app/main.py
    - backend/pyproject.toml
    - backend/tests/domain/test_agent.py
    - backend/tests/agent/test_runner_real.py
    - backend/tests/agent/test_llm_retry.py
    - backend/tests/agent/test_local_path_safety.py
    - backend/tests/api/test_artifact_export.py
    - backend/tests/services/test_generation_service.py
  deleted:
    - backend/app/agent/graph.py
    - backend/app/agent/nodes/__init__.py
    - backend/app/agent/nodes/architect.py
    - backend/app/agent/nodes/coder.py
    - backend/app/agent/nodes/debugger.py
    - backend/app/agent/nodes/executor.py
    - backend/app/agent/nodes/reviewer.py
    - backend/app/agent/nodes/git_manager.py
    - backend/tests/agent/nodes/test_architect_node.py
    - backend/tests/agent/nodes/test_coder_node.py
    - backend/tests/agent/nodes/test_executor_node.py
decisions:
  - "TrackedAnthropicClient wraps anthropic.AsyncAnthropic and tracks usage via response.usage (not LangChain callbacks)"
  - "_invoke_with_retry signature changed from (llm, messages) to (client, system, messages, max_tokens=4096)"
  - "agent.py /chat and /chat/stream endpoints stub to 503 until Phase 41 AutonomousRunner replaces them"
  - "Removed langgraph namespace directory remnant from pyenv site-packages (pip uninstall left empty dirs)"
metrics:
  duration: "11 minutes"
  completed: "2026-02-24"
  tasks_completed: 2
  files_modified: 13
  files_created: 1
  files_deleted: 11
---

# Phase 40 Plan 03: LangGraph Removal and Anthropic SDK Migration Summary

All LangGraph and LangChain dependencies atomically removed: 8 files deleted (graph.py + 6 nodes + nodes/__init__.py), llm_config.py rewritten to TrackedAnthropicClient wrapping anthropic.AsyncAnthropic, RunnerReal rewritten to use direct Anthropic message format, main.py checkpointer block removed, 4 dependencies removed from pyproject.toml, all broken tests fixed, full unit suite green at 533 passed.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Delete LangGraph files, rewrite llm_config.py and RunnerReal, clean main.py and pyproject.toml | 0435a7d | graph.py (deleted), nodes/* (deleted), llm_config.py, llm_helpers.py, runner_real.py, main.py, pyproject.toml |
| 2 | Fix broken tests and create LangGraph removal verification tests | e64fc79 | test_langgraph_removal.py (new), test_runner_real.py, test_llm_retry.py, test_agent.py, test_local_path_safety.py, test_artifact_export.py, test_generation_service.py, agent.py routes |

## What Was Built

### llm_config.py — TrackedAnthropicClient

Replaced `ChatAnthropic` + `AsyncCallbackHandler` with `TrackedAnthropicClient`:

```python
class TrackedAnthropicClient:
    def __init__(self, client: anthropic.AsyncAnthropic, model: str, user_id, session_id, role):
        self._client = client
        self.model = model
        self.messages = _TrackedMessages(self)  # proxies create() with usage tracking

class _TrackedMessages:
    async def create(self, **kwargs) -> anthropic.types.Message:
        response = await self._tracked._client.messages.create(**kwargs)
        # Track usage from response.usage.input_tokens / output_tokens
        await self._tracked._track_usage(...)
        return response

async def create_tracked_llm(user_id, role, session_id) -> TrackedAnthropicClient:
    model = await resolve_llm_config(user_id, role)
    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    return TrackedAnthropicClient(client=client, model=model, ...)
```

### llm_helpers.py — New `_invoke_with_retry` Signature

```python
# Old: async def _invoke_with_retry(llm, messages): return await llm.ainvoke(messages)
# New:
async def _invoke_with_retry(client, system: str, messages: list[dict], max_tokens: int = 4096) -> str:
    response = await client.messages.create(
        model=client.model, system=system, messages=messages, max_tokens=max_tokens
    )
    return response.content[0].text
```

Tenacity retry decorator unchanged (still retries `OverloadedError` up to 4 attempts).

### runner_real.py — Direct Anthropic SDK

All methods now use:
- `system = COFOUNDER_SYSTEM.format(...)` (str, not `SystemMessage`)
- `messages = [{"role": "user", "content": "..."}]` (dict, not `HumanMessage`)
- `content = await _invoke_with_retry(client, system, messages)` (returns str)
- `result = _parse_json_response(content)` (unchanged)

Constructor now `RunnerReal()` with no args (no checkpointer).

### main.py — Checkpointer Block Removed

Removed 26-line block that initialized `AsyncPostgresSaver` / `MemorySaver` from `langgraph.checkpoint.postgres.aio`.

### pyproject.toml — 4 Dependencies Removed

```
- langgraph>=0.2.0
- langgraph-checkpoint-postgres>=2.0.0
- langchain-anthropic>=0.3.0
- langchain-core>=0.3.0
```

### agent.py Routes — Stubs for Phase 41

`/chat` and `/chat/stream` return `503 Service Unavailable` with message "Build agent temporarily unavailable — AutonomousRunner implementation in progress (Phase 41)".

### test_langgraph_removal.py — 7 Verification Tests

- `test_langgraph_not_importable` — ImportError on `import langgraph`
- `test_langchain_core_not_importable` — ImportError on `import langchain_core`
- `test_langchain_anthropic_not_importable` — ImportError on `import langchain_anthropic`
- `test_no_langgraph_in_pyproject` — pyproject.toml doesn't mention langgraph
- `test_no_langchain_in_pyproject` — pyproject.toml doesn't mention langchain
- `test_nodes_directory_deleted` — `backend/app/agent/nodes/` doesn't exist
- `test_graph_py_deleted` — `backend/app/agent/graph.py` doesn't exist

## Verification Results

```
tests/agent/test_langgraph_removal.py  — 7 passed
tests/domain/test_agent.py             — 2 passed
tests/agent/test_runner_real.py        — 18 passed
tests/agent/test_llm_retry.py          — 5 passed
Full unit suite: 533 passed, 0 failures
```

Grep verification:
- `grep -rn "langgraph|langchain|ChatAnthropic" app/ --include="*.py"` → 0 matches
- `grep -n "langgraph|langchain" pyproject.toml` → 0 matches
- `ls backend/app/agent/nodes/` → directory does not exist
- `ls backend/app/agent/graph.py` → file does not exist
- `python -c "from app.agent.runner_real import RunnerReal; print('RunnerReal importable')"` → RunnerReal importable

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed app/agent/__init__.py still importing create_cofounder_graph**

- **Found during:** Task 2 (running unit suite — conftest.py import chain hit __init__.py)
- **Issue:** `app/agent/__init__.py` had `from app.agent.graph import create_cofounder_graph` which failed after graph.py was deleted
- **Fix:** Removed the import, `__all__` now only exports `CoFounderState`
- **Files modified:** `backend/app/agent/__init__.py`
- **Commit:** e64fc79

**2. [Rule 1 - Bug] Fixed app/api/routes/agent.py importing from deleted graph module**

- **Found during:** Task 2 (running unit suite — test_artifact_export.py import chain hit routes/__init__.py → agent.py)
- **Issue:** `agent.py` imported `create_cofounder_graph, create_production_graph` and called `graph.ainvoke()` and `graph.astream()`
- **Fix:** Removed graph imports, stubbed `/chat` and `/chat/stream` with 503 responses, kept session management, history, and memory endpoints intact
- **Files modified:** `backend/app/api/routes/agent.py`
- **Commit:** e64fc79

**3. [Rule 1 - Bug] Fixed tests/agent/nodes/ test files importing deleted node modules**

- **Found during:** Task 2 (running unit suite — ImportError on test_architect_node.py)
- **Issue:** `tests/agent/nodes/` contained test files for deleted node implementations
- **Fix:** Deleted the entire `tests/agent/nodes/` directory
- **Files deleted:** `test_architect_node.py`, `test_coder_node.py`, `test_executor_node.py`, `__init__.py`
- **Commit:** e64fc79

**4. [Rule 1 - Bug] Fixed test_local_path_safety.py importing from deleted executor/git_manager nodes**

- **Found during:** Task 2 (running unit suite — ImportError on test_local_path_safety.py)
- **Issue:** File imported `_execute_locally` and `_local_git_operations` from deleted node files
- **Fix:** Removed deleted-node tests, kept valid `resolve_safe_project_path` tests
- **Files modified:** `backend/tests/agent/test_local_path_safety.py`
- **Commit:** e64fc79

**5. [Rule 1 - Bug] Fixed test_generation_service.py importing from deleted architect/coder nodes**

- **Found during:** Task 2 (grepping for remaining node imports in tests)
- **Issue:** Two tests imported `ARCHITECT_SYSTEM_PROMPT` and `CODER_SYSTEM_PROMPT` from deleted node files
- **Fix:** Removed those two test functions
- **Files modified:** `backend/tests/services/test_generation_service.py`
- **Commit:** e64fc79

**6. [Rule 1 - Bug] Fixed test_llm_retry.py using old _invoke_with_retry(llm, messages) signature**

- **Found during:** Task 2 (running unit suite — TypeError on test_success_on_first_try)
- **Issue:** test_llm_retry.py was testing the old LangChain-style `llm.ainvoke(messages)` signature
- **Fix:** Rewrote tests to use new `_invoke_with_retry(client, system, messages)` signature
- **Files modified:** `backend/tests/agent/test_llm_retry.py`
- **Commit:** e64fc79

**7. [Rule 1 - Bug] Uninstalled langgraph packages and removed namespace remnant from pyenv**

- **Found during:** Task 2 (test_langgraph_not_importable failed — packages still installed)
- **Issue:** `pip uninstall` removed langgraph but left empty namespace directories at `/Users/vladcortex/.pyenv/versions/3.12.4/lib/python3.12/site-packages/langgraph/` (cache/, checkpoint/, store/) which allowed `import langgraph` to succeed as a namespace package
- **Fix:** `pip uninstall -y langgraph langgraph-checkpoint-postgres ...` then `rm -rf .../langgraph/`
- **Commit:** Out-of-band (environment change, no code commit needed)

## Self-Check

Files created exist:
- [x] `backend/tests/agent/test_langgraph_removal.py` — 7 tests

Files modified exist:
- [x] `backend/app/core/llm_config.py` — contains `TrackedAnthropicClient`, `AsyncAnthropic`
- [x] `backend/app/agent/llm_helpers.py` — `_invoke_with_retry(client, system, messages)`
- [x] `backend/app/agent/runner_real.py` — no langchain imports, uses direct message dicts
- [x] `backend/app/main.py` — no checkpointer block
- [x] `backend/pyproject.toml` — no langgraph/langchain entries

Files deleted:
- [x] `backend/app/agent/graph.py` — does not exist
- [x] `backend/app/agent/nodes/` — directory does not exist

Commits exist:
- [x] 0435a7d — Task 1: delete LangGraph files, rewrite all core modules
- [x] e64fc79 — Task 2: fix broken tests, add removal verification

## Self-Check: PASSED
