# Pitfalls Research

**Domain:** AI-powered Technical Co-Founder SaaS (code generation, state machines, founder dashboards)
**Researched:** 2026-02-16
**Confidence:** HIGH

## Critical Pitfalls

### Pitfall 1: Silent Logic Failures in AI-Generated Code

**What goes wrong:**
AI-generated code runs without syntax errors but produces incorrect behavior. Recent research shows AI creates [1.7x more bugs than humans](https://www.coderabbit.ai/blog/state-of-ai-vs-human-code-generation-report), with the most dangerous category being logic errors that pass initial validation but fail under specific conditions. [IEEE reports](https://spectrum.ieee.org/ai-coding-degrades) that LLMs increasingly generate code that "seems to run successfully" by removing safety checks or creating fake output that matches desired format.

**Why it happens:**
LLMs optimize for pattern matching, not correctness. They generate plausible-looking code that compiles/runs but contains subtle logic flaws, especially in concurrency, error handling, and edge cases. Models reached a quality plateau in 2025 and [recent models show decline](https://futurism.com/artificial-intelligence/ai-code-bug-filled-mess).

**How to avoid:**
- **Execution validation:** Every code generation must include test execution in E2B sandbox with actual validation (not just "does it run")
- **Reviewer node skepticism:** Implement adversarial review that specifically checks for removed safety checks, missing error handling, and edge case coverage
- **Regression test suite:** Auto-generate tests for each feature before generating implementation (TDD protocol)
- **Debugging loop with concrete errors:** When Debugger node receives failures, require concrete error messages and stack traces (not hallucinated fixes)

**Warning signs:**
- Tests pass but user reports "it doesn't work as expected"
- Code has fewer lines than expected (possible safety check removal)
- Error handling blocks are missing or use bare `pass`
- Coder node completes unusually fast (<30s for complex features)

**Phase to address:**
- Phase 1 (Foundation): Implement test-first generation in Coder node
- Phase 2 (Execution): Strengthen Reviewer node with adversarial checks
- Phase 3 (Iteration): Add regression test persistence across builds

---

### Pitfall 2: LangGraph State Corruption Without Checkpointing

**What goes wrong:**
State machine executes for 5+ minutes across multiple nodes, then fails at Executor or Debugger node. Without checkpointing, entire execution history is lost. User must restart from scratch. [LangGraph production reviews](https://sider.ai/blog/ai-tools/langgraph-review-is-the-agentic-state-machine-worth-your-stack-in-2025) warn: "Failed agent executions can corrupt the shared state or disrupt workflows."

**Why it happens:**
LangGraph `StateGraph` execution keeps state in memory. On failure, timeout, or deployment, state vanishes unless explicitly checkpointed to persistent storage. Your codebase analysis shows "no LangGraph state checkpointing (state lost on failure)" in milestone context.

**How to avoid:**
- **Implement PostgreSQL checkpointing:** Use `langgraph-checkpoint-postgres` (already in dependencies) to persist state after each node
- **Node-level recovery:** On failure, reload last checkpoint and retry from failed node (not from beginning)
- **Timeout handling:** Set `graph.invoke(..., timeout=300)` and checkpoint before timeout expires
- **Session resurrection:** If user refreshes browser, reload state from checkpoint (not new session)
- **Checkpoint pruning:** Archive checkpoints older than 7 days to S3, keep recent in database

**Warning signs:**
- Users report "lost all progress" after errors
- Redis session exists but CoFounderState is empty
- Architect creates plan, then Coder re-creates identical plan (state reset symptom)
- Episodic memory shows duplicate goals (repeated executions)

**Phase to address:**
- Phase 1 (Foundation): Enable PostgreSQL checkpointing on LangGraph
- Phase 2 (Execution): Add checkpoint-based recovery in API routes
- Phase 3 (Iteration): Implement session resurrection UI ("Resume where you left off")

---

### Pitfall 3: LLM Cost Explosion from Dynamic Questioning

**What goes wrong:**
Dynamic LLM-tailored questions (Understanding Interview, Decision Gates) create unbounded prompt chains. Each question depends on previous answer, requiring full context. At 1000 users with 10 questions each daily, costs spiral: 1000 users × 10 questions × 2K tokens × $0.003 (Opus) = $60/day = $1800/month just for interviews. [Research shows](https://ai.koombea.com/blog/llm-cost-optimization) businesses can see costs spiral "with monthly bills that can quickly spiral out of control" without proper controls.

**Why it happens:**
Opus for questioning × cumulative context growth × no caching = exponential token usage. Each new question includes full conversation history. 5-question interview = 2K + 4K + 6K + 8K + 10K = 30K tokens (vs. static 5×2K = 10K tokens).

**How to avoid:**
- **Context windowing:** Send only last 3 exchanges to LLM, not full history
- **Prompt caching:** Use Anthropic's prompt caching for system instructions and conversation prefix (30K token cache = [15-30% cost reduction](https://ai.koombea.com/blog/llm-cost-optimization))
- **Question budget:** Limit Understanding Interview to 7 questions max per project (enforced in state machine)
- **Template-first strategy:** Use static templates for 70% of questions, dynamic only for ambiguous cases
- **Model downshift:** Use Sonnet for clarifying questions, Opus only for strategy synthesis
- **RAG compression:** Decision Gate context should be [70% smaller](https://ai.koombea.com/blog/llm-cost-optimization) via retrieval (not full document dumps)

**Warning signs:**
- UsageLog shows >50K tokens for single Understanding Interview
- Clarifying questions exceed 10 per project
- Users report slow response times (large context processing)
- Monthly LLM costs exceed $5/user

**Phase to address:**
- Phase 1 (Foundation): Implement question budget and context windowing
- Phase 2 (Execution): Add prompt caching for repeated system prompts
- Phase 3 (Iteration): Optimize with RAG compression for Decision Gates

---

### Pitfall 4: E2B Sandbox Cost at Scale (1000+ Users)

**What goes wrong:**
E2B charges per-second of running sandbox. At $0.05/hour (1 vCPU), 1000 concurrent builds × 5 minutes average = 83 hours = $4.15 per deployment wave. [E2B pricing](https://e2b.dev/pricing) shows Pro plan at $150/month includes limited usage, then per-second billing. At production scale with 1000+ users, [costs escalate fast](https://www.softwareseni.com/e2b-daytona-modal-and-sprites-dev-choosing-the-right-ai-agent-sandbox-platform).

**Why it happens:**
Current architecture creates new E2B sandbox per execution, runs tests, then terminates. No sandbox reuse. Debugging loops (Executor → Debugger → Executor × 5 retries) create 5× sandbox costs per build.

**How to avoid:**
- **Sandbox pooling:** Maintain warm pool of 10 sandboxes, reuse across executions (reset filesystem state)
- **Per-user sandbox persistence:** Pro/Enterprise tiers get long-lived sandboxes (24-hour sessions), restart only on failure
- **Lazy sandbox creation:** Don't provision sandbox until Coder produces code (not during Architect/interview phases)
- **Timeout enforcement:** Kill sandboxes after 10 minutes of execution (current code has no timeout)
- **Batch testing:** Run all test files in single sandbox session (not new sandbox per test)
- **Tier gating:** Bootstrapper tier gets shared sandbox pool (slower), Partner/CTO get dedicated (faster)

**Warning signs:**
- E2B bill exceeds $500/month with <100 active users
- Average sandbox lifetime >15 minutes
- Multiple sandboxes per project_id exist simultaneously
- Sandboxes persist after user logs out

**Phase to address:**
- Phase 1 (Foundation): Implement sandbox timeout and cleanup
- Phase 2 (Execution): Add sandbox pooling for Bootstrapper tier
- Phase 3 (Iteration): Implement per-user long-lived sandboxes for paid tiers

---

### Pitfall 5: Queue-Based Rate Limiting Without Fairness

**What goes wrong:**
Queue-based worker capacity model allows "noisy neighbor" problem: One user with 10 concurrent projects monopolizes queue, starving other users. [Research shows](https://www.gravitee.io/blog/rate-limiting-apis-scale-patterns-strategies) distributed counter inconsistency leads to "clients exceeding their intended limits as each service instance maintains its own partial view."

**Why it happens:**
Redis queue is FIFO without per-user fairness. Large projects (100+ files) create long-running jobs that block queue. No priority levels based on subscription tier.

**How to avoid:**
- **Per-user queue limits:** Max 3 concurrent jobs per user, queue additional requests
- **Fair queuing algorithm:** Round-robin across users (not strict FIFO)
- **Tier-based priority:** CTO tier jobs get priority over Bootstrapper
- **Job splitting:** Break large projects into 10-file chunks, interleave across users
- **Wait time estimation:** Calculate queue position × average job time, show "Estimated 3 minutes" in UI
- **Circuit breaker:** If user's job fails 3x, deprioritize future jobs (prevent retry storms)
- **Redis Lua atomicity:** Use [Lua scripts for atomic operations](https://redis.io/learn/howtos/ratelimiting) on queue management (current code has race conditions)

**Warning signs:**
- One user has >5 jobs in queue while others wait
- Average wait time >5 minutes for simple requests
- Redis queue depth >50 items
- Users report "stuck in queue" despite low system load

**Phase to address:**
- Phase 1 (Foundation): Implement per-user queue limits and fair queuing
- Phase 2 (Execution): Add tier-based priority and wait time estimation
- Phase 3 (Iteration): Implement job splitting for large projects

---

### Pitfall 6: Non-Technical User Overwhelm (Dashboard UX Failure)

**What goes wrong:**
Founders abandon product because dashboard is too complex. [Builder.ai's $1.5B failure](https://medium.com/@tahirbalarabe2/the-truth-behind-builder-ais-1-5b-failure-77817464897e) showed "users found the process frustrating, with one bakery owner giving up after spending weeks trying to get a simple ordering app to work." [MIT research](https://www.mindtheproduct.com/why-most-ai-products-fail-key-findings-from-mits-2025-ai-report/) found "85% of AI projects fail to deliver real business outcomes" largely due to UX that doesn't match user mental models.

**Why it happens:**
Technical terminology ("nodes", "state machine", "deployment pipeline") alienates non-technical founders. Too many options paralyze decision-making. No clear "what do I do next?" guidance. [Dashboard UX research](https://www.smashingmagazine.com/2025/09/ux-strategies-real-time-dashboards/) emphasizes: "dashboards should connect metrics with actions" and avoid "overwhelming users with too much information."

**How to avoid:**
- **Inverted pyramid:** Most critical info at top (stage, completion %, next action), drill-down below
- **Action-oriented language:** "Review build" not "Execute reviewer node"; "Make pricing decision" not "Configure monetization strategy"
- **Chatbot-first fallback:** [Emerging trend](https://medium.com/@CarlosSmith24/admin-dashboard-ui-ux-best-practices-for-2025-8bdc6090c57d) for "natural language questions, lowering entry barrier"
- **Progress storytelling:** "3 of 5 milestones complete" not "60% through Validated Direction stage"
- **Decision templates with tradeoffs:** Present 2-3 options with "Fast/Expensive" vs "Slow/Cheap" labels (not raw engineering details)
- **Glossary tooltips:** Hover on "Build v0.2" shows "Second iteration of your MVP with new features"
- **Empty state guidance:** First login shows checklist: "1. Answer questions about your idea 2. Review strategy 3. Approve build plan"

**Warning signs:**
- Session duration <2 minutes (user confused, leaves)
- Users ask support "what do I click next?"
- High bounce rate on Dashboard page
- Low Decision Gate completion rate (users stuck at decisions)

**Phase to address:**
- Phase 1 (Foundation): Implement inverted pyramid dashboard with action-first language
- Phase 2 (Execution): Add decision templates with tradeoffs UI
- Phase 3 (Iteration): Implement chatbot fallback for confused users

---

### Pitfall 7: Neo4j Strategy Graph Query Performance Degradation

**What goes wrong:**
Strategy Graph grows to 500+ decision nodes per project (Understanding Interview + Execution Plan + Decision Gates + iterations). Cypher queries for "show all decisions impacting pricing" become slow (>5s). [Production tuning guides](https://medium.com/@satanialish/the-production-ready-neo4j-guide-performance-tuning-and-best-practices-15b78a5fe229) warn about query performance at scale without proper indexing.

**Why it happens:**
No indexes on node properties. Full graph scans for label-based queries. Relationship traversals without depth limits. Current code creates nodes but doesn't define indexes or constraints for lookup patterns.

**How to avoid:**
- **Define indexes at initialization:** `CREATE INDEX decision_by_project IF NOT EXISTS FOR (d:Decision) ON (d.project_id, d.timestamp)`
- **Constrain traversal depth:** `MATCH (d:Decision)-[:IMPACTS*1..3]->(m:Milestone)` (not unbounded `*`)
- **Property-based filtering:** Filter on indexed properties before traversal, not after
- **Parameterized queries:** Use `$project_id` parameters (enables query plan caching)
- **Graph projections:** For dashboard queries, use Neo4j Graph Data Science projections (in-memory subgraphs)
- **Query profiling:** `PROFILE MATCH ...` to identify full scans, add indexes accordingly
- **Lazy loading:** Dashboard shows top 5 decisions, "Load more" for full graph

**Warning signs:**
- Cypher query logs show >1000ms execution times
- Dashboard "Strategy Graph" section takes >3s to load
- Neo4j CPU usage >80% during graph queries
- Graph visualization times out with >100 nodes

**Phase to address:**
- Phase 1 (Foundation): Define indexes and constraints during Neo4j initialization
- Phase 2 (Execution): Implement depth-limited traversals in graph queries
- Phase 3 (Iteration): Add lazy loading and graph projections for large graphs

---

### Pitfall 8: Async/Await Blocking in Production (Existing Codebase Issue)

**What goes wrong:**
Mem0 semantic memory uses synchronous API calls inside `async` functions without proper wrapping. [FastAPI async pitfalls research](https://medium.com/@bhagyarana80/10-async-pitfalls-in-fastapi-and-how-to-avoid-them-60d6c67ea48f) shows "blocking calls in async endpoints can block the event loop, causing performance degradation or timeout errors." Your CONCERNS.md already flagged this: "Mem0 Semantic Memory Missing Async Handling" — methods never actually await Mem0 calls.

**Why it happens:**
Mem0 library is synchronous, but methods are marked `async` for compatibility with FastAPI. Calling `self.client.search(...)` blocks the event loop. At scale, this causes [event loop saturation](https://fastro.ai/blog/fastapi-mistakes).

**How to avoid:**
- **Immediate fix:** Wrap Mem0 calls with `await asyncio.to_thread(self.client.search, ...)`
- **Long-term:** Evaluate async alternatives (LangChain memory, native PostgreSQL RAG) or fork Mem0 with async client
- **Connection pooling:** Configure Mem0 with connection pool to reduce blocking time
- **Circuit breaker:** If Mem0 search takes >2s, skip memory context (graceful degradation)
- **Remove if unused:** Audit if semantic memory actually improves results — if not, remove dependency

**Warning signs:**
- Uvicorn logs show "event loop blocked for >0.5s"
- API latency spikes during memory-heavy operations
- Concurrent requests drop (event loop saturated)
- Thread pool exhaustion errors

**Phase to address:**
- Phase 1 (Foundation): Wrap Mem0 calls with `asyncio.to_thread()` immediately
- Phase 2 (Execution): Evaluate async memory alternatives
- Phase 3 (Iteration): Implement circuit breaker for memory operations

---

## Technical Debt Patterns

Shortcuts that seem reasonable but create long-term problems.

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Silent exception swallowing (`except: pass`) | "Works" in happy path | Debugging production failures impossible; silent data loss | **Never** — always log at minimum |
| `datetime.utcnow()` (deprecated in 3.12) | Simple syntax | Naive datetimes cause lock timeout bugs during DST; multi-region failures | **Never** — use `datetime.now(timezone.utc)` |
| No distributed lock ownership validation | Simpler Redis logic | Two users edit same file simultaneously; data corruption | **Never** — implement UUID-based lock tokens |
| Full state in Redis (no compression) | Easy serialization | Redis memory exhaustion at 1000+ sessions; slow deserializes | **MVP only** — compress or move to Postgres |
| Hard-coded model strings (not Enums) | Quick prototyping | Typos cause wrong model usage; no autocomplete | **Never** — use ModelRole enum from start |
| Readiness probe that doesn't check DB | Faster startup | Load balancer routes to unhealthy instances; cascading failures | **Never** — always validate dependencies |
| Static question forms (not dynamic LLM) | Cheaper, faster | Misses context-specific questions; poor requirement extraction | **Acceptable for MVP** if budget-constrained |
| Global admin flag (not RBAC) | Simple auth | Can't delegate permissions; all-or-nothing access | **Acceptable for MVP** — add RBAC in Phase 3+ |

---

## Integration Gotchas

Common mistakes when connecting to external services.

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| **Anthropic Claude** | Not handling rate limits (429) | Implement exponential backoff; cache responses; use tier limits to prevent bursts |
| **E2B Sandbox** | Creating new sandbox per request | Maintain warm pool; reuse sandboxes with filesystem reset |
| **Neo4j** | Not using parameterized queries | Always use `$param` syntax; prevents injection and enables query plan caching |
| **Redis** | Non-atomic check-then-set | Use Lua scripts or `WATCH`/`MULTI`/`EXEC` for atomicity |
| **Clerk** | Caching JWT validation results too long | Refresh JWKS every 1 hour; validate on every request (fast with key caching) |
| **GitHub API** | No handling for PR create failures | Check for existing PR before create; handle branch conflicts; retry with backoff |
| **Mem0** | Assuming search is instant | Add timeout; implement fallback to episodic memory if Mem0 fails |
| **Stripe Webhooks** | Not verifying signature | Always verify `stripe.Webhook.construct_event()`; prevents forged webhooks |

---

## Performance Traps

Patterns that work at small scale but fail as usage grows.

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| **Semantic memory on every message** | >500ms latency per chat message | Cache memory context for 5 minutes; refresh in background | >10 concurrent users |
| **Full state serialization to Redis** | Redis memory growth, slow writes | Store only session metadata in Redis, full state in Postgres | >100 active sessions |
| **Linear lock scanning (`SCAN cofounder:lock:*`)** | Lock queries take >1s | Use sorted sets indexed by project_id; O(log N) lookup | >1000 locks per project |
| **N+1 UserSettings queries** | DB connection pool exhaustion | Cache UserSettings with 1-hour TTL in Redis; eager load with JOIN | >50 concurrent users |
| **No LangGraph timeout** | Runaway agents consume resources indefinitely | Set `timeout=300` on graph invoke; checkpoint before timeout | First infinite loop bug |
| **Unbounded graph traversal in Neo4j** | Graph queries timeout | Always set max depth (`-[*1..3]->`) and result limits (`LIMIT 100`) | >500 nodes in graph |
| **Creating E2B sandbox during Architect phase** | Unnecessary sandbox costs | Lazy create: provision sandbox only when Coder produces code | >100 builds/day |

---

## Security Mistakes

Domain-specific security issues beyond general web security.

| Mistake | Risk | Prevention |
|---------|------|------------|
| **Storing API keys in CoFounderState** | Keys logged to episodic memory, visible in dashboard | Store secrets in AWS Secrets Manager; inject at runtime only |
| **No sandbox path validation** | User-provided paths escape sandbox root | Validate all paths with `os.path.abspath()` and check prefix |
| **Admin flag in JWT public metadata** | User can modify Clerk metadata via API | Verify admin status server-side against database, not just JWT |
| **GitHub App private key in environment** | Key exposed in logs, error traces | Use AWS Secrets Manager rotation; never log key material |
| **No rate limiting on Understanding Interview** | Attacker exhausts LLM quota with bogus questions | Enforce 1 interview per project; 3 projects per user per day |
| **Executing user-provided code without limits** | Fork bombs, infinite loops, resource exhaustion | E2B enforces limits; add timeout, memory cap, CPU cap per execution |
| **Allowing arbitrary Neo4j Cypher** | Cypher injection if user input in query | Use parameterized queries; whitelist allowed node labels and properties |

---

## UX Pitfalls

Common user experience mistakes in this domain.

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| **"Building..." with no progress** | User assumes it's frozen, refreshes (loses state) | Show estimated time ("~3 minutes"), progress steps ("2 of 5 tests passing") |
| **Technical error messages** | "StateGraph execution failed at node coder" confuses non-technical founders | "We couldn't generate code for this feature. Our team has been notified." |
| **No "why" for decisions** | Founder doesn't trust AI choices, manually overrides everything | Decision Cards show 2-3 options with tradeoffs ("Fast but expensive" vs "Slow but cheap") |
| **Chat-only interface** | Founders think in roadmaps, not conversations | Dashboard-first UX with chat as secondary fallback |
| **Artifacts buried in JSON** | Can't share Product Brief with investors | PDF export with branding; Markdown for technical stakeholders |
| **No abort/pause** | User wants to stop long-running build, can't | "Pause build" button checkpoints state, allows resume |
| **Version confusion** | "Which build am I looking at? v0.1 or v0.2?" | Version badge everywhere; timeline shows all versions with dates |
| **Hidden costs** | Founder surprised by $500 bill, churns | Usage dashboard shows tokens used, cost estimate, tier limits in real-time |

---

## "Looks Done But Isn't" Checklist

Things that appear complete but are missing critical pieces.

- [ ] **State machine transitions:** Verified all edge conditions trigger correct transitions (not just happy path)
- [ ] **Decision Gates:** Tested "Pivot" and "Park" paths (not just "Proceed")
- [ ] **Artifact generation:** PDFs render correctly with all content (not truncated), Markdown escapes special chars
- [ ] **Live preview URLs:** E2B sandbox URL is accessible from browser (not just localhost references)
- [ ] **Queue fairness:** Verified round-robin across users (not FIFO monopolization)
- [ ] **Error recovery:** Tested all failure modes checkpoint state (not just success path)
- [ ] **Async operations:** Profiled event loop blocking (all blocking calls wrapped with `asyncio.to_thread()`)
- [ ] **Rate limits:** Verified tier limits enforced per user per day (not global counters)
- [ ] **Strategy Graph indexes:** Ran `PROFILE` on all Cypher queries (no full scans)
- [ ] **Timezone handling:** All datetimes use `timezone.utc` (no naive datetimes in database)
- [ ] **Lock ownership:** Tested concurrent lock acquisition (UUID validation prevents conflicts)
- [ ] **Cost tracking:** UsageLog records tokens for all LLM calls (not just chat endpoints)
- [ ] **Sandbox cleanup:** Verified sandboxes terminate on timeout (no orphaned sandboxes)
- [ ] **Health checks:** Readiness probe returns 503 when DB/Redis down (not always 200)

---

## Recovery Strategies

When pitfalls occur despite prevention, how to recover.

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| **State corruption from no checkpointing** | HIGH | 1. Enable PostgreSQL checkpointing 2. Notify affected users 3. Provide "Resume" UI |
| **LLM cost explosion** | MEDIUM | 1. Implement emergency circuit breaker (disable Opus) 2. Add prompt caching 3. Refund overcharged users |
| **E2B sandbox cost spiral** | MEDIUM | 1. Kill all running sandboxes 2. Implement timeout enforcement 3. Add budget alerts |
| **Queue monopolization** | LOW | 1. Flush queue 2. Implement per-user limits 3. Restart with fair queuing |
| **Neo4j query slowdown** | LOW | 1. Add missing indexes via `CREATE INDEX` 2. Add `LIMIT` to slow queries 3. Monitor query performance |
| **Event loop saturation** | HIGH | 1. Identify blocking calls via profiling 2. Wrap with `asyncio.to_thread()` 3. Add event loop monitoring |
| **Silent logic failures in generated code** | HIGH | 1. Implement test-first generation 2. Strengthen Reviewer node 3. Notify users of past failures |
| **Dashboard confusion (user churn)** | MEDIUM | 1. Add onboarding checklist 2. Simplify language 3. User research sessions |

---

## Pitfall-to-Phase Mapping

How roadmap phases should address these pitfalls.

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Silent logic failures in AI code | Phase 2 (Execution) | Run test suite on all generated code; adversarial review enabled |
| No LangGraph checkpointing | Phase 1 (Foundation) | Session recovery works after simulated failure |
| LLM cost explosion | Phase 1 (Foundation) | UsageLog shows <30K tokens per Understanding Interview |
| E2B sandbox cost spiral | Phase 1 (Foundation) | Max sandbox lifetime <10 minutes; pool reuse confirmed |
| Queue fairness issues | Phase 2 (Execution) | Load test: 10 users with equal job completion times |
| Dashboard UX overwhelm | Phase 1 (Foundation) | User testing: non-technical founder completes flow in <5 minutes |
| Neo4j query performance | Phase 1 (Foundation) | All graph queries <500ms with 500-node test graph |
| Async/await blocking | Phase 1 (Foundation) | Event loop never blocked >100ms under load |
| Datetime timezone bugs | Phase 1 (Foundation) | All timestamps in DB have timezone info |
| Lock race conditions | Phase 1 (Foundation) | Concurrency test: 100 simultaneous lock attempts, no duplicates |
| Health check inadequacy | Phase 1 (Foundation) | Kill DB container, readiness returns 503 |
| Session serialization failures | Phase 1 (Foundation) | All state types JSON round-trip without errors |
| Exception swallowing | Phase 1 (Foundation) | No bare `except: pass` in codebase, all errors logged |
| Missing usage tracking | Phase 2 (Execution) | Every LLM call logged to UsageLog |
| Artifact export failures | Phase 2 (Execution) | PDF renders correctly with multi-page content |

---

## Sources

**AI Code Generation Quality:**
- [AI Code Is a Bug-Filled Mess - Futurism](https://futurism.com/artificial-intelligence/ai-code-bug-filled-mess)
- [AI vs Human Code Gen Report - CodeRabbit](https://www.coderabbit.ai/blog/state-of-ai-vs-human-code-generation-report)
- [AI Coding Degrades: Silent Failures - IEEE Spectrum](https://spectrum.ieee.org/ai-coding-degrades)
- [Are Bugs Inevitable with AI Coding Agents? - Stack Overflow](https://stackoverflow.blog/2026/01/28/are-bugs-and-incidents-inevitable-with-ai-coding-agents)

**LangGraph Production Issues:**
- [LangGraph Review: Worth Your Stack in 2025? - Sider.ai](https://sider.ai/blog/ai-tools/langgraph-review-is-the-agentic-state-machine-worth-your-stack-in-2025)
- [LangGraph 2025 Review: State-Machine Agents - NeurlCreators](https://neurlcreators.substack.com/p/langgraph-agent-state-machine-review)
- [Mastering LangGraph State Management 2025 - Sparkco](https://sparkco.ai/blog/mastering-langgraph-state-management-in-2025)

**Rate Limiting at Scale:**
- [Rate Limiting at Scale - Gravitee](https://www.gravitee.io/blog/rate-limiting-apis-scale-patterns-strategies)
- [Not All at Once! Redis Semaphores - Wolk](https://www.wolk.work/blog/posts/not-all-at-once-user-friendly-rate-limiting-with-redis-semaphores)
- [How to Implement Rate Limiting with Redis - OneUptime](https://oneuptime.com/blog/post/2026-01-21-redis-rate-limiting/view)

**LLM Cost Optimization:**
- [LLM Cost Optimization Guide - Koombea](https://ai.koombea.com/blog/llm-cost-optimization)
- [LLM Cost Optimization 2025 - FutureAGI](https://futureagi.com/blogs/llm-cost-optimization-2025)

**E2B Sandbox Scaling:**
- [E2B Pricing](https://e2b.dev/pricing)
- [Choosing the Right AI Agent Sandbox Platform - SoftwareSeni](https://www.softwareseni.com/e2b-daytona-modal-and-sprites-dev-choosing-the-right-ai-agent-sandbox-platform/)
- [E2B Review 2026 - AI Agents List](https://aiagentslist.com/agents/e2b)

**AI Builder UX Failures:**
- [Builder.ai's $1.5B Failure - Medium](https://medium.com/@tahirbalarabe2/the-truth-behind-builder-ais-1-5b-failure-77817464897e)
- [Why Most AI Products Fail - Mind the Product](https://www.mindtheproduct.com/why-most-ai-products-fail-key-findings-from-mits-2025-ai-report/)
- [Why AI Agent Pilots Fail - Composio](https://composio.dev/blog/why-ai-agent-pilots-fail-2026-integration-roadmap)

**Dashboard UX Best Practices:**
- [From Data to Decisions: UX for Real-Time Dashboards - Smashing Magazine](https://www.smashingmagazine.com/2025/09/ux-strategies-real-time-dashboards/)
- [20 Principles Modern Dashboard UI/UX 2025 - Medium](https://medium.com/@allclonescript/20-best-dashboard-ui-ux-design-principles-you-need-in-2025-30b661f2f795)
- [Admin Dashboard UI/UX Best Practices 2025 - Medium](https://medium.com/@CarlosSmith24/admin-dashboard-ui-ux-best-practices-for-2025-8bdc6090c57d)

**Neo4j Scaling:**
- [Production-Ready Neo4j Guide - Medium](https://medium.com/@satanialish/the-production-ready-neo4j-guide-performance-tuning-and-best-practices-15b78a5fe229)
- [Neo4j Infinigraph Architecture - BigDataWire](https://www.bigdatawire.com/2025/09/05/neo4j-cranks-up-the-scaling-factor-with-new-infinigraph-architecture/)
- [Neo4j Performance Tuning - Graphable](https://graphable.ai/blog/neo4j-performance/)

**FastAPI Async Pitfalls:**
- [10 Async Pitfalls in FastAPI - Medium](https://medium.com/@bhagyarana80/10-async-pitfalls-in-fastapi-and-how-to-avoid-them-60d6c67ea48f)
- [FastAPI Mistakes That Kill Performance - FastroAI](https://fastro.ai/blog/fastapi-mistakes)
- [Async APIs with FastAPI: Patterns & Pitfalls - Medium](https://shiladityamajumder.medium.com/async-apis-with-fastapi-patterns-pitfalls-best-practices-2d72b2b66f25)

**Distributed Systems Antipatterns:**
- [Common Antipatterns in Distributed Systems - GeeksforGeeks](https://www.geeksforgeeks.org/system-design/common-antipatterns-in-distributed-systems/)
- [Distributed Systems Antipatterns - Thoughtworks](https://www.thoughtworks.com/insights/podcasts/technology-podcasts/distributed-systems-antipattern)

---

*Pitfalls research for: AI-powered Technical Co-Founder SaaS*
*Researched: 2026-02-16*
