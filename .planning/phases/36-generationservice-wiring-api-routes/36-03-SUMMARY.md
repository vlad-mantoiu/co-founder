---
phase: 36-generationservice-wiring-api-routes
plan: "03"
subsystem: backend/api
tags: [sse, redis-pubsub, fastapi, streaming, tdd]
dependency_graph:
  requires: [36-01]
  provides: [GET /api/jobs/{id}/events/stream]
  affects: [frontend/phase-37-sse-consumer]
tech_stack:
  added: []
  patterns:
    - pubsub.get_message() with asyncio.wait_for(timeout=1.0) for heartbeat-interleaved SSE
    - stream_job_events co-exists with legacy stream_job_status at separate path
    - pytest.mark.asyncio for direct async endpoint function testing (avoids streaming body hang)
key_files:
  created:
    - backend/tests/api/test_events_stream.py
  modified:
    - backend/app/api/routes/jobs.py
decisions:
  - pubsub.get_message() not pubsub.listen() — enables heartbeat interleaving without blocking loop
  - 15s heartbeat interval (not 20s like logs.py) — ALB default is 60s, 15s gives 4x safety margin
  - Test 5 uses direct async endpoint call not TestClient streaming — avoids blocking on infinite generator
  - Heartbeat timer reset on data events — avoids unnecessary heartbeats during active streaming
metrics:
  duration: "~18 minutes"
  completed: "2026-02-24"
  tasks_completed: 2
  files_modified: 2
---

# Phase 36 Plan 03: SSE Events Stream Endpoint Summary

**One-liner:** Typed SSE stream `GET /api/jobs/{id}/events/stream` with 15-second ALB heartbeat and immediate terminal-job close via Redis Pub/Sub `get_message()` polling pattern.

## What Was Built

Added `stream_job_events` endpoint to `backend/app/api/routes/jobs.py`. The endpoint:

- Subscribes to `job:{job_id}:events` Redis Pub/Sub channel
- Passes through all typed events (build.stage.started, build.stage.completed, snapshot.updated, documentation.updated) raw
- Sends `event: heartbeat` every 15 seconds to prevent ALB idle timeout (60s default)
- Resets heartbeat timer on data events (avoids unnecessary heartbeats during active streaming)
- Detects already-terminal jobs on connect and emits final status then closes immediately
- Returns 404 for unknown job or wrong-user access (auth enforced)
- Uses `asyncio.wait_for(pubsub.get_message(...), timeout=1.0)` pattern (not `pubsub.listen()`) to interleave heartbeat checks without blocking the event loop

The endpoint coexists with the legacy `/{job_id}/stream` endpoint at the separate path `/{job_id}/events/stream`.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Write tests for SSE events stream endpoint (RED) | 228f616 | backend/tests/api/test_events_stream.py |
| 2 | Add GET /{job_id}/events/stream typed SSE endpoint (GREEN) | e4ea559 | backend/app/api/routes/jobs.py, backend/tests/api/test_events_stream.py |

## Key Code: stream_job_events endpoint

```python
@router.get("/{job_id}/events/stream")
async def stream_job_events(
    job_id: str,
    request: Request,
    user: ClerkUser = Depends(require_auth),
    redis=Depends(get_redis),
):
    # Auth check
    job_data = await state_machine.get_job(job_id)
    if not job_data or job_data.get("user_id") != user.user_id:
        raise HTTPException(status_code=404, detail="Job not found")

    async def event_generator():
        # Already terminal — emit final status and close immediately
        if current_status in ("ready", "failed"):
            yield f"data: {json.dumps({...status: current_status...})}\n\n"
            return

        # Active job — subscribe and poll with heartbeat
        pubsub = redis.pubsub()
        await pubsub.subscribe(f"job:{job_id}:events")
        last_heartbeat = time.monotonic()
        while True:
            if await request.is_disconnected(): return
            if now - last_heartbeat >= 15:
                yield "event: heartbeat\ndata: {}\n\n"
            message = await asyncio.wait_for(pubsub.get_message(...), timeout=1.0)
            if message:
                yield f"data: {message['data']}\n\n"
                if data.get("status") in ("ready", "failed"): return
```

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Test 5 blocking on streaming body consumption**

- **Found during:** Task 2 verification
- **Issue:** `TestClient.get()` tries to read full response body, but the non-terminal job generator runs indefinitely waiting for pubsub messages. Test hung indefinitely.
- **Fix:** Changed test 5 to use `pytest.mark.asyncio` and call `stream_job_events()` directly (not via HTTP client). This tests `StreamingResponse` construction + headers without consuming the infinite generator body.
- **Files modified:** backend/tests/api/test_events_stream.py
- **Commit:** e4ea559 (included in GREEN commit)

## Verification Results

```
tests/api/test_events_stream.py::test_events_stream_returns_404_for_unknown_job PASSED
tests/api/test_events_stream.py::test_events_stream_returns_404_for_wrong_user PASSED
tests/api/test_events_stream.py::test_events_stream_terminal_job_emits_final_and_closes PASSED
tests/api/test_events_stream.py::test_events_stream_terminal_failed_job PASSED
tests/api/test_events_stream.py::test_events_stream_returns_streaming_response PASSED
5 passed in 0.29s

Regression check (jobs API + events stream):
16 passed, 1 skipped in 2.32s
```

## Requirements Satisfied

- SNAP-03: snapshot.updated events pass through the new channel (channel passthrough is type-agnostic)
- NARR-02: narration-enriched build.stage.started events pass through (same passthrough)

## Self-Check: PASSED

- backend/app/api/routes/jobs.py — FOUND, contains `stream_job_events` and `_EVENTS_HEARTBEAT_INTERVAL = 15`
- backend/tests/api/test_events_stream.py — FOUND, 5 tests all passing
- .planning/phases/36-generationservice-wiring-api-routes/36-03-SUMMARY.md — FOUND
- Commit 228f616 (RED tests) — FOUND
- Commit e4ea559 (GREEN implementation) — FOUND
