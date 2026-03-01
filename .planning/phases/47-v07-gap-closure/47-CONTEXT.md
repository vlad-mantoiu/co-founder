# Phase 47: v0.7 Gap Closure — REST Bootstrap + Escalation SSE - Context

**Gathered:** 2026-03-01
**Status:** Ready for planning

<domain>
## Phase Boundary

Close the 3 integration gaps identified by the v0.7 milestone audit. All fixes are surgical — exact files, exact keys, exact approaches are specified by the audit. No new capabilities, no UI changes, no architectural decisions.

Gaps:
1. `budget_pct` Redis key never written → REST bootstrap returns null
2. `wake_at` Redis key never written → countdown timer broken on reload
3. `agent.escalation_resolved` SSE event never emitted → multi-session visibility broken

</domain>

<decisions>
## Implementation Decisions

### Redis key: budget_pct
- Write `cofounder:agent:{session_id}:budget_pct` after each `record_call_cost()` call in `runner_autonomous.py`
- Value: integer 0-100 representing percentage of daily budget consumed
- TTL: 90 seconds (matches SSE heartbeat window — stale data auto-expires)
- `GET /api/jobs/{id}/status` already reads this key — no API changes needed

### Redis key: wake_at
- Write `cofounder:agent:{session_id}:wake_at` on sleep transition in `runner_autonomous.py`
- Value: ISO 8601 UTC timestamp of next budget refresh (next midnight UTC or subscription reset)
- TTL: match sleep duration (key expires when agent wakes)
- `AgentStateBadge` countdown timer already reads this key — no frontend changes needed

### SSE event: agent.escalation_resolved
- Emit via `state_machine.publish_event()` after `session.commit()` in `resolve_escalation()` endpoint
- Event type: `AGENT_ESCALATION_RESOLVED` (constant already exists in SSE event types)
- Payload: escalation_id, resolution text, resolved_at timestamp
- Frontend handler already exists — no frontend changes needed

### Claude's Discretion
- Exact TTL values (90s suggested but Claude can adjust based on codebase patterns)
- Test structure and mocking approach
- Whether to combine Redis writes into a helper or keep inline

</decisions>

<specifics>
## Specific Ideas

All three fixes are specified by the v0.7 milestone audit (`.planning/v0.7-MILESTONE-AUDIT.md`). The audit includes exact file locations, exact key names, and recommended implementation approaches.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 47-v07-gap-closure*
*Context gathered: 2026-03-01*
