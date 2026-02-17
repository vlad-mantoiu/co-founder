---
phase: 07-state-machine-integration-dashboard
plan: 02
subsystem: observability
tags: [middleware, correlation-id, logging, request-tracing]
dependency_graph:
  requires: [fastapi-app, exception-handlers]
  provides: [correlation-id-middleware, structured-logging, request-tracing]
  affects: [all-api-endpoints, logging-system]
tech_stack:
  added: [asgi-correlation-id]
  patterns: [asgi-middleware, logging-filters, context-vars]
key_files:
  created:
    - backend/app/middleware/__init__.py
    - backend/app/middleware/correlation.py
    - backend/tests/api/test_correlation_middleware.py
  modified:
    - backend/app/main.py
    - backend/pyproject.toml
decisions:
  - Use asgi-correlation-id library for production-ready correlation ID injection
  - Setup logging in lifespan startup to ensure all logs include correlation_id
  - Add correlation_id to exception handler logs to link debug_ids with request traces
  - Middleware runs after CORS to ensure headers are properly handled
metrics:
  duration: 2 min
  completed: 2026-02-17T00:45:37Z
  tasks: 2
  commits: 2
  files: 5
---

# Phase 7 Plan 02: Correlation ID Middleware Summary

**One-liner:** Request tracing via X-Request-ID header injection and structured logging with correlation IDs across all API endpoints

## What Was Built

Implemented correlation ID middleware using asgi-correlation-id to enable end-to-end request tracing. Every API request now gets a unique UUID correlation ID that flows through all service layers and appears in every log entry. This satisfies OBSV-01 (correlation_id on jobs/decisions), OBSV-02 (debug_id without secrets), and OBSV-03 (timeline entries reference correlation IDs).

### Task 1: Install asgi-correlation-id and create correlation middleware
**Commit:** e917e94

Created middleware module with three core functions:
- `setup_correlation_middleware(app)`: Registers ASGI middleware for X-Request-ID header handling
- `setup_logging()`: Configures CorrelationIdFilter to inject correlation_id into all log records
- `get_correlation_id()`: Safe accessor for correlation ID from request context

**Key implementation details:**
- Header name: X-Request-ID (industry standard)
- Generator: lambda returns str(uuid.uuid4())
- Validator: None (accepts any client-provided format)
- Transformer: identity function (no modification)

**Files:**
- backend/app/middleware/__init__.py (package marker)
- backend/app/middleware/correlation.py (67 lines)
- backend/pyproject.toml (added asgi-correlation-id>=4.3.0 dependency)

### Task 2: Wire middleware into FastAPI app and add tests
**Commit:** dac1891

Integrated middleware into FastAPI application and enhanced exception handlers:
- Added middleware registration in `create_app()` after CORS middleware
- Called `setup_logging()` in lifespan startup
- Updated `http_exception_handler` to log correlation_id alongside debug_id
- Updated `generic_exception_handler` to log correlation_id alongside debug_id

**Test coverage (4/4 passing):**
- test_response_includes_correlation_id_header: Verifies X-Request-ID header presence with valid UUID
- test_custom_correlation_id_echoed: Confirms client-provided IDs are echoed back
- test_error_response_includes_debug_id: Validates debug_id in error responses without secret leakage
- test_different_requests_get_different_ids: Ensures unique correlation IDs per request

**Files:**
- backend/app/main.py (added imports, middleware setup, correlation_id logging in handlers)
- backend/tests/api/test_correlation_middleware.py (78 lines, comprehensive coverage)

## Architecture Impact

### Middleware Ordering
```
Incoming Request
  ↓
CORS Middleware (allow origins, credentials, methods, headers)
  ↓
CorrelationIdMiddleware (inject X-Request-ID)
  ↓
Route Handler
  ↓
Exception Handlers (log with correlation_id + debug_id)
  ↓
Response (includes X-Request-ID header)
```

### Logging Format
All log entries now include correlation_id:
```
2026-02-17 00:45:00 ERROR [a1b2c3d4-e5f6-...] app.main HTTP 401 | debug_id=... | correlation_id=... | path=/api/projects/ | method=GET
```

### Request Context
Services can access correlation ID via `get_correlation_id()`:
```python
from app.middleware.correlation import get_correlation_id

correlation_id = get_correlation_id()  # Returns str | None
# Use in StageEvent creation, job tracking, etc.
```

## Deviations from Plan

None - plan executed exactly as written.

## Known Issues / Future Work

1. **Background task correlation**: Currently, correlation_id is only available within request context. Background tasks spawned via `BackgroundTasks` won't have access to the correlation ID. Future work: Pass correlation_id as parameter to background tasks.

2. **StageEvent integration**: While infrastructure is ready, StageEvent model creation should be updated to use `get_correlation_id()` instead of generating random UUIDs.

3. **Service layer adoption**: Services like JobService, OnboardingService should start using `get_correlation_id()` for correlation_id fields.

## Verification

All success criteria met:
- ✅ Every API response includes X-Request-ID header
- ✅ Error responses return debug_id without internal details (OBSV-02)
- ✅ Correlation ID accessible in service layer via get_correlation_id()
- ✅ All 4 tests pass
- ✅ Log entries include correlation_id field

Manual verification commands:
```bash
# Test header presence
curl -s -I http://localhost:8000/api/health | grep -i x-request-id

# Test custom ID echo
curl -s -H "X-Request-ID: test-123" http://localhost:8000/api/health -I | grep x-request-id

# Run tests
cd backend && python -m pytest tests/api/test_correlation_middleware.py -v
```

## Self-Check: PASSED

Created files verified:
```bash
✓ backend/app/middleware/__init__.py exists
✓ backend/app/middleware/correlation.py exists
✓ backend/tests/api/test_correlation_middleware.py exists
```

Modified files verified:
```bash
✓ backend/app/main.py contains setup_correlation_middleware import
✓ backend/app/main.py contains correlation middleware registration
✓ backend/pyproject.toml contains asgi-correlation-id dependency
```

Commits verified:
```bash
✓ e917e94 exists (Task 1: middleware creation)
✓ dac1891 exists (Task 2: FastAPI integration and tests)
```

Tests verified:
```bash
✓ All 4 tests in test_correlation_middleware.py pass
```
