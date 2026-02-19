# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-18)

**Core value:** A non-technical founder can go from idea to running MVP preview in under 10 minutes, making product decisions the entire way.
**Current focus:** v0.2 Production Ready — Phase 17: CI/Deploy Pipeline Fix

## Current Position

Phase: 17 of 17 (CI/Deploy Pipeline Fix)
Plan: 1 of 2 in current phase (Plan 01 COMPLETE, Plan 02 remaining)
Status: In Progress
Last activity: 2026-02-19 — Phase 17 Plan 01 complete: 16 test failures fixed, clean working tree

Progress: [█████████░] 90% (v0.2) — v0.1 complete (phases 1-12), phases 13-17P01 complete

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
| Phase 14 P02 | 4 min | 1 task | 1 file |
| Phase 14 P03 | 3 | 2 tasks | 3 files |
| Phase 14 P04 | 15 min | 2 tasks | 1 file |

**Phase 15 (v0.2):**

| Plan | Duration | Tasks | Files |
|------|----------|-------|-------|
| Phase 15 P01 | 18 min | 2 tasks | 51 files |
| Phase 15 P02 | 1 min | 2 tasks | 3 files |
| Phase 15 P03 | 2 min | 3 tasks | 4 files |

**Phase 16 (v0.2):**

| Plan | Duration | Tasks | Files |
|------|----------|-------|-------|
| Phase 16 P02 | 2 min | 2 tasks | 3 files |
| Phase 16 P01 | 14 | 2 tasks | 23 files |
| Phase 16 P03 | 8 | 2 tasks | 6 files |

**Phase 17 (v0.2):**

| Plan | Duration | Tasks | Files |
|------|----------|-------|-------|
| Phase 17 P01 | 25 min | 2 tasks | 13 files |

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
- [Phase 14 P02]: Use stripe.SignatureVerificationError (not generic Exception) in webhook signature mocks — billing.py only catches specific exception types
- [Phase 14 P02]: Unit-test _handle_payment_failed directly via patched session factory to avoid asyncio event-loop conflicts with sync TestClient
- [Phase 14 P02]: Billing webhook tests: patch stripe.Webhook.construct_event with return_value=fake_event dict; async SDK tests: AsyncMock with assert_called_once()
- [Phase 14]: UsageMeter shown as first visual element for subscribed users — token usage is the primary billing signal
- [Phase 14]: CheckoutSuccessDetector and CheckoutAutoRedirector are separate client components in Suspense — Next.js 15 requires useSearchParams callers to be inside Suspense
- [Phase 14]: Billing page upgrade section references $99/mo explicitly — no 'free tier' framing for bootstrapper
- [Phase 14 P04]: Annual pricing cards show 'billed annually' beneath price figure — clarifies lump-sum annual charge to founders
- [Phase 14 P04]: Webhook endpoint registered at https://api.cofounder.getinsourced.ai/api/webhooks/stripe; signing secret in cofounder/app Secrets Manager
- [Phase 15 P01]: asyncio_default_fixture_loop_scope="function" — each test gets isolated event loop, prevents cross-test contamination
- [Phase 15 P01]: Test categorization correction — test_auth.py, test_response_contracts.py, test_artifact_markdown_export.py, test_generation_service.py, test_gate2_and_change_requests.py, test_iteration_build.py marked unit (plan said integration)
- [Phase 15 P01]: test_feature_flags.py and test_provisioning.py in domain/ marked integration (require real PostgreSQL)
- [Phase 15 P02]: SIGTERM handler sets app.state.shutting_down bool in main thread; health check reads it defensively via getattr with False default
- [Phase 15 P02]: ALB setAttribute() workaround for 60s deregistration delay (CDK Issue #4015 — no first-class prop on ApplicationLoadBalancedFargateService)
- [Phase 15 P03]: Use workflow_run (not needs:) to chain deploy.yml after test.yml — separate workflows cannot use needs: across files
- [Phase 15 P03]: workflow_dispatch bypasses test gate and path filter by design — changes job conditional on workflow_run only; hotfix use case
- [Phase 15 P03]: CDK deploy step removed from deploy.yml — infrastructure changes require deliberate CDK runs, not every code push
- [Phase 15 P03]: ECS task definitions fetched dynamically from ECS at deploy time via describe-task-definition — avoids staleness when CDK updates infra
- [Phase 15 P03]: always() + needs.result == 'success' + changes.result == 'skipped' pattern handles skipped changes job on manual dispatch
- [Phase 16]: ObservabilityStack uses physical resource ID props (not Fn.importValue) to avoid circular dependency risk
- [Phase 16]: ECS task count alarm uses BREACHING for missing data; ALB/latency alarms use NOT_BREACHING (absence of traffic != alert)
- [Phase 16]: FilterPattern.anyTerm(ERROR, level:error) covers both stdlib and structlog JSON logs during migration window
- [Phase 16]: structlog 25.5.0 with stdlib bridge replaces all stdlib logging in backend
- [Phase 16]: configure_structlog() called before all app imports in main.py to prevent processor cache pitfall
- [Phase 16]: All log calls use snake_case event names with keyword args; error_type= on every error/warning
- [Phase 16]: ThreadPoolExecutor(max_workers=2) dispatches boto3 put_metric_data calls off async event loop for fire-and-forget metric emission
- [Phase 16]: llm.model property (ChatAnthropic) used to extract resolved model name in RunnerReal LLM latency metrics — no extra params needed
- [Phase 16]: artifact_generated metric only emitted on successful build completion in execute_build — not on failure or in finally block
- [Phase 17 P01]: Future-date pattern for fakeredis: use datetime(2030, 6, 15) to avoid expireat expiring keys immediately when test date is in the past
- [Phase 17 P01]: Patch app.core.provisioning.provision_user_on_first_login (not app.core.auth.*) — lazy import inside require_auth means module-level auth patch misses the function
- [Phase 17 P01]: Ruff CI lint gate had 751 pre-existing errors before this plan — not in scope; ruff was already failing CI

### Pending Todos

- [ ] Verify workflow_run gate: push a commit with a failing test and confirm deploy.yml does NOT trigger
- [ ] Verify path filtering: push a backend-only change and confirm deploy-frontend job is skipped in Actions UI
- [RESOLVED] Fix 16 pre-existing unit test failures — all fixed in Phase 17 Plan 01 (commit c8e7a38)
- [ ] Fix ruff CI lint gate: 751 pre-existing errors blocking CI lint step (separate from test gate)

### Blockers/Concerns

- [Phase 13 prereq]: ANTHROPIC_API_KEY must be confirmed set in `cofounder/app` Secrets Manager before Phase 13 deploy
- [Phase 14 prereq]: Stripe Dashboard webhook URL must be registered after service deploy (operational ordering: deploy first, then register URL)
- [Phase 15 P01 - RESOLVED]: pytest-asyncio scope fix (CICD-08) complete
- [Phase 17 P01 - RESOLVED]: 16 pre-existing unit test failures fixed (c8e7a38)
- [Phase 17 ACTIVE]: Ruff CI lint gate has 751 pre-existing errors — CI lint step will fail until resolved

## Session Continuity

Last session: 2026-02-19
Stopped at: Phase 17 Plan 01 complete — 16 test failures fixed, clean working tree
Resume file: .planning/phases/17-ci-deploy-pipeline-fix/17-01-SUMMARY.md
Next action: Execute Phase 17 Plan 02 — dynamic ECS service name resolution in deploy.yml

---
*v0.1 COMPLETE — 56 plans, 12 phases, 76/76 requirements (2026-02-17)*
*v0.2 IN PROGRESS — 5 phases (13-17), 43 requirements, phases 13-16 complete, phase 17 P01 complete (2026-02-19)*
