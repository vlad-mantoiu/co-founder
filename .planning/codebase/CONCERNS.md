# Codebase Concerns

**Analysis Date:** 2026-02-20

## Critical Integration Breaks

### 1. SSE Authentication Failure - Build Progress UI Non-Functional

**Severity:** Critical — Complete feature breakdown

**Problem:** The browser's native `EventSource` API cannot set custom HTTP headers (like `Authorization`). Frontend `useBuildProgress.ts` attempts SSE connection to `/api/jobs/{jobId}/stream` with auth requirement, causing every connection to return 401 Unauthorized.

**Impact:**
- Build progress page never displays real-time updates
- Builds DO complete server-side but users see failure state indefinitely
- "Build Progress Visibility" flow broken in main founder journey (blocks phase 10)

**Files:**
- `frontend/src/hooks/useBuildProgress.ts` lines 1-189 (already refactored to use long-polling)
- `backend/app/api/routes/jobs.py` lines 205-209 (SSE endpoint with auth requirement)

**Fix Status:** ✓ RESOLVED - Hook refactored to use authenticated long-polling via `apiFetch` with 5s intervals instead of SSE (lines 114-189)

**Remaining Work:** Verify `/api/generation/{jobId}/status` endpoint supports all polling clients and monitor request volume for performance

---

### 2. ProjectId Lost in Onboarding→Understanding Transition

**Severity:** Critical — Breaks main founder flow

**Problem:** After `createProject` API call succeeds, `useOnboarding.ts` redirects to `/dashboard` without passing the returned `project_id` via query parameters. When user navigates to `/understanding`, `projectId` is empty, causing downstream API calls with empty IDs.

**Impact:**
- Gate creation: `POST /api/gates/create` with `project_id: ""` returns 422
- Plan generation: `POST /api/plans/generate` with `""` returns 404
- Main flow blocked: onboarding → understanding → gate → plan → build

**Files:**
- `frontend/src/hooks/useOnboarding.ts` lines 454-460 (redirect without project context)
- `frontend/src/app/(dashboard)/understanding/page.tsx` line 64 (empty projectId read)

**Fix Approach:**
```typescript
// useOnboarding.ts — redirect with project context
const data = await response.json();
window.location.href = `/understanding?sessionId=${state.sessionId}&projectId=${data.project_id}`;
```

---

### 3. Brief Edit Always 404 - Param Mismatch

**Severity:** Medium — Edit feature broken, core flow unaffected

**Problem:** `useUnderstandingInterview.ts` sends `state.artifactId` to `PATCH /api/understanding/{project_id}/brief`, but the route expects `project_id`. Sending artifact UUID as route param returns 404.

**Impact:**
- Brief section edits visually succeed (optimistic update) then revert ~1s later with 404
- Confidence scores never persist
- User confidence in system reduced but core understanding workflow unaffected

**Files:**
- `frontend/src/hooks/useUnderstandingInterview.ts` line 327 (wrong param)
- `backend/app/api/routes/understanding.py` line 233 (expects project_id)

**Fix:** Use `projectId` from search params instead of `artifactId` in edit calls

---

## Known Tech Debt

### Build Failure Count Not Tracked

**Severity:** Low — Risk detection incomplete

**Problem:** `build_failure_count` is hardcoded to 0 via failed jobs query in `JourneyService` and `DashboardService`, but the logic doesn't preserve state between calls. Jobs can fail without incrementing a counter.

**Files:**
- `backend/app/services/journey.py` line 552 (always = 0)
- `backend/app/services/dashboard_service.py` line 157 (always = 0)
- `backend/app/domain/risks.py` lines 59-67 (rule exists but never triggered)

**Impact:** Risk rule "build_failures" (triggers at 3+ consecutive failures) never fires, even if builds consistently fail. Users won't see warnings about broken dependencies/code.

**Fix Approach:** Track failed job count in `Project.build_failure_count` column, reset on successful build, increment on failure

---

### LLM Risk Detection Incomplete

**Severity:** Low — Feature stub

**Problem:** `detect_llm_risks()` in `backend/app/domain/risks.py` only detects token usage (high_token_usage). No detection for:
- Rate limit errors from Anthropic API
- Latency degradation
- Model availability issues
- Cost trajectory warnings

**Files:**
- `backend/app/domain/risks.py` lines 83-125 (only checks token budget)
- Called from `backend/app/services/journey.py` line 564 and `dashboard_service.py` line 167

**Impact:** Users building complex projects won't get warnings about approaching rate limits or API instability until failures occur

---

## Neo4j Dual-Write Non-Fatal But Fragile

**Severity:** Medium — Silent degradation

**Problem:** Graph writes in `GateService._sync_to_graph()` are wrapped in try/except, so Neo4j failures silently fail. No alerting. If Neo4j becomes unavailable, the system continues to function but loses graph relationships.

**Files:**
- `backend/app/services/gate_service.py` (dual-write after gate resolution)
- `backend/app/services/graph_service.py` (graph operations)
- `backend/app/db/graph/strategy_graph.py` (Neo4j client)

**Impact:**
- Strategy graph visualization shows incomplete data
- Impact analysis queries return empty results
- No visibility into when sync fails (logs only, no monitoring)
- Current deployment requires Neo4j manual configuration

**Fix Approach:**
1. Add structured logging with attempt counts
2. CloudWatch metric for failed writes
3. Dashboard indicator for graph sync health
4. Fallback: Mark graph nodes as "unsynced" in PostgreSQL

---

## Force-Dynamic Performance Workaround

**Severity:** Low → Medium (design concern)

**Problem:** Dashboard layout forces Next.js dynamic rendering (`export const dynamic = "force-dynamic"`) because all dashboard pages use `useSearchParams()` in client components. This prevents any static prerendering and increases TTL.

**Files:**
- `frontend/src/app/(dashboard)/layout.tsx` line 6 (force-dynamic)
- Affects all dashboard children: dashboard, understanding, strategy, timeline, etc.

**Root Cause:** `useSearchParams()` is a client-side hook that can't be prerendered. All 7+ pages using it require dynamic rendering.

**Impact:**
- Every dashboard request hits server (no static caching)
- Higher latency for users
- Increased server load during peak usage
- CDN caching not possible

**Better Approach:**
1. Move search params to server-side via dynamic route segments: `[projectId]/page.tsx`
2. Or use URL-safe redirect pattern instead of query params
3. Or use context providers to pass IDs instead of search params

---

## Dashboard useSearchParams() Dependency

**Severity:** Medium — Architectural limitation

**Problem:** Dashboard pages rely on `useSearchParams()` to extract `projectId`, `sessionId`, etc. from URL. This client-side pattern forced the `force-dynamic` workaround and breaks static rendering.

**Files:**
- `frontend/src/app/(dashboard)/understanding/page.tsx` line 64 (projectId from params)
- `frontend/src/app/(dashboard)/dashboard/page.tsx` (search params usage)
- `frontend/src/app/(dashboard)/projects/[id]/page.tsx` (mix of params and search params)

**Examples of Pattern:**
```typescript
// Fragile pattern
const projectId = searchParams.get('projectId');  // Client-side, requires dynamic
```

**Better Pattern:**
```typescript
// Static-safe pattern
export default function Page({ params }: { params: { projectId: string } }) {
  // Server-side, can prerender
}
```

**Impact:** Cannot optimize dashboard for static caching, increases perceived latency

---

## Frontend Security: Admin Routes Listed as Public

**Severity:** Low — Backend protected, but violates defense-in-depth

**Problem:** `/admin(.*)` is listed in `isPublicRoute` in middleware, protected only by client-side `useAdmin` check. Backend `/api/admin` routes have proper `require_admin` dependency, but principle of defense-in-depth is violated.

**Files:**
- `frontend/src/middleware.ts` lines 4-16 (admin routes in public list)
- `backend/app/api/routes/admin.py` line 31 (proper require_admin check)

**Risk:** Minimal — backend auth is correct. But if client-side check is bypassed, `/admin` pages load and only fail when making API calls. Better to redirect at middleware level.

**Fix:** Remove `/admin(.*)` from `isPublicRoute`, add explicit check in middleware like `/api/admin` routes

---

## Orphaned Capacity Queue Endpoint

**Severity:** Medium — Rich features unused

**Problem:** Phase 5's `POST /api/jobs` (`submit_job`) with UsageTracker daily limits, WaitTimeEstimator, and TIER_DAILY_LIMIT enforcement is bypassed. Generation flow uses inline `QueueManager.enqueue()` in `/api/generation/start` instead, losing capacity management.

**Files:**
- `backend/app/api/routes/jobs.py` (unused endpoint)
- `backend/app/api/routes/generation.py` lines 1-360 (inline queue logic)
- `backend/app/queue/manager.py` (parallel queue implementation)

**Impact:** Two queue paths can diverge in rate-limiting behavior. UsageTracker daily limits and WaitTimeEstimator with confidence intervals from Phase 5 are not applied to generation jobs

**Fix:** Consolidate both paths to use Phase 5's queue with full tier enforcement

---

## Test Coverage Gaps — Async Fixture Limitations

**Severity:** Low — Logic tested via domain tests, integration gaps

**Problem:** 18+ integration tests deferred due to pytest-asyncio event loop limitations. Tests involving async fixtures with DB manipulation couldn't be written in Phase 6.

**Files:**
- `backend/tests/integration/artifacts/test_artifact_service.py` (12 tests deferred)
- `backend/tests/integration/generation/test_pdf_generation.py` (6 tests deferred)

**Impact:**
- PDF generation pipeline untested in integration (but covered by domain tests)
- Artifact service integration gaps not verified
- E2E tests in Phase 10 provide coverage but integration layer not fully validated

**Fix:** Upgrade pytest-asyncio or use alternative async test fixtures

---

## Complex Large Files

**Severity:** Low — Maintainability concern

**Problem:** Several backend modules exceed 750 lines, making them difficult to navigate and test:

**Files:**
- `backend/app/agent/runner_fake.py` (1,021 lines) — Scenario test double with all responses
- `backend/app/agent/runner_real.py` (764 lines) — Real LangGraph runner
- `backend/app/api/routes/artifacts.py` (752 lines) — Artifact export routes
- `backend/app/services/journey.py` (661 lines) — State machine orchestration

**Impact:**
- Hard to locate specific functionality
- Increased merge conflict risk
- Cognitive load when making changes
- Difficult to write focused unit tests

**Fix Approach:** Break into smaller modules by concern (e.g., separate PDF export, markdown export, JSON export in artifacts.py)

---

## Database Migration State

**Severity:** Low — Operational concern

**Problem:** Alembic migrations exist and are applied (10 migrations found), but no verification that migration history matches deployed state. If a migration is edited after application, next deploy could fail.

**Files:**
- `backend/alembic/versions/` (10 migration files)
- `backend/alembic.ini` (config)

**Monitoring Gap:** No pre-deploy check that migrations are clean and in order

---

## Performance Bottlenecks

### Long-Polling Poll Interval

**Severity:** Low — Usability tradeoff

**Problem:** `useBuildProgress.ts` polls `/api/generation/{jobId}/status` every 5 seconds. For slow builds, users see 5-second stale status. For fast builds, could add unnecessary load.

**Files:**
- `frontend/src/hooks/useBuildProgress.ts` line 172 (5000ms interval)

**Impact:**
- 5s latency for build progress visibility
- Multiple polls if build completes just after fetch
- Could be optimized with exponential backoff or shorter interval for critical stages

**Better Approach:** Shorter interval (2-3s) or exponential backoff that accelerates as stages progress

---

### Redis Connection Pooling

**Severity:** Low — Deployment concern

**Problem:** Redis client created via `get_redis()` singleton. No explicit connection pooling config. Under high concurrency, connection limits could be hit.

**Files:**
- `backend/app/db/redis.py` (Redis singleton)
- `backend/app/queue/semaphore.py` (heavy Redis user for concurrency limits)
- `backend/app/domain/risks.py` (Redis usage for token tracking)

**Monitoring Gap:** No metrics on Redis connection pool utilization

---

## Missing Observable Features

**Severity:** Low → Medium (observability gap)

**Problem:** No distributed tracing for critical paths:
- Gate resolution flow
- Artifact generation pipeline
- Neo4j sync operations
- Queue processing

**Impact:** When failures occur, hard to trace request through multiple services. Correlation IDs exist but not propagated to all services.

**Files:**
- `backend/app/middleware/correlation.py` (only on HTTP level)
- `backend/app/services/` (services don't pass correlation_id through async calls)

**Fix:** Implement context variables to propagate correlation_id through async call chains

---

## Scaling Limits Not Documented

**Severity:** Medium — Operational risk

**Problem:** No documented capacity limits:
- Max concurrent jobs per user/project (tier-based but not validated)
- PostgreSQL connection pool size
- Redis memory requirements for usage tracking
- ElastiCache capacity for sessions
- ECS Fargate task resource limits (512 CPU, 1GB memory)

**Files:**
- `backend/app/core/config.py` (no capacity constants)
- `infra/lib/compute-stack.ts` lines 79-87 (hardcoded task size)

**Impact:**
- Can't predict when system will hit limits
- No pre-emptive scaling strategy
- Cost trajectory unclear

---

## Missing Admin Observability

**Severity:** Low — Operational tooling gap

**Problem:** `/api/admin/*` routes for plan management and usage analytics exist but no admin dashboard in frontend. Only API-level access.

**Files:**
- `backend/app/api/routes/admin.py` (complete but frontend doesn't consume)
- No admin UI in frontend

**Impact:** Admins must use curl/Postman to view plans and usage. No real-time visibility into user tiers, token consumption, etc.

---

## Environment Configuration Validation

**Severity:** Medium — Deployment risk

**Problem:** `backend/app/core/config.py` loads from env but doesn't validate critical vars at startup. Missing keys silently default or cause cryptic errors at runtime.

**Files:**
- `backend/app/core/config.py` (config loading)
- `backend/app/main.py` (no pre-flight checks)

**Missing Checks:**
- ANTHROPIC_API_KEY present
- CLERK_SECRET_KEY present
- E2B_API_KEY present (if e2b integration enabled)
- DATABASE_URL valid PostgreSQL connection
- REDIS_URL valid Redis connection

**Fix:** Add `startup_checks()` in main.py that validates all required env vars before accepting requests

---

## Stripe Configuration in Production

**Severity:** Low — Integration concern

**Problem:** Stripe API key loaded from env. No validation that it's a prod key when ENVIRONMENT=production. If dev key accidentally used in prod, payments succeed but don't settle.

**Files:**
- `backend/app/core/config.py` (loads STRIPE_SECRET_KEY)
- `backend/app/api/routes/billing.py` (uses it)

**Fix:** Add check in startup that prod key starts with `sk_live_` if ENVIRONMENT=production

---

## Session Stale Management Gap

**Severity:** Low — Data consistency

**Problem:** Session records in PostgreSQL don't have automatic cleanup. Old sessions accumulate indefinitely. Script exists (`backend/scripts/fix_stale_sessions.py`) but not integrated into deployment or scheduled maintenance.

**Files:**
- `backend/scripts/fix_stale_sessions.py` (manual cleanup script)
- `backend/app/db/models/` (no TTL on sessions)

**Impact:** Database grows unbounded with stale session records, increases query time

**Fix:**
1. Add `created_at` TTL to session tables (expire after 30 days)
2. Schedule cleanup as Lambda or cron job
3. Or integrate `fix_stale_sessions.py` into deployment

---

## Marketing Site Deployment Coupling

**Severity:** Low → Medium (operational concern)

**Problem:** Marketing site (`/marketing`) is a separate Next.js 15 static export but shares no infrastructure with main app. Different build process, different deploy, different CDN.

**Files:**
- `marketing/next.config.ts` (output: "export")
- CI/CD doesn't exist for marketing yet (Phase 21 in progress)

**Impact:**
- Marketing updates require separate deploy
- Version drift between main site and marketing site
- No unified CDN strategy
- DNS routing manually managed

---

## Documentation Gaps

**Severity:** Low — Developer experience

**Problem:** No inline API documentation. OpenAPI/Swagger not exposed. Developers must read source or DEPLOYMENT.md to understand routes.

**Files:**
- `backend/app/api/routes/` (no OpenAPI decorators)
- `backend/app/main.py` (no swagger setup)

**Fix:** Add FastAPI OpenAPI/Swagger decorator or use Starlite/Litestar for auto-docs

---

## Summary of Action Priorities

| Issue | Severity | Blocks | Status |
|-------|----------|--------|--------|
| SSE Auth Break | Critical | Build progress | ✓ FIXED (long-polling) |
| ProjectId Lost | Critical | Main flow | Needs fix |
| Brief Edit 404 | Medium | Editing feature | Needs fix |
| Build Failure Count | Low | Risk detection | Deferred |
| Force-Dynamic | Medium | Performance | Deferred (design choice) |
| Neo4j Dual-Write | Medium | Graph visibility | Acceptable risk |
| Admin Client-Side Only | Low | Security principle | Deferred |
| Orphaned Queue Endpoint | Medium | Consistency | Deferred |
| Test Coverage Gaps | Low | Validation | E2E covers |
| Redis Pooling | Low | Scaling | Deferred |

---

*Concerns audit: 2026-02-20*
