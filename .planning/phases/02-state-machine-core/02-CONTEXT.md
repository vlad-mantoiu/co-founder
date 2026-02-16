# Phase 2: State Machine Core - Context

**Gathered:** 2026-02-16
**Status:** Ready for planning

<domain>
## Phase Boundary

Five-stage startup journey FSM with transition logic, decision gate enforcement, deterministic progress computation, and observability. This phase builds the core state machine engine — no UI, no API endpoints, no frontend. Dashboard integration is Phase 7.

</domain>

<decisions>
## Implementation Decisions

### Stage Definitions
- Projects start in a **pre-stage state** (no stage assigned) — they exist but haven't entered the journey
- Entry into Stage 1 (Thesis Defined) happens **after the first decision gate is passed** (founder chooses Proceed)
- Stage 5 (Scale & Optimize) is **visible but locked** — exists in the model so founders see the full path, marked as "Coming Soon" / inaccessible in MVP
- Exit criteria use a **template + dynamic** model: base template of required criteria per stage, plus optional criteria generated from the project's specifics

### Transition Rules
- **Backward transitions allowed** — a Pivot can send a project back to an earlier stage (e.g., Pivot from Stage 3 → Stage 1)
- **Parked** projects move to a **special "Parked" status** separate from the 5 stages — effectively shelved, can be resumed later
- **Multiple decision gates can coexist** — a project can have more than one pending gate at a time (e.g., direction gate + build path gate)
- **Narrowing re-validates exit criteria** — when a founder chooses "Narrow", some exit criteria may reset since the brief changed, and progress may decrease

### Progress Computation
- **Both per-stage and global progress** — each stage has its own 0-100%, plus an overall journey percentage
- Progress is based on **weighted milestones** per stage (e.g., "brief generated" = 30%, "gate passed" = 20%, "build ready" = 50%)
- Milestone weights are **configurable per project** — can be adjusted based on project type or complexity
- **Progress can decrease** — if a pivot invalidates artifacts, progress drops to reflect reality

### Risk & Focus Signals
- Blocking risks use **both system-defined rules AND LLM-assessed risks** — system rules catch obvious blockers (no decision in 7 days, build failed 3x, stale project), LLM adds nuanced assessment (scope too broad for MVP)
- Suggested focus is **context-aware** — LLM considers project state, risks, and time to suggest the highest-impact next action
- Risk flags are **dismissible** — founder can acknowledge and dismiss, won't show again unless conditions worsen

### Claude's Discretion
- Event storage approach for correlation_id observability (separate timeline table vs JSONB event log)
- Exact FSM library choice (transitions, custom, etc.)
- Internal data model for milestone weights
- How to compute global progress from per-stage progress (equal stage weight vs weighted by complexity)

</decisions>

<specifics>
## Specific Ideas

- The pre-stage → Stage 1 transition only fires after the founder explicitly chooses "Proceed" at Decision Gate 1 — no automatic promotions
- Park is a first-class status, not a hack on top of the stage model — parked projects should be easy to find and resume
- Progress decreasing on pivot is important for honesty — the dashboard should never lie about where a project actually stands

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 02-state-machine-core*
*Context gathered: 2026-02-16*
