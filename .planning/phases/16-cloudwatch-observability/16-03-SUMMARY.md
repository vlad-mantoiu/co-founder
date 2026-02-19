---
phase: 16-cloudwatch-observability
plan: 03
subsystem: backend-metrics
tags: [cloudwatch, metrics, llm-latency, business-events, boto3, fire-and-forget]
dependency_graph:
  requires: [16-01]
  provides: [llm-latency-metrics, business-event-metrics, cloudwatch-custom-metrics]
  affects:
    - backend/app/metrics/cloudwatch.py
    - backend/app/agent/runner_real.py
    - backend/app/api/routes/billing.py
    - backend/app/services/generation_service.py
tech_stack:
  added: [boto3>=1.35.0]
  patterns: [ThreadPoolExecutor-fire-and-forget, run_in_executor, lazy-boto3-client]
key_files:
  created:
    - backend/app/metrics/__init__.py
    - backend/app/metrics/cloudwatch.py
  modified:
    - backend/app/agent/runner_real.py
    - backend/app/api/routes/billing.py
    - backend/app/services/generation_service.py
    - backend/pyproject.toml
decisions:
  - "ThreadPoolExecutor(max_workers=2) dispatches boto3 put_metric_data calls off async event loop — boto3 is synchronous, loop.run_in_executor provides fire-and-forget without awaiting"
  - "llm.model property (ChatAnthropic) used to extract resolved model name in RunnerReal methods — avoids re-resolving model or passing extra params"
  - "clerk_user_id extracted from user_settings.clerk_user_id in _handle_subscription_deleted — subscription dict only has customer_id, not clerk_user_id directly"
  - "artifact_generated only emitted on successful completion in execute_build, not in finally block and not on exception path"
  - "Timing wraps entire LLM call including JSON retry (t0 before first attempt, emit after final result) — measures total wall-clock time including retries"
metrics:
  duration: 8 min
  completed_date: 2026-02-19
  tasks: 2
  files_modified: 6
---

# Phase 16 Plan 03: CloudWatch Custom Metrics (LLM Latency + Business Events) Summary

**One-liner:** Added CloudWatch metric emission for LLM call latency (8 RunnerReal methods via ThreadPoolExecutor fire-and-forget) and 3 business events (new_subscription, subscription_cancelled, artifact_generated) using boto3 put_metric_data.

## What Was Built

- **`backend/app/metrics/__init__.py`** — Package init for metrics module (empty).

- **`backend/app/metrics/cloudwatch.py`** — Central metric emission module with:
  - `emit_llm_latency(method_name, duration_ms, model)` — async fire-and-forget; dispatches to ThreadPoolExecutor
  - `emit_business_event(event_name, user_id=None)` — async fire-and-forget; dispatches to ThreadPoolExecutor
  - `_put_llm_latency` / `_put_business_event` — synchronous worker functions that run in thread pool
  - `_get_client()` — lazy boto3 CloudWatch client initialization (us-east-1)
  - `ThreadPoolExecutor(max_workers=2, thread_name_prefix="cw-metrics")` — off-loop dispatch
  - `CoFounder/LLM` namespace: Latency metric with Method + Model dimensions
  - `CoFounder/Business` namespace: EventCount metric with Event + optional UserId dimensions
  - All exceptions caught internally — metric failure NEVER propagates to caller

- **`backend/app/agent/runner_real.py`** — 8 methods instrumented with LLM latency timing:
  1. `generate_questions` — t0 wraps try/except retry pattern; emits after result
  2. `generate_brief` — same pattern
  3. `generate_understanding_questions` — same pattern
  4. `generate_idea_brief` — same pattern
  5. `check_question_relevance` — same pattern
  6. `assess_section_confidence` — simpler (no JSON retry); t0/emit wraps single call
  7. `generate_execution_options` — try/except retry pattern
  8. `generate_artifacts` — try/except retry pattern
  - Uses `llm.model` (ChatAnthropic property) to extract resolved model name
  - `import time` added at top; `from app.metrics.cloudwatch import emit_llm_latency` added

- **`backend/app/api/routes/billing.py`** — Business events:
  - `_handle_checkout_completed`: emits `new_subscription` after successful DB commit
  - `_handle_subscription_deleted`: extracts `clerk_user_id` from `user_settings.clerk_user_id`, emits `subscription_cancelled` after successful downgrade

- **`backend/app/services/generation_service.py`** — Business event:
  - `execute_build`: emits `artifact_generated` after post-build hook, before return — ONLY on successful pipeline completion, not in except block

- **`backend/pyproject.toml`** — Added `boto3>=1.35.0` to production dependencies

## Task Commits

| Task | Commit | Description |
|------|--------|-------------|
| Task 1 | b1e5776 | Create CloudWatch metrics module with LLM latency and business event emitters |
| Task 2 | f728bc6 | Instrument RunnerReal LLM methods with latency metrics and business events |

## Verification Results

All 7 verification checks passed:

1. `grep -c 'emit_llm_latency' backend/app/agent/runner_real.py` — returns 9 (1 import + 8 calls)
2. `grep -c 'emit_business_event' backend/app/api/routes/billing.py` — returns 3 (1 import + 2 calls)
3. `grep 'emit_business_event' backend/app/services/generation_service.py` — finds artifact_generated emission
4. `grep 'ThreadPoolExecutor' backend/app/metrics/cloudwatch.py` — confirms async emission via executor
5. `python -c "from app.main import app"` — no import errors
6. `grep 'CoFounder/LLM' backend/app/metrics/cloudwatch.py` — namespace defined
7. `grep 'CoFounder/Business' backend/app/metrics/cloudwatch.py` — namespace defined

## Metric Dimensions

**CoFounder/LLM / Latency:**
```
Namespace: CoFounder/LLM
MetricName: Latency
Unit: Milliseconds
Dimensions:
  - Method: generate_questions | generate_brief | generate_understanding_questions | generate_idea_brief
           | check_question_relevance | assess_section_confidence | generate_execution_options | generate_artifacts
  - Model: claude-sonnet-4-20250514 | claude-opus-4-20250514 (resolved per user/role)
```

**CoFounder/Business / EventCount:**
```
Namespace: CoFounder/Business
MetricName: EventCount
Unit: Count (value=1.0 per event)
Dimensions:
  - Event: new_subscription | subscription_cancelled | artifact_generated
  - UserId: clerk_user_id (optional, present when available)
```

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical Dependency] Added boto3 to pyproject.toml**
- **Found during:** Task 1 verification
- **Issue:** boto3 installed in local venv but not listed in pyproject.toml — Docker image builds would fail without it
- **Fix:** Added `boto3>=1.35.0` to production dependencies in pyproject.toml
- **Files modified:** backend/pyproject.toml
- **Commit:** b1e5776

**2. [Rule 1 - Bug] Fixed JSON retry try/except pattern to preserve emit timing**
- **Found during:** Task 2 implementation
- **Issue:** Original plan showed wrapping `_invoke_with_retry` in try/except but `JSONDecodeError` is raised by `_parse_json_response`, not `_invoke_with_retry`. Naive refactoring would break the catch.
- **Fix:** Restructured to: `result = _parse_json_response(response.content)` inside try/except, emit after block, return result — preserves original semantics while adding timing
- **Files modified:** backend/app/agent/runner_real.py
- **Commit:** f728bc6

## Self-Check: PASSED

- backend/app/metrics/__init__.py: FOUND
- backend/app/metrics/cloudwatch.py: FOUND
- 16-03-SUMMARY.md: FOUND
- Commit b1e5776 (Task 1): FOUND
- Commit f728bc6 (Task 2): FOUND
