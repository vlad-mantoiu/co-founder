# Phase 17: CI/Deploy Pipeline Fix - Context

**Gathered:** 2026-02-19
**Status:** Ready for planning

<domain>
## Phase Boundary

Fix the 16 pre-existing test failures blocking the CI gate and correct ECS service names in deploy.yml so the first automated deploy succeeds. Also clean up the git working tree (unstaged changes from v0.2 development). This is gap closure — no new features.

</domain>

<decisions>
## Implementation Decisions

### Test fix strategy
- Investigate each of the 16 failures individually — don't assume all are stale v0.1 assertions
- If a test is testing behavior intentionally changed in v0.2, delete and rewrite rather than patching dead code
- For the 8 test_usage_counters failures: review both the API and the tests — if the API shape seems wrong, fix both together
- Scope includes filling obvious test coverage gaps for v0.2 features if noticed, but primary goal is fixing the 16 failures

### ECS service name resolution
- Query live AWS (aws ecs list-services) to resolve actual CDK-generated service names with random suffixes
- deploy.yml resolves service names dynamically at deploy time — same pattern as existing dynamic task definition lookup
- Filter by known prefix (e.g., "cofounder") against the cofounder-cluster
- Fail loudly if service name can't be resolved — abort deploy with clear error, no silent wrong deploys, no fallback to hardcoded names

### Verification approach
- Run pytest locally first to catch obvious issues, then CI as final validation
- Query aws ecs list-services and compare against what deploy.yml would resolve — don't attempt a live deploy just to verify names
- Definition of "done": green CI on main AND a successful ECS deploy
- If deploy fails due to issues outside original scope (missing env var, Docker build issue), handle it in this phase — fix whatever prevents the first successful deploy

### Deleted test files
- Investigate test_agent.py and test_auth.py deletions before deciding — check if they contain any of the 16 failing tests
- Per-file decision: if coverage exists elsewhere (replaced by better Phase 13-16 tests), stage the deletion; if unique coverage would be lost, restore and fix

### Git working tree cleanup
- Clean up all pending unstaged changes — stage everything for a clean working tree before deploy
- Commit grouping at Claude's discretion — group by whatever makes git log most readable

### Claude's Discretion
- Per-file decision on whether deleted tests should be restored or staged for deletion
- Commit grouping strategy for git cleanup (single vs grouped by area)
- Which v0.2 coverage gaps are "obvious" enough to fill vs defer

</decisions>

<specifics>
## Specific Ideas

- Dynamic service name resolution should follow the exact same pattern as the existing dynamic task definition lookup in deploy.yml (Phase 15 decision: ECS task definitions fetched dynamically via describe-task-definition)
- The 16 failures are distributed: test_auth (4), test_usage_counters (8), test_runner_protocol (1), test_runner_fake (2), test_artifact_models (1)
- Phase is truly "done" only when GitHub Actions shows green AND a real ECS deploy succeeds — not just local pytest passing

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 17-ci-deploy-pipeline-fix*
*Context gathered: 2026-02-19*
