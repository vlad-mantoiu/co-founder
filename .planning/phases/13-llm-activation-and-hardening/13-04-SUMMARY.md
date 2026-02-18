---
phase: 13-llm-activation-and-hardening
plan: "04"
subsystem: api-routes, services, llm-helpers
tags: [runner-real, llm-activation, overloaded-error, queue, tier-injection]
dependency_graph:
  requires: [13-01, 13-02]
  provides: [RunnerReal-wired, tier-context-flow, overloaded-queue]
  affects: [13-05, understanding-service, artifact-service, execution-plan-service]
tech_stack:
  added: []
  patterns: [queue-on-exhausted-retries, tier-injection-via-dict, RunnerReal-conditional]
key_files:
  created: []
  modified:
    - backend/app/api/routes/onboarding.py
    - backend/app/api/routes/understanding.py
    - backend/app/api/routes/execution_plans.py
    - backend/app/services/understanding_service.py
    - backend/app/services/artifact_service.py
    - backend/app/agent/llm_helpers.py
decisions:
  - "get_runner() returns RunnerReal when ANTHROPIC_API_KEY is set; RunnerFake fallback for local dev without API key"
  - "OverloadedError after 4 retries returns 202 with queue message; request payload stored in Redis cofounder:llm_queue for future consumer"
  - "_tier injected via dict spread into answers (before generate_idea_brief), brief_content, and onboarding_data (before generate_cascade) — no runner method signature changes needed"
metrics:
  duration: "3 min"
  completed_date: "2026-02-18"
  tasks_completed: 3
  files_modified: 6
---

# Phase 13 Plan 04: Wire RunnerReal + Fix Service Context + Queue-on-Exhausted Summary

RunnerReal wired into all 3 route files via conditional get_runner(), UnderstandingService context fixed with user_id/session_id/tier, _tier injected into answers/brief/onboarding_data for downstream tier-differentiated prompts, exhausted OverloadedError queued to Redis cofounder:llm_queue with 202 response.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Update get_runner() in all 3 route files to return RunnerReal | 948ab46 | onboarding.py, understanding.py, execution_plans.py |
| 2 | Fix UnderstandingService context passing and inject _tier into data dicts | 5460361 | understanding_service.py, artifact_service.py |
| 3 | Catch exhausted OverloadedError in route handlers and queue the request | b4266ab | llm_helpers.py, understanding.py, execution_plans.py, onboarding.py |

## What Was Built

### Task 1: get_runner() -> RunnerReal

All 3 route files (`onboarding.py`, `understanding.py`, `execution_plans.py`) now have identical conditional `get_runner(request: Request)` dependency:

```python
def get_runner(request: Request) -> Runner:
    from app.core.config import get_settings
    settings = get_settings()

    if settings.anthropic_api_key:
        from app.agent.runner_real import RunnerReal
        checkpointer = getattr(request.app.state, "checkpointer", None)
        return RunnerReal(checkpointer=checkpointer)
    else:
        return RunnerFake()
```

FastAPI automatically injects `Request` into the dependency. Route handlers with `Depends(get_runner)` are unchanged. Tests continue to work via `app.dependency_overrides`.

### Task 2: UnderstandingService Context + _tier Injection

**start_session**: Now resolves tier via `get_or_create_user_settings` and passes `user_id`, `session_id`, `tier` in context dict to `generate_understanding_questions`.

**edit_answer**: Now loads the parent `OnboardingSession` to pass the actual `idea_text` (not empty string `""`) to `check_question_relevance`.

**re_interview**: Now resolves tier and passes complete context (`onboarding_answers`, `user_id`, `session_id`, `tier`) to runner.

**finalize**: Now:
1. Resolves tier via `get_or_create_user_settings`
2. Creates `answers_with_tier = {**understanding.answers, "_tier": tier_slug}`
3. Passes `answers_with_tier` to `generate_idea_brief` (runner reads `answers.get("_tier", "bootstrapper")`)
4. Injects `brief_content["_tier"] = tier_slug` for downstream methods

**artifact_service.generate_all**: Creates `onboarding_data_with_tier = {**onboarding_data, "_tier": tier}` before `generate_cascade`. This flows through `ArtifactGenerator.generate_artifact` to `runner.generate_artifacts(brief_context)`.

### Task 3: enqueue_failed_request + OverloadedError Handlers

New `enqueue_failed_request()` in `llm_helpers.py`:
- Non-blocking Redis `rpush` to `cofounder:llm_queue`
- Stores: `user_id`, `session_id`, `action`, `payload`, `queued_at`
- Logs warning on Redis failure (does not re-raise)

OverloadedError wrapped in:
- `understanding.py`: `start_understanding`, `edit_answer`, `finalize_interview`, `re_interview`
- `execution_plans.py`: `generate_execution_plans`, `regenerate_execution_plans`
- `onboarding.py`: `start_onboarding`, `finalize_session`

All exhausted paths return:
```json
{"status": "queued", "message": "Added to queue — we'll continue automatically when capacity is available."}
```
with HTTP 202.

## Decisions Made

1. **get_runner() returns RunnerReal when ANTHROPIC_API_KEY is set** — Since config defines `anthropic_api_key: str` (required), in production this check is always True. The `else: RunnerFake()` branch serves local dev where the var might be overridden to empty via `.env`.

2. **OverloadedError returns 202 (not 500)** — The locked decision: queue the request instead of failing. HTTP 202 signals "accepted but not yet processed." The `cofounder:llm_queue` Redis list stores enough context for a future background worker to replay.

3. **_tier injected via dict spread, no method signature changes** — `{**answers, "_tier": tier_slug}` and `{**onboarding_data, "_tier": tier}` pass tier downstream without breaking existing Runner protocol method signatures. Plan 13-05 tier-differentiated prompts read `context.get("_tier", "bootstrapper")`.

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check

Files exist:
- backend/app/api/routes/onboarding.py: YES
- backend/app/api/routes/understanding.py: YES
- backend/app/api/routes/execution_plans.py: YES
- backend/app/services/understanding_service.py: YES
- backend/app/services/artifact_service.py: YES
- backend/app/agent/llm_helpers.py: YES

Commits exist:
- 948ab46: Task 1
- 5460361: Task 2
- b4266ab: Task 3

## Self-Check: PASSED
