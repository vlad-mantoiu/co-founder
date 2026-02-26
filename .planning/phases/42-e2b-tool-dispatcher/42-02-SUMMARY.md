---
phase: 42-e2b-tool-dispatcher
plan: 02
subsystem: infra
tags: [s3, boto3, e2b, snapshot, tar, ttl, asyncio, testing]

# Dependency graph
requires:
  - phase: 42-e2b-tool-dispatcher
    provides: Research confirming tar-in-sandbox strategy, boto3 asyncio.to_thread pattern, E2B TTL management API (get_info/set_timeout)
  - phase: 28-sandbox-integration
    provides: E2BSandboxRuntime with run_command(), _sandbox.files.read(), _sandbox.get_info(), _sandbox.set_timeout()
provides:
  - S3SnapshotService class with sync(), maybe_extend_ttl(), _put_s3(), _prune_old_snapshots()
  - Rolling 5-snapshot retention per project via list_objects_v2 + delete_objects
  - Proactive sandbox TTL extension when < 5 minutes remaining
  - 10 unit tests covering all behaviors with fully mocked E2B and S3
affects:
  - phase-43-agent-session (wake lifecycle needs restore from S3 snapshots)
  - phase-41-autonomous-runner (E2BToolDispatcher will call sync() after each phase commit)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "asyncio.to_thread(boto3.client(...).put_object()) for non-blocking S3 uploads"
    - "Tar-in-sandbox strategy: single tar czf + files.read() vs N individual file reads"
    - "Pure numeric ISO timestamp (YYYYMMDDTHHMMSSZ) for lexicographic S3 key ordering"
    - "Non-fatal retry: 3 attempts, return None on total failure — agent continues"
    - "Timezone-aware datetime comparison: datetime.now(timezone.utc) vs end_at"

key-files:
  created:
    - backend/app/agent/sync/__init__.py
    - backend/app/agent/sync/s3_snapshot.py
    - backend/tests/agent/test_s3_snapshot.py
  modified: []

key-decisions:
  - "asyncio.to_thread(boto3.*) for S3 operations — locked project pattern from STATE.md, not aioboto3"
  - "Tar-in-sandbox: one tar czf + one files.read() rather than N individual file API calls"
  - "YYYYMMDDTHHMMSSZ timestamp format (no hyphens/colons) ensures correct lexicographic sort for retention"
  - "Non-fatal sync: 3 retries then return None — E2B file loss mitigated but agent never blocked by S3 failures"
  - "TTL check uses datetime.now(timezone.utc) not datetime.utcnow() — end_at is timezone-aware, naive subtract raises TypeError"

patterns-established:
  - "S3SnapshotService is instantiated with bucket + region; no singleton — caller controls lifecycle"
  - "sync() owns the full write path: tar → read bytes → S3 upload → prune old"
  - "maybe_extend_ttl() is a standalone async method on the service — called by dispatcher before each tool dispatch"

requirements-completed: [MIGR-04]

# Metrics
duration: 2min
completed: 2026-02-26
---

# Phase 42 Plan 02: S3 Snapshot Service Summary

**S3SnapshotService with tar-in-sandbox sync, rolling 5-snapshot retention via boto3, and proactive E2B TTL extension — mitigates E2B Issue #884 file loss on multi-resume**

## Performance

- **Duration:** 2 min
- **Started:** 2026-02-26T05:43:42Z
- **Completed:** 2026-02-26T05:45:47Z
- **Tasks:** 2 (RED + GREEN TDD)
- **Files modified:** 3 created, 0 modified

## Accomplishments

- `S3SnapshotService` class: `sync()` runs `tar czf` in sandbox (7 excludes), reads bytes via `files.read()`, uploads via `asyncio.to_thread(s3.put_object())`, returns pure-numeric S3 key or None after 3 failures
- Rolling 5-snapshot retention: `_prune_old_snapshots()` lists with prefix, sorts newest-first, deletes beyond limit
- Proactive TTL management: `maybe_extend_ttl()` compares timezone-aware `end_at` to `datetime.now(timezone.utc)`, extends by 3600s when < 5 minutes remain
- 10 unit tests all pass: upload path, key format regex, exclude dirs, 3-attempt retry, none-after-failure, prune-7-to-5, no-prune-under-limit, TTL extend, TTL skip, tar-failure path

## Task Commits

Each task was committed atomically:

1. **Task 1: RED — Write failing tests for S3SnapshotService** - `222539c` (test)
2. **Task 2: GREEN — Implement S3SnapshotService** - `fcc8bdd` (feat)

## Files Created/Modified

- `backend/app/agent/sync/__init__.py` - Package marker for agent.sync subpackage
- `backend/app/agent/sync/s3_snapshot.py` - S3SnapshotService class (sync, prune, TTL management)
- `backend/tests/agent/test_s3_snapshot.py` - 10 unit tests covering all behaviors (all mocked)

## Decisions Made

- `asyncio.to_thread(boto3.*)` for S3 operations — locked project pattern, `aioboto3` not installed
- Tar-in-sandbox: one `tar czf` + one `files.read()` vs N individual `files.read()` calls — orders of magnitude faster at scale
- `YYYYMMDDTHHMMSSZ` format (no hyphens/colons) — ISO timestamps sort lexicographically, enabling correct newest-first pruning
- Non-fatal sync with 3 retries + None return — agent work must never be blocked by snapshot failures; next phase commit produces a fresh snapshot
- `datetime.now(timezone.utc)` not `datetime.utcnow()` — `SandboxInfo.end_at` is timezone-aware; naive subtraction raises `TypeError`

## Deviations from Plan

None — plan executed exactly as written. All 10 specified test cases implemented (plan required minimum 8).

## Issues Encountered

None.

## User Setup Required

None — no external service configuration required for this plan. S3 bucket and region are constructor parameters; the caller (E2BToolDispatcher, Phase 42 Plan 01) supplies them from `Settings`.

## Next Phase Readiness

- `S3SnapshotService` is ready to be instantiated by `E2BToolDispatcher` (Phase 42 Plan 01) after each phase commit
- Phase 43 wake lifecycle can call `restore()` (not yet implemented — Phase 43 scope) by listing `projects/{id}/snapshots/` and fetching the newest key
- `maybe_extend_ttl()` is ready to be called by the dispatcher before each tool dispatch

---
*Phase: 42-e2b-tool-dispatcher*
*Completed: 2026-02-26*
