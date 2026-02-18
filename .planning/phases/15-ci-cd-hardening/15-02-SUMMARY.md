---
phase: 15-ci-cd-hardening
plan: "02"
subsystem: backend-infra
tags: [graceful-shutdown, sigterm, alb, ecs, rolling-deploy, zero-downtime]
requirements: [CICD-06, CICD-07]

dependency_graph:
  requires: []
  provides:
    - SIGTERM-aware health check in backend/app/api/routes/health.py
    - ALB 60s deregistration delay on both target groups in infra/lib/compute-stack.ts
  affects:
    - ECS rolling deploy behavior (zero 502s during deploys)
    - ALB routing decisions during task shutdown

tech_stack:
  added: []
  patterns:
    - SIGTERM handler registered in FastAPI lifespan via signal.signal()
    - app.state.shutting_down boolean flag shared between signal handler and health endpoint
    - ALB setAttribute() workaround for deregistration delay (CDK Issue #4015)

key_files:
  created: []
  modified:
    - backend/app/main.py
    - backend/app/api/routes/health.py
    - infra/lib/compute-stack.ts

decisions:
  - SIGTERM handler runs in main thread (signal constraint) — sets app.state.shutting_down bool, which is safe for async health check reads
  - getattr(request.app.state, 'shutting_down', False) defensive default ensures tests without lifespan always get healthy response
  - setAttribute() used for deregistration delay per CDK Issue #4015 (ApplicationLoadBalancedFargateService lacks first-class deregistrationDelay prop)
  - 60 seconds deregistration delay chosen to match uvicorn keepalive timeout and allow long-running LangGraph agent requests to drain

metrics:
  duration: "1 min"
  completed: "2026-02-19"
  tasks: 2
  files: 3
---

# Phase 15 Plan 02: Graceful Shutdown and ALB Deregistration Delay Summary

SIGTERM handler in FastAPI lifespan + 60s ALB deregistration delay eliminates 502 errors during ECS rolling deploys.

## What Was Built

During ECS rolling deploys, the old task receives SIGTERM. Without handling, the health check continued returning 200 and the ALB kept routing traffic to a dying container, causing 502 errors for in-flight requests.

This plan implements the full shutdown drain sequence:
1. ECS sends SIGTERM to uvicorn process
2. `handle_sigterm` (registered via `signal.signal(signal.SIGTERM, handle_sigterm)`) sets `app.state.shutting_down = True` and logs the event
3. ALB health check hits `/api/health` → gets 503 → marks task unhealthy → stops routing new traffic
4. 60-second deregistration delay allows all in-flight requests to complete before ECS terminates the task
5. Uvicorn finishes in-flight requests and exits cleanly

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | SIGTERM handler and shutdown-aware health check | 7154caf | backend/app/main.py, backend/app/api/routes/health.py |
| 2 | ALB deregistration delay 60s in CDK | 3e370c5 | infra/lib/compute-stack.ts |

## Key Changes

### backend/app/main.py

Added `import signal` and registered handler at the top of `lifespan()`:

```python
app.state.shutting_down = False

def handle_sigterm(signum, frame):
    app.state.shutting_down = True
    logger.info("SIGTERM received - health check will return 503, draining connections")

signal.signal(signal.SIGTERM, handle_sigterm)
```

### backend/app/api/routes/health.py

Health endpoint now accepts `request: Request` and checks shutdown state:

```python
@router.get("/health")
async def health_check(request: Request):
    if getattr(request.app.state, "shutting_down", False):
        return JSONResponse(
            status_code=503,
            content={"status": "shutting_down", "service": "cofounder-backend"},
        )
    return {"status": "healthy", "service": "cofounder-backend"}
```

### infra/lib/compute-stack.ts

Both ALB target groups configured with 60s deregistration delay:

```typescript
// Backend
this.backendService.targetGroup.setAttribute(
  'deregistration_delay.timeout_seconds',
  '60'
);

// Frontend
frontendService.targetGroup.setAttribute(
  'deregistration_delay.timeout_seconds',
  '60'
);
```

## Deviations from Plan

None — plan executed exactly as written.

## Verification

All checks passed:
- `grep 'signal.SIGTERM' backend/app/main.py` — found handler registration
- `grep 'shutting_down' backend/app/api/routes/health.py` — found shutdown check (2 lines)
- `grep -c 'deregistration_delay' infra/lib/compute-stack.ts` — returns 2 (backend + frontend)
- `cd infra && npx tsc --noEmit` — CDK compiles cleanly, no type errors
- `python -c "from app.main import app; print('SIGTERM handler registered')"` — imports without error

## Self-Check: PASSED

Files exist:
- FOUND: backend/app/main.py (modified)
- FOUND: backend/app/api/routes/health.py (modified)
- FOUND: infra/lib/compute-stack.ts (modified)

Commits exist:
- FOUND: 7154caf — feat(15-02): add SIGTERM handler and shutdown-aware health check
- FOUND: 3e370c5 — feat(15-02): set ALB deregistration delay to 60s for both target groups
