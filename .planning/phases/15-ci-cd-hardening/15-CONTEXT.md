# Phase 15: CI/CD Hardening - Context

**Gathered:** 2026-02-19
**Status:** Ready for planning

<domain>
## Phase Boundary

No broken code can reach production. Deploys are test-gated, path-filtered, and traceable to a specific image SHA. Rolling deploys shut down gracefully with no 502s. All 18 deferred integration tests are fixed and passing.

</domain>

<decisions>
## Implementation Decisions

### Test gate strictness
- Only pytest (unit + integration) blocks deploys — no ruff, no mypy, no frontend build check in the gate
- Gate applies to PRs targeting main only — feature branches push freely
- Merge is blocked via GitHub branch protection (not advisory) — cannot merge with failing tests
- Fix the pytest-asyncio scope issue and ensure all 18 deferred integration tests pass as part of this phase — the gate is only as good as the tests behind it

### Deploy trigger model
- Auto-deploy on merge to main — every merge triggers build + deploy
- Backend and frontend deploy independently based on path filtering: `backend/` changes deploy backend only, `frontend/` changes deploy frontend only, both change = both deploy
- Changes to shared files (`docker/`, `infra/`, root configs) trigger both deploys as a safety net
- Manual deploy button (workflow_dispatch) available as fallback for hotfixes or emergency redeploys

### Rollback strategy
- Manual redeploy of previous SHA via workflow_dispatch — no automatic rollback on health check failure
- ECR images tagged with git SHA + `latest` — SHA enables precise rollback, `latest` for convenience
- 60-second graceful shutdown window — ALB deregistration delay + SIGTERM handler
- Backend handles SIGTERM gracefully: stop accepting new requests, wait for in-flight to complete (up to timeout), then exit cleanly

### Deploy notifications
- GitHub status checks only — no email, no Slack, no external notifications
- GitHub deployment environment status shows which SHA is currently deployed to production
- Deploy logs live in GitHub Actions run logs only — no CloudWatch push for deploy metadata

### Claude's Discretion
- Exact GitHub Actions workflow structure (jobs, steps, caching)
- Path filter implementation details (dorny/paths-filter vs native)
- SIGTERM handler implementation pattern in FastAPI/uvicorn
- Branch protection API configuration approach

</decisions>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 15-ci-cd-hardening*
*Context gathered: 2026-02-19*
