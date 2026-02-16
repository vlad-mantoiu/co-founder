# Phase 1: Runner Interface & Test Foundation - Context

**Gathered:** 2026-02-16
**Status:** Ready for planning

<domain>
## Phase Boundary

Wrap the existing LangGraph agent pipeline with a testable Runner interface (RunnerReal/RunnerFake) and establish the test harness structure for the entire project. Runner covers ALL LLM operations in the system (not just code generation). Fix critical tech debt that affects reliability.

</domain>

<decisions>
## Implementation Decisions

### Runner Scope
- Runner protocol covers ALL LLM operations: code generation pipeline, onboarding questions, understanding interview, brief generation, artifact generation
- Expose both full pipeline and individual stages: `Runner.run(goal)` for end-to-end AND `Runner.step(stage)` for individual node execution
- The existing 6-node LangGraph pipeline (Architect → Coder → Executor → Debugger → Reviewer → GitManager) wrapped without modification
- Additional Runner methods for non-pipeline LLM calls: `Runner.generate_questions()`, `Runner.generate_brief()`, `Runner.generate_artifacts()`, etc.

### Test Double Behavior
- Scenario-based RunnerFake with named scenarios: `happy_path`, `llm_failure`, `partial_build`, `rate_limited`
- Each scenario is a pre-built response set that covers the full founder flow for that path
- Realistic content in fakes — plausible code, briefs, and artifacts (not "test stub" or "lorem ipsum")
- All 4 scenarios must be pre-built for MVP

### Test Harness Structure
- Separate directories for each test group: `tests/api/`, `tests/domain/`, `tests/orchestration/`, `tests/e2e/`
- Both single command (`pytest`) and convenience targets (`make test-api`, `make test-domain`, `make test-e2e`, `make test`)
- GitHub Actions CI pipeline with PostgreSQL + Redis services
- Tests runnable locally with identical behavior to CI

### Claude's Discretion
- Whether RunnerFake uses instant returns or configurable delays (pick what makes tests fastest and most reliable)
- Whether outputs are fully deterministic (same seed = identical) or schema-stable (pick what's most practical for CI)
- Test function naming convention (spec IDs in names vs descriptive names with IDs in docstrings)
- Tech debt triage: Mem0 async fix, datetime.utcnow() replacement, silent exception fixes, health check fix — Claude decides what to include in Phase 1 vs defer, based on risk to Runner reliability and foundation stability

</decisions>

<specifics>
## Specific Ideas

- The spec explicitly defines RunnerReal (actual tools/LLMs) and RunnerFake (tests) as a core pattern
- RunnerFake scenarios map to spec test groups: happy path covers Stories A-M, LLM failure covers D3/H6, partial build covers H6/L3, rate limited covers X1
- Test harness must support the spec's TDD execution order (A→B→C→D→E→F→G→H→I→J→K→L→M→X)
- "No real LLM calls in test suite" is a hard requirement — all tests must pass with RunnerFake only

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 01-runner-interface-test-foundation*
*Context gathered: 2026-02-16*
