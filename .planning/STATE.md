# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-18)

**Core value:** A non-technical founder can go from idea to running MVP preview in under 10 minutes, making product decisions the entire way.
**Current focus:** v0.2 Production Ready — Phase 13: LLM Activation and Hardening

## Current Position

Phase: 14 of 16 (Stripe Live Activation)
Plan: 1 of 4 in current phase
Status: In Progress
Last activity: 2026-02-19 — Phase 14 Plan 01 complete (Stripe billing hardening — idempotency, async SDK, startup validation)

Progress: [█░░░░░░░░░] 10% (v0.2) — v0.1 complete (phases 1-12)

## Performance Metrics

**Velocity (v0.1):**
- Total plans completed: 56
- Average duration: ~4.5 min
- Total execution time: ~4.2 hours

**By Phase (v0.1):**

| Phase | Plans | Avg/Plan |
|-------|-------|----------|
| 01-07 | 28    | ~4.0 min |
| 08-12 | 28    | ~5.0 min |

**Recent Trend:**
- Last 5 plans (v0.1): Phase 12 P01 (2 min), Phase 11 P02 (5 min), Phase 11 P01 (5 min), Phase 10 P11 (4 min), Phase 10 P10 (15 min)
- Trend: Stable

*Updated after each plan completion*

**Phase 13 (v0.2):**

| Plan | Duration | Tasks | Files |
|------|----------|-------|-------|
| Phase 13 P01 | 2 min | 2 tasks | 3 files |
| Phase 13 P02 | — | — | — |
| Phase 13 P03 | 2 min | 1 task | 1 file |
| Phase 13 P06 | 2 min | 2 tasks | 4 files |
| Phase 13 P04 | 3 | 3 tasks | 6 files |
| Phase 13 P05 | 3 | 1 tasks | 1 files |
| Phase 13 P07 | 5 | 2 tasks | 4 files |

**Phase 14 (v0.2):**

| Plan | Duration | Tasks | Files |
|------|----------|-------|-------|
| Phase 14 P01 | 3 min | 2 tasks | 5 files |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting v0.2 work:

- [v0.1]: Runner protocol wraps LangGraph via adapter — RunnerReal + RunnerFake both implement same 10-method protocol
- [v0.1]: create_tracked_llm() pattern already handles model resolution, usage tracking, tier enforcement — RunnerReal must use it
- [v0.1]: MemorySaver is test-only; AsyncPostgresSaver.from_conn_string() must replace it before RunnerReal goes live
- [v0.2]: LLM activation is critical path — Stripe enforcement and CloudWatch LLM alarms only become meaningful after RunnerReal is live
- [v0.2]: Phase 14 (Stripe) and Phase 15 (CI/CD) can be planned in parallel; both depend on Phase 13 being live first
- [v0.2]: Phase 16 (CloudWatch) must follow Phase 13 (real LLM calls must flow for LLM alarms to fire)
- [Phase 13]: Use async context manager split pattern in FastAPI lifespan to persist AsyncPostgresSaver across yield boundary
- [Phase 13]: Deprecate database_url param in create_production_graph in favor of injected checkpointer from app.state
- [Phase 13]: Exception fallback to MemorySaver ensures startup never hard-fails due to checkpointer initialization
- [Phase 13 P01]: _invoke_with_retry uses tenacity stop_after_attempt(4) with reraise=True — OverloadedError propagates after exhausting retries
- [Phase 13 P01]: UsageTrackingCallback logs failures at WARNING (not ERROR) — operational noise, not bugs
- [Phase 13 P01]: Import pattern for all subsequent plans: from app.agent.llm_helpers import _strip_json_fences, _parse_json_response, _invoke_with_retry
- [Phase 13 P03]: COFOUNDER_SYSTEM constant centralizes "we" voice — all RunnerReal methods use it via {task_instructions} template slot
- [Phase 13 P03]: assess_section_confidence uses plain-string keyword search (not JSON parse) with "moderate" as safe default
- [Phase 13 P03]: JSON retry pattern: catch JSONDecodeError, prepend strict prompt, retry once — no silent swallowing, raises RuntimeError on second failure
- [Phase 13 P06]: detect_llm_risks is async with module-level get_redis/get_or_create_user_settings imports for patchability in tests
- [Phase 13 P06]: build_failure_count queries Job.status=="failed" rows; journey.py uses project.clerk_user_id from already-loaded project
- [Phase 13]: get_runner() returns RunnerReal when ANTHROPIC_API_KEY is set; RunnerFake fallback for local dev
- [Phase 13]: OverloadedError after 4 retries: return 202 with queue message; enqueue to cofounder:llm_queue Redis list
- [Phase 13]: _tier injected via dict spread into answers/brief/onboarding_data — no runner method signature changes needed
- [Phase 13]: cto_scale tier gets 14 brief sections; _tier injection pattern avoids runner method signature changes; EXEC_PLAN_DETAIL_BY_TIER provides tier-conditional engineering analysis depth
- [Phase 13]: Mock create_tracked_llm via side_effect factory (not return_value) to handle async await chain correctly in RunnerReal tests
- [Phase 13]: httpx.Request required for OverloadedError constructor — plain httpx.Response(529) fails without attached request
- [Phase 13]: tenacity retry_with(wait=wait_none()) pattern for disabling backoff in tests without modifying production code
- [Phase 14 P01]: StripeWebhookEvent uses event_id as PK — PK collision on duplicate naturally raises IntegrityError without extra query
- [Phase 14 P01]: validate_price_map() returns early if settings.debug=True so local dev and tests are never blocked
- [Phase 14 P01]: success_url redirects to /dashboard?checkout_success=true (locked decision — main dashboard with success toast)
- [Phase 14 P01]: Payment failure sets plan_tier_id to bootstrapper immediately — no grace period; stripe_subscription_id preserved for Stripe recovery

### Pending Todos

None yet.

### Blockers/Concerns

- [Phase 13 prereq]: ANTHROPIC_API_KEY must be confirmed set in `cofounder/app` Secrets Manager before Phase 13 deploy
- [Phase 14 prereq]: Stripe Dashboard webhook URL must be registered after service deploy (operational ordering: deploy first, then register URL)
- [Phase 13 tech debt]: pytest-asyncio scope fix (CICD-08) needed before expanding test suite — deferred to Phase 15 but can be pulled into Phase 13 if tests fail

## Session Continuity

Last session: 2026-02-19
Stopped at: Phase 14 Plan 01 complete (Stripe billing hardening)
Resume file: .planning/phases/14-stripe-live-activation/14-01-SUMMARY.md
Next action: Execute Phase 14 Plan 02

---
*v0.1 COMPLETE — 56 plans, 12 phases, 76/76 requirements (2026-02-17)*
*v0.2 STARTED — roadmap defined, 4 phases, 41 requirements (2026-02-18)*
