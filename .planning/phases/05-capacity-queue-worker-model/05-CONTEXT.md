# Phase 5: Capacity Queue & Worker Model - Context

**Gathered:** 2026-02-17
**Status:** Ready for planning

<domain>
## Phase Boundary

Queue-based throughput limiting with tier enforcement preventing cost explosion. Users submit jobs that enter a priority queue backed by Redis. Work slows down but never halts — the system always accepts jobs, queuing or scheduling them when limits are reached. This phase covers job submission, queue management, concurrency control, wait time feedback, iteration depth control, and usage counters.

</domain>

<decisions>
## Implementation Decisions

### Tier Capacity Numbers
- Concurrent jobs per user: Bootstrapper: 2, Partner: 3, CTO: 10
- Daily job limits: Bootstrapper: 5/day, Partner: 50/day, CTO: 200/day
- Per-project concurrency: Bootstrapper: 2, Partner: 3, CTO: 5 (tier-scaled, not uniform)
- When daily limit hit: accept the job but schedule for next reset window ("Scheduled for tomorrow") — never block

### Queue Priority & Fairness
- FIFO with boost: first-come-first-served base, higher tiers jump ahead by N positions
- Boost values: CTO +5 positions, Partner +2 positions, Bootstrapper +0 (base FIFO)
- Global queue cap: 100 queued jobs. Beyond 100, reject with "system busy, try again in N minutes"
- Per-project concurrency is tier-scaled (see above), not the uniform max-3 from original requirements

### Wait Time Feedback
- Show queue position to user: "You are #4 in queue"
- Include upgrade CTA for lower tiers: "Upgrade to jump ahead" nudge alongside position
- Job statuses shown as detailed pipeline: queued → starting → scaffold → code → deps → checks → ready/failed
- Error display: friendly summary by default + expandable sanitized detail section, always include debug_id

### Iteration Depth Control
- Iteration = one full build cycle (generate → test → fix). Internal agent runs don't count separately
- Auto-iteration depth is tier-based: Bootstrapper: 2, Partner: 3, CTO: 5 cycles before confirmation
- After confirmation: grants another tier-based batch (not unlimited). Check-in repeats each batch
- Each usage counter response includes: jobs_used, jobs_remaining, iterations_used, iterations_remaining

### Claude's Discretion
- Real-time update transport (polling, SSE, WebSocket) — pick based on existing FastAPI + Redis infrastructure
- Confirmation flow UX (modal vs banner vs inline) — pick what fits the dashboard
- Queue position update frequency
- Daily limit reset time (midnight UTC or rolling 24h)
- Redis data structures for queue implementation

</decisions>

<specifics>
## Specific Ideas

- "Work slows down, never halts" — this is the core philosophy. Even at daily limit, jobs get scheduled for tomorrow
- Queue position display with upgrade CTA is a monetization touchpoint — make it feel helpful, not pushy
- Detailed pipeline statuses (scaffold → code → deps → checks) give founders transparency into what their AI co-founder is doing

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 05-capacity-queue-worker-model*
*Context gathered: 2026-02-17*
