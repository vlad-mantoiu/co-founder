# Phase 41: Autonomous Runner Core (TAOR Loop) - Research

**Researched:** 2026-02-25
**Domain:** Anthropic tool-use API, agentic loop patterns, Python async streaming
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Streaming Narration**
- First-person collaborative co-founder voice using "we/us" language (not founder's name)
- Narrate both reasoning AND actions — share WHY decisions are made alongside what's happening
- Narrate before AND after each tool call — "I'm creating the auth module..." then "Auth module created. Moving to routes."
- Tool calls shown in collapsible detail sections — narration is primary, tool invocations expandable for curious founders
- Distinct labeled phases in the narration stream — founder sees named stages (e.g. "Scaffolding", "Authentication")
- Section summaries after each major group of work completes — clear milestones of what was built
- Light markdown formatting — bold for phase names, inline code for file paths
- Errors narrated honestly but reassuringly — "Hit an issue with X. Trying a different approach..."
- No action counts or progress numbers — phases and section summaries provide structure instead
- Claude's discretion on token-by-token vs sentence-chunk streaming — pick what works best with existing SSE channel

**System Prompt Design**
- Full verbatim injection of both Idea Brief and Understanding Interview QnA — nothing summarized, agent sees everything the founder said
- System prompt includes identity + instructions — co-founder persona definition shapes narration voice and behavior
- Minimal critical-only guardrails in the prompt — only forbid catastrophic actions (data deletion, external prod API calls); trust tool-level sandbox safety for everything else
- Agent receives a structured build plan in the system prompt — it executes the plan, it does not decide what to build or in what order

**Loop Termination Behavior**
- Iteration cap (MAX_TOOL_CALLS) is a hard number per session — predictable cost, simple to test
- On hitting iteration cap: narrated graceful stop with handoff — "I've reached my action limit. Here's what I completed and what's remaining..."
- On repetition detection (same tool call 3x): try an alternative approach first before stopping — agent attempts a different strategy, only escalates if the alternative also fails
- On successful completion (end_turn): structured build report — summary of what was built, files created, architecture decisions, what to look at first (PR-description style)

**Tool Stub Strategy**
- Stubs return realistic fake output — read_file returns plausible content, bash returns realistic command output
- Stateful in-memory filesystem — write_file then read_file returns what was written; stubs maintain coherent state across the loop
- Configurable failures — tests can inject tool failures at specific points to validate error handling paths
- Clean Strategy pattern interface (ToolDispatcher) — stubs implement the interface now, Phase 42 swaps in E2B implementation without rewriting the loop

### Claude's Discretion
- Streaming granularity (token-by-token vs sentence chunks) — pick what works with SSE
- Exact system prompt structure and ordering of sections
- In-memory filesystem implementation details
- Repetition detection window tuning (the spec says 10-call window, implementation details are flexible)

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| AGNT-01 | Agent executes a TAOR (Think-Act-Observe-Repeat) loop using Anthropic tool-use API, autonomously deciding next actions until build is complete or human input needed | Anthropic `messages.create(tools=[...])` with streaming, loop on `stop_reason="tool_use"`, exit on `stop_reason="end_turn"` |
| AGNT-02 | Agent consumes Understanding Interview QnA + Idea Brief as input context, using it to make autonomous product/architecture decisions | Full verbatim injection into system prompt; artifacts fetched from existing PostgreSQL artifact tables via `generate_idea_brief` and understanding routes |
| AGNT-06 | Agent loop has iteration cap (MAX_TOOL_CALLS), repetition detection, and context window management (middle-truncation of large tool results) | MAX_TOOL_CALLS counter per loop session; repetition detection via `hash(tool_name + json(tool_input))`; middle-truncation algorithm keeping first 500 + last 500 tokens |
</phase_requirements>

---

## Summary

Phase 41 implements `AutonomousRunner.run_agent_loop()` — the core TAOR loop that replaces the LangGraph pipeline. The implementation uses the Anthropic SDK's `messages.create()` with `tools=[...]` and `stream=True`, loops while `stop_reason == "tool_use"`, and exits cleanly on `stop_reason == "end_turn"`. Tools are stubbed behind a `ToolDispatcher` interface with an in-memory stateful filesystem.

The existing SSE infrastructure (`LogStreamer` → Redis Stream → `stream_job_logs` SSE endpoint) is the correct channel for streaming narration. The agent writes narration text to the Redis stream via `LogStreamer.write_event()` — no new streaming infrastructure is needed. Text delta chunks from `stream.text_stream` are accumulated sentence-by-sentence (or flushed at `content_block_stop`) before writing to the stream, avoiding token-level Redis overhead.

The three safety guards (AGNT-06) are pure Python with no external dependencies: a counter against `MAX_TOOL_CALLS`, a sliding deque for repetition detection using `collections.deque(maxlen=10)`, and a middle-truncation function that tokenizes by splitting on whitespace (word-count proxy for tokens). All three are independently testable without LLM calls.

**Primary recommendation:** Implement `run_agent_loop()` directly inside `runner_autonomous.py` as a self-contained method that uses `client.messages.stream(...)`, dispatch tool calls through a `ToolDispatcher` protocol, and write narration via the injected `LogStreamer`. The caller (worker) passes job context including `idea_brief` and `understanding_qna` from PostgreSQL.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `anthropic` | 0.79.0 (installed) | TAOR loop, streaming, tool-use | Already in project; `AsyncAnthropic.messages.stream()` returns `AsyncMessageStreamManager` with `text_stream` and full message snapshot |
| `collections.deque` | stdlib | Repetition detection window (deque(maxlen=10)) | Zero-cost; maxlen auto-evicts oldest entries |
| `hashlib` / `json` | stdlib | Tool call fingerprinting for repetition detection | `hash(tool_name + json.dumps(tool_input, sort_keys=True))` is stable across calls |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `structlog` | installed | Structured loop iteration logging | Already used throughout; bind `job_id`, `iteration`, `tool_name` per call |
| `tenacity` | installed | Retry on `OverloadedError` (529) | Already used in `_invoke_with_retry`; apply same pattern to streaming API calls |
| `LogStreamer` | project | Write narration to Redis Stream → SSE | Already exists at `app/services/log_streamer.py`; use `write_event()` for narration lines |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `client.messages.stream()` | `client.messages.create(stream=True)` | `stream()` context manager provides clean `text_stream` and final `get_final_message()`; both yield the same events. Use `stream()`. |
| Word-count truncation proxy | `tiktoken` | `tiktoken` not installed; word-count proxy is sufficient given the 1000-token spec is approximate |
| In-memory filesystem dict | E2B sandbox (Phase 42) | Phase 42 concern; stubs use `dict[str, str]` with path as key |

---

## Architecture Patterns

### Recommended Project Structure

```
backend/app/agent/
├── runner_autonomous.py      # AutonomousRunner — Phase 41 replaces stub with TAOR loop
├── tools/
│   ├── __init__.py           # (exists, empty)
│   ├── dispatcher.py         # ToolDispatcher protocol + InMemoryToolDispatcher stub
│   └── definitions.py        # Tool JSON schemas for Anthropic API
└── loop/                     # NEW module for loop internals
    ├── __init__.py
    ├── safety.py             # IterationGuard: MAX_TOOL_CALLS, repetition detection, truncation
    └── system_prompt.py      # build_system_prompt(idea_brief, qna, build_plan) → str
```

### Pattern 1: TAOR Loop with Streaming

**What:** The core agent loop. Each iteration: send messages → stream response → if `tool_use` block found, dispatch tool → append result to messages → repeat.

**When to use:** Single entry point `run_agent_loop(context)` on `AutonomousRunner`.

```python
# Source: anthropic SDK 0.79.0 AsyncMessageStreamManager pattern
async def _run_taor_loop(
    self,
    client: anthropic.AsyncAnthropic,
    system: str,
    tools: list[dict],
    initial_messages: list[dict],
    dispatcher: ToolDispatcher,
    streamer: LogStreamer,
    guard: IterationGuard,
) -> LoopResult:
    messages = list(initial_messages)

    while True:
        # Think: stream response
        async with client.messages.stream(
            model=self._model,
            system=system,
            messages=messages,
            tools=tools,
            max_tokens=4096,
        ) as stream:
            # Accumulate narration text from stream — write to SSE on sentence boundaries
            accumulated_text = ""
            async for chunk in stream.text_stream:
                accumulated_text += chunk
                # Flush on sentence boundary to avoid token-per-redis-call overhead
                if accumulated_text.endswith((".", "!", "?", "\n")):
                    await streamer.write_event(accumulated_text.strip(), source="agent")
                    accumulated_text = ""

            # Flush remaining text
            if accumulated_text.strip():
                await streamer.write_event(accumulated_text.strip(), source="agent")

            # Get the full message snapshot
            response = await stream.get_final_message()

        # Check stop condition
        if response.stop_reason == "end_turn":
            return LoopResult(status="completed", message=response)

        # Act: find tool_use blocks
        tool_use_blocks = [b for b in response.content if b.type == "tool_use"]
        if not tool_use_blocks:
            # No tool calls but not end_turn — treat as completion
            return LoopResult(status="completed", message=response)

        # Append assistant turn to history
        messages.append({"role": "assistant", "content": response.content})

        # Observe: dispatch each tool call
        tool_results = []
        for tool_block in tool_use_blocks:
            guard.check_iteration_cap()  # raises IterationCapError if exceeded
            guard.check_repetition(tool_block.name, tool_block.input)  # raises RepetitionError

            result_text = await dispatcher.dispatch(tool_block.name, tool_block.input)
            result_text = guard.truncate_tool_result(result_text)  # middle-truncate if >1000 tokens

            tool_results.append({
                "type": "tool_result",
                "tool_use_id": tool_block.id,
                "content": result_text,
            })

        # Append tool results to history (user turn)
        messages.append({"role": "user", "content": tool_results})

        # Repeat
```

### Pattern 2: ToolDispatcher Protocol + InMemoryToolDispatcher

**What:** Strategy pattern — loop calls `dispatcher.dispatch(name, input)`, stubs return canned responses, Phase 42 replaces with E2B.

```python
# Source: project convention (existing Runner protocol pattern)
from typing import Protocol

class ToolDispatcher(Protocol):
    """Protocol for tool execution — stubs in Phase 41, E2B in Phase 42."""
    async def dispatch(self, tool_name: str, tool_input: dict) -> str: ...


class InMemoryToolDispatcher:
    """Stateful in-memory stub — write_file then read_file returns what was written."""

    def __init__(self, failure_map: dict[tuple[str, int], Exception] | None = None):
        self._fs: dict[str, str] = {}
        self._call_counts: dict[str, int] = {}
        self._failure_map = failure_map or {}  # (tool_name, call_N) -> Exception to raise

    async def dispatch(self, tool_name: str, tool_input: dict) -> str:
        n = self._call_counts.get(tool_name, 0)
        self._call_counts[tool_name] = n + 1

        # Inject configured failure
        if (tool_name, n) in self._failure_map:
            raise self._failure_map[(tool_name, n)]

        if tool_name == "write_file":
            path = tool_input["path"]
            content = tool_input["content"]
            self._fs[path] = content
            return f"File written: {path} ({len(content)} bytes)"

        if tool_name == "read_file":
            path = tool_input["path"]
            return self._fs.get(path, f"# File not found: {path}")

        if tool_name == "bash":
            cmd = tool_input.get("command", "")
            return f"$ {cmd}\n[exit 0]"

        # Default: realistic stub response
        return f"[{tool_name} completed successfully]"
```

### Pattern 3: IterationGuard (All Safety Guards)

**What:** Encapsulates all three AGNT-06 safety behaviors — cap, repetition, truncation.

```python
import collections
import json

class IterationCapError(Exception):
    pass

class RepetitionError(Exception):
    pass

class IterationGuard:
    def __init__(self, max_tool_calls: int = 150):
        self._max = max_tool_calls
        self._count = 0
        self._window: collections.deque[str] = collections.deque(maxlen=10)
        self._fingerprint_counts: dict[str, int] = {}

    def check_iteration_cap(self) -> None:
        self._count += 1
        if self._count > self._max:
            raise IterationCapError(
                f"Iteration limit reached after {self._max} tool calls."
            )

    def check_repetition(self, tool_name: str, tool_input: dict) -> None:
        fingerprint = f"{tool_name}:{json.dumps(tool_input, sort_keys=True)}"
        self._window.append(fingerprint)
        # Count occurrences of this fingerprint in the last 10 calls
        count = sum(1 for fp in self._window if fp == fingerprint)
        if count >= 3:
            raise RepetitionError(
                f"Repetition detected: '{tool_name}' called 3 times with same args in last 10 calls"
            )

    def truncate_tool_result(self, text: str, token_limit: int = 1000) -> str:
        """Middle-truncate tool result if >1000 tokens. Word-count proxy (1 word ≈ 1 token)."""
        words = text.split()
        if len(words) <= token_limit:
            return text
        half = token_limit // 2
        omitted = len(words) - token_limit
        head = " ".join(words[:half])
        tail = " ".join(words[-half:])
        return f"{head}\n[{omitted} words omitted]\n{tail}"
```

### Pattern 4: System Prompt Builder

**What:** Assembles the system prompt with identity, Idea Brief (verbatim), Understanding Interview QnA (verbatim), and the build plan.

```python
def build_system_prompt(
    idea_brief: dict,
    understanding_qna: list[dict],
    build_plan: dict,
) -> str:
    """Build the TAOR agent system prompt from founder context."""
    import json

    persona = """You are the founder's AI co-founder — a senior technical partner building their product together.

Voice: Use "we/us" for shared decisions. Use "I" for your internal reasoning. Narrate what you're doing and WHY.
Narrate before every tool call ("I'm creating the auth module next because...") and after ("Auth module created.").
Use light markdown: **Phase Name** for phases, `file/path.py` for files.
On errors: "Hit an issue with X. Trying a different approach..." — never panicked.

CRITICAL: Do not delete data. Do not make external API calls to production services.
Execute the provided build plan in sequence. Do not deviate from the plan order."""

    brief_section = f"""## Founder's Idea Brief
{json.dumps(idea_brief, indent=2)}"""

    qna_section = "## Understanding Interview (Founder's Answers)\n"
    for item in understanding_qna:
        qna_section += f"Q: {item.get('question', '')}\nA: {item.get('answer', '')}\n\n"

    plan_section = f"""## Build Plan (Execute in Order)
{json.dumps(build_plan, indent=2)}"""

    return "\n\n".join([persona, brief_section, qna_section, plan_section])
```

### Pattern 5: Tool Schema Definitions

**What:** The 7 tool definitions passed to `messages.create(tools=[...])`. Phase 41 defines all 7 per AGNT-03 spec (even though only stubs execute them).

```python
# Source: anthropic SDK ToolParam type
AGENT_TOOLS: list[dict] = [
    {
        "name": "read_file",
        "description": "Read the contents of a file in the sandbox.",
        "input_schema": {
            "type": "object",
            "properties": {"path": {"type": "string", "description": "Absolute file path"}},
            "required": ["path"],
        },
    },
    {
        "name": "write_file",
        "description": "Write content to a file. Creates parent directories if needed.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "content": {"type": "string"},
            },
            "required": ["path", "content"],
        },
    },
    {
        "name": "edit_file",
        "description": "Replace a specific string in a file with new content.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "old_string": {"type": "string"},
                "new_string": {"type": "string"},
            },
            "required": ["path", "old_string", "new_string"],
        },
    },
    {
        "name": "bash",
        "description": "Run a shell command in the sandbox and return stdout/stderr.",
        "input_schema": {
            "type": "object",
            "properties": {"command": {"type": "string"}},
            "required": ["command"],
        },
    },
    {
        "name": "grep",
        "description": "Search for a pattern in files.",
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
        "description": "List files matching a glob pattern.",
        "input_schema": {
            "type": "object",
            "properties": {"pattern": {"type": "string"}},
            "required": ["pattern"],
        },
    },
    {
        "name": "take_screenshot",
        "description": "Capture a screenshot of the current sandbox browser state.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
]
```

### Anti-Patterns to Avoid

- **Calling `client.messages.create()` instead of `client.messages.stream()`:** Loses streaming — narration won't appear until the API call completes. Use `client.messages.stream()` context manager.
- **Writing every text delta token to Redis:** One Redis `xadd` per token (up to 10/second) will overwhelm Redis. Accumulate text on sentence boundaries (`.`, `!`, `?`, `\n`) before writing.
- **Passing `stream.text_stream` alone:** `text_stream` only yields text deltas; `tool_use` blocks are not visible there. Always call `stream.get_final_message()` to get the full response with tool blocks.
- **Appending tool results before assistant turn:** Anthropic API requires `assistant` turn (with `tool_use` blocks) before the `user` turn (with `tool_result` blocks). Order matters.
- **Using `TrackedAnthropicClient` for streaming:** `_TrackedMessages.create()` calls `await client.messages.create(**kwargs)` and returns a `Message` — it does not support streaming. For Phase 41, use the raw `AsyncAnthropic` client and track usage from `stream.get_final_message().usage`.
- **Checking repetition on the `tool_use` block before appending to history:** The guard must fire before dispatching the tool but the assistant content must still be appended to messages even when the loop terminates (so message history is valid for any post-hoc inspection).

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Streaming text from Anthropic | Custom SSE parser | `client.messages.stream()` `AsyncMessageStreamManager` | SDK handles SSE framing, reconnects, event parsing |
| Token counting for truncation | Custom tokenizer | Word-count proxy (1 word ≈ 1 token) | `tiktoken` not installed; spec says "1000 tokens" as approximate limit — word count is sufficient |
| Loop retry on 529 | Custom exponential backoff | `tenacity` (already in `_invoke_with_retry`) | Already proven pattern in `app/agent/llm_helpers.py` |
| Streaming to frontend | New WebSocket channel | Existing `LogStreamer` → Redis Stream → `/logs/stream` SSE | SSE channel already live and tested; no new infrastructure |

**Key insight:** The TAOR loop itself is simple — the complexity is in the safety guards and the streaming narration routing. Both are pure Python with no new dependencies.

---

## Common Pitfalls

### Pitfall 1: TrackedAnthropicClient Does Not Support Streaming

**What goes wrong:** `TrackedAnthropicClient._TrackedMessages.create()` awaits `client.messages.create(**kwargs)` and returns a `Message`. Passing `stream=True` returns an unprocessed `AsyncStream` object, not a message. The usage tracking also won't fire.

**Why it happens:** `_TrackedMessages.create()` was built for non-streaming JSON calls in `_invoke_with_retry`.

**How to avoid:** In `run_agent_loop()`, instantiate `AsyncAnthropic` directly and call `client.messages.stream(...)`. Track usage separately after each iteration using `response.usage.input_tokens` and `response.usage.output_tokens` from `stream.get_final_message()`.

**Warning signs:** `AttributeError: 'AsyncStream' object has no attribute 'content'` or empty narration with completed tool calls.

### Pitfall 2: Empty Message History Causes 400 Error

**What goes wrong:** Anthropic API requires at least one `user` message in `messages`. Passing `messages=[]` returns HTTP 400.

**Why it happens:** The TAOR loop starts with the initial user message (the build trigger). If `run_agent_loop(context)` initializes `messages` without a first user turn, the first API call fails.

**How to avoid:** Always initialize `messages` with a first user message, e.g.:
```python
messages = [{"role": "user", "content": "Begin building the project per the build plan."}]
```

**Warning signs:** `anthropic.BadRequestError: messages must contain at least one user turn`.

### Pitfall 3: Tool Result Without Matching tool_use_id Causes 400

**What goes wrong:** Each `tool_result` block in the user turn must reference a `tool_use_id` from the preceding assistant turn. Mismatching IDs or missing IDs causes API rejection.

**Why it happens:** Developers build tool result lists manually without referencing `tool_block.id`.

**How to avoid:** Always use `tool_block.id` from the response content block:
```python
{"type": "tool_result", "tool_use_id": tool_block.id, "content": result_text}
```

**Warning signs:** `anthropic.BadRequestError: tool_result.tool_use_id must match a tool_use block`.

### Pitfall 4: Repetition Detection Window Resets On Error

**What goes wrong:** If an `IterationCapError` or `RepetitionError` is caught and the loop retries (alternative approach path), the window may clear the fingerprints. The spec says "try an alternative approach first before stopping" — the window must persist across the retry attempt.

**Why it happens:** Guard is reinstantiated on retry.

**How to avoid:** Pass the same `IterationGuard` instance through the retry. Only reset the `_fingerprint_counts` (not the deque) when the agent explicitly switches strategy.

**Warning signs:** Repetition detection never fires despite the agent obviously looping.

### Pitfall 5: `stream.get_final_message()` Returns After Stream Exhausted

**What goes wrong:** Calling `stream.get_final_message()` before consuming the full stream raises an error or blocks. The SDK requires the stream to be consumed first.

**Why it happens:** Developers try to get the final message immediately after opening the stream.

**How to avoid:** Always consume `stream.text_stream` (or `stream.__aiter__()`) first, then call `stream.get_final_message()` after the `async for` loop exits.

**Warning signs:** `RuntimeError: stream has not been consumed`.

### Pitfall 6: Narration Written to Wrong Stream Key

**What goes wrong:** `LogStreamer` writes to `job:{job_id}:logs`. If `run_agent_loop()` receives `job_id` from the context dict, the narration lands in the correct stream. If the key is constructed differently, the SSE endpoint at `/{job_id}/logs/stream` won't find the entries.

**Why it happens:** `run_agent_loop(context)` receives `project_id` and `user_id` but not necessarily `job_id`. The `job_id` is set in the worker's `process_next_job()` before calling the runner.

**How to avoid:** Ensure `context` dict always includes `job_id` (add it in `process_next_job` before calling `runner.run_agent_loop(context)`). Log key pattern: `job:{job_id}:logs`.

---

## Code Examples

### Complete Streaming Tool-Use Loop (Anthropic SDK 0.79.0)

```python
# Source: anthropic SDK 0.79.0 — AsyncMessageStreamManager + tool_use pattern
import anthropic

client = anthropic.AsyncAnthropic(api_key="...")

tools = [
    {
        "name": "write_file",
        "description": "Write content to a file.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "content": {"type": "string"},
            },
            "required": ["path", "content"],
        },
    }
]

messages = [{"role": "user", "content": "Create a hello world Python file."}]

while True:
    async with client.messages.stream(
        model="claude-sonnet-4-20250514",
        system="You are a co-founder. Narrate what you're doing.",
        messages=messages,
        tools=tools,
        max_tokens=4096,
    ) as stream:
        # Stream narration text
        async for chunk in stream.text_stream:
            print(chunk, end="", flush=True)

        response = await stream.get_final_message()

    if response.stop_reason == "end_turn":
        break  # Done

    # Find tool_use blocks
    tool_blocks = [b for b in response.content if b.type == "tool_use"]
    if not tool_blocks:
        break

    # Append assistant turn
    messages.append({"role": "assistant", "content": response.content})

    # Dispatch tools and collect results
    results = []
    for tb in tool_blocks:
        result = await dispatch_tool(tb.name, tb.input)
        results.append({
            "type": "tool_result",
            "tool_use_id": tb.id,
            "content": result,
        })

    # Append tool results as user turn
    messages.append({"role": "user", "content": results})
```

### Usage Tracking After Streaming Call

```python
# Source: TrackedAnthropicClient pattern in app/core/llm_config.py — adapted for streaming
response = await stream.get_final_message()
input_tokens = response.usage.input_tokens
output_tokens = response.usage.output_tokens
# Cache read tokens are also available if using prompt caching:
cache_read = getattr(response.usage, "cache_read_input_tokens", 0)
await tracked_client._track_usage(input_tokens + cache_read, output_tokens)
```

### Writing Narration to Existing SSE Channel

```python
# Source: app/services/log_streamer.py write_event() pattern
# LogStreamer already exists — just inject and use
streamer = LogStreamer(redis=redis, job_id=job_id, phase="agent")

# Write narration line — appears in frontend SSE stream immediately
await streamer.write_event("**Scaffolding** — Creating project structure", source="agent")
await streamer.write_event("Writing `app/main.py` with FastAPI entry point", source="agent")
```

### Sentence-Boundary Flushing Pattern

```python
# Accumulate text stream, flush at sentence boundaries
accumulated = ""
async for chunk in stream.text_stream:
    accumulated += chunk
    if accumulated.rstrip().endswith((".", "!", "?", "\n")):
        line = accumulated.strip()
        if line:
            await streamer.write_event(line, source="agent")
        accumulated = ""

# Flush remaining at end of block
if accumulated.strip():
    await streamer.write_event(accumulated.strip(), source="agent")
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| LangGraph TAOR-style nodes | Direct `messages.create()` loop with tool-use | Phase 40 removal decision | Simpler, no graph abstraction, full control over loop |
| `NarrationService` (external Claude call for stage narrative) | Native narration from agent text_stream | Phase 41 target | Agent narrates inline; no secondary LLM call needed |
| `_invoke_with_retry(client, system, messages)` pattern | `client.messages.stream(...)` context manager | Phase 41 new | Stream context manager handles SSE parsing; `get_final_message()` provides full response snapshot |

**Deprecated/outdated:**
- `_invoke_with_retry` return signature: returns `response.content[0].text` (string). Not suitable for tool-use response which has multiple content blocks. For TAOR loop, process `response.content` as a list directly.
- `TrackedAnthropicClient.messages.create()`: Synchronously awaits full response. Do not use for streaming calls in the TAOR loop.

---

## Open Questions

1. **Where does `run_agent_loop()` get the `idea_brief` and `understanding_qna` from?**
   - What we know: `run_agent_loop(context: dict)` receives `project_id`, `user_id`, `idea_brief`, `execution_plan` per the Runner protocol docstring.
   - What's unclear: Are `idea_brief` and `understanding_qna` passed in `context` by the caller (worker), or does `run_agent_loop` fetch them from DB internally?
   - Recommendation: Caller (worker or generation service) fetches artifacts from DB and includes them in `context`. This keeps `run_agent_loop` stateless and testable without DB. The worker already fetches `job_data` which includes `project_id`; add a pre-loop artifact fetch in the caller.

2. **Does the existing build endpoint trigger `run_agent_loop()` or `runner.run(state)`?**
   - What we know: `start_generation` in `generation.py` currently returns 501 when `AUTONOMOUS_AGENT=true`. The worker calls `generation_service.execute_build()` which calls `runner.run(state)`. The `run_agent_loop()` method is separate.
   - What's unclear: Phase 41 must wire `run_agent_loop()` into the execution path — either replace `runner.run()` or have `execute_build()` call `run_agent_loop()` when the runner is `AutonomousRunner`.
   - Recommendation: Add a check in `GenerationService.execute_build()`: if `isinstance(runner, AutonomousRunner)`, call `await runner.run_agent_loop(context)` instead of `runner.run(state)`. This avoids changing the runner protocol and keeps the GenerationService as the orchestrator. Alternatively, implement `run()` on `AutonomousRunner` to delegate to `run_agent_loop()` internally — cleaner but requires more refactoring of the state → context mapping.

3. **Should narration from the TAOR loop use a separate Redis stream key or the existing `job:{job_id}:logs` stream?**
   - What we know: `LogStreamer` writes to `job:{job_id}:logs`. The existing SSE endpoint at `/{job_id}/logs/stream` reads from this key. The frontend already renders this stream.
   - Recommendation: Use the same `job:{job_id}:logs` stream with `source="agent"` to distinguish from build tool output. The frontend already shows all stream entries. Using a separate key would require frontend changes.

---

## Validation Architecture

> `workflow.nyquist_validation` not present in `.planning/config.json` — standard test approach applies.

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.x with pytest-asyncio |
| Config file | `backend/pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `cd backend && .venv/bin/pytest tests/agent/test_taor_loop.py -x -q` |
| Full suite command | `cd backend && .venv/bin/pytest tests/ -x -q --ignore=tests/e2e` |
| Estimated runtime | ~15 seconds (unit tests, no LLM calls) |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| AGNT-01 | Loop executes end-to-end, reaches `end_turn`, no manual intervention | unit | `pytest tests/agent/test_taor_loop.py::test_loop_reaches_end_turn -x` | Wave 0 gap |
| AGNT-01 | Loop dispatches tool calls from `stop_reason="tool_use"` | unit | `pytest tests/agent/test_taor_loop.py::test_loop_dispatches_tools -x` | Wave 0 gap |
| AGNT-02 | System prompt contains idea_brief verbatim | unit | `pytest tests/agent/test_system_prompt.py::test_idea_brief_in_prompt -x` | Wave 0 gap |
| AGNT-02 | System prompt contains understanding QnA verbatim | unit | `pytest tests/agent/test_system_prompt.py::test_qna_in_prompt -x` | Wave 0 gap |
| AGNT-06 | Loop terminates at MAX_TOOL_CALLS=5 with structured message | unit | `pytest tests/agent/test_iteration_guard.py::test_iteration_cap -x` | Wave 0 gap |
| AGNT-06 | Repetition detection triggers on 3rd identical call in 10-call window | unit | `pytest tests/agent/test_iteration_guard.py::test_repetition_detection -x` | Wave 0 gap |
| AGNT-06 | Tool result >1000 tokens is middle-truncated with `[N words omitted]` | unit | `pytest tests/agent/test_iteration_guard.py::test_middle_truncation -x` | Wave 0 gap |

### Wave 0 Gaps (must be created before implementation)

- [ ] `tests/agent/test_taor_loop.py` — covers AGNT-01 (loop mechanics with `InMemoryToolDispatcher` + mock Anthropic stream)
- [ ] `tests/agent/test_system_prompt.py` — covers AGNT-02 (prompt building with idea_brief and QnA verbatim injection)
- [ ] `tests/agent/test_iteration_guard.py` — covers AGNT-06 (all three safety guards: cap, repetition, truncation)
- [ ] `backend/app/agent/tools/dispatcher.py` — ToolDispatcher protocol + InMemoryToolDispatcher
- [ ] `backend/app/agent/loop/safety.py` — IterationGuard class
- [ ] `backend/app/agent/loop/system_prompt.py` — build_system_prompt() function

---

## Sources

### Primary (HIGH confidence)

- Anthropic SDK 0.79.0 installed at `backend/.venv/lib/python3.12/site-packages/anthropic/` — verified `messages.stream()` signature, `AsyncMessageStreamManager`, `text_stream`, `get_final_message()`, `ToolParam`, `ToolUseBlock`
- `backend/.venv/lib/python3.12/site-packages/anthropic/lib/streaming/_messages.py` — verified `text_delta` event handling, `content_block_start/stop` events, `tool_use` content block accumulation
- `backend/app/services/log_streamer.py` — verified `write_event()` API for narration injection
- `backend/app/api/routes/logs.py` — verified SSE endpoint at `/{job_id}/logs/stream` reads `job:{job_id}:logs` stream
- `backend/app/core/llm_config.py` — verified `TrackedAnthropicClient` does NOT support streaming; raw `AsyncAnthropic` required
- `backend/app/agent/runner.py` — verified `run_agent_loop(context: dict)` signature and expected return shape

### Secondary (MEDIUM confidence)

- `backend/app/agent/llm_helpers.py` — existing `_invoke_with_retry` pattern with tenacity; same retry strategy applicable to streaming loop

### Tertiary (LOW confidence)

- Word-count as token proxy: widely used approximation (1 word ≈ 1 token for English prose); no official Anthropic validation for this specific use case

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — Anthropic SDK 0.79.0 verified in-situ, all APIs inspected directly from installed source
- Architecture: HIGH — derived from existing codebase patterns (LogStreamer, Runner protocol, TrackedAnthropicClient)
- Pitfalls: HIGH — identified by inspecting SDK source (TrackedAnthropicClient non-streaming), Anthropic API constraints (message ordering), and existing project patterns

**Research date:** 2026-02-25
**Valid until:** 2026-03-25 (Anthropic SDK APIs are stable; internal patterns won't change)
