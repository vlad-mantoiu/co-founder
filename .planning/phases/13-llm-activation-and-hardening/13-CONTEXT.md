# Phase 13: LLM Activation and Hardening - Context

**Gathered:** 2026-02-18
**Status:** Ready for planning

<domain>
## Phase Boundary

Wire RunnerReal to real Claude calls so founders receive dynamically generated interviews, briefs, and artifacts instead of fake inventory-tracker stubs. Replace MemorySaver with AsyncPostgresSaver. Fix silent failures (JSON parsing, UsageTrackingCallback, detect_llm_risks). Add retry logic for Claude overload. Implement tier-differentiated LLM behavior.

</domain>

<decisions>
## Implementation Decisions

### Co-founder Voice & Tone
- Professional partner tone — senior co-founder energy, direct and concise but warm. "We should consider..." / "The risk here is..."
- Mixed "we" usage — "we" for shared decisions, "your" for the founder's vision, "I'd suggest" for technical recommendations
- Supportive guide posture — validate first, then gently steer. "That's a solid instinct. One thing to consider..." Never confrontational
- Plain English reading level — no jargon, explain everything. A non-technical founder reads generated briefs and artifacts without Googling anything

### Tier Differentiation
- Interview depth varies by tier — bootstrapper gets 6-8 questions, higher tiers get more questions with deeper follow-ups
- Execution plan options: same count across tiers (2-3), but higher tiers get richer engineering impact analysis per option
- Brief structure: higher tiers unlock extra sections (competitive analysis, scalability notes, risk deep-dives) that lower tiers don't see
- Model selection: use existing create_tracked_llm() tier-to-model mapping as-is — don't override

### Failure Experience
- Claude 529 overload: silent retry for the founder. Just show normal loading state, no retry counters. Retries visible in server logs / network tab for debugging
- All retries exhausted: queue the request. "Added to queue — we'll continue automatically when capacity is available." Auto-retry later
- Malformed LLM output (bad JSON): retry once silently with a stricter prompt hint. If second attempt also fails, surface a generic error
- UsageTrackingCallback DB/Redis failures: log at WARNING level only. Founder never sees usage tracking errors — it's internal bookkeeping

### Interview Depth
- Bootstrapper baseline: 6-8 questions per interview
- Higher tiers: more questions with deeper follow-ups (scaling up from the 6-8 baseline)
- Answer edits: check relevance of remaining questions, drop irrelevant ones, may add 1-2 new ones based on the changed answer
- Confidence scoring (strong/moderate/needs_depth): appears in the final Idea Brief only, not during the interview
- Interview conclusion: "I have enough to build your brief. Want to add anything else before I do?" — offer founder agency before generating

### Claude's Discretion
- Exact question wording and ordering within the interview
- How to scale question count for partner and cto_scale tiers (above 6-8 baseline)
- Which extra brief sections to unlock per tier
- Loading state UI during silent retries
- Queue retry timing and backoff strategy

</decisions>

<specifics>
## Specific Ideas

- The AI should feel like a co-founder you'd meet at a coffee shop — smart, invested in your success, never condescending
- When offering to go deeper at interview end, the language should feel like an invitation, not a gate ("Want to add anything else?" not "Do you have sufficient information?")
- Queue-based failure recovery means the founder can close their browser and come back later — their work isn't lost

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 13-llm-activation-and-hardening*
*Context gathered: 2026-02-18*
