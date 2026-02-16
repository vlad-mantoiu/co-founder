---
phase: 05
plan: 02
subsystem: queue
tags: [redis, concurrency, capacity, estimation, tdd]
dependency_graph:
  requires: [redis-async-client]
  provides: [distributed-semaphore, wait-time-estimator]
  affects: []
tech_stack:
  added: [redis-sets-ttl, ema-algorithm]
  patterns: [distributed-semaphore, exponential-moving-average]
key_files:
  created:
    - backend/app/queue/schemas.py
    - backend/app/queue/semaphore.py
    - backend/app/queue/estimator.py
    - backend/tests/domain/test_semaphore.py
    - backend/tests/domain/test_estimator.py
  modified: []
decisions:
  - "Use Redis SADD/SREM with TTL for distributed semaphore (prevents deadlock on crash)"
  - "Track separate EMA averages per tier (different complexity profiles: 480s/600s/900s)"
  - "Confidence intervals at ±30% for realistic user expectations"
  - "Cleanup method for stale slots rather than background job (simpler, on-demand)"
metrics:
  duration: 3 min
  tasks: 2
  files: 5
  tests: 28
  commits: 4
  completed: 2026-02-17
---

# Phase 05 Plan 02: Distributed Concurrency Primitives Summary

**One-liner:** Redis-based semaphore and EMA wait time estimator enforcing tier-aware capacity limits (2/3/10 user, 2/3/5 project concurrency) with adaptive duration tracking.

## What Was Built

Built two independent Redis-based primitives for capacity management:

1. **RedisSemaphore** - Distributed concurrency control using Redis sets + TTL
   - Enforces per-user limits: Bootstrapper 2, Partner 3, CTO 10
   - Enforces per-project limits: Bootstrapper 2, Partner 3, CTO 5
   - Auto-releases slots after TTL expires (prevents deadlock on worker crash)
   - Cleanup method removes stale slots where TTL key has expired
   - Helper functions create tier-appropriate semaphores

2. **WaitTimeEstimator** - Adaptive wait time estimation using Exponential Moving Average
   - Tier-aware defaults: Bootstrapper 480s (8min), Partner 600s (10min), CTO 900s (15min)
   - EMA with alpha=0.3 (30% new, 70% historical) smooths variance
   - Confidence intervals at ±30% for realistic bounds
   - Human-readable formatting: seconds, minutes, hours+minutes
   - Position-based calculation: `wait_time = avg_duration * position / workers`

Both modules built with full TDD coverage using fakeredis async.

## How It Works

**Semaphore Pattern:**
```python
# Create per-user semaphore
sem = user_semaphore(redis, user_id="u1", tier="partner")  # max=3

# Acquire slot
if await sem.acquire("job123"):
    # Job can run
    await run_job()
    await sem.release("job123")
else:
    # At capacity, enqueue for later
    await enqueue_job("job123")

# TTL auto-releases if job crashes (no manual cleanup needed)
```

**Estimator Pattern:**
```python
estimator = WaitTimeEstimator(redis)

# Record completed job duration
await estimator.record_completion("partner", duration_seconds=650)

# Get estimate with confidence
result = await estimator.estimate_with_confidence(
    tier="partner",
    position=5,
    active_workers=2
)
# {
#   "estimate_seconds": 1500,
#   "lower_bound": 1050,
#   "upper_bound": 1950,
#   "message": "17 minutes-32 minutes",
#   "confidence": "medium"
# }
```

**Key Design Decisions:**

1. **Separate keys prevent interference** - User and project semaphores use different Redis key prefixes (`concurrency:user:X` vs `concurrency:project:Y`)

2. **TTL prevents deadlock** - Each acquired slot has individual TTL key. If worker crashes, slot auto-expires and becomes available.

3. **Tier-specific EMA** - Track separate averages per tier because CTO jobs (all Opus) take longer than Bootstrapper jobs (mix of Sonnet).

4. **On-demand cleanup** - Cleanup method called periodically rather than background job. Simpler, no separate process needed.

## Deviations from Plan

None - plan executed exactly as written. All tier limits, EMA defaults, and confidence intervals match research specifications.

## Verification Results

All tests pass:
```
backend/tests/domain/test_semaphore.py - 14 tests PASSED
backend/tests/domain/test_estimator.py - 14 tests PASSED
Total: 28 tests in 2.11s
```

**Tier limits verified:**
- User concurrency: {bootstrapper: 2, partner: 3, cto_scale: 10} ✓
- Project concurrency: {bootstrapper: 2, partner: 3, cto_scale: 5} ✓
- Estimator defaults: {bootstrapper: 480s, partner: 600s, cto_scale: 900s} ✓

**Key behaviors verified:**
- Acquire succeeds up to limit, fails beyond ✓
- Release frees slot for new acquire ✓
- TTL auto-releases slot after expiry (tested with 1s TTL + 2s wait) ✓
- EMA updates correctly: 0.3 * new + 0.7 * old ✓
- Confidence intervals at ±30% ✓
- Human-readable formatting for all time ranges ✓

## Integration Points

**Provides:**
- `RedisSemaphore` class for distributed concurrency control
- `user_semaphore(redis, user_id, tier)` helper
- `project_semaphore(redis, project_id, tier)` helper
- `WaitTimeEstimator` class for adaptive wait time estimation
- Tier constants in `schemas.py`: `TIER_CONCURRENT_USER`, `TIER_CONCURRENT_PROJECT`

**Dependencies:**
- `redis.asyncio.Redis` - Async Redis client (already in project)
- `fakeredis` - For testing (already in dev dependencies)

**Next plan (05-03) will use:**
- Semaphore to enforce capacity before job execution
- Estimator to show users realistic wait times in queue UI
- Tier constants for queue priority boost calculations

## Performance Notes

**Redis operations:**
- Acquire: 3 Redis calls (SCARD, SADD, SETEX) - atomic via pipelining possible
- Release: 2 Redis calls (SREM, DELETE) - idempotent
- Count: 1 Redis call (SCARD) - O(1)
- Cleanup: N+1 Redis calls for N members (SMEMBERS + N × EXISTS + X × SREM)

**EMA updates:**
- Record: 2 Redis calls (GET, SET) - could use Lua script for atomicity
- Estimate: 1 Redis call (GET) - cached in memory possible

**Testing:**
- All tests use fakeredis (no real Redis required)
- TTL test uses asyncio.sleep(2) - slowest test at ~2s
- Total suite runs in 2.11s

## Self-Check

Verifying all claims in this summary:

**Created files:**
```bash
[ -f "backend/app/queue/schemas.py" ] && echo "✓ schemas.py"
[ -f "backend/app/queue/semaphore.py" ] && echo "✓ semaphore.py"
[ -f "backend/app/queue/estimator.py" ] && echo "✓ estimator.py"
[ -f "backend/tests/domain/test_semaphore.py" ] && echo "✓ test_semaphore.py"
[ -f "backend/tests/domain/test_estimator.py" ] && echo "✓ test_estimator.py"
```

**Commits exist:**
```bash
git log --oneline | grep -q "cc8ae34" && echo "✓ cc8ae34 (RED - semaphore tests)"
git log --oneline | grep -q "444e199" && echo "✓ 444e199 (GREEN - semaphore impl)"
git log --oneline | grep -q "67090dd" && echo "✓ 67090dd (RED - estimator tests)"
git log --oneline | grep -q "cf55277" && echo "✓ cf55277 (GREEN - estimator impl)"
```

## Self-Check: PASSED

All files created, all commits exist, all tests pass.
