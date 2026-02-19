---
phase: 16-cloudwatch-observability
plan: 01
subsystem: backend-logging
tags: [structlog, cloudwatch, observability, logging, correlation-id]
dependency_graph:
  requires: []
  provides: [structured-json-logs, correlation-id-injection, cloudwatch-insights-queryable]
  affects: [backend/app/core/logging.py, backend/app/main.py, backend/app/middleware/correlation.py, all-backend-py-files]
tech_stack:
  added: [structlog>=25.0.0]
  patterns: [stdlib-bridge, processor-chain, keyword-arg-logs, bound-loggers]
key_files:
  created:
    - backend/app/core/logging.py
  modified:
    - backend/app/main.py
    - backend/app/middleware/correlation.py
    - backend/pyproject.toml
    - backend/app/agent/runner_real.py
    - backend/app/agent/llm_helpers.py
    - backend/app/agent/nodes/architect.py
    - backend/app/core/llm_config.py
    - backend/app/services/deploy_readiness_service.py
    - backend/app/services/graph_service.py
    - backend/app/services/change_request_service.py
    - backend/app/services/gate_service.py
    - backend/app/services/generation_service.py
    - backend/app/services/timeline_service.py
    - backend/app/api/routes/strategy_graph.py
    - backend/app/api/routes/timeline.py
    - backend/app/api/routes/billing.py
    - backend/app/api/routes/generation.py
    - backend/app/api/routes/agent.py
    - backend/app/api/routes/health.py
    - backend/app/api/routes/deploy_readiness.py
    - backend/app/domain/risks.py
    - backend/app/queue/worker.py
    - backend/app/queue/scheduler.py
decisions:
  - "structlog 25.5.0 installed; stdlib bridge via ProcessorFormatter captures LangChain/uvicorn/FastAPI logs as JSON"
  - "configure_structlog() called before all app imports in main.py to avoid processor cache pitfall"
  - "setup_logging() removed from correlation.py — structlog handles all log formatting"
  - "Log event names use snake_case (e.g., startup_begin, http_exception) — not printf format strings"
  - "All error/warning calls include error_type=type(e).__name__ for CloudWatch Insights queryability"
  - "runner_real.py uses bound loggers per method via logger.bind(method=...)"
metrics:
  duration: 14 min
  completed_date: 2026-02-19
  tasks: 2
  files_modified: 23
---

# Phase 16 Plan 01: Structured JSON Logging (structlog Migration) Summary

**One-liner:** Migrated all 22 backend files from stdlib logging to structlog with JSONRenderer, stdlib bridge, and correlation_id injection — enabling CloudWatch Insights queries by correlation_id, user_id, and error_type.

## What Was Built

- **`backend/app/core/logging.py`** — Central structlog configuration with:
  - `configure_structlog(log_level, json_logs)` called at startup before any app imports
  - `add_correlation_id` processor injects from `asgi_correlation_id` context var
  - JSONRenderer for production, ConsoleRenderer for dev
  - `logging.config.dictConfig` stdlib bridge captures third-party logs (LangChain, uvicorn, FastAPI, httpx)
  - Shared processor chain: `merge_contextvars → add_log_level → add_logger_name → add_correlation_id → TimeStamper → StackInfoRenderer`

- **22 backend files migrated** from `import logging` / `logging.getLogger(__name__)` to `import structlog` / `structlog.get_logger(__name__)`

- **All log calls converted** from printf-style (`logger.info("msg %s", arg)`) to keyword-arg style (`logger.info("event_name", key=value)`)

## Task Commits

| Task | Commit | Description |
|------|--------|-------------|
| Task 1 | edaae27 | Create structlog configuration and stdlib bridge |
| Task 2 | fa98461 | Migrate all 20 remaining backend files |

## Verification Results

All 6 verification checks passed:

1. `grep -rn 'import logging' backend/app/ --include='*.py' | grep -v 'core/logging.py'` — returns zero lines
2. `grep -rn 'logging.getLogger' backend/app/ --include='*.py' | grep -v 'core/logging.py'` — returns zero lines
3. `grep -c 'configure_structlog' backend/app/main.py` — returns 3 (import, call, comment)
4. `grep -c 'structlog' backend/app/core/logging.py` — returns 17
5. `python -c "from app.main import app"` — no import errors
6. `grep 'structlog' backend/pyproject.toml` — `structlog>=25.0.0` listed

## Log Pattern Examples

**Before (stdlib):**
```python
logger.error(f"HTTP {exc.status_code} | debug_id={debug_id} | correlation_id={correlation_id} | path={path}")
logger.warning("Claude overloaded (attempt %d/4), retrying in %.1fs", rs.attempt_number, rs.next_action.sleep)
```

**After (structlog):**
```python
logger.error("http_exception", status_code=exc.status_code, debug_id=debug_id, path=path, user_id=user_id)
logger.warning("claude_overloaded_retrying", attempt=rs.attempt_number, sleep_seconds=rs.next_action.sleep)
```

**JSON output in production:**
```json
{"event": "http_exception", "level": "error", "timestamp": "2026-02-19T01:00:00Z", "logger": "app.main", "correlation_id": "abc-123", "status_code": 404, "path": "/api/projects/xyz"}
```

## Deviations from Plan

None — plan executed exactly as written. All 22 files identified in the plan were migrated. The `logging.config` import within `core/logging.py` itself is intentional (it configures the stdlib handler) and correctly excluded from the zero-stdlib-imports check.

## Self-Check: PASSED

- backend/app/core/logging.py: FOUND
- 16-01-SUMMARY.md: FOUND
- Commit edaae27 (Task 1): FOUND
- Commit fa98461 (Task 2): FOUND
