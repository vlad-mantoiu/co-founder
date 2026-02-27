# Phase 44: Native Agent Capabilities - Research

**Researched:** 2026-02-27
**Domain:** LangGraph-era service replacement — TAOR tool-dispatch pattern
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Narration voice & style**
- Confident builder personality — "I'm setting up auth with Clerk because your brief specified enterprise-grade security." Direct, explains reasoning, sounds like a senior engineer partner
- Each narration includes WHAT the agent is doing AND WHY — ties decisions back to the founder's original brief/answers when relevant
- Narrate at significant actions only — phase/task boundaries and major decisions. Skip individual file writes, grep calls, small edits. ~1 narration per significant step
- Agent's system prompt includes narration guidance: "Narrate significant actions in first-person co-founder voice. Reference the founder's brief when relevant." The agent decides when and what to narrate — narrate() is a passthrough, not a validator

**Documentation structure**
- Agent writes doc sections progressively as it builds — "I just built auth, let me document how login works." Docs reflect the actual implementation
- 4 sections: overview, features, getting_started, faq — matches existing Redis hash structure in job:{id}:docs
- Documentation written for end-users of the built product — "To sign up, click Create Account..." The founder can hand these to their users
- Separate document() tool distinct from narrate() — document(section='getting_started', content='...'). Writes to job:{id}:docs Redis hash

**Narration delivery timing**
- Each narrate() call emits an SSE event immediately — founder sees updates in real time as the agent works
- Narration API calls count toward the token budget — honest cost accounting, can trigger sleep if budget consumed
- Reuse existing narration SSE event type — frontend already handles it, zero UI changes needed
- Narrations persist to the job:{id}:logs Redis stream — late-connecting founders can replay all past narrations

**Service deletion & tool integration**
- Full deletion of NarrationService and DocGenerationService — delete files, remove all imports, delete their tests, remove route references. grep for zero remaining references
- narrate() and document() tools added to existing tool dispatch system alongside read_file, write_file, etc. — no separate dispatcher or registry
- Write dedicated tests for narrate() and document() tools — verify SSE emission, Redis persistence, budget tracking. Replace deleted NarrationService tests

### Claude's Discretion
- Exact SSE event type name to reuse (inspect existing NarrationService SSE events)
- How narrate() and document() are registered in the tool dispatch system (tool definition format)
- System prompt wording for narration guidance
- Whether document() also emits SSE events or only writes to Redis

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| AGNT-04 | Agent handles narration natively via narrate() tool — first-person co-founder voice describing what it's doing and why | narrate() tool definition added to AGENT_TOOLS; InMemoryToolDispatcher and E2BToolDispatcher both handle it; budget integration via existing record_call_cost() pattern; SSE via JobStateMachine.publish_event() using SSEEventType.BUILD_STAGE_STARTED (already consumed by frontend) |
| AGNT-05 | Agent handles documentation generation natively as part of its workflow — no separate DocGenerationService | document() tool definition added to AGENT_TOOLS; dispatcher writes to job:{id}:docs Redis hash via existing hset pattern; section validation against SECTION_ORDER = ["overview", "features", "getting_started", "faq"]; SSE via SSEEventType.DOCUMENTATION_UPDATED |
</phase_requirements>

---

## Summary

Phase 44 replaces NarrationService and DocGenerationService with two native agent tools: `narrate()` and `document()`. The key shift is from fire-and-forget background tasks triggered at stage boundaries to inline tool calls made by the agent mid-loop, in its own voice and on its own timing.

The existing TAOR loop infrastructure already handles 95% of what is needed. The dispatcher pattern in `app/agent/tools/dispatcher.py` is the only place that needs extending — both `InMemoryToolDispatcher` and `E2BToolDispatcher` gain two new tool name handlers. The tool definitions in `app/agent/tools/definitions.py` grow by two entries. The system prompt in `app/agent/loop/system_prompt.py` gains a clarified narration instruction (replacing the current instruction to narrate before/after every tool call with one that tells the agent to call `narrate()` at significant steps instead).

The deletion side is a surgical grep-and-remove. There are exactly 10 files that reference NarrationService or DocGenerationService. Only `generation_service.py` uses them in the old non-autonomous path — that path is still live (autonomous_agent=False uses RunnerFake/RunnerReal), so the import and singleton must be removed entirely and the old narration/doc-gen calls in generation_service.py must be removed too. The frontend reads `job:{id}:docs` and the `job:{id}:logs` stream — both Redis contracts are preserved by the native tools.

**Primary recommendation:** Add narrate() and document() to AGENT_TOOLS and both dispatcher impls, wire narrate() to emit SSE + Redis stream exactly as the old NarrationService did, wire document() to hset job:{id}:docs + emit DOCUMENTATION_UPDATED SSE, delete the two service files and their tests, scrub all 10 import sites.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| anthropic (AsyncAnthropic) | >=0.40.0 (project-pinned) | narrate() makes a separate Anthropic API call with the narration text content as input | Project pattern — all LLM calls use this client; TrackedAnthropicClient is NOT used for narrate() (streaming not needed here, but cost must be recorded via record_call_cost separately) |
| redis.asyncio | >=5.2.0 (project-pinned) | hset for doc sections; xadd for narration to logs stream | Existing project pattern — all Redis I/O uses this |
| structlog | >=25.0.0 (project-pinned) | Logging inside tool handlers | Project-wide logger pattern |
| fakeredis.aioredis | >=2.26.0 (dev dep) | Unit test Redis layer for dispatcher tests | Already used in all agent tests |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest-asyncio | >=0.24.0 (dev dep) | async unit tests (asyncio_mode="auto") | All new tests |
| unittest.mock AsyncMock | stdlib | Mocking Redis and state_machine in tests | Standard pattern — all existing tests use it |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Separate Anthropic call for narrate() content | Let the agent's narration text flow through directly as the tool input | narrate() is a passthrough — agent writes the narration text; the tool just emits it. No LLM call needed inside the tool handler. This is the correct interpretation per CONTEXT.md: "The agent decides when and what to narrate — narrate() is a passthrough, not a validator" |
| SSEEventType.BUILD_STAGE_STARTED for narration | New SSEEventType constant | CONTEXT.md locked: "Reuse existing narration SSE event type — frontend already handles it, zero UI changes needed." BUILD_STAGE_STARTED is what NarrationService used. |

**Installation:** No new packages required — all dependencies are already in pyproject.toml.

---

## Architecture Patterns

### How Tool Dispatch Works (Existing Pattern)

The tool dispatch system has three layers:

1. **`AGENT_TOOLS`** in `app/agent/tools/definitions.py` — the JSON schema list passed to `messages.create(tools=AGENT_TOOLS)`. Claude uses this to decide which tools to call and what arguments to pass.

2. **`ToolDispatcher` Protocol** in `app/agent/tools/dispatcher.py` — `dispatch(tool_name, tool_input) -> str | list[dict]`. All dispatchers implement this.

3. **`InMemoryToolDispatcher`** (tests) and **`E2BToolDispatcher`** (production) — both implement `dispatch()` with if/elif chains for each tool name.

The TAOR loop calls `dispatcher.dispatch(tool_name, tool_input)` for every tool_use block. The result is appended to tool_results. For narrate() and document(), the result can be a simple acknowledgment string.

### narrate() Tool Pattern

**Tool definition (adds to AGENT_TOOLS):**
```python
{
    "name": "narrate",
    "description": (
        "Narrate a significant action in first-person co-founder voice. "
        "Call this when you start or complete a major step — authentication setup, "
        "database schema design, API routing, etc. "
        "Include WHAT you are doing AND WHY, referencing the founder's brief when relevant. "
        "Skip minor actions like individual file writes or grep calls. "
        "Example: 'I'm setting up auth with Clerk because your brief specified enterprise-grade security.'"
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "message": {
                "type": "string",
                "description": "First-person narration of the significant action being taken.",
            },
        },
        "required": ["message"],
    },
},
```

**Dispatcher handler (InMemoryToolDispatcher and E2BToolDispatcher):**
```python
if tool_name == "narrate":
    return await self._narrate(tool_input, job_id, redis, state_machine)
```

The `_narrate()` method on both dispatchers:
1. Emits SSE event via `state_machine.publish_event()` with `type = SSEEventType.BUILD_STAGE_STARTED` (existing type, frontend handles it)
2. Writes to `job:{job_id}:logs` Redis stream via `streamer.write_event(message, source="agent")`
3. Returns `"[narration emitted]"` to the agent (passthrough — no Anthropic call inside the tool)

**Budget tracking for narrate():** The narrate() tool itself makes no API call. The cost of the agent thinking and deciding to call narrate() is already captured in the TAOR loop's `record_call_cost()` call after every streaming response from Anthropic. No additional budget tracking is needed inside the narrate() handler.

**CONTEXT.md clarification:** "Narration API calls count toward the token budget" — this refers to the agent's own API call that includes narrate() in its tool_use decision, NOT a separate Anthropic call inside the handler. The budget daemon already tracks all Anthropic calls made by the TAOR loop.

### document() Tool Pattern

**Tool definition (adds to AGENT_TOOLS):**
```python
{
    "name": "document",
    "description": (
        "Write a section of end-user documentation for the product being built. "
        "Call this progressively as you complete major features — document auth after setting it up, "
        "document onboarding after building it. "
        "Sections: 'overview', 'features', 'getting_started', 'faq'. "
        "Write for the product's end users, not the founder. Plain English, no technical jargon, "
        "no file paths, no framework names. Use 'you' and 'your' throughout."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "section": {
                "type": "string",
                "enum": ["overview", "features", "getting_started", "faq"],
                "description": "Documentation section to write.",
            },
            "content": {
                "type": "string",
                "description": "Markdown content for the section.",
            },
        },
        "required": ["section", "content"],
    },
},
```

**Dispatcher handler:**
```python
if tool_name == "document":
    return await self._document(tool_input, job_id, redis, state_machine)
```

The `_document()` method:
1. Validates section is in `["overview", "features", "getting_started", "faq"]`
2. Writes to Redis: `await redis.hset(f"job:{job_id}:docs", section, content)`
3. Emits SSE: `state_machine.publish_event(job_id, {"type": SSEEventType.DOCUMENTATION_UPDATED, "section": section})`
4. Returns `f"[doc section '{section}' written]"` to agent

**Redis key:** `job:{job_id}:docs` hash — same key the existing DocGenerationService wrote to. The frontend reads this key and expects the same hash structure. Contract preserved.

### Dispatcher Context Problem

The current dispatchers (`InMemoryToolDispatcher`, `E2BToolDispatcher`) take no constructor arguments related to `job_id`, `redis`, or `state_machine`. The TAOR loop passes them via `context["dispatcher"]`. For narrate() and document() to emit SSE and write to Redis, the dispatcher needs access to these.

**Two solutions — choose one:**

**Option A (recommended): Inject context into dispatcher at construction**
Pass `job_id`, `redis`, and `state_machine` when creating the E2BToolDispatcher and InMemoryToolDispatcher. The TAOR loop already constructs the dispatcher from `context["dispatcher"]` or creates a default `InMemoryToolDispatcher()`. Add optional parameters:
```python
class InMemoryToolDispatcher:
    def __init__(
        self,
        failure_map=None,
        job_id: str = "",
        redis=None,
        state_machine=None,
    ) -> None:
        ...
```

**Option B: Pass context dict per dispatch call**
Change the Protocol to `dispatch(tool_name, tool_input, context)`. Broader breaking change.

**Option A is correct.** The ToolDispatcher Protocol needs to stay backward-compatible (`dispatch(tool_name, tool_input)`). The context is injected once at construction. The TAOR loop already has access to `job_id`, `redis`, and `state_machine` when it creates dispatchers.

### System Prompt Update

The existing `_PERSONA_SECTION` in `system_prompt.py` already says:
```
**Narration (mandatory):**
- Narrate before every tool call: "I'm creating the auth module..."
- Narrate after every tool call: "Auth module created. Moving to routes."
```

This is the OLD pattern (text narration in the streamed response). After Phase 44, narration happens via the `narrate()` tool instead. The system prompt must be updated to:
1. Remove "narrate before/after every tool call" instruction
2. Add "Call narrate() at significant steps — phase starts, major design decisions, significant completions"
3. Add "Call document() progressively as you complete major features"
4. Keep the co-founder voice and "we/I" voice guidance

### SSE Event Type Decision (Claude's Discretion)

The existing `SSEEventType.BUILD_STAGE_STARTED` is what `NarrationService.narrate()` used. Per CONTEXT.md locked decision: "Reuse existing narration SSE event type — frontend already handles it, zero UI changes needed."

Use `SSEEventType.BUILD_STAGE_STARTED` for narrate() tool SSE events. The payload shape the frontend expects:
```python
{
    "type": SSEEventType.BUILD_STAGE_STARTED,
    "stage": "agent",       # use "agent" as stage identifier
    "narration": message,   # the narration text
    "agent_role": "Engineer",
    "time_estimate": "",
}
```

For document(), use `SSEEventType.DOCUMENTATION_UPDATED` with `"section": section`. Frontend already handles both.

### Whether document() Emits SSE (Claude's Discretion)

YES — document() should emit `SSEEventType.DOCUMENTATION_UPDATED`. The frontend's document panel subscribes to this event to show new sections in real time. Without SSE, sections only appear on hard refresh. Emit it.

### Deletion Scope

Files to DELETE outright:
- `backend/app/services/narration_service.py`
- `backend/app/services/doc_generation_service.py`
- `backend/tests/services/test_narration_service.py`
- `backend/tests/services/test_narration_wiring.py`
- `backend/tests/services/test_doc_generation_service.py`
- `backend/tests/services/test_doc_generation_wiring.py`
- `backend/tests/services/test_changelog_wiring.py`

Files to EDIT (remove imports and usage):
- `backend/app/services/generation_service.py` — remove `from app.services.doc_generation_service import DocGenerationService`, `from app.services.narration_service import NarrationService`, `_doc_generation_service = DocGenerationService()`, `_narration_service = NarrationService()`, and all 8 `create_task()` calls that invoke them
- `backend/app/queue/state_machine.py` — no import, but grep confirms it appears in comments about DOCUMENTATION_UPDATED (these are benign docstrings, not imports; leave them)

After deletion, run: `grep -r "narration_service\|doc_generation_service\|NarrationService\|DocGenerationService" backend/` must return zero results from non-test, non-deleted files.

### Recommended Project Structure (new files)

No new files needed. All changes are:
- Edits to `app/agent/tools/definitions.py` (add 2 tool schemas)
- Edits to `app/agent/tools/dispatcher.py` (add 2 handlers to both dispatchers + constructor params)
- Edits to `app/agent/tools/e2b_dispatcher.py` (add 2 handlers + constructor params)
- Edits to `app/agent/loop/system_prompt.py` (update narration instruction)
- Deletions of 7 files

New test files:
- `backend/tests/agent/test_narrate_tool.py` — unit tests for narrate() dispatch
- `backend/tests/agent/test_document_tool.py` — unit tests for document() dispatch

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Budget tracking for narrate() | Additional Anthropic API call in the tool handler | None needed — budget is tracked by the TAOR loop's existing record_call_cost() after every streaming response | The narrate() handler makes no LLM call; budget is already captured upstream |
| SSE delivery for narrate() | Custom Redis pub/sub code | `state_machine.publish_event()` (existing) | JobStateMachine already handles publish to job:{id}:events channel |
| Log stream persistence | Direct xadd calls | `streamer.write_event()` (existing LogStreamer) | LogStreamer handles ANSI stripping, secret redaction, TTL, MAXLEN |
| Section validation for document() | Custom validator | Python `if section not in SECTION_ORDER` guard | Simple list membership check is sufficient |
| Safety filtering on narration/docs content | Re-implementing _SAFETY_PATTERNS from DocGenerationService | No safety filter on native tool content | The agent is already operating inside the safe tool-use context. The safety filter was needed to sanitize Claude's LLM output from a separate Haiku call. The agent's own tool input is already constrained by the tool schema. |

**Key insight:** narrate() and document() are thin wrappers around existing infrastructure. The agent writes the content; the tools just route it to the right Redis keys and SSE channels. No Claude calls inside handlers.

---

## Common Pitfalls

### Pitfall 1: Dispatcher Context Unavailability
**What goes wrong:** narrate() and document() tools need `job_id`, `redis`, and `state_machine` to emit SSE and write Redis. Current dispatcher constructors take neither.
**Why it happens:** The dispatcher was designed for stateless tools (read_file, write_file are all sandbox-relative). Narration and documentation require job-level context.
**How to avoid:** Inject optional `job_id`, `redis`, `state_machine` into both `InMemoryToolDispatcher` and `E2BToolDispatcher` constructors. The TAOR loop already creates these with access to the full context — thread the values through.
**Warning signs:** Tests fail with AttributeError on `self._redis` or `self._state_machine`; tool returns a generic "[narrate completed]" without actually emitting SSE.

### Pitfall 2: Double-Counting Budget
**What goes wrong:** If narrate() handler makes a separate Anthropic API call for the narration content, budget is counted twice — once for the call and once for the parent TAOR iteration that spawned the tool call.
**Why it happens:** Confusion between old NarrationService model (Haiku call to generate narration text) and new model (agent writes narration text directly).
**How to avoid:** narrate() is a passthrough. The `message` parameter IS the narration. No Anthropic call inside the handler. The agent wrote the message; just emit it.
**Warning signs:** Test shows two budget record_call_cost calls per narrate() invocation.

### Pitfall 3: Orphan Imports After Deletion
**What goes wrong:** Deleting narration_service.py and doc_generation_service.py leaves broken imports in generation_service.py, causing startup ImportError.
**Why it happens:** generation_service.py has module-level imports and creates module-level singletons.
**How to avoid:** Edit generation_service.py BEFORE or in the same commit as deleting the service files. Run `pytest -x` immediately after deletion to catch import errors.
**Warning signs:** `ImportError: cannot import name 'NarrationService' from 'app.services.narration_service'`

### Pitfall 4: generation_service.py Old Path Still Calls Services
**What goes wrong:** The AUTONOMOUS_AGENT=False path in generation_service.py still calls `_narration_service.narrate()` and `_doc_generation_service.generate()`. After deletion these calls fail.
**Why it happens:** The old pipeline (RunnerFake/RunnerReal) is still exercised in tests with `autonomous_agent=False`. Even though the default production path is AUTONOMOUS_AGENT=True, the old code path still runs in CI via test_narration_wiring.py and test_doc_generation_wiring.py.
**How to avoid:** Delete the 8 `create_task()` invocations from generation_service.py at the same time as deleting the service files. The wiring tests must also be deleted.
**Warning signs:** test_narration_wiring.py or test_doc_generation_wiring.py still running and referencing deleted symbols.

### Pitfall 5: InMemoryToolDispatcher narrate() Silently No-ops in Tests
**What goes wrong:** In tests without Redis/state_machine, calling narrate() through InMemoryToolDispatcher returns a stub string but never emits SSE or writes to Redis. Tests that verify SSE emission pass but the real behavior is untested.
**Why it happens:** InMemoryToolDispatcher is used in TAOR loop tests that don't inject Redis.
**How to avoid:** Write dedicated `test_narrate_tool.py` that constructs InMemoryToolDispatcher WITH a fakeredis instance and a mock state_machine. Verify `state_machine.publish_event.call_count == 1` and `redis.hkeys("job:X:logs")` returns entries.
**Warning signs:** Tests pass but no assertion on state_machine calls.

### Pitfall 6: System Prompt Conflict
**What goes wrong:** The updated system prompt removes "narrate before/after every tool call" but the agent falls back to text-only narration in its streaming response instead of calling narrate(). The old streaming narration accumulates in the log stream but is not formatted as an SSE event.
**Why it happens:** The old `_PERSONA_SECTION` explicitly instructed text narration. Without the narrate() tool schema in the system prompt instructions, the agent may not know to call it.
**How to avoid:** The tool description in AGENT_TOOLS itself educates the agent on when to call narrate(). The system prompt update should explicitly say "Use the narrate() tool instead of narrating in plain text."
**Warning signs:** Agent stops calling narrate() tool after first iteration; activity feed shows streaming text but no structured SSE narration events.

---

## Code Examples

### narrate() Dispatcher Handler Pattern
```python
# In InMemoryToolDispatcher (and E2BToolDispatcher)
async def _narrate(self, tool_input: dict) -> str:
    """Emit narration as SSE + Redis stream entry."""
    message = tool_input.get("message", "")
    if not message:
        return "[narrate: empty message ignored]"

    # Emit SSE for real-time frontend update
    if self._state_machine and self._job_id:
        await self._state_machine.publish_event(
            self._job_id,
            {
                "type": SSEEventType.BUILD_STAGE_STARTED,
                "stage": "agent",
                "narration": message,
                "agent_role": "Engineer",
                "time_estimate": "",
            },
        )

    # Persist to log stream for replay
    if self._redis and self._job_id:
        from app.services.log_streamer import LogStreamer
        streamer = LogStreamer(redis=self._redis, job_id=self._job_id, phase="agent")
        await streamer.write_event(message, source="agent")

    return "[narration emitted]"
```

### document() Dispatcher Handler Pattern
```python
async def _document(self, tool_input: dict) -> str:
    """Write doc section to Redis hash + emit SSE."""
    from app.queue.state_machine import SSEEventType

    VALID_SECTIONS = ["overview", "features", "getting_started", "faq"]
    section = tool_input.get("section", "")
    content = tool_input.get("content", "")

    if section not in VALID_SECTIONS:
        return f"[document: invalid section '{section}'. Must be one of: {VALID_SECTIONS}]"
    if not content.strip():
        return f"[document: empty content for section '{section}' ignored]"

    if self._redis and self._job_id:
        await self._redis.hset(f"job:{self._job_id}:docs", section, content)
        if self._state_machine:
            await self._state_machine.publish_event(
                self._job_id,
                {
                    "type": SSEEventType.DOCUMENTATION_UPDATED,
                    "section": section,
                },
            )

    return f"[doc section '{section}' written ({len(content)} chars)]"
```

### InMemoryToolDispatcher Constructor Update
```python
def __init__(
    self,
    failure_map: dict[tuple[str, int], Exception] | None = None,
    job_id: str = "",
    redis=None,
    state_machine=None,
) -> None:
    self._fs: dict[str, str] = {}
    self._call_counts: dict[str, int] = {}
    self._failure_map: dict[tuple[str, int], Exception] = failure_map or {}
    self._job_id = job_id
    self._redis = redis
    self._state_machine = state_machine
```

### System Prompt Narration Instruction Update
Replace the old text narration instructions in `_PERSONA_SECTION`:
```python
# OLD:
"""**Narration (mandatory):**
- Narrate before every tool call: "I'm creating the auth module..."
- Narrate after every tool call: "Auth module created. Moving to routes."
- Narrate reasoning alongside actions — share WHY decisions are made.
- After each major group of work, provide a section summary..."""

# NEW:
"""**Narration (mandatory):**
- Call narrate() at significant steps: phase starts, major architectural decisions,
  feature completions. ~1 narrate() call per major step, not per file write.
- Include WHAT you are doing AND WHY. Reference the founder's brief when it adds value.
  Example: "I'm setting up auth with Clerk because your brief specified enterprise-grade security."
- Do NOT narrate in plain text — use the narrate() tool so narration reaches the activity feed.

**Documentation (progressive):**
- Call document() as you complete major features — document auth after building it, not at the end.
- Write for the product's end users. Plain English, "you/your", no technical jargon.
- Use sections: overview, features, getting_started, faq."""
```

### Test Pattern for narrate() Tool
```python
# backend/tests/agent/test_narrate_tool.py
import fakeredis.aioredis
import pytest
from unittest.mock import AsyncMock, MagicMock
from app.agent.tools.dispatcher import InMemoryToolDispatcher

@pytest.mark.unit
async def test_narrate_emits_sse_event():
    redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
    state_machine = MagicMock()
    state_machine.publish_event = AsyncMock(return_value=None)

    dispatcher = InMemoryToolDispatcher(
        job_id="test-narrate-job-001",
        redis=redis,
        state_machine=state_machine,
    )
    result = await dispatcher.dispatch(
        "narrate",
        {"message": "I'm setting up auth with Clerk."},
    )
    assert result == "[narration emitted]"
    state_machine.publish_event.assert_called_once()
    call_kwargs = state_machine.publish_event.call_args[0]
    payload = call_kwargs[1]
    assert payload["narration"] == "I'm setting up auth with Clerk."
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| NarrationService: separate Haiku LLM call generates stage narration text at stage boundaries | narrate() tool: agent writes narration text inline, tool routes to SSE + Redis | Phase 44 | Narration is in co-founder voice (same model as builder); no added latency for separate API call; narration tied to actual agent reasoning |
| DocGenerationService: background asyncio.create_task fired after scaffold, writes 4 sections in one shot | document() tool: agent calls document(section=...) progressively as it builds each feature | Phase 44 | Documentation reflects actual implementation; written incrementally; no background task management |
| NarrationService uses "we" voice ("We're setting up your project structure") | narrate() tool uses "I" voice ("I'm setting up auth because...") | Phase 44 per CONTEXT.md | "I" is more natural for co-founder partner; "we" is reserved for shared direction per existing _PERSONA_SECTION |

**Deprecated/outdated:**
- `NarrationService`: Remove. Was a legacy service predating the TAOR loop.
- `DocGenerationService`: Remove. Was a legacy service predating the TAOR loop.
- `generate_changelog()` on DocGenerationService: Remove with the service. Changelog generation is not scoped to Phase 44.

---

## Open Questions

1. **LogStreamer instance reuse vs. per-call creation**
   - What we know: LogStreamer is stateful (has stdout/stderr buffers for E2B callbacks). In the narrate() handler, we only call write_event() directly (no buffering needed).
   - What's unclear: Should narrate() create a new LogStreamer per call, or should the dispatcher hold a persistent LogStreamer instance?
   - Recommendation: Create a new LogStreamer per narrate() call for simplicity — the buffers are unused (we call write_event directly) and LogStreamer construction is cheap. Alternatively, expose write_event as a standalone function to avoid the class entirely. Either is fine.

2. **generation_service.py changelog cleanup**
   - What we know: `DocGenerationService.generate_changelog()` is called in generation_service.py at line 716 for iteration builds. This call must be removed.
   - What's unclear: Does changelog generation need a replacement in Phase 44 or later?
   - Recommendation: Remove the changelog call without replacement — changelog generation is not in AGNT-04/AGNT-05 scope. The agent can narrate changes naturally.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.3 + pytest-asyncio 0.24 |
| Config file | `backend/pyproject.toml` — `[tool.pytest.ini_options]` |
| Quick run command | `cd backend && python -m pytest tests/agent/test_narrate_tool.py tests/agent/test_document_tool.py -x -q` |
| Full suite command | `cd backend && python -m pytest tests/ -x -q` |
| Estimated runtime | ~8-15 seconds (932 tests currently, will drop by ~60 when wiring tests deleted) |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| AGNT-04 | narrate() tool dispatched by InMemoryToolDispatcher → emits SSE + writes to Redis stream | unit | `pytest tests/agent/test_narrate_tool.py -x` | No — Wave 0 gap |
| AGNT-04 | narrate() tool schema present in AGENT_TOOLS with required "message" field | unit | `pytest tests/agent/test_narrate_tool.py::test_narrate_tool_in_agent_tools -x` | No — Wave 0 gap |
| AGNT-04 | narrate() SSE event uses existing BUILD_STAGE_STARTED event type | unit | `pytest tests/agent/test_narrate_tool.py::test_narrate_emits_build_stage_started -x` | No — Wave 0 gap |
| AGNT-04 | Budget daemon still fires (via existing TAOR loop tracking) when narrate() is called | unit | Part of existing `test_taor_budget_integration.py` — verify narrate() tool_use call is counted as a TAOR iteration | Partially covered in existing file |
| AGNT-05 | document() tool dispatched → hsets job:{id}:docs Redis hash for valid section | unit | `pytest tests/agent/test_document_tool.py -x` | No — Wave 0 gap |
| AGNT-05 | document() tool dispatched → emits DOCUMENTATION_UPDATED SSE | unit | `pytest tests/agent/test_document_tool.py::test_document_emits_documentation_updated_sse -x` | No — Wave 0 gap |
| AGNT-05 | document() rejects invalid section names | unit | `pytest tests/agent/test_document_tool.py::test_document_invalid_section -x` | No — Wave 0 gap |
| AGNT-04+05 | Zero remaining imports of NarrationService/DocGenerationService in codebase after deletion | static/grep | `grep -r "NarrationService\|DocGenerationService\|narration_service\|doc_generation_service" backend/ && echo FAIL \|\| echo PASS` | No — post-deletion verification |
| AGNT-04+05 | pytest suite passes with zero references to deleted modules (import check) | unit | `cd backend && python -m pytest tests/ -x -q` | Existing suite (must pass after deletions) |

### Nyquist Sampling Rate
- **Minimum sample interval:** After every committed task → run: `cd backend && python -m pytest tests/agent/ -x -q`
- **Full suite trigger:** Before merging final task of any plan wave: `cd backend && python -m pytest tests/ -x -q`
- **Phase-complete gate:** Full suite green before `/gsd:verify-work` runs
- **Estimated feedback latency per task:** ~5-8 seconds (agent tests only)

### Wave 0 Gaps (must be created before implementation)
- [ ] `backend/tests/agent/test_narrate_tool.py` — covers AGNT-04: narrate() SSE emission, Redis stream write, tool schema, budget passthrough
- [ ] `backend/tests/agent/test_document_tool.py` — covers AGNT-05: document() Redis hset, SSE emission, invalid section rejection, section enum validation

*(No new framework install needed — pytest-asyncio and fakeredis are already in dev dependencies)*

---

## Sources

### Primary (HIGH confidence)
- Direct codebase inspection — `backend/app/agent/tools/dispatcher.py` — ToolDispatcher Protocol, InMemoryToolDispatcher implementation
- Direct codebase inspection — `backend/app/agent/tools/definitions.py` — AGENT_TOOLS JSON schema list structure
- Direct codebase inspection — `backend/app/agent/runner_autonomous.py` — TAOR loop, context dict keys, dispatcher injection pattern
- Direct codebase inspection — `backend/app/services/narration_service.py` — SSEEventType.BUILD_STAGE_STARTED payload shape, NarrationService pattern
- Direct codebase inspection — `backend/app/services/doc_generation_service.py` — job:{id}:docs Redis hash structure, SECTION_ORDER, _SAFETY_PATTERNS
- Direct codebase inspection — `backend/app/queue/state_machine.py` — SSEEventType constants, publish_event() signature
- Direct codebase inspection — `backend/app/services/log_streamer.py` — write_event() method, Redis stream key format
- Direct codebase inspection — `backend/app/services/generation_service.py` — all 8 narrate/docgen call sites that need removal
- Direct codebase inspection — `backend/pyproject.toml` — test framework, asyncio_mode="auto", markers
- Grep output — 10 files containing NarrationService/DocGenerationService references — exact deletion scope

### Secondary (MEDIUM confidence)
- `.planning/STATE.md` accumulated decisions — confirmed NarrationService deletion blocked on Phase 44, AutonomousRunner context dict shape, per-tool cost tracking patterns

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries already in pyproject.toml; no new deps
- Architecture: HIGH — all patterns verified from actual production code; no speculation
- Pitfalls: HIGH — derived from reading actual implementation; pitfall 3/4 verified by inspecting generation_service.py import lines
- Deletion scope: HIGH — grep returned exact 10-file list with line-level context

**Research date:** 2026-02-27
**Valid until:** 2026-03-28 (stable — existing codebase patterns won't change before Phase 44 executes)
