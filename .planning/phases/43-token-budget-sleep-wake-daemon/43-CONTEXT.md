# Phase 43: Token Budget + Sleep/Wake Daemon - Context

**Gathered:** 2026-02-26
**Status:** Ready for planning

<domain>
## Phase Boundary

The agent distributes work across the subscription window using a cost-weighted daily allowance, transitions to "sleeping" state when budget is consumed, wakes automatically on budget refresh, persists all session state to PostgreSQL so conversation history survives sleep/wake cycles, and hard circuit breakers prevent cost runaway. Tier-based model routing (Opus vs Sonnet) is included. Subscription management and billing UI are separate phases.

</domain>

<decisions>
## Implementation Decisions

### Budget allocation strategy
- Even daily split: remaining_budget / remaining_days — recalculated fresh each day at midnight UTC
- No rollover — unused daily budget is lost; next day recalculates from total remaining
- Cost weights are config-driven (not hardcoded): store model cost multipliers in a config dict/table (e.g., `{opus_output: 5x, opus_input: 1x, sonnet_output: 1x, sonnet_input: 0.2x}`) so pricing changes don't require code changes
- Budget refresh happens at 00:00 UTC daily — all users on the same clock

### Sleep/wake founder experience
- **Sleep notification:** Minimal — "Agent paused until budget refresh" in the activity feed. No cost details in the notification itself
- **Wake announcement:** Brief status message when agent resumes — "Resuming — budget refreshed. Continuing from [last task]." Gives founder confidence the wake succeeded
- **Graceful wind-down:** At 90% budget spent, agent finishes current task/commit but does not start new work. The 10% overage circuit breaker (BDGT-07) is the hard stop for race conditions
- **Immediate wake on top-up:** If founder upgrades subscription or manually tops up while agent is sleeping, detect the change, recalculate budget, and wake the agent immediately — no waiting for next midnight

### Session checkpoint scope
- Checkpoint after every TAOR loop iteration — if server crashes, at most one iteration of work is lost
- On wake: full verify of sandbox filesystem against last S3 snapshot before resuming
- If integrity check fails: auto-restore from S3, log the discrepancy, post brief note in activity feed, and continue — no manual founder action needed

### Cost visibility & alerts
- Session-level cost shown as **percentage of daily budget** (not dollar amounts) — e.g., "Budget: 47% used"
- **Budget meter:** Visual progress bar with color progression green → yellow → red as budget depletes
- No per-model cost breakdown — just total session cost percentage
- **budget_exceeded alert:** In-app red banner ("Agent stopped — daily budget exceeded") AND email notification, since founder may not be watching the dashboard

### Claude's Discretion
- Conversation history persistence depth (full history vs sliding window + summary) — pick what makes the agent most effective after wake
- Redis key structure for per-session cost tracking
- Exact checkpoint table schema beyond the required fields (message history, sandbox_id, current phase, retry counts)

</decisions>

<specifics>
## Specific Ideas

- Cost in the activity feed should feel lightweight — a percentage badge, not an accounting ledger
- Budget meter color thresholds: green (0-60%), yellow (60-90%), red (90-100%)
- The graceful wind-down at 90% creates a natural buffer zone where the agent wraps up cleanly before the hard 10% overage circuit breaker kicks in

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 43-token-budget-sleep-wake-daemon*
*Context gathered: 2026-02-26*
