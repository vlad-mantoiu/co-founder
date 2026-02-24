# Architecture Research

**Domain:** Autonomous Claude Agent replacing LangGraph in AI Co-Founder SaaS (v0.7)
**Researched:** 2026-02-24
**Confidence:** HIGH — based on direct codebase analysis of all integration points + verified Anthropic SDK docs

---

## System Overview

### Current Architecture (v0.6, being replaced)

```
Browser (Next.js)
  |
  +-- GET /api/jobs/{id}/events/stream  (SSE, Redis Pub/Sub)
  +-- GET /api/generation/{id}/status  (5s poll)
                    |
              FastAPI Backend
                    |
              BackgroundTask: process_next_job(runner=RunnerReal)
                    |
              GenerationService.execute_build()
              +-- runner.run(agent_state)        <- LangGraph 6-node pipeline
              +-- sandbox.start()                <- E2B create
              +-- sandbox.write_file()            <- write generated files
              +-- sandbox.start_dev_server()      <- npm install + run
              +-- returns preview_url
                    |
              Redis (job:{id} hash, job:{id}:events Pub/Sub)
              Postgres (jobs table — terminal state persist)
              E2B Cloud (sandbox)
```

### Target Architecture (v0.7)

```
┌────────────────────────────────────────────────────────────────────┐
│                  Next.js Frontend (existing, unchanged)             │
│  Activity Feed | Build Canvas | Preview                            │
│  SSE: GET /api/jobs/{id}/events/stream  (same channel, new events) │
└────────────────────────────┬───────────────────────────────────────┘
                             │ HTTPS / SSE
┌────────────────────────────▼───────────────────────────────────────┐
│                   FastAPI Backend (port 8000, existing)             │
├────────────────────────────────────────────────────────────────────┤
│  POST /api/generation/start  (unchanged — enqueue + BG task)        │
│  GET  /api/jobs/{id}/events/stream  (unchanged — Redis Pub/Sub SSE) │
│  POST /api/agent/{id}/wake  (NEW — resume sleeping agent)           │
├────────────────────────────────────────────────────────────────────┤
│  ┌────────────────────────────────────────────────────────────┐    │
│  │         AutonomousRunner  (replaces RunnerReal)             │    │
│  │  Implements Runner Protocol (all 13 methods preserved)      │    │
│  │  + run_agent_loop(system_prompt, initial_message)           │    │
│  │  Uses native anthropic.AsyncAnthropic (NOT LangChain)      │    │
│  │  Tool dispatch: E2BToolDispatcher (7 tools)                 │    │
│  │  Budget checkpoint: TokenBudgetDaemon.checkpoint()          │    │
│  └──────────────┬─────────────────────────────────────────────┘    │
│                 │                                                   │
│  ┌──────────────▼─────────────────────────────────────────────┐    │
│  │         E2BToolDispatcher  (app/agent/tools/)               │    │
│  │  Maps Claude tool_use blocks → E2BSandboxRuntime methods    │    │
│  │  Tools: read_file, write_file, edit_file, bash,             │    │
│  │         grep, glob, take_screenshot                         │    │
│  │  Publishes agent.tool.called/result SSE events              │    │
│  └──────────────┬─────────────────────────────────────────────┘    │
│                 │                                                   │
│  ┌──────────────▼─────────────────────────────────────────────┐    │
│  │         TokenBudgetDaemon  (app/agent/daemon.py)            │    │
│  │  asyncio.Event — suspends loop when daily budget consumed   │    │
│  │  Reads cofounder:usage:{user_id}:{today} from Redis         │    │
│  │  agent_state: "active" | "sleeping" | "waiting_founder"     │    │
│  │  Wakes on POST /api/agent/{id}/wake or midnight auto-reset  │    │
│  └──────────────┬─────────────────────────────────────────────┘    │
└─────────────────┼──────────────────────────────────────────────────┘
                  │
┌─────────────────▼──────────────────────────────────────────────────┐
│                    Infrastructure (all existing)                     │
├──────────────────┬─────────────────────────────────────────────────┤
│  PostgreSQL       │  jobs table, usage_logs, plan_tiers              │
│  Redis            │  job:{id}:events Pub/Sub, usage counters         │
│  E2B Cloud        │  AsyncSandbox.create() / .connect() / .commands  │
│  S3 + CloudFront  │  Screenshots, build log archives                 │
└──────────────────┴─────────────────────────────────────────────────┘
```

---

## Component Boundaries: New vs Modified vs Deleted

### New Components (build from scratch)

| Component | Path | Purpose |
|-----------|------|---------|
| `AutonomousRunner` | `app/agent/autonomous_runner.py` | Runner protocol impl; replaces RunnerReal for agentic builds |
| `TokenBudgetDaemon` | `app/agent/daemon.py` | Sleep/wake lifecycle; budget checkpoint per API call |
| `AgentStateStore` | `app/agent/agent_state_store.py` | Persists message history to Postgres for resume after sleep |
| `E2BToolDispatcher` | `app/agent/tools/e2b_tools.py` | Tool dispatch to E2B sandbox methods |
| `ToolSchemas` | `app/agent/tools/schemas.py` | Claude tool JSON schemas for all 7 tools |
| `ScreenshotTool` | `app/agent/tools/screenshot_tool.py` | take_screenshot → S3 upload + SSE snapshot.updated event |
| Wake endpoint | `app/api/routes/agent.py` | POST /api/agent/{job_id}/wake — signals daemon to resume |

### Modified Components (extend existing)

| Component | Change |
|-----------|--------|
| `Runner` protocol (`runner.py`) | Add `run_agent_loop(system_prompt, initial_message)` method signature |
| `RunnerFake` (`runner_fake.py`) | Add stub `run_agent_loop()` that returns immediately (for tests) |
| `GenerationService` | Call `runner.run_agent_loop()` instead of `runner.run()` in `execute_build()` |
| `JobStateMachine` | Add new `SSEEventType` constants for agent events; keep existing ones |
| `llm_config.py` | Add `resolve_model_for_tier(tier)` → model string (Opus/Sonnet); keep `create_tracked_llm()` |
| `PlanTier` DB model | Add `monthly_token_budget: int` field for daemon initialization |
| `job:{id}` Redis hash | Add `agent_state` field: `"active" \| "sleeping" \| "waiting_founder"` |

### Deleted After AutonomousRunner Stable

| Component | Notes |
|-----------|-------|
| `RunnerReal` | Remove after v0.7 integration tests pass |
| `app/agent/graph.py` | LangGraph graph definition |
| `app/agent/llm_helpers.py` | LangChain helpers |
| `app/agent/nodes/` (6 files) | architect, coder, executor, debugger, reviewer, git_manager |
| `NarrationService` | Agent handles narration natively via text output |
| `DocGenerationService` | Agent handles docs natively via write_file tool |
| `langchain-anthropic` dep | Remove from requirements after LangGraph removed |

---

## Architectural Patterns

### Pattern 1: Agentic Loop with Native Anthropic SDK Streaming

**What:** Use `anthropic.AsyncAnthropic` directly (not LangChain). The loop calls `client.messages.stream()` as an async context manager, streams text deltas to SSE, accumulates the full message, dispatches tool calls, then loops until `stop_reason == "end_turn"`.

**Why not `client.beta.messages.tool_runner()`:** The beta tool runner hides the loop internals — no ability to publish SSE events between tool calls, no budget checkpoint per iteration, no way to suspend mid-loop for the sleep/wake daemon. The SSE stream would go dark for the entire build duration.

**Example (core agentic loop):**
```python
# app/agent/autonomous_runner.py

import anthropic
from app.agent.tools.schemas import TOOL_SCHEMAS
from app.agent.tools.e2b_tools import E2BToolDispatcher

class AutonomousRunner:
    def __init__(
        self,
        model: str,
        sandbox: E2BSandboxRuntime,
        streamer: LogStreamer,
        state_machine: JobStateMachine,
        job_id: str,
        budget_daemon: TokenBudgetDaemon,
    ):
        self._client = anthropic.AsyncAnthropic()
        self._model = model
        self._dispatcher = E2BToolDispatcher(sandbox, streamer, state_machine, job_id)
        self._budget = budget_daemon
        self._messages: list[dict] = []
        self._streamer = streamer
        self._state_machine = state_machine
        self._job_id = job_id

    async def run_agent_loop(self, system_prompt: str, initial_message: str) -> None:
        self._messages = [{"role": "user", "content": initial_message}]

        while True:
            # Suspend here if daily budget exhausted — resumes on wake signal
            await self._budget.checkpoint()

            async with self._client.messages.stream(
                model=self._model,
                max_tokens=8192,
                system=system_prompt,
                tools=TOOL_SCHEMAS,
                messages=self._messages,
            ) as stream:
                # Stream text deltas to SSE in real time
                async for event in stream:
                    if (
                        event.type == "content_block_delta"
                        and event.delta.type == "text_delta"
                    ):
                        await self._streamer.write_event(
                            event.delta.text, source="agent"
                        )
                        # Also publish typed SSE event for activity feed
                        await self._state_machine.publish_event(self._job_id, {
                            "type": "agent.thinking",
                            "text": event.delta.text,
                        })

                full_message = await stream.get_final_message()

            # Accumulate token usage against daily budget
            await self._budget.record_tokens(
                full_message.usage.input_tokens + full_message.usage.output_tokens
            )

            # No tool calls — agent has completed its work
            if full_message.stop_reason == "end_turn":
                self._messages.append(
                    {"role": "assistant", "content": full_message.content}
                )
                break

            # Dispatch all tool calls in this response
            self._messages.append(
                {"role": "assistant", "content": full_message.content}
            )
            tool_results = []
            for block in full_message.content:
                if block.type == "tool_use":
                    result = await self._dispatcher.dispatch(block.name, block.input)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result,
                    })

            self._messages.append({"role": "user", "content": tool_results})
```

### Pattern 2: E2B Operations as Claude Tool Schemas

**What:** Each `E2BSandboxRuntime` method becomes a JSON schema Claude uses as a tool. `E2BToolDispatcher` maps tool names to async sandbox calls. The 7-tool surface (read, write, edit, bash, grep, glob, screenshot) covers all build operations.

**Boundary:** Sandbox lifecycle (start, pause, kill) is NOT exposed as agent tools — it is owned by `GenerationService` and the worker. The agent only operates on files and commands inside the running sandbox.

**Example (tool schemas):**
```python
# app/agent/tools/schemas.py
TOOL_SCHEMAS = [
    {
        "name": "read_file",
        "description": "Read file content from the sandbox.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Absolute sandbox path, e.g. /home/user/project/src/index.ts"}
            },
            "required": ["path"]
        }
    },
    {
        "name": "write_file",
        "description": "Write content to a file. Creates parent directories.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "content": {"type": "string"}
            },
            "required": ["path", "content"]
        }
    },
    {
        "name": "edit_file",
        "description": "Apply a targeted patch to an existing file. Replaces old_string with new_string (first occurrence).",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "old_string": {"type": "string"},
                "new_string": {"type": "string"}
            },
            "required": ["path", "old_string", "new_string"]
        }
    },
    {
        "name": "bash",
        "description": "Run a shell command in the sandbox. Returns stdout, stderr, exit_code.",
        "input_schema": {
            "type": "object",
            "properties": {
                "command": {"type": "string"},
                "cwd": {"type": "string", "default": "/home/user/project"},
                "timeout": {"type": "integer", "default": 120}
            },
            "required": ["command"]
        }
    },
    {
        "name": "grep",
        "description": "Search file contents with a regex. Returns matching lines with paths.",
        "input_schema": {
            "type": "object",
            "properties": {
                "pattern": {"type": "string"},
                "path": {"type": "string", "default": "/home/user/project"},
                "include": {"type": "string", "description": "Glob filter e.g. '*.ts'"}
            },
            "required": ["pattern"]
        }
    },
    {
        "name": "glob",
        "description": "List files matching a glob pattern in the sandbox.",
        "input_schema": {
            "type": "object",
            "properties": {
                "pattern": {"type": "string", "description": "e.g. '/home/user/project/src/**/*.ts'"}
            },
            "required": ["pattern"]
        }
    },
    {
        "name": "take_screenshot",
        "description": "Capture a screenshot of the running preview. Uploads to S3, returns URL.",
        "input_schema": {
            "type": "object",
            "properties": {
                "stage": {"type": "string", "description": "Label for this checkpoint, e.g. 'after_auth_flow'"}
            },
            "required": ["stage"]
        }
    }
]
```

**Example (dispatcher):**
```python
# app/agent/tools/e2b_tools.py
import json

class E2BToolDispatcher:
    def __init__(
        self,
        sandbox: E2BSandboxRuntime,
        streamer: LogStreamer,
        state_machine: JobStateMachine,
        job_id: str,
    ):
        self._sandbox = sandbox
        self._streamer = streamer
        self._state_machine = state_machine
        self._job_id = job_id

    async def dispatch(self, tool_name: str, tool_input: dict) -> str:
        # Publish verbose-mode SSE event before every tool call
        await self._state_machine.publish_event(self._job_id, {
            "type": "agent.tool.called",
            "tool": tool_name,
            "input": tool_input,
        })
        result = await self._execute(tool_name, tool_input)
        await self._state_machine.publish_event(self._job_id, {
            "type": "agent.tool.result",
            "tool": tool_name,
            "result_preview": str(result)[:200],
        })
        return result

    async def _execute(self, tool_name: str, tool_input: dict) -> str:
        match tool_name:
            case "read_file":
                return await self._sandbox.read_file(tool_input["path"])
            case "write_file":
                await self._sandbox.write_file(tool_input["path"], tool_input["content"])
                return json.dumps({"ok": True, "path": tool_input["path"]})
            case "edit_file":
                content = await self._sandbox.read_file(tool_input["path"])
                if tool_input["old_string"] not in content:
                    return json.dumps({"error": f"old_string not found in {tool_input['path']}"})
                updated = content.replace(tool_input["old_string"], tool_input["new_string"], 1)
                await self._sandbox.write_file(tool_input["path"], updated)
                return json.dumps({"ok": True})
            case "bash":
                result = await self._sandbox.run_command(
                    tool_input["command"],
                    cwd=tool_input.get("cwd", "/home/user/project"),
                    timeout=tool_input.get("timeout", 120),
                    on_stdout=self._streamer.on_stdout,
                    on_stderr=self._streamer.on_stderr,
                )
                return json.dumps(result)
            case "grep":
                include = tool_input.get("include", "*")
                path = tool_input.get("path", "/home/user/project")
                result = await self._sandbox.run_command(
                    f"grep -rn --include='{include}' {repr(tool_input['pattern'])} {path}",
                    timeout=30,
                )
                return result["stdout"][:10000]
            case "glob":
                result = await self._sandbox.run_command(
                    f"find /home/user/project -name '{tool_input['pattern']}' -type f",
                    timeout=15,
                )
                return result["stdout"]
            case "take_screenshot":
                from app.agent.tools.screenshot_tool import take_and_upload_screenshot
                url = await take_and_upload_screenshot(
                    sandbox=self._sandbox,
                    job_id=self._job_id,
                    stage=tool_input["stage"],
                    state_machine=self._state_machine,
                )
                return json.dumps({"screenshot_url": url})
            case _:
                return json.dumps({"error": f"Unknown tool: {tool_name}"})
```

### Pattern 3: Token Budget Daemon with Sleep/Wake

**What:** `TokenBudgetDaemon` runs as a collaborator to the agentic loop. Before every API call, the loop calls `await budget.checkpoint()`. If the daily allowance is consumed, the daemon suspends the loop via `asyncio.Event.clear()`, writes `agent_state=sleeping` to Redis, and publishes an SSE event. The loop resumes when `asyncio.Event.set()` is called — either by the wake endpoint or the midnight auto-reset coroutine.

**Daemon lifecycle:** The daemon is instantiated in `GenerationService.execute_build()` and passed to `AutonomousRunner`. It does not run as a separate process — it runs in the same asyncio event loop as the background task.

**Wake endpoint challenge:** The FastAPI wake endpoint (`POST /api/agent/{id}/wake`) must reach the daemon's `asyncio.Event` object. Since the daemon lives inside a BackgroundTask in the same process, store it in `app.state.active_daemons[job_id]` during build and remove it on completion.

**Example:**
```python
# app/agent/daemon.py
import asyncio
from datetime import UTC, datetime

class TokenBudgetDaemon:
    """Paces agent token consumption across the subscription window.

    Budget: daily_allowance = (monthly_budget - window_tokens_used) / days_until_renewal
    Checkpoint: called before every API request. Blocks if allowance exhausted.
    """

    def __init__(self, user_id: str, job_id: str, redis, daily_token_allowance: int):
        self._user_id = user_id
        self._job_id = job_id
        self._redis = redis
        self._daily_allowance = daily_token_allowance
        self._tokens_today = 0
        self._wake_event = asyncio.Event()
        self._wake_event.set()  # Start awake

    async def checkpoint(self) -> None:
        """Block the loop if daily budget is exhausted. Resumes on wake()."""
        # Sync token count from Redis (UsageTrackingCallback writes there)
        today = datetime.now(UTC).date().isoformat()
        raw = await self._redis.get(f"cofounder:usage:{self._user_id}:{today}")
        self._tokens_today = int(raw) if raw else self._tokens_today

        if self._tokens_today >= self._daily_allowance:
            await self._sleep()
            await self._wake_event.wait()  # Blocks here until wake()

    async def record_tokens(self, tokens: int) -> None:
        """Record tokens consumed by one API call."""
        self._tokens_today += tokens

    async def _sleep(self) -> None:
        self._wake_event.clear()
        await self._redis.hset(f"job:{self._job_id}", "agent_state", "sleeping")
        await self._redis.publish(
            f"job:{self._job_id}:events",
            '{"type": "agent.sleeping", "reason": "daily_budget_exhausted"}'
        )

    def wake(self) -> None:
        """Called by the wake endpoint or midnight reset coroutine."""
        self._wake_event.set()
        # Caller also hsets agent_state=active and publishes agent.waking event
```

**Wake endpoint:**
```python
# app/api/routes/agent.py
@router.post("/{job_id}/wake")
async def wake_agent(
    job_id: str,
    request: Request,
    user: ClerkUser = Depends(require_auth),
    redis=Depends(get_redis),
):
    """Resume a sleeping agent — resets daily budget window for a new day."""
    # Verify ownership
    state_machine = JobStateMachine(redis)
    job_data = await state_machine.get_job(job_id)
    if not job_data or job_data.get("user_id") != user.user_id:
        raise HTTPException(status_code=404, detail="Job not found")

    daemon = getattr(request.app.state, "active_daemons", {}).get(job_id)
    if daemon is None:
        raise HTTPException(status_code=409, detail="No active agent for this job")

    daemon.wake()
    await redis.hset(f"job:{job_id}", "agent_state", "active")
    await redis.publish(f"job:{job_id}:events", '{"type": "agent.waking"}')
    return {"status": "woken"}
```

### Pattern 4: Runner Protocol Evolution

**What:** The existing `Runner` Protocol has 13 methods used by `GateService`, tests, and the generation pipeline. `AutonomousRunner` implements all 13 (using direct Anthropic SDK calls, not LangChain) plus the new `run_agent_loop()`. The `run()` method on `AutonomousRunner` becomes a thin adapter that sets up the sandbox and calls `run_agent_loop()`.

**Migration path:**
1. Add `run_agent_loop()` to `Runner` protocol with `...` stub (non-breaking — existing impls don't need it until called)
2. Implement `AutonomousRunner` with all 13 methods + `run_agent_loop()`
3. `GenerationService.execute_build()` calls `runner.run_agent_loop()` — new call site, not replacing existing `runner.run()`
4. Keep `RunnerReal` and LangGraph until `AutonomousRunner` passes all integration tests
5. Switch `_get_runner()` in `generation.py` to return `AutonomousRunner` when `AUTONOMOUS_AGENT=true` env var set
6. Remove `RunnerReal`, `graph.py`, `nodes/`, in cleanup phase

### Pattern 5: SSE Event Schema Evolution (Additive)

**What:** New event types added to the existing `job:{id}:events` Pub/Sub channel. Existing events (`build.stage.started`, `snapshot.updated`, `documentation.updated`) continue unchanged. Frontend consumers ignore unknown event types — safe to add.

**New SSEEventType constants:**
```python
class SSEEventType:
    # Existing — keep unchanged
    BUILD_STAGE_STARTED = "build.stage.started"
    BUILD_STAGE_COMPLETED = "build.stage.completed"
    SNAPSHOT_UPDATED = "snapshot.updated"
    DOCUMENTATION_UPDATED = "documentation.updated"

    # New for autonomous agent (v0.7)
    AGENT_THINKING = "agent.thinking"          # text delta from Claude (activity feed default)
    AGENT_TOOL_CALLED = "agent.tool.called"    # verbose mode: tool name + input
    AGENT_TOOL_RESULT = "agent.tool.result"    # verbose mode: tool result preview
    AGENT_SLEEPING = "agent.sleeping"          # budget exhausted, loop suspended
    AGENT_WAKING = "agent.waking"              # budget refreshed, loop resumed
    AGENT_WAITING_FOUNDER = "agent.waiting_founder"  # escalated — needs decision
    GSD_PHASE_STARTED = "gsd.phase.started"    # Kanban timeline: new phase begun
    GSD_PHASE_COMPLETED = "gsd.phase.completed"  # Kanban timeline: phase done
```

**Frontend activity feed:** Default view shows `agent.thinking` text (plain phase summaries). Verbose toggle additionally shows `agent.tool.called` and `agent.tool.result`. This directly satisfies the PROJECT.md "Activity feed with verbose toggle" requirement.

---

## Data Flow

### Full Agentic Build Flow (v0.7)

```
Founder clicks "Build"
    ↓
POST /api/generation/start
    ↓
JobStateMachine.create_job()  →  job:{id} hash (status=QUEUED) in Redis
QueueManager.enqueue(job_id, tier)
BackgroundTasks.add_task(process_next_job, runner=AutonomousRunner)
    ↓
process_next_job() [FastAPI background task, same asyncio event loop]
    ├── Acquire user_semaphore + project_semaphore (existing)
    └── GenerationService.execute_build(job_id, job_data, state_machine)
            │
            ├── STARTING: state_machine.transition() → Redis Pub/Sub event
            │
            ├── E2BSandboxRuntime.start()  → creates fresh sandbox
            ├── E2BSandboxRuntime.set_timeout(3600)
            │
            ├── Compute daily_token_allowance:
            │     query PlanTier.monthly_token_budget
            │     query UsageLog: tokens_used_this_window
            │     query PlanTier.renewal_date
            │     daily_allowance = remaining / days_until_renewal
            │
            ├── TokenBudgetDaemon(user_id, job_id, redis, daily_allowance)
            ├── app.state.active_daemons[job_id] = daemon
            │
            ├── AutonomousRunner(model, sandbox, streamer, state_machine, daemon)
            │
            ├── SCAFFOLD: state_machine.transition()  →  SSE: build.stage.started
            │
            ├── AutonomousRunner.run_agent_loop(system_prompt, idea_brief_text)
            │     │
            │     ├── [LOOP ITERATION N]
            │     │
            │     ├── TokenBudgetDaemon.checkpoint()
            │     │     └── If exhausted: await asyncio.Event (suspended here)
            │     │           UI shows "agent.sleeping" state
            │     │           Resumes on POST /api/agent/{id}/wake
            │     │
            │     ├── anthropic.AsyncAnthropic.messages.stream(tools=TOOL_SCHEMAS)
            │     │     ├── text deltas → streamer.write_event() → job:{id}:logs
            │     │     │       also: publish SSE agent.thinking event
            │     │     └── accumulate full_message via get_final_message()
            │     │
            │     ├── TokenBudgetDaemon.record_tokens(usage.input + usage.output)
            │     │
            │     ├── If stop_reason == "end_turn":  break  (agent finished)
            │     │
            │     ├── For each tool_use block in full_message.content:
            │     │     ├── E2BToolDispatcher.dispatch(block.name, block.input)
            │     │     │     ├── publish SSE: agent.tool.called
            │     │     │     ├── call E2BSandboxRuntime method
            │     │     │     └── publish SSE: agent.tool.result
            │     │     └── collect tool_result (JSON string)
            │     │
            │     └── messages.append tool_results; [LOOP ITERATION N+1]
            │
            ├── CODE: state_machine.transition()  → SSE: build.stage.started
            │
            ├── E2BSandboxRuntime.start_dev_server()  → preview_url
            │
            ├── CHECKS: state_machine.transition()
            │
            ├── state_machine.transition(READY)   → SSE: build.stage.started{status:"ready"}
            │
            ├── E2BSandboxRuntime.beta_pause()
            ├── del app.state.active_daemons[job_id]
            └── persist job to Postgres (terminal state)

Frontend SSE consumer (existing GET /api/jobs/{id}/events/stream):
    ├── build.stage.started  →  stage ring + Kanban update
    ├── agent.thinking       →  activity feed text (default view)
    ├── agent.tool.called    →  verbose mode: "Running bash: npm install..."
    ├── agent.tool.result    →  verbose mode: exit_code, truncated output
    ├── agent.sleeping       →  "Agent paused — budget refreshes at midnight"
    ├── gsd.phase.started    →  Kanban column → in_progress
    └── build.stage.started{status:"ready"}  →  build complete state
```

### Token Budget Pacing Flow

```
On build start:
    ├── UsageLog query: SUM(total_tokens) WHERE user_id AND created_at >= window_start
    ├── PlanTier.monthly_token_budget  (e.g., 2_000_000 for bootstrapper)
    ├── tokens_remaining = monthly_budget - window_tokens_used
    ├── days_until_renewal = (renewal_date - today).days  (min 1)
    └── daily_allowance = max(50_000, tokens_remaining / days_until_renewal)

Every agentic loop iteration (before API call):
    ├── TokenBudgetDaemon.checkpoint()
    │     read cofounder:usage:{user_id}:{today} from Redis
    │     compare to daily_allowance
    └── If within budget: proceed with API call

After API call:
    └── TokenBudgetDaemon.record_tokens(input_tokens + output_tokens)
        (UsageTrackingCallback also writes to Redis — daemon syncs on next checkpoint)

When budget exhausted:
    ├── asyncio.Event.clear()  →  loop suspends at await checkpoint()
    ├── Redis: job:{id} hset agent_state = "sleeping"
    └── SSE publish: {"type": "agent.sleeping", "reason": "daily_budget_exhausted"}

On wake (user action or midnight auto-reset):
    ├── daemon.wake()  →  asyncio.Event.set()
    ├── Redis: job:{id} hset agent_state = "active"
    └── SSE publish: {"type": "agent.waking"}
```

### GSD Kanban Phase Recording Flow

```
AutonomousRunner system prompt includes phase reporting instructions.
Agent signals phase transitions via a special "record_gsd_phase" tool
OR via structured markers in its text output that the runner parses.

On phase_start:
    ├── StageEvent INSERT (event_type="gsd_phase_started", detail={phase_name, phase_index})
    └── SSE publish: {"type": "gsd.phase.started", "phase": "planning", "index": 0}

On phase_complete:
    ├── StageEvent INSERT (event_type="gsd_phase_completed", detail={phase_name, duration_ms})
    └── SSE publish: {"type": "gsd.phase.completed", "phase": "planning", "duration_ms": 45000}

Frontend Kanban Timeline:
    Reads gsd.phase.started/completed events from SSE
    Updates column status: queued → in_progress → done
```

### Self-Healing Error Flow (3 retries then escalate)

```
AutonomousRunner detects build failure (bash tool returns non-zero exit_code):
    ├── Retry 1: Modify approach, try again (same loop)
    ├── Retry 2: Different approach (loop continues)
    ├── Retry 3: Different approach (loop continues)
    └── After 3 failures: agent writes a structured explanation and stops
          sets agent_state = "waiting_founder" in Redis
          SSE publish: {"type": "agent.waiting_founder", "reason": "..."}
          Frontend shows: "Your input needed" card with explanation

This pattern is implemented entirely by the agent's system prompt instructions
and the agent's own reasoning — no special loop machinery required.
```

---

## Recommended Project Structure

```
backend/app/agent/
├── runner.py                 # Protocol: add run_agent_loop() signature
├── runner_fake.py            # Keep: add stub run_agent_loop()
├── runner_real.py            # DEPRECATE: keep during transition, remove after
├── autonomous_runner.py      # NEW: AutonomousRunner implements Runner protocol
├── daemon.py                 # NEW: TokenBudgetDaemon — sleep/wake lifecycle
├── agent_state_store.py      # NEW: conversation history persistence
├── tools/
│   ├── __init__.py
│   ├── schemas.py            # NEW: Claude tool JSON schemas (7 tools)
│   ├── e2b_tools.py          # NEW: E2BToolDispatcher
│   └── screenshot_tool.py   # NEW: take_screenshot → S3 + SSE
├── state.py                  # Keep: CoFounderState (used by RunnerFake)
├── graph.py                  # DEPRECATE after v0.7 stable
├── llm_helpers.py            # DEPRECATE after v0.7 stable
├── nodes/                    # DEPRECATE: all 6 node files
└── path_safety.py            # Keep: reuse path validation in tool adapters

backend/app/api/routes/
├── agent.py                  # NEW: POST /api/agent/{id}/wake endpoint
└── ... (existing routes unchanged)
```

---

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| Anthropic API | `anthropic.AsyncAnthropic` (native SDK, NOT LangChain) | Remove `langchain-anthropic` dep after LangGraph removed; keep during transition |
| E2B Cloud | Existing `AsyncSandbox.create()` / `.connect()` / `.commands.run()` | No changes to E2BSandboxRuntime; tools wrap existing methods |
| Redis | Existing `job:{id}:events` Pub/Sub + `agent_state` field in `job:{id}` hash | Add `agent_state` field; new SSEEventType constants are additive |
| PostgreSQL | Existing `UsageLog` table for per-call token tracking | Add `monthly_token_budget` to `PlanTier`; read window usage for daemon init |
| S3 | Existing screenshot upload path from ScreenshotService | `screenshot_tool.py` reuses ScreenshotService S3 logic directly |
| Anthropic API (usage tracking) | Existing `UsageTrackingCallback` writes token counts to Redis daily counter | Daemon reads `cofounder:usage:{user_id}:{today}` — no double-counting |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| AutonomousRunner ↔ E2BToolDispatcher | Direct async call (same process, constructor injection) | Dispatcher does not own sandbox lifecycle |
| AutonomousRunner ↔ TokenBudgetDaemon | `await daemon.checkpoint()` + `daemon.wake()` via asyncio.Event | Both in same asyncio event loop; no queue needed |
| Wake endpoint ↔ TokenBudgetDaemon | `request.app.state.active_daemons[job_id]` registry | Set at build start, del at build end; 404 if no active daemon |
| Worker ↔ SSE frontend | Redis Pub/Sub `job:{id}:events` (unchanged transport) | Only new event types added; existing frontend ignores unknown types |
| GenerationService ↔ AutonomousRunner | Runner Protocol `run_agent_loop()` method | Same DI pattern as current `runner.run()` call |
| AutonomousRunner ↔ LogStreamer | Direct call: `streamer.write_event()`, `streamer.on_stdout/on_stderr` | LogStreamer instance passed to AutonomousRunner constructor |
| AutonomousRunner ↔ JobStateMachine | Direct call: `state_machine.publish_event()` | State machine passed to AutonomousRunner constructor |

---

## Scaling Considerations

| Scale | Architecture Adjustments |
|-------|--------------------------|
| 0-100 concurrent users | FastAPI BackgroundTasks model works. asyncio.Event per daemon in-process. One E2B sandbox per active job. |
| 100-1k users | Move workers out of FastAPI process — asyncio event loop saturation risk from long-running builds. Use dedicated asyncio worker pool or Celery with asyncio executor. Wake endpoint signals via Redis Pub/Sub instead of in-process asyncio.Event. |
| 1k+ users | E2B concurrency limits per org become binding. Multiple worker processes with Redis-based daemon signaling. Anthropic API RPM limits — exponential backoff already implemented via tenacity in RunnerReal; carry forward to AutonomousRunner. |

**First bottleneck:** FastAPI background task loop saturation. A 30-60 minute agentic build blocks the event loop from starting new background tasks. Mitigation for v0.7: run one build per ECS task (scale out horizontally, not vertically). Each task picks one job from the Redis queue. This requires no architecture change — just ECS task count scaling.

**Second bottleneck:** Anthropic API rate limits under parallel agent load. Mitigation: the existing per-user daily token limit enforcement already constrains peak usage. Add a global RPM counter in Redis with leaky bucket for additional safety.

---

## Anti-Patterns

### Anti-Pattern 1: Using `client.beta.messages.tool_runner()` for the Agent Loop

**What people do:** Use the SDK's beta `tool_runner` helper because it handles the agentic loop automatically.

**Why it's wrong:** The tool runner runs the entire loop internally — no opportunity to publish SSE events between tool calls, no budget checkpoint per iteration, no way to suspend on sleep. The SSE activity feed would go dark for the entire 30-60 minute build.

**Do this instead:** Implement the loop manually with `async with client.messages.stream()` so each tool call boundary is observable and checkpointable.

### Anti-Pattern 2: Keeping LangChain for the Autonomous Agent

**What people do:** Use `ChatAnthropic` from `langchain-anthropic` for the new agent, because it's already in the codebase.

**Why it's wrong:** LangChain wraps Anthropic's streaming events and does not expose `input_json_delta` events mid-stream. You lose fine-grained streaming control and cannot intercept tool call parameters as they stream in. The LangChain callback system also adds latency.

**Do this instead:** Use native `anthropic.AsyncAnthropic` for `AutonomousRunner`. Keep `langchain-anthropic` only for the 13 RunnerFake-backed protocol methods during the transition period, then remove it entirely.

### Anti-Pattern 3: Storing Full Conversation History in Redis

**What people do:** Serialize the full `messages` list into a Redis key for persistence across sleep/wake cycles.

**Why it's wrong:** A build that writes 50 files via tool calls accumulates MBs of message history. Each `write_file` tool result includes the file content. Redis is not suited for large blobs and has performance issues above ~1MB per key.

**Do this instead:** Store conversation checkpoints in a new PostgreSQL `AgentCheckpoint` table (`job_id`, `message_index`, `role`, `content_json`, `created_at`). Redis holds only `agent_state` (active/sleeping/waiting_founder), `message_count`, and `tokens_used_today`. On resume after sleep, load checkpoint from Postgres and continue from where the loop suspended.

### Anti-Pattern 4: Exposing Sandbox Lifecycle as Agent Tools

**What people do:** Give the agent a `start_sandbox` or `kill_sandbox` tool so it can manage its own environment.

**Why it's wrong:** The agent could kill its own sandbox mid-build, leaving the job in an unrecoverable state. Sandbox lifecycle is infrastructure owned by `GenerationService` and the worker — not agent responsibility.

**Do this instead:** `GenerationService` creates and destroys the sandbox. The agent only receives tools that operate *within* the running sandbox (read, write, bash, etc.).

### Anti-Pattern 5: Polling Budget Check Inside the Agent Loop

**What people do:** Check a Redis budget key every N iterations rather than before every API call.

**Why it's wrong:** "Every N iterations" means N-1 over-budget API calls happen before the check fires. For Opus at $75/M output tokens, even one extra call can cost $0.60+.

**Do this instead:** `TokenBudgetDaemon.checkpoint()` runs before every single API call. `record_tokens()` runs immediately after. The window between exceeding budget and stopping is exactly one API call (unavoidable — you can't know tokens before the call completes).

### Anti-Pattern 6: Replacing the Runner Protocol Instead of Extending It

**What people do:** Delete the `Runner` protocol and `RunnerFake`, replacing all callers with direct `AutonomousRunner` references.

**Why it's wrong:** `RunnerFake` is used by `GateService` and ~150 existing tests. Removing it breaks the entire test suite and forces simultaneous rewrite of all test fixtures.

**Do this instead:** `AutonomousRunner` implements the existing `Runner` protocol. `RunnerFake` gets a stub `run_agent_loop()`. Only `GenerationService.execute_build()` changes its call site. All other callers are unaffected.

---

## Sources

- Anthropic API Streaming docs: https://platform.claude.com/docs/en/build-with-claude/streaming (verified 2026-02-24, HIGH confidence)
- Anthropic Python SDK: https://github.com/anthropics/anthropic-sdk-python (verified 2026-02-24, HIGH confidence)
- Codebase — `backend/app/agent/runner.py` — Runner protocol, 13 methods (HIGH confidence)
- Codebase — `backend/app/agent/runner_real.py` — LangChain usage patterns to migrate away from (HIGH confidence)
- Codebase — `backend/app/agent/state.py` — CoFounderState schema (HIGH confidence)
- Codebase — `backend/app/sandbox/e2b_runtime.py` — E2B API surface, all available methods (HIGH confidence)
- Codebase — `backend/app/queue/worker.py` — process_next_job orchestration pattern (HIGH confidence)
- Codebase — `backend/app/services/generation_service.py` — execute_build() pipeline stages (HIGH confidence)
- Codebase — `backend/app/services/log_streamer.py` — Redis Stream write pattern (HIGH confidence)
- Codebase — `backend/app/queue/state_machine.py` — SSE Pub/Sub, event types (HIGH confidence)
- Codebase — `backend/app/api/routes/jobs.py` — existing SSE stream endpoint (HIGH confidence)
- Codebase — `backend/app/core/llm_config.py` — token tracking, model resolution (HIGH confidence)

---

*Architecture research for: v0.7 Autonomous Claude Agent replacing LangGraph in AI Co-Founder SaaS*
*Researched: 2026-02-24*
