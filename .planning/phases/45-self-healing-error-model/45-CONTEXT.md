# Phase 45: Self-Healing Error Model - Context

**Gathered:** 2026-03-01
**Status:** Ready for planning

<domain>
## Phase Boundary

The agent retries failed operations 3 times with meaningfully different approaches per unique error signature before escalating to the founder via the existing DecisionConsole pattern. Retry state persists across sleep/wake cycles. This phase covers backend retry logic, error classification, escalation payload construction, and persistence — NOT the founder-facing UI (Phase 46).

</domain>

<decisions>
## Implementation Decisions

### Retry strategy
- Full replanning on retry — agent steps back and replans the entire current task from scratch, potentially choosing a different architectural approach
- Per error signature (error_type + message_hash), not per task — different errors during the same task each get their own 3 retries
- Agent narrates retry reasoning via narrate() — "That approach hit a dependency issue — I'm trying a different pattern"
- Full context injected on retry: original intent, what was tried, the error, and instruction to try a fundamentally different approach

### Error classification
- Three error categories:
  1. **Never-retry (immediate escalation):** Auth failures, permission denied, missing credentials, rate limit exceeded, invalid subscription
  2. **Code errors (full replanning retries):** Syntax errors, type errors, logic errors, compilation failures — agent gets 3 attempts with different approaches
  3. **Environment errors (wait-and-retry or escalate):** Network timeouts, disk full, package registry down — distinct handling from code errors
- Anthropic API errors (rate limit, overloaded, context too long) handled transparently with exponential backoff — do NOT count against the 3 error-signature retries
- Global failure threshold: if N total escalation-worthy failures accumulate in one build session, pause the build and notify the founder (prevents death-by-a-thousand-cuts)

### Escalation experience
- Multiple choice options presented to founder: 2-3 concrete choices like "A) Skip this feature, B) Try a simpler version, C) Give me specific guidance"
- Plain English only — no code, no jargon, no stack traces. Non-technical founder audience
- While waiting for founder decision, agent continues other work (skips blocked task, picks up unblocked tasks). When founder responds, agent returns to blocked task
- In-app notification only (dashboard agent state card + activity feed). Email/push is post-v0.7 (NOTIF-01)

### Error memory & expiry
- Error signatures persist for entire build session — if agent failed 3 times Monday, still remembers Tuesday after wake. Only clears on new build
- Exception: rebuilds of the same project inherit error history from previous builds. Different projects start fresh
- Founder input resets retry count — founder's guidance is new information, agent gets 3 fresh attempts with the founder's direction
- Founder sees escalations only — recovered errors are invisible. Clean, non-technical experience

### Claude's Discretion
- Exact error signature hashing algorithm
- Global failure threshold number (N)
- How to structure the replanning prompt injection
- PostgreSQL schema for error signature storage
- Exponential backoff timing for API errors

</decisions>

<specifics>
## Specific Ideas

- The escalation should feel like a team member asking for help, not a crash report — "I tried 3 ways to set up the payment system but kept hitting a configuration issue"
- The agent should be able to work around blocked tasks and come back later — like a real developer who parks a problem and works on something else

</specifics>

<deferred>
## Deferred Ideas

- Email/push notification when agent escalates — NOTIF-01 (post-v0.7)
- "Problems" dashboard view showing all errors (recovered + escalated) — potential future UX feature

</deferred>

---

*Phase: 45-self-healing-error-model*
*Context gathered: 2026-03-01*
