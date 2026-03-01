# Phase 47: v0.7 Gap Closure — REST Bootstrap + Escalation SSE - Research

**Researched:** 2026-03-01
**Domain:** Redis key writing in the TAOR loop + SSE event emission from REST endpoint
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Redis key: budget_pct**
- Write `cofounder:agent:{session_id}:budget_pct` after each `record_call_cost()` call in `runner_autonomous.py`
- Value: integer 0-100 representing percentage of daily budget consumed
- TTL: 90 seconds (matches SSE heartbeat window — stale data auto-expires)
- `GET /api/jobs/{id}/status` already reads this key — no API changes needed

**Redis key: wake_at**
- Write `cofounder:agent:{session_id}:wake_at` on sleep transition in `runner_autonomous.py`
- Value: ISO 8601 UTC timestamp of next budget refresh (next midnight UTC or subscription reset)
- TTL: match sleep duration (key expires when agent wakes)
- `AgentStateBadge` countdown timer already reads this key — no frontend changes needed

**SSE event: agent.escalation_resolved**
- Emit via `state_machine.publish_event()` after `session.commit()` in `resolve_escalation()` endpoint
- Event type: `AGENT_ESCALATION_RESOLVED` (constant already exists in SSE event types)
- Payload: escalation_id, resolution text, resolved_at timestamp
- Frontend handler already exists — no frontend changes needed

### Claude's Discretion
- Exact TTL values (90s suggested but Claude can adjust based on codebase patterns)
- Test structure and mocking approach
- Whether to combine Redis writes into a helper or keep inline

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| AGNT-08 | Escalation surfaces problem description, what was tried, and recommended action to founder via existing DecisionConsole pattern | Gap: `agent.escalation_resolved` SSE never emitted from resolve endpoint. Fix: call `state_machine.publish_event()` after `session.commit()` in `resolve_escalation()`. All infrastructure (SSEEventType constant, frontend handler, publish_event method) already exists. |
| UIAG-04 | Dashboard displays agent state: working, sleeping, waiting-for-input, error | Gap: `budget_pct` and `wake_at` Redis keys never written. Fix: write both keys at correct integration points in `run_agent_loop()`. REST bootstrap endpoint already reads both keys. Frontend components already handle them. |
</phase_requirements>

## Summary

Phase 47 closes three surgical integration gaps found by the v0.7 milestone audit. All three fixes touch code that is already wired end-to-end — the reading side (REST endpoint, frontend) and the infrastructure (SSEEventType constants, `publish_event` method) already exist. What's missing is the writing side: two Redis keys that `runner_autonomous.py` never writes, and one SSE event that `escalations.py` never emits.

The work is additive, not architectural. No new services, no new models, no new frontend components. Each fix is 2-5 lines of code at a precisely identified location. The primary risk is test coverage: all three fixes must be TDD'd against the existing mock infrastructure established in Phases 43-46.

The three changes are independent and can be planned and verified as a single plan wave, since they touch different files (`runner_autonomous.py` for gaps 1-2, `escalations.py` for gap 3).

**Primary recommendation:** Write one plan covering all three gaps in a single wave. Each fix has a clearly identified insertion point, uses only existing infrastructure, and requires 1-2 new test assertions to verify.

## Standard Stack

### Core (already installed — no new dependencies)
| Component | Version/Key | Purpose | Why Standard |
|-----------|-------------|---------|--------------|
| `redis.asyncio.Redis` | project dependency | `await redis.set(key, value, ex=ttl)` | Existing pattern throughout `runner_autonomous.py` |
| `app.queue.state_machine.JobStateMachine` | in-codebase | `await state_machine.publish_event(job_id, event)` | Already used in escalations flow |
| `app.queue.state_machine.SSEEventType` | in-codebase | `SSEEventType.AGENT_ESCALATION_RESOLVED` constant | Already defined, Phase 45 added it |
| `datetime.UTC`, `datetime.now(UTC)` | stdlib | ISO 8601 UTC timestamp | Project-standard — see STATE.md: "datetime.now(timezone.utc) not datetime.utcnow()" |
| `pytest`, `pytest-asyncio`, `fakeredis` | dev deps | Unit testing with mocked Redis | Existing test infrastructure |

### No new installations needed
All required libraries are already in `backend/pyproject.toml`.

## Architecture Patterns

### Where the fixes live

```
backend/app/agent/runner_autonomous.py    # Gaps 1 + 2: budget_pct + wake_at writes
backend/app/api/routes/escalations.py    # Gap 3: agent.escalation_resolved emission
backend/tests/agent/test_taor_budget_integration.py  # New tests for gaps 1+2
backend/tests/api/test_escalation_routes.py          # New tests for gap 3
```

### Pattern 1: Redis.set() in runner_autonomous.py (Gaps 1 + 2)

The existing pattern for Redis writes in `run_agent_loop()` is:
```python
if redis:
    await redis.set(
        f"cofounder:agent:{session_id}:state",
        "sleeping",
        ex=90_000,
    )
```

All Redis writes in the loop are guarded with `if redis:` (backward compat — redis is optional in context).

**Gap 1 — budget_pct write location:** Integration Point 2 (lines 291-321 of `runner_autonomous.py`). Currently `budget_pct` is computed via `budget_service.get_budget_percentage()` and emitted via SSE, but never written to Redis. The write belongs immediately after the SSE emit:

```python
# Source: runner_autonomous.py, Integration Point 2 (after line ~314)
if state_machine:
    await state_machine.publish_event(
        job_id,
        {
            "type": "agent.budget_updated",
            "budget_pct": int(budget_pct * 100),
        },
    )
# NEW: write budget_pct Redis key for REST bootstrap
if redis:
    await redis.set(
        f"cofounder:agent:{session_id}:budget_pct",
        int(budget_pct * 100),
        ex=90,  # 90s TTL — matches SSE heartbeat window per locked decision
    )
```

**Gap 2 — wake_at write location:** Integration Point 4 (sleep transition block, lines 331-395 of `runner_autonomous.py`). The `agent.sleeping` SSE event fires and state is set to "sleeping" — wake_at belongs here, before `wake_daemon.wake_event.wait()`:

```python
# Source: runner_autonomous.py, Integration Point 4 (after Redis state set to "sleeping")
# NEW: write wake_at Redis key so REST bootstrap can show countdown timer
if redis:
    from datetime import UTC, datetime as _dt_wake
    now_utc = _dt_wake.now(UTC)
    # Next midnight UTC
    next_midnight = now_utc.replace(
        hour=0, minute=0, second=0, microsecond=0
    ) + timedelta(days=1)
    wake_at_iso = next_midnight.isoformat()
    sleep_seconds = int((next_midnight - now_utc).total_seconds())
    await redis.set(
        f"cofounder:agent:{session_id}:wake_at",
        wake_at_iso,
        ex=sleep_seconds,  # TTL matches sleep duration — key expires when agent wakes
    )
```

Note: `timedelta` is already imported at the top of `service.py` but NOT in `runner_autonomous.py`. The write must either import locally (consistent with Phase 43/44/46 `from datetime import ...` local import pattern) or use arithmetic on the datetime object directly.

### Pattern 2: state_machine.publish_event() in escalations.py (Gap 3)

The resolve endpoint currently has no access to `state_machine` — it only uses `get_session_factory()` for DB. The fix requires:
1. Inject Redis dependency into the endpoint (`redis=Depends(get_redis)`)
2. Construct `JobStateMachine(redis)` locally
3. Call `state_machine.publish_event(esc.job_id, {...})` after `session.commit()`

```python
# Source: escalations.py resolve_escalation() (after line 191 — await session.commit())
# NEW: emit agent.escalation_resolved SSE for multi-session visibility
from app.db.redis import get_redis
from app.queue.state_machine import JobStateMachine, SSEEventType

@router.post("/escalations/{escalation_id}/resolve", response_model=EscalationResponse)
async def resolve_escalation(
    escalation_id: uuid.UUID,
    request: ResolveEscalationRequest,
    user: ClerkUser = Depends(require_auth),
    redis=Depends(get_redis),         # NEW dependency
) -> EscalationResponse:
    ...
    await session.commit()

    # NEW: emit SSE for cross-session visibility (AGNT-08)
    state_machine = JobStateMachine(redis)
    from app.queue.state_machine import SSEEventType
    await state_machine.publish_event(
        esc.job_id,
        {
            "type": SSEEventType.AGENT_ESCALATION_RESOLVED,
            "escalation_id": str(esc.id),
            "resolution": request.decision,
            "resolved_at": esc.resolved_at.isoformat(),
        },
    )
    return _to_response(esc)
```

**Critical detail:** `get_redis` is already used throughout the routes layer (`app.db.redis.get_redis`). The import pattern is already established in `jobs.py` (`from app.db.redis import get_redis`).

**Critical detail:** `SSEEventType` import inside the function body follows the Phase 43/44/46 pattern ("SSEEventType imported locally inside handlers — avoids circular import at module level").

### Pattern 3: Test mock infrastructure (existing patterns)

**For gaps 1+2 (runner tests):** The existing `test_taor_budget_integration.py` mock infrastructure is the template. Use `_make_redis()` which already has `r.set = AsyncMock(return_value=True)`. Verify with `redis.set.call_args_list` inspection.

**For gap 3 (escalation route tests):** The existing `test_escalation_routes.py` mock infrastructure is the template. Tests use `patch("app.api.routes.escalations.get_session_factory", ...)`. The new test needs to also mock `get_redis` and verify `state_machine.publish_event()` was called.

### Anti-Patterns to Avoid
- **Importing `timedelta` at module level in runner_autonomous.py:** Not currently imported there. Use local import or arithmetic — do NOT add a new module-level import that breaks the existing clean import structure.
- **Calling `datetime.utcnow()`:** PROJECT-BANNED. State.md: "datetime.now(timezone.utc) not datetime.utcnow()".
- **Emitting SSE before `session.commit()`:** The event must fire AFTER commit — never before. If commit fails, the SSE would be stale.
- **Using hardcoded "agent.escalation_resolved" string:** Use `SSEEventType.AGENT_ESCALATION_RESOLVED` constant.
- **Non-conditional Redis writes:** Always guard with `if redis:` in the TAOR loop (backward compat when redis not injected).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| SSE pub/sub | Custom channel logic | `state_machine.publish_event(job_id, event)` | Already wired end-to-end, handles timestamp injection and channel routing |
| Next midnight calculation | Custom date math | `datetime.now(UTC).replace(hour=0,...) + timedelta(days=1)` | Standard stdlib — no library needed |
| Redis dependency injection | Manual Redis construction in endpoint | `redis=Depends(get_redis)` | Established pattern in every route that needs Redis |
| SSE constant string | Inline string `"agent.escalation_resolved"` | `SSEEventType.AGENT_ESCALATION_RESOLVED` | Constant already exists, typo-safe |

**Key insight:** Every piece of infrastructure needed for these fixes already exists. The only work is wiring the final connections.

## Common Pitfalls

### Pitfall 1: TTL units — 90 vs 90_000
**What goes wrong:** The locked decision says "TTL: 90 seconds" for `budget_pct`, but the existing pattern for `cofounder:agent:{session_id}:state` uses `ex=90_000` (90,000 seconds = 25 hours). These are different keys with different TTL requirements.
**Why it happens:** Copy-paste from the nearby `redis.set(..., ex=90_000)` state key write.
**How to avoid:** `budget_pct` TTL = 90 seconds (CONTEXT.md locked: "matches SSE heartbeat window"). `wake_at` TTL = sleep duration (dynamic). State TTL = 90_000s.
**Warning signs:** TTL values that are 1000x too large on `budget_pct`.

### Pitfall 2: wake_at key conditionals
**What goes wrong:** Writing `wake_at` unconditionally (not gated on `if redis:`).
**Why it happens:** Forgetting the backward-compat pattern.
**How to avoid:** All Redis writes in `run_agent_loop()` are gated with `if redis:`. Follow the same pattern.

### Pitfall 3: timedelta not imported in runner_autonomous.py
**What goes wrong:** `NameError: name 'timedelta' is not defined` at runtime.
**Why it happens:** `runner_autonomous.py` imports `datetime` objects locally inside function bodies using `from datetime import UTC, datetime as _dt`. `timedelta` is not in scope.
**How to avoid:** Either (a) import `timedelta` locally alongside the datetime import: `from datetime import UTC, datetime as _dt_wake, timedelta as _timedelta`, or (b) compute next midnight using `timedelta(days=1)` directly inline after the local import. Do NOT add a module-level import.

### Pitfall 4: SSE emitted after closed DB session
**What goes wrong:** In `resolve_escalation()`, the DB session is managed by `async with session_factory() as session:`. The `session.commit()` and ORM attribute access (`esc.resolved_at`) must happen INSIDE this context manager. The SSE emit should also happen inside or use captured values (escalation_id, job_id, decision, resolved_at as strings) that were extracted before the context exits.
**Why it happens:** `esc` is an ORM object — after the session context closes, lazy-loading attributes may fail.
**How to avoid:** Capture all needed values (`job_id = esc.job_id`, `resolved_at_str = esc.resolved_at.isoformat()`) before `session.commit()`, then emit SSE using those captured strings — or move the SSE emit inside the `async with` block, after `await session.commit()`.

### Pitfall 5: Test mocking get_redis for escalations test
**What goes wrong:** The test uses `patch("app.api.routes.escalations.get_session_factory", ...)` but doesn't mock `get_redis`, so FastAPI's dependency injection fails or uses real Redis.
**Why it happens:** The existing tests were written before `redis` was a dependency of `resolve_escalation`.
**How to avoid:** Add `app.dependency_overrides[get_redis] = lambda: mock_redis` in the test fixture, or patch `app.api.routes.escalations.get_redis`. The existing test in `test_jobs_api.py` shows this pattern.

## Code Examples

### Gap 1: budget_pct write (Integration Point 2 in runner_autonomous.py)
```python
# Source: runner_autonomous.py, lines ~307-320 (Integration Point 2)
# Existing code (abbreviated):
if budget_service:
    session_cost = await budget_service.record_call_cost(...)
    budget_pct = await budget_service.get_budget_percentage(...)
    if state_machine:
        await state_machine.publish_event(
            job_id, {"type": "agent.budget_updated", "budget_pct": int(budget_pct * 100)}
        )
    # --- NEW: write budget_pct Redis key for REST bootstrap ---
    if redis:
        await redis.set(
            f"cofounder:agent:{session_id}:budget_pct",
            int(budget_pct * 100),
            ex=90,
        )
    await budget_service.check_runaway(...)
    if budget_service.is_at_graceful_threshold(session_cost, daily_budget):
        graceful_wind_down = True
```

### Gap 2: wake_at write (Integration Point 4 in runner_autonomous.py)
```python
# Source: runner_autonomous.py, sleep transition block (after redis.set state=sleeping)
# Existing code sets state to "sleeping", then saves checkpoint.
# NEW block goes after the state set:
if redis:
    from datetime import UTC, datetime as _dt_wake, timedelta as _td_wake
    _now_utc = _dt_wake.now(UTC)
    _next_midnight = (_now_utc.replace(hour=0, minute=0, second=0, microsecond=0)
                      + _td_wake(days=1))
    _sleep_seconds = max(1, int((_next_midnight - _now_utc).total_seconds()))
    await redis.set(
        f"cofounder:agent:{session_id}:wake_at",
        _next_midnight.isoformat(),
        ex=_sleep_seconds,
    )
```

### Gap 3: SSE emit in resolve_escalation (escalations.py)
```python
# Source: escalations.py — updated resolve_escalation signature + body

@router.post("/escalations/{escalation_id}/resolve", response_model=EscalationResponse)
async def resolve_escalation(
    escalation_id: uuid.UUID,
    request: ResolveEscalationRequest,
    user: ClerkUser = Depends(require_auth),
    redis=Depends(get_redis),       # NEW
) -> EscalationResponse:
    session_factory = get_session_factory()
    async with session_factory() as session:
        result = await session.execute(...)
        esc = result.scalar_one_or_none()
        # ... 404 and 409 checks ...
        esc.founder_decision = request.decision
        esc.founder_guidance = request.guidance
        esc.status = "resolved"
        esc.resolved_at = datetime.now(UTC)
        await session.commit()

        # NEW: emit SSE after commit for cross-session visibility (AGNT-08)
        from app.queue.state_machine import JobStateMachine, SSEEventType
        _sm = JobStateMachine(redis)
        await _sm.publish_event(
            esc.job_id,
            {
                "type": SSEEventType.AGENT_ESCALATION_RESOLVED,
                "escalation_id": str(esc.id),
                "resolution": request.decision,
                "resolved_at": esc.resolved_at.isoformat(),
            },
        )
    return _to_response(esc)
```

### Test: verifying budget_pct Redis write (extends test_taor_budget_integration.py)
```python
async def test_budget_pct_written_to_redis():
    """budget_pct Redis key written after each record_call_cost() call."""
    runner = AutonomousRunner()
    budget_service = _make_budget_service(budget_pct=0.65)
    redis = _make_redis()

    r1 = make_response(stop_reason="end_turn", text="Done.")

    with patch.object(runner._client.messages, "stream", return_value=MockStream([r1])):
        result = await runner.run_agent_loop(
            _base_context(budget_service=budget_service, redis=redis)
        )

    assert result["status"] == "completed"
    # Verify budget_pct key was written with value 65 (int(0.65 * 100))
    pct_calls = [
        c for c in redis.set.call_args_list
        if "budget_pct" in str(c.args[0])
    ]
    assert len(pct_calls) >= 1
    assert pct_calls[0].args[1] == 65
    assert pct_calls[0].kwargs.get("ex") == 90  # 90s TTL
```

### Test: verifying wake_at Redis write (extends test_taor_budget_integration.py)
```python
async def test_wake_at_written_to_redis_on_sleep():
    """wake_at Redis key written when graceful wind-down transitions to sleeping."""
    runner = AutonomousRunner()
    # ... same setup as test_graceful_winddown_at_90_percent ...
    # After run_agent_loop completes:
    wake_at_calls = [
        c for c in redis.set.call_args_list
        if "wake_at" in str(c.args[0])
    ]
    assert len(wake_at_calls) == 1
    # Value is ISO timestamp (contains 'T' separator)
    assert "T" in wake_at_calls[0].args[1]
    # TTL is positive integer
    assert wake_at_calls[0].kwargs.get("ex", 0) > 0
```

### Test: verifying SSE emitted from resolve endpoint (extends test_escalation_routes.py)
```python
def test_resolve_emits_escalation_resolved_sse(client_with_redis):
    """POST /escalations/{id}/resolve emits agent.escalation_resolved SSE event."""
    esc_id = uuid.uuid4()
    mock_esc = _mock_escalation(escalation_id=esc_id, status="pending")
    mock_esc.job_id = "job-sse-test"

    # mock_redis captures publish_event calls via JobStateMachine mock
    mock_redis = AsyncMock()
    mock_redis.publish = AsyncMock(return_value=1)
    # ... patch get_session_factory + get_redis + make request ...
    # Verify redis.publish was called with the correct channel and event type
    publish_calls = mock_redis.publish.call_args_list
    sse_calls = [c for c in publish_calls if "job-sse-test:events" in str(c)]
    assert len(sse_calls) == 1
    import json
    event_data = json.loads(sse_calls[0].args[1])
    assert event_data["type"] == "agent.escalation_resolved"
    assert event_data["escalation_id"] == str(esc_id)
```

## State of the Art

| Old State (Gaps) | Fixed State (Post-Phase 47) | Impact |
|------------------|-----------------------------|--------|
| `budget_pct` read from Redis by GET /status → always null | Written after each `record_call_cost()` with 90s TTL | Budget bar shows real value on page reload |
| `wake_at` read from Redis by GET /status → always null | Written on sleep transition with TTL=sleep_duration | Countdown timer works on reload during sleeping state |
| `agent.escalation_resolved` never emitted | Emitted after `session.commit()` in resolve endpoint | Second browser session sees resolution in real time |

## Open Questions

1. **timedelta import in runner_autonomous.py**
   - What we know: `timedelta` is not currently imported in `runner_autonomous.py` at the module level. The Phase 43/44/46 pattern uses local imports inside `if state_machine:` guards.
   - What's unclear: Whether a local import inside a loop body has any performance concern (it does not — Python caches module imports after the first load).
   - Recommendation: Use `from datetime import UTC, datetime as _dt_wake, timedelta as _td_wake` as a local import inside the `if redis:` guard, consistent with existing Phase 46 patterns.

2. **wake_at TTL precision when near midnight**
   - What we know: `sleep_seconds = int((next_midnight - now_utc).total_seconds())`. If the agent sleeps at 23:59:58, this is 2 seconds.
   - What's unclear: Whether a 2-second TTL is acceptable or if there's a minimum floor.
   - Recommendation: Use `max(1, int(...))` to ensure TTL is at least 1 second. The WakeDaemon will set the actual wake_event — the Redis key is purely informational for REST bootstrap.

3. **SSE emit inside vs. outside the session context manager**
   - What we know: The session closes when `async with session_factory() as session:` exits. ORM attributes on `esc` may become unavailable after the context closes (lazy loading, detached instance errors).
   - Recommendation: Place the SSE emit INSIDE the `async with` block, after `await session.commit()`. This ensures `esc.job_id`, `esc.id`, and `esc.resolved_at` are still accessible via the live session.

## Sources

### Primary (HIGH confidence)
- Direct codebase inspection — `runner_autonomous.py` (read in full, 862 lines)
- Direct codebase inspection — `escalations.py` (read in full, 194 lines)
- Direct codebase inspection — `state_machine.py` (read in full, 269 lines) — SSEEventType constants, publish_event signature
- Direct codebase inspection — `jobs.py` (read in full, 489 lines) — confirmed both Redis keys are read at lines 218-233
- Direct codebase inspection — `service.py` BudgetService (read in full) — `get_budget_percentage()` returns 0.0-1.0 float
- Direct codebase inspection — `test_taor_budget_integration.py` (read in full) — mock infrastructure template for gaps 1+2
- Direct codebase inspection — `test_escalation_routes.py` (read in full) — mock infrastructure template for gap 3
- Direct codebase inspection — `.planning/v0.7-MILESTONE-AUDIT.md` — exact file locations and recommended fixes

### Secondary (MEDIUM confidence)
- STATE.md accumulated decisions — confirmed datetime.now(UTC) requirement, local import pattern for SSEEventType

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries already in use, confirmed by reading source files
- Architecture: HIGH — insertion points confirmed by reading exact lines in source files
- Pitfalls: HIGH — derived from reading existing code patterns and STATE.md decisions
- Test patterns: HIGH — derived from reading existing test files with identical mock infrastructure

**Research date:** 2026-03-01
**Valid until:** 2026-04-01 (codebase-internal research — valid until the files change)
