---
phase: 05-capacity-queue-worker-model
plan: 01
subsystem: queue-foundation
tags: [tdd, redis, queue, priority, schemas]
dependency-graph:
  requires: [redis-client, pydantic]
  provides: [QueueManager, JobStatus, Job-model, queue-schemas]
  affects: []
tech-stack:
  added: [fakeredis, redis-sorted-sets]
  patterns: [priority-queue, composite-scoring, FIFO-tiebreaker]
key-files:
  created:
    - backend/app/queue/manager.py
    - backend/app/db/models/job.py
    - backend/tests/domain/test_queue_schemas.py
    - backend/tests/domain/test_queue_manager.py
  modified:
    - backend/app/db/models/__init__.py
    - backend/app/queue/schemas.py
decisions:
  - Redis sorted set for O(log N) priority queue operations
  - Composite score formula (1000-boost)*1e12+counter for tier priority with FIFO tiebreaker
  - Global cap of 100 jobs with retry estimation (2min/job / avg concurrency)
  - Job model follows Project model pattern (UUID, lambda datetime, timezone-aware)
  - fakeredis for isolated async testing without Docker dependency
metrics:
  duration: 174s
  tasks: 1
  files: 6
  tests: 15
  commits: 1
  completed: 2026-02-16T20:25:05Z
---

# Phase 05 Plan 01: Job Queue Foundation Summary

**One-liner:** Redis sorted set priority queue with tier boost (CTO+5, Partner+2) and FIFO tiebreaker, Job Postgres model, and full TDD coverage.

## What Was Built

### Core Components

**QueueManager (backend/app/queue/manager.py)**
- Redis sorted set-based priority queue with composite scoring
- `enqueue(job_id, tier)`: Add job with tier-based priority, returns position/score or rejection
- `dequeue()`: Pop highest priority job (lowest score)
- `get_position(job_id)`: Return 1-indexed queue position
- `get_length()`: Return current queue size
- `remove(job_id)`: Delete job from queue (cancellation)
- Global cap enforcement: 100 jobs, rejection with retry estimate

**Priority Score Formula**
```python
score = (1000 - boost) * 1e12 + counter
```
- Lower score = higher priority
- Tier boost: CTO=5, Partner=2, Bootstrapper=0
- Counter ensures FIFO within same tier

**Queue Schemas (backend/app/queue/schemas.py)**
- `JobStatus` enum: 9 states (queued, starting, scaffold, code, deps, checks, ready, failed, scheduled)
- `JobRequest`: project_id, user_id, tier, goal
- `JobRecord`: job_id, project_id, user_id, tier, status, enqueued_at, position, score
- `UsageCounters`: jobs_used/remaining, iterations_used/remaining, daily_limit_resets_at
- Tier constants: TIER_BOOST, TIER_CONCURRENT_USER/PROJECT, TIER_DAILY_LIMIT, TIER_ITERATION_DEPTH, GLOBAL_QUEUE_CAP

**Job DB Model (backend/app/db/models/job.py)**
- UUID primary key with project_id FK to projects
- Fields: tier, status, goal, enqueued_at, started_at, completed_at, error_message, debug_id, iterations_used
- Lambda datetime defaults for timezone-aware timestamps (follows Project model pattern)

### Test Coverage

**test_queue_schemas.py (5 tests)**
- JobStatus has exactly 9 states
- JobRequest validates required fields
- JobRecord includes all 8 fields
- UsageCounters includes all 5 fields
- Tier constants match locked decisions

**test_queue_manager.py (10 tests)**
- Enqueue returns position 1 for first job
- CTO job enqueued after bootstrapper jumps ahead (priority boost)
- FIFO within same tier (first enqueued = position 1)
- Dequeue returns highest priority job (CTO → Partner → Bootstrapper)
- Dequeue returns None on empty queue
- get_position returns accurate 1-indexed position
- Global cap enforced at 100 jobs with rejection message
- Priority score calculation verified (995*1e12 for CTO, 998*1e12 for Partner, 1000*1e12 for Bootstrapper)
- get_length returns current queue size
- remove deletes job from queue

All 15 tests pass using fakeredis for isolated async testing.

## Key Decisions

**Redis sorted set over list/stream**
- O(log N) enqueue/dequeue vs O(N) list operations
- Native priority support with ZADD/ZPOPMIN
- Atomic ZRANK for position queries

**Composite score with counter tiebreaker**
- Base priority: 1000 - tier_boost
- Multiply by 1e12 to reserve space for counter
- Counter from INCR ensures FIFO within tier
- Example: CTO job #42 = 995000000000042

**Global cap with retry estimation**
- Hard cap at 100 jobs prevents Redis memory issues
- Retry estimate: (queue_length - cap + 1) * 2min / avg_concurrency
- Returns rejection dict with message and retry_after_minutes

**fakeredis for testing**
- No Docker dependency for CI/local development
- Async support via fakeredis.aioredis.FakeRedis
- Deterministic tests with FLUSHALL cleanup

## Deviations from Plan

None — plan executed exactly as written. Schemas.py already had constants from previous work, only added JobRequest and JobRecord models.

## Verification

```bash
python -m pytest backend/tests/domain/test_queue_schemas.py backend/tests/domain/test_queue_manager.py -v
# ✅ 15 passed in 0.07s
```

**Verified behaviors:**
- JobStatus has 9 states
- TIER_BOOST = {cto_scale: 5, partner: 2, bootstrapper: 0}
- GLOBAL_QUEUE_CAP = 100
- CTO job jumps ahead of bootstrapper (priority boost)
- FIFO preserved within same tier
- Queue position accurate after concurrent enqueues
- Rejection at 101st job with retry estimate

## Files Created/Modified

**Created:**
- `backend/app/queue/manager.py` (93 lines) — QueueManager class
- `backend/app/db/models/job.py` (39 lines) — Job SQLAlchemy model
- `backend/tests/domain/test_queue_schemas.py` (119 lines) — Schema tests
- `backend/tests/domain/test_queue_manager.py` (176 lines) — QueueManager tests

**Modified:**
- `backend/app/db/models/__init__.py` — Added Job import and __all__ export

## Dependencies Added

- `fakeredis[aioredis]` (v2.34.0) — Async Redis mock for testing

## Next Steps

This foundation enables:
- **Plan 05-02**: Job state machine for status transitions
- **Plan 05-03**: Capacity-aware dequeuer with concurrency limits
- **Plan 05-04**: Worker health monitoring and job execution
- **Plan 05-05**: API endpoints for job submission and status

## Self-Check: PASSED

**Files exist:**
```bash
✅ backend/app/queue/manager.py
✅ backend/app/db/models/job.py
✅ backend/tests/domain/test_queue_schemas.py
✅ backend/tests/domain/test_queue_manager.py
```

**Commits exist:**
```bash
✅ fdbbfd2: test(05-01): add queue manager and schemas tests with fakeredis
```

**Tests pass:**
```bash
✅ 15/15 tests passing
```
