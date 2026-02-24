---
phase: 40-langgraph-removal-protocol-extension
plan: 04
subsystem: backend/feature-flags, frontend/build-ux
tags: [feature-flag, migration, autonomous-agent, 501, frontend-banner]
dependency_graph:
  requires: [40-01, 40-03]
  provides: [AUTONOMOUS_AGENT feature flag, 501 response for autonomous mode, frontend coming-soon banner]
  affects:
    - backend/app/core/config.py
    - backend/app/api/routes/generation.py
    - backend/tests/agent/test_feature_flag_routing.py
    - backend/tests/api/test_generation_routes.py
    - frontend/src/app/(dashboard)/projects/[id]/build/page.tsx
tech_stack:
  added: []
  patterns: [feature flag routing, lru_cache patch pattern with model_copy, 501 HTTP status gate]
key_files:
  created:
    - backend/tests/agent/test_feature_flag_routing.py
  modified:
    - backend/app/core/config.py
    - backend/app/api/routes/generation.py
    - backend/tests/api/test_generation_routes.py
    - frontend/src/app/(dashboard)/projects/[id]/build/page.tsx
decisions:
  - "AUTONOMOUS_AGENT=true (default) returns 501 immediately at the top of start_generation before any gate/job logic"
  - "_get_runner() renamed to _build_runner() — cleaner separation of concerns, scoped to generation.py only"
  - "_real_settings_with_flag() helper uses model_copy() on real Settings — avoids MagicMock attribute errors when patching lru_cached get_settings across all callers"
  - "501 response before gate check is correct — flag=true means no job should be enqueued, so gate state is irrelevant"
metrics:
  duration: "8 minutes"
  completed: "2026-02-24"
  tasks_completed: 2
  files_modified: 4
  files_created: 1
---

# Phase 40 Plan 04: AUTONOMOUS_AGENT Feature Flag and Frontend Coming-Soon Banner Summary

AUTONOMOUS_AGENT feature flag wired to generation.py routing: flag=true (default) returns HTTP 501 "Your AI Co-Founder is being built" immediately from the build start endpoint, flag=false falls back to RunnerReal/RunnerFake; frontend build page detects 501 and shows a non-blocking blue "coming soon" banner scoped to the PreBuildView component.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Wire AUTONOMOUS_AGENT feature flag with 501 response | 3cdbe27 | config.py, generation.py, test_feature_flag_routing.py (new), test_generation_routes.py |
| 2 | Add frontend 501 "coming soon" banner on build page | 6281fdf | build/page.tsx |

## What Was Built

### Settings Extension (`backend/app/core/config.py`)

Added `autonomous_agent: bool = True` to the Settings class, placed after the existing feature flags block:

```python
# Feature flag for autonomous agent migration (Phase 40 — v0.7)
autonomous_agent: bool = True  # env: AUTONOMOUS_AGENT
```

pydantic-settings reads `AUTONOMOUS_AGENT` env var automatically. Default is `True` — conservative: build endpoint returns 501 until Phase 41 ships AutonomousRunner.

### Feature Flag Routing (`backend/app/api/routes/generation.py`)

Renamed `_get_runner()` to `_build_runner()` with three-way routing:

```python
def _build_runner(request: Request):
    """Return AutonomousRunner or RunnerReal based on AUTONOMOUS_AGENT flag."""
    settings = get_settings()
    if settings.autonomous_agent:
        from app.agent.runner_autonomous import AutonomousRunner
        return AutonomousRunner()
    elif settings.anthropic_api_key:
        from app.agent.runner_real import RunnerReal
        return RunnerReal()
    else:
        from app.agent.runner_fake import RunnerFake
        return RunnerFake()
```

501 gate in `start_generation` endpoint — fires before gate check and job creation:

```python
if _get_settings().autonomous_agent:
    raise HTTPException(
        status_code=501,
        detail="Autonomous agent coming soon. Your AI Co-Founder is being built.",
    )
```

### Test Coverage (`backend/tests/agent/test_feature_flag_routing.py`)

Created 7 new unit tests:
- `test_default_flag_value_is_true` — Settings default
- `test_flag_overridable_via_env_false` — env var override
- `test_flag_overridable_via_env_true` — env var override
- `test_flag_true_routes_to_autonomous_runner` — AutonomousRunner routing
- `test_flag_false_with_api_key_routes_to_runner_real` — RunnerReal routing
- `test_flag_false_no_api_key_routes_to_runner_fake` — RunnerFake routing
- `test_build_runner_function_exists_in_generation_module` — rename verification

### test_generation_routes.py — 2 New Tests + 3 Fixed Tests

Added:
- `test_start_generation_returns_501_when_autonomous_agent_true` — MIGR-02
- `test_start_generation_returns_201_when_autonomous_agent_false` — MIGR-02

Fixed (Rule 1 — these tests exercise the flag=false legacy path and need to mock it explicitly):
- `test_start_generation_returns_job_id`
- `test_start_generation_blocked_by_gate`
- `test_rerun_creates_new_version`

All three now use `_real_settings_with_flag(autonomous_agent=False)` via `model_copy()` — this returns a real Settings instance so downstream callers (`generation_service.py`, `worker.py`) still see all real settings fields.

### Frontend Banner (`frontend/src/app/(dashboard)/projects/[id]/build/page.tsx`)

In `PreBuildView`:

```tsx
const [comingSoon, setComingSoon] = useState(false);

// In handleStartBuild, before generic error handling:
if (res.status === 501) {
  setComingSoon(true);
  setStarting(false);
  return;
}

// In JSX, after error banner:
{comingSoon && (
  <div className="rounded-lg border border-blue-200 bg-blue-50 p-4 text-center dark:border-blue-800 dark:bg-blue-950">
    <p className="text-sm font-medium text-blue-800 dark:text-blue-200">
      Your AI Co-Founder is being built
    </p>
    <p className="mt-1 text-xs text-blue-600 dark:text-blue-400">
      We&apos;re upgrading your co-founder with autonomous capabilities. This feature will be available soon.
    </p>
  </div>
)}
```

Banner is non-blocking — navigation, the plan card, and the back link all remain functional.

## Verification Results

```
tests/agent/test_feature_flag_routing.py  — 7 passed
tests/api/test_generation_routes.py       — 22 passed (including 2 new + 3 fixed)
Full unit suite: 540 passed, 0 failures

Settings verification:
- python -c "from app.core.config import Settings; s = Settings(); assert s.autonomous_agent is True" → default True OK
- AUTONOMOUS_AGENT=false python -c "from app.core.config import Settings; s = Settings(); assert s.autonomous_agent is False" → override False OK

TypeScript: npx tsc --noEmit → 0 errors
```

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed _get_runner() still passing checkpointer= to RunnerReal()**

- **Found during:** Task 1 (reading generation.py — RunnerReal.__init__ takes no args after 40-03 removal)
- **Issue:** Old `_get_runner()` passed `checkpointer=checkpointer` to `RunnerReal()`, which now takes no args
- **Fix:** Renamed to `_build_runner()` and removed checkpointer — RunnerReal() needs no args (40-03 decision)
- **Files modified:** `backend/app/api/routes/generation.py`
- **Commit:** 3cdbe27

**2. [Rule 1 - Bug] Fixed 3 existing start_generation tests broken by AUTONOMOUS_AGENT=True default**

- **Found during:** Task 1 (running test_generation_routes.py — 3 tests expected 201, got 501)
- **Issue:** `test_start_generation_returns_job_id`, `test_start_generation_blocked_by_gate`, `test_rerun_creates_new_version` all hit the 501 gate because `Settings()` defaults to `autonomous_agent=True`
- **Fix:** Added `_real_settings_with_flag()` helper using `Settings.model_copy(update={"autonomous_agent": False})` — returns real Settings with all real defaults except the one overridden field; avoids MagicMock attribute explosion when patching lru_cached `get_settings`
- **Files modified:** `backend/tests/api/test_generation_routes.py`
- **Commit:** 3cdbe27

## Self-Check

Files created exist:
- [x] `backend/tests/agent/test_feature_flag_routing.py` — 7 tests, 100+ lines

Files modified exist:
- [x] `backend/app/core/config.py` — contains `autonomous_agent: bool = True`
- [x] `backend/app/api/routes/generation.py` — contains `_build_runner`, 501 response
- [x] `backend/tests/api/test_generation_routes.py` — contains `test_start_generation_returns_501_when_autonomous_agent_true`
- [x] `frontend/src/app/(dashboard)/projects/[id]/build/page.tsx` — contains `comingSoon`, `setComingSoon`, banner JSX

Commits exist:
- [x] 3cdbe27 — Task 1: feature flag + 501 response
- [x] 6281fdf — Task 2: frontend banner

## Self-Check: PASSED
