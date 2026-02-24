# Stack Research

**Domain:** Autonomous Claude agent with tool-use, token budgeting, and daemon execution (v0.7 milestone additions only)
**Researched:** 2026-02-24
**Confidence:** HIGH (Anthropic SDK — official docs + PyPI + GitHub releases), MEDIUM (E2B — official docs + PyPI), HIGH (asyncio daemon pattern — stdlib, no external verification needed)

---

## Context: What Exists vs What Changes

The existing stack is validated and ships in production. This document covers only what v0.7 adds or removes.

**Remove (LangGraph replacement):**
- `langgraph>=0.2.0`
- `langgraph-checkpoint-postgres>=2.0.0`
- `langchain-anthropic>=0.3.0`
- `langchain-core>=0.3.0`

**Keep (unchanged):**
- `anthropic>=0.40.0` — already present, bump version only
- `e2b-code-interpreter>=1.0.0` — already present, may swap or add base `e2b` package
- All existing FastAPI, PostgreSQL, Redis, Clerk, Stripe, AWS infrastructure
- `playwright>=1.58.0` — added in v0.6, keep for screenshot tool
- `boto3>=1.35.0` — keep for S3 screenshot uploads from agent

---

## Recommended Stack Additions

### Core: Anthropic SDK (Version Bump + Drop LangChain)

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| `anthropic` | `>=0.83.0` | Direct Claude API access for autonomous agentic loop — tool-use, streaming, token counting | Already in `pyproject.toml` at `>=0.40.0`. Bump to `>=0.83.0` (released 2026-02-19) to get top-level cache control, stable server-side tool runner, and `client.messages.count_tokens()`. Removes the LangChain wrapper entirely — the direct SDK gives full control over the tool-use loop with no graph abstraction overhead. |

**Why drop LangChain/LangGraph for the direct Anthropic SDK:**

The autonomous agent loop is `while stop_reason != "end_turn"` over `client.messages.create()` with a `tools=` list. LangGraph adds value when the pipeline is a predefined graph of named nodes (Architect → Coder → Executor). An autonomous agent with dynamic tool dispatch doesn't fit a static graph — the model drives execution, not the graph. The direct SDK removes 4 dependencies, is fully typed, and the agentic loop is ~30 lines of Python.

**Agentic loop pattern (HIGH confidence — verified via official Anthropic docs):**

```python
async def run_agent_loop(
    client: anthropic.AsyncAnthropic,
    messages: list[dict],
    tools: list[dict],
    model: str,
    max_iterations: int = 50,
) -> list[dict]:
    for _ in range(max_iterations):
        response = await client.messages.create(
            model=model,
            max_tokens=8192,
            tools=tools,
            messages=messages,
        )
        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason == "end_turn":
            break

        # Claude may return multiple tool_use blocks in one response (parallel tool calls)
        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                result = await dispatch_tool(block.name, block.input)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result,
                })

        if tool_results:
            messages.append({"role": "user", "content": tool_results})

    return messages
```

**Token counting — built into SDK, free, no extra library (HIGH confidence — verified via official docs):**

```python
# Before each iteration — check budget before consuming tokens
count = await client.messages.count_tokens(
    model=model,
    tools=tools,
    messages=messages,
)
tokens_this_turn_estimate = count.input_tokens
# Compare against budget.daily_remaining before proceeding
```

**Streaming to SSE activity feed:**

```python
async with client.messages.stream(
    model=model,
    max_tokens=8192,
    tools=tools,
    messages=messages,
) as stream:
    async for event in stream:
        # Emit text_delta events and tool_use_delta blocks to the SSE queue
        await sse_queue.put(serialize_event(event))
    final = await stream.get_final_message()
```

**Tool definitions with strict mode (HIGH confidence — verified via official docs):**

```python
AGENT_TOOLS = [
    {
        "name": "bash",
        "description": "Run a bash command in the E2B sandbox.",
        "input_schema": {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "The bash command to run."},
            },
            "required": ["command"],
        },
    },
    {
        "name": "read_file",
        "description": "Read the contents of a file in the sandbox.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Absolute path to the file."},
            },
            "required": ["path"],
        },
    },
    {
        "name": "write_file",
        "description": "Write content to a file in the sandbox, creating it if it does not exist.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Absolute path to the file."},
                "content": {"type": "string", "description": "Content to write."},
            },
            "required": ["path", "content"],
        },
    },
    {
        "name": "grep",
        "description": "Search file contents for a pattern.",
        "input_schema": {
            "type": "object",
            "properties": {
                "pattern": {"type": "string"},
                "path": {"type": "string"},
            },
            "required": ["pattern", "path"],
        },
    },
    {
        "name": "glob",
        "description": "Find files matching a glob pattern.",
        "input_schema": {
            "type": "object",
            "properties": {
                "pattern": {"type": "string"},
                "directory": {"type": "string"},
            },
            "required": ["pattern"],
        },
    },
    {
        "name": "take_screenshot",
        "description": "Capture a screenshot of the running dev server and return a URL.",
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },
]
```

---

### Tool Implementation: E2B Base Package

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| `e2b` | `>=2.13.0` | Implement bash, read_file, write_file, grep, glob tools — filesystem and command execution inside sandbox | The existing `pyproject.toml` has `e2b-code-interpreter>=1.0.0`, which is the high-level stateful Python REPL / Jupyter-style sandbox. The autonomous agent needs raw `sandbox.filesystem.read/write()` and `sandbox.commands.run()` directly — not the code interpreter's cell execution model. The base `e2b` package (latest: 2.13.3 released 2026-02-21) exposes the Sandbox class with Filesystem, Commands, and Pty subsystems. |

**E2B tool dispatch mapping (MEDIUM confidence — verified via e2b.dev/docs):**

```python
from e2b import AsyncSandbox

async def dispatch_tool(sandbox: AsyncSandbox, name: str, inputs: dict) -> str:
    match name:
        case "bash":
            result = await sandbox.commands.run(inputs["command"], timeout=60)
            return f"stdout: {result.stdout}\nstderr: {result.stderr}"

        case "read_file":
            content = await sandbox.filesystem.read(inputs["path"])
            return content

        case "write_file":
            await sandbox.filesystem.write(inputs["path"], inputs["content"])
            return f"Written: {inputs['path']}"

        case "grep":
            result = await sandbox.commands.run(
                f"grep -r {shlex.quote(inputs['pattern'])} {shlex.quote(inputs['path'])}"
            )
            return result.stdout or "(no matches)"

        case "glob":
            directory = inputs.get("directory", "/home/user/project")
            result = await sandbox.commands.run(
                f"find {shlex.quote(directory)} -name {shlex.quote(inputs['pattern'])} -type f"
            )
            return result.stdout or "(no matches)"

        case "take_screenshot":
            # Reuse existing Playwright-in-sandbox pattern from v0.6
            return await capture_screenshot_and_upload(sandbox)

        case _:
            return f"Unknown tool: {name}"
```

**Key E2B API methods (MEDIUM confidence — e2b.dev/docs/sdk-reference):**

| Method | What it does |
|--------|-------------|
| `sandbox.filesystem.read(path)` | Read file content as string |
| `sandbox.filesystem.write(path, content)` | Write string content to file |
| `sandbox.filesystem.list(path)` | List directory contents |
| `sandbox.filesystem.exists(path)` | Check file/directory existence |
| `sandbox.commands.run(cmd, timeout=60)` | Execute bash command, returns `result.stdout` / `result.stderr` |
| `sandbox.commands.kill(pid)` | Terminate a running process |

**Package decision — keep both or swap:**
- Keep `e2b-code-interpreter>=1.0.0` if anything in the existing codebase calls its REPL API (check `app/sandbox/e2b_runtime.py`)
- Add `e2b>=2.13.0` for the new agent tool implementations
- Both packages can coexist — different namespaces (`e2b` vs `e2b_code_interpreter`)
- After v0.7 ships and old code is removed, audit and drop `e2b-code-interpreter` if unused

---

### Daemon Execution: No New Library — Use asyncio

The sleep/wake daemon model requires no external library. It is a long-lived `asyncio.Task` that checks token budget and calls `asyncio.sleep()` when the daily allocation is exhausted.

**Why not APScheduler, Celery, or RQ:**

| Option | Why rejected |
|--------|-------------|
| APScheduler | Designed for recurring cron-style jobs at fixed intervals. The daemon is a per-session coroutine with dynamic sleep duration computed from budget state. APScheduler adds configuration, persistence layer, and process management for a pattern that stdlib handles in 10 lines. |
| Celery | Distributed task queue requiring a separate worker process and broker configuration. The daemon is in-process, shares the FastAPI app's database connections, and is already backed by Redis for state. Celery adds a full process architecture for zero benefit. |
| RQ (Redis Queue) | Same objection as Celery — external worker process. The daemon's "sleep" is not a deferred task, it's a sleeping coroutine that wakes on a timer. |

**Daemon pattern (HIGH confidence — FastAPI + asyncio stdlib):**

```python
# Launch from a FastAPI route or startup event
async def agent_daemon(project_id: str, user_id: str, sandbox: AsyncSandbox) -> None:
    """Persistent agent daemon: runs iterations, sleeps when budget exhausted."""
    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    messages = await load_conversation_history(project_id)

    while True:
        # Check daily token budget before each iteration
        budget = await get_token_budget(user_id)
        if budget.daily_tokens_remaining <= 0:
            # Sleep until next reset (midnight UTC)
            await update_agent_status(project_id, "sleeping")
            await asyncio.sleep(budget.seconds_until_reset)
            continue

        # Estimate tokens for this iteration before consuming them
        token_estimate = await client.messages.count_tokens(
            model=resolve_model(user_id),
            tools=AGENT_TOOLS,
            messages=messages,
        )
        if token_estimate.input_tokens > budget.daily_tokens_remaining:
            await update_agent_status(project_id, "sleeping")
            await asyncio.sleep(budget.seconds_until_reset)
            continue

        # Run one agent iteration
        await update_agent_status(project_id, "active")
        result = await run_agent_iteration(client, sandbox, messages, user_id)
        messages = result.messages

        if result.done or result.needs_founder_input:
            await update_agent_status(project_id, "waiting" if result.needs_founder_input else "done")
            break

        # Pace between iterations — avoid bursts, give SSE events time to flush
        await asyncio.sleep(2)


# Register task in FastAPI lifespan or route
@router.post("/agent/{project_id}/start")
async def start_agent(project_id: str, background_tasks: BackgroundTasks, ...):
    sandbox = await get_or_create_sandbox(project_id)
    background_tasks.add_task(agent_daemon, project_id, user_id, sandbox)
    return {"status": "started"}
```

**For tasks that must survive longer than the request lifetime**, register in the app's lifespan and store the `asyncio.Task` in a process-level registry keyed by project_id. This allows the route to check if a daemon is already running before starting a duplicate.

---

## Token Budget Integration with Existing Infrastructure

The existing `app/queue/usage.py` `UsageTracker` tracks job counts against daily limits. The v0.7 token budget extends this pattern — track token counts in the same Redis key space.

**Extend `UsageTracker` — add token budget methods:**

```python
# New methods to add to UsageTracker

async def increment_token_usage(self, user_id: str, tokens: int) -> int:
    """Increment daily token counter. Returns new total."""
    today = datetime.now(UTC).date().isoformat()
    key = f"cofounder:usage:{user_id}:{today}"
    new_total = await self.redis.incrby(key, tokens)
    await self.redis.expire(key, 90_000)  # 25h TTL
    return new_total

async def get_token_budget(self, user_id: str, tier: str) -> TokenBudget:
    """Return remaining daily token budget and seconds until reset."""
    today = datetime.now(UTC).date().isoformat()
    key = f"cofounder:usage:{user_id}:{today}"
    used = int(await self.redis.get(key) or 0)
    daily_limit = TIER_DAILY_TOKEN_LIMIT[tier]  # Add to schemas.py
    remaining = max(0, daily_limit - used)
    reset_at = self._get_next_reset()
    seconds_until_reset = int((reset_at - datetime.now(UTC)).total_seconds())
    return TokenBudget(
        daily_tokens_used=used,
        daily_tokens_remaining=remaining,
        seconds_until_reset=seconds_until_reset,
    )
```

**The existing `resolve_llm_config()` and `_check_daily_token_limit()` in `llm_config.py` already tracks tokens in `cofounder:usage:{user_id}:{today}`. The daemon reads this key — no duplicate tracking.**

---

## Model Configuration Per Subscription Tier

The existing `resolve_llm_config()` in `app/core/llm_config.py` resolves model per user+role from plan tier. For v0.7, add a single "agent" role:

```python
# In MODEL_COSTS — add new model IDs if not present
MODEL_COSTS: dict[str, dict[str, int]] = {
    "claude-opus-4-6": {"input": 15_000_000, "output": 75_000_000},
    "claude-sonnet-4-6": {"input": 3_000_000, "output": 15_000_000},
}

# Tier mapping in plan seed data or PlanTier.default_models:
# bootstrapper: {"agent": "claude-sonnet-4-6"}  # cost-efficient
# partner:      {"agent": "claude-sonnet-4-6"}  # balanced
# cto_scale:    {"agent": "claude-opus-4-6"}    # highest quality
```

---

## Complete Dependency Delta for pyproject.toml

```toml
# REMOVE (LangGraph pipeline replaced by direct Anthropic SDK):
# "langgraph>=0.2.0",
# "langgraph-checkpoint-postgres>=2.0.0",
# "langchain-anthropic>=0.3.0",
# "langchain-core>=0.3.0",

# BUMP (already present — version upgrade only):
# "anthropic>=0.40.0"  →  "anthropic>=0.83.0",

# ADD (base E2B package for raw filesystem + command tools):
# "e2b>=2.13.0",

# AUDIT THEN DECIDE (keep if existing sandbox code uses it, remove after v0.7 migration):
# "e2b-code-interpreter>=1.0.0",

# KEEP UNCHANGED:
# "fastapi>=0.115.0",
# "redis>=5.2.0",
# "pydantic>=2.10.0",
# "playwright>=1.58.0",
# "boto3>=1.35.0",
# "structlog>=25.0.0",
# ... all other existing deps
```

---

## What NOT to Add

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| `langgraph`, `langchain-anthropic`, `langchain-core` | Adds graph abstraction between the autonomous loop and Claude's API. The agent's control flow comes from Claude's `stop_reason`, not a predefined graph. Removes 4 packages. | Direct `anthropic>=0.83.0` SDK |
| `tiktoken` | OpenAI's tokenizer. Wrong library for Claude token counting. | `client.messages.count_tokens()` — built into Anthropic SDK, free, authoritative for Claude models |
| `apscheduler` | Cron-style recurring job scheduler. The daemon is a per-session coroutine with dynamic sleep, not a recurring job at fixed intervals. | `asyncio.sleep()` inside `BackgroundTasks` or `asyncio.create_task()` |
| `celery` | Distributed task queue requiring external worker process. Overkill for a single in-process async coroutine. | `asyncio.create_task()` — same event loop as FastAPI |
| `rq` | Same objection as Celery. Redis Queue is for durable deferred tasks across processes, not in-process coroutines. | `asyncio.create_task()` |
| `mem0ai` | Present in `pyproject.toml`. The autonomous agent manages context via the conversation `messages[]` array passed directly to Claude. The v0.7 agent doesn't need a separate memory layer — audit and remove if nothing calls mem0. | Conversation history in `messages[]` + existing `episodic.py` if needed |
| MCP framework libraries | MCP is the right architecture for tools shared across multiple AI clients or hosted externally. The agent's tools are internal, co-located with FastAPI, and call E2B directly. | Custom tool functions dispatched in the agent loop |
| `anthropic-tools` or similar wrappers | Non-official library. The Anthropic SDK's tool-use protocol is simple enough to implement directly with dicts. No wrapper needed. | Direct `client.messages.create(tools=[...])` |

---

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| Direct `anthropic` SDK agentic loop | LangGraph with Anthropic nodes | Use LangGraph when the pipeline is a fixed, predefined multi-node graph with human-in-the-loop checkpoints, persistent state across process restarts, and branching logic that doesn't come from the model itself. Not appropriate for an autonomous loop where Claude drives control flow. |
| `e2b` base package | `e2b-code-interpreter` | Use `e2b-code-interpreter` when you need a stateful Jupyter-style Python REPL with variable persistence across executions. The agent's tool surface needs raw bash and file I/O, not a REPL session. |
| `asyncio.sleep()` daemon | APScheduler | Use APScheduler when running recurring jobs on fixed cron schedules across multiple server instances with a shared job store. Not appropriate for a per-session coroutine with dynamic sleep duration. |
| `client.messages.count_tokens()` | Heuristic estimation (tokens ~= chars / 4) | Use heuristic estimation only when you cannot make an API call (offline or latency-sensitive). The Anthropic token counting API is free and synchronous — use it for accurate pre-flight budget checks. |
| Single `messages[]` array as context | Separate vector DB / RAG for agent memory | Use vector DB when the agent operates across multiple disconnected sessions with a large external knowledge base. The v0.7 agent operates within a single project session — the conversation history is the context, kept in Redis or PostgreSQL between daemon wake cycles. |

---

## Version Compatibility

| Package | Version | Compatible With | Notes |
|---------|---------|-----------------|-------|
| `anthropic>=0.83.0` | 0.83.0 (2026-02-19) | Python 3.9+, FastAPI 0.115+ | Drops LangChain dependency chain entirely. No conflicts with remaining packages. |
| `e2b>=2.13.0` | 2.13.3 (2026-02-21) | Python 3.10+, asyncio | Project requires Python 3.12 — no constraint issues. `e2b` and `e2b-code-interpreter` coexist in different namespaces. |
| `asyncio` (stdlib) | Python 3.12 stdlib | FastAPI 0.115+, uvicorn 0.32+ | `asyncio.create_task()` and `BackgroundTasks` are the FastAPI-blessed patterns for in-process daemon tasks. No compatibility concerns. |

---

## Sources

- [Anthropic Python SDK — PyPI](https://pypi.org/project/anthropic/) — latest version 0.83.0 confirmed (released 2026-02-19) — **HIGH confidence**
- [Anthropic SDK GitHub — Release History](https://github.com/anthropics/anthropic-sdk-python/releases) — v0.83.0 top-level cache control, v0.81.0 tool versions, v0.79.0 `count_tokens()` speed param — **HIGH confidence**
- [Anthropic Tool Use — Official Docs](https://platform.claude.com/docs/en/docs/build-with-claude/tool-use/overview) — `stop_reason: tool_use`, `tool_result` protocol, parallel tool calls, tool pricing — **HIGH confidence** (official docs, fetched directly)
- [E2B Documentation — e2b.dev/docs](https://e2b.dev/docs) — `sandbox.commands.run()` confirmed as primary bash execution method — **MEDIUM confidence** (official docs, some details indirect)
- [E2B SDK Reference Python v1.0.4](https://e2b.dev/docs/sdk-reference/python-sdk/v1.0.4/sandbox_sync) — `filesystem.read/write/list/exists`, `commands.run/kill/list`, `Pty.create` — **MEDIUM confidence** (official docs)
- [E2B PyPI](https://pypi.org/project/e2b/) — latest version 2.13.3 (released 2026-02-21) — **MEDIUM confidence** (PyPI, JS-disabled page returned error, version sourced from web search)
- [FastAPI Background Tasks](https://fastapi.tiangolo.com/tutorial/background-tasks/) — `BackgroundTasks` + `asyncio.create_task()` daemon pattern — **HIGH confidence** (official FastAPI docs)
- Existing `backend/app/core/llm_config.py` — token tracking in `cofounder:usage:{user_id}:{today}` Redis key — **HIGH confidence** (code review)
- Existing `backend/app/queue/usage.py` — `UsageTracker` pattern for extension — **HIGH confidence** (code review)
- Existing `backend/pyproject.toml` — confirmed current dependency versions and what to remove — **HIGH confidence** (code review)

---

*Stack research for: v0.7 Autonomous Claude Agent — direct SDK, E2B tool surface, asyncio daemon model*
*Researched: 2026-02-24*
*Supersedes: v0.6 STACK.md entries only for Anthropic SDK usage pattern and LangGraph dependencies — all v0.6 E2B/SSE/S3/Playwright entries remain valid*
