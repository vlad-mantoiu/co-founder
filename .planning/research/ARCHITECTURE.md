# Architecture Research

**Domain:** AI-powered Technical Co-Founder SaaS (Brownfield Migration)
**Researched:** 2026-02-16
**Confidence:** HIGH

## Standard Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          FRONTEND LAYER                                  │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐            │
│  │   Dashboard    │  │ Strategy Graph │  │  Artifacts     │            │
│  │   (PM View)    │  │   (Neo4j)      │  │  (Versioned)   │            │
│  └───────┬────────┘  └───────┬────────┘  └───────┬────────┘            │
│          │                    │                    │                     │
├──────────┴────────────────────┴────────────────────┴─────────────────────┤
│                          API GATEWAY LAYER                               │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐            │
│  │ State Machine  │  │    Artifact    │  │     Runner     │            │
│  │   API (NEW)    │  │   API (NEW)    │  │   API (NEW)    │            │
│  └───────┬────────┘  └───────┬────────┘  └───────┬────────┘            │
│          │                    │                    │                     │
├──────────┴────────────────────┴────────────────────┴─────────────────────┤
│                       ORCHESTRATION LAYER                                │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                  State Machine Controller                        │    │
│  │  (5 stages: Thesis → Validated → MVP → Feedback → Scale)        │    │
│  └────────────────────┬─────────────────────────────────────────────┘   │
│                       │                                                  │
│          ┌────────────┴────────────┐                                     │
│          ▼                         ▼                                     │
│  ┌──────────────┐         ┌──────────────┐                              │
│  │ Runner Layer │         │  Artifact    │                              │
│  │ (Interface)  │         │  Generator   │                              │
│  └──────┬───────┘         └──────┬───────┘                              │
│         │                        │                                       │
│    ┌────┴────┐              ┌────┴────┐                                 │
│    ▼         ▼              ▼         ▼                                 │
│  RunnerReal  RunnerFake   Versioning  Neo4j                             │
│  (LangGraph)  (Tests)     System      Strategy                          │
│         │                              Graph                             │
│         ▼                                                                │
├─────────┴────────────────────────────────────────────────────────────────┤
│                       EXISTING AGENT LAYER                               │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │        LangGraph Pipeline (6 nodes, preserved as-is)             │   │
│  │  Architect → Coder → Executor → Debugger → Reviewer → GitMgr    │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│         │            │            │            │            │            │
│         ▼            ▼            ▼            ▼            ▼            │
│      Opus 4       Sonnet 4     E2B         Sonnet 4     Opus 4          │
│                              Sandbox                                     │
├──────────────────────────────────────────────────────────────────────────┤
│                       PERSISTENCE LAYER                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                  │
│  │  PostgreSQL  │  │    Redis     │  │    Neo4j     │                  │
│  │ (State, DB)  │  │  (Queue,     │  │  (Strategy   │                  │
│  │              │  │   Capacity)  │  │   Graph)     │                  │
│  └──────────────┘  └──────────────┘  └──────────────┘                  │
└──────────────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Typical Implementation |
|-----------|----------------|------------------------|
| **State Machine Controller** | Orchestrates founder journey through 5 stages, enforces decision gates, computes progress | Python state machine with stage transition guards, PostgreSQL persistence |
| **Runner Interface** | Abstract interface wrapping LangGraph agent (RunnerReal for prod, RunnerFake for tests) | Protocol/ABC defining `run(goal, context) -> Result`, implementations inject LangGraph or mock |
| **Artifact Generator** | Produces versioned artifacts (briefs, scopes, risk logs) from state + LLM reasoning | Template-driven with Claude Opus, stores in PostgreSQL with version history |
| **Worker Capacity System** | Queue-based rate limiting that slows (not halts) work when capacity exceeded | Redis-backed priority queue + worker pool, returns estimated wait times |
| **Strategy Graph** | Records decision nodes (options, rationale, tradeoffs, impact) as graph in Neo4j | Cypher queries on Neo4j, nodes = decisions, edges = dependencies/alternatives |
| **Versioning System** | Tracks artifact versions (v0.1, v0.2) with diffs, supports rollback | PostgreSQL JSONB column with version array, timestamp + diff metadata |
| **Execution Timeline** | Kanban-style view of all tickets/steps with states | Derived from State Machine + LangGraph plan steps, real-time updates via SSE |

## Recommended Project Structure

### Backend (New Components)

```
backend/app/
├── state_machine/           # NEW — Startup state orchestration
│   ├── __init__.py
│   ├── machine.py          # Core state machine (5 stages + transitions)
│   ├── stages.py           # Stage definitions (entry/exit criteria)
│   ├── gates.py            # Decision gate logic (Proceed/Narrow/Pivot/Park)
│   └── progress.py         # Progress computation from artifacts/builds
├── runner/                  # NEW — Testable agent interface
│   ├── __init__.py
│   ├── interface.py        # Abstract Runner protocol
│   ├── real.py             # RunnerReal wrapping existing LangGraph
│   ├── fake.py             # RunnerFake for tests (predictable outputs)
│   └── context.py          # Runner execution context (user, project, stage)
├── artifacts/               # NEW — Versioned document generation
│   ├── __init__.py
│   ├── generator.py        # Artifact generation orchestrator
│   ├── templates/          # Jinja2 templates for each artifact type
│   │   ├── idea_brief.md.j2
│   │   ├── product_brief.md.j2
│   │   ├── mvp_scope.md.j2
│   │   └── risk_log.md.j2
│   ├── versioning.py       # Version tracking + diff computation
│   └── export.py           # PDF and Markdown export
├── capacity/                # NEW — Worker capacity management
│   ├── __init__.py
│   ├── queue.py            # Redis-backed priority queue
│   ├── worker.py           # Worker pool manager
│   ├── limits.py           # Per-tier capacity limits
│   └── estimator.py        # Wait time estimation
├── strategy/                # NEW — Neo4j decision graph
│   ├── __init__.py
│   ├── graph.py            # Decision node CRUD
│   ├── queries.py          # Graph traversal queries
│   └── schemas.py          # Decision/Edge schemas
├── agent/                   # EXISTING — preserved as-is
│   ├── graph.py            # LangGraph definition
│   ├── state.py            # CoFounderState
│   └── nodes/              # 6 specialist nodes
├── api/routes/              # MIXED — new + existing
│   ├── state_machine.py    # NEW — Stage transitions, progress
│   ├── artifacts.py        # NEW — Artifact CRUD, versioning
│   ├── strategy.py         # NEW — Decision graph queries
│   ├── runner.py           # NEW — Job submission, status
│   ├── agent.py            # EXISTING — chat preserved as secondary
│   ├── projects.py         # EXISTING — enhanced with stage info
│   └── billing.py          # EXISTING — unchanged
└── db/models/               # MIXED
    ├── startup_stage.py    # NEW — Current stage per project
    ├── artifact.py         # NEW — Versioned artifacts
    ├── decision.py         # NEW — Decision log (audit trail)
    ├── job_queue.py        # NEW — Background job metadata
    ├── project.py          # EXISTING — add stage_id FK
    └── user_settings.py    # EXISTING — add beta flags
```

### Frontend (New Components)

```
frontend/src/
├── app/(dashboard)/
│   ├── company/            # NEW — Main dashboard
│   │   └── page.tsx       # Stage, version, progress, risks, preview
│   ├── strategy/           # NEW — Interactive strategy graph
│   │   └── page.tsx       # Neo4j graph visualization
│   ├── timeline/           # NEW — Kanban execution board
│   │   └── page.tsx       # Tickets, states, drill-down
│   ├── decisions/          # NEW — Decision console
│   │   └── page.tsx       # Templated decisions with options
│   ├── artifacts/          # NEW — Artifact library
│   │   └── page.tsx       # Versioned docs with export
│   └── chat/               # EXISTING — de-emphasized, preserved
│       └── page.tsx
├── components/
│   ├── dashboard/          # NEW — PM-style cards
│   │   ├── StageCard.tsx
│   │   ├── ProgressMeter.tsx
│   │   ├── RiskPanel.tsx
│   │   └── PreviewLink.tsx
│   ├── strategy/           # NEW — Graph visualization
│   │   ├── DecisionNode.tsx
│   │   └── GraphCanvas.tsx
│   ├── timeline/           # NEW — Kanban components
│   │   ├── KanbanBoard.tsx
│   │   ├── TicketCard.tsx
│   │   └── StateColumn.tsx
│   ├── artifacts/          # NEW — Document viewer
│   │   ├── ArtifactViewer.tsx
│   │   ├── VersionHistory.tsx
│   │   └── ExportButton.tsx
│   └── chat/               # EXISTING — unchanged
└── lib/
    ├── api/                # MIXED
    │   ├── state-machine.ts  # NEW
    │   ├── artifacts.ts      # NEW
    │   ├── strategy.ts       # NEW
    │   ├── runner.ts         # NEW
    │   └── agent.ts          # EXISTING
    └── hooks/
        ├── useStage.ts       # NEW — Stage state + transitions
        ├── useArtifacts.ts   # NEW — Artifact fetching + versioning
        ├── useStrategy.ts    # NEW — Decision graph queries
        └── useCapacity.ts    # NEW — Queue status + estimates
```

### Structure Rationale

- **state_machine/:** Encapsulates all stage orchestration logic separate from agent execution — state machine is pure business logic, runner is execution interface
- **runner/:** Introduces testability layer without modifying existing LangGraph code — existing graph.py untouched, wrapped via RunnerReal
- **artifacts/:** Single responsibility for document generation, versioning, and export — templates separate from logic
- **capacity/:** Queue and worker logic isolated — can be scaled independently, Redis-backed for distributed systems
- **strategy/:** Neo4j-specific logic contained — already have knowledge_graph.py, strategy graph is parallel structure for decisions

## Architectural Patterns

### Pattern 1: State Machine with Deterministic Progress

**What:** Startup stages (Thesis → Validated → MVP → Feedback → Scale) managed by explicit state machine with computed progress based on artifacts and build status, not user input.

**When to use:** Multi-step workflows where user completes tasks in order and progress is objectively measurable.

**Trade-offs:**
- **Pro:** Progress always accurate, no manual updates, prevents skipping critical steps
- **Con:** Requires clear entry/exit criteria for each stage, more complex than free-form chat

**Example:**
```python
# backend/app/state_machine/machine.py
class StartupStage(Enum):
    THESIS_DEFINED = "thesis_defined"
    VALIDATED_DIRECTION = "validated_direction"
    MVP_BUILT = "mvp_built"
    FEEDBACK_LOOP_ACTIVE = "feedback_loop_active"
    SCALE_OPTIMIZE = "scale_optimize"  # out of scope for MVP

class StateMachine:
    def __init__(self, project: Project):
        self.project = project
        self.current_stage = project.startup_stage

    def can_transition_to(self, target_stage: StartupStage) -> bool:
        """Check if transition is allowed based on exit criteria."""
        criteria = EXIT_CRITERIA[self.current_stage]
        return all(criterion.is_met(self.project) for criterion in criteria)

    def compute_progress(self) -> float:
        """Deterministic progress calculation from artifacts + build status."""
        artifacts = get_artifacts_for_stage(self.project, self.current_stage)
        builds = get_builds_for_project(self.project)

        required_artifacts = STAGE_REQUIREMENTS[self.current_stage]["artifacts"]
        required_builds = STAGE_REQUIREMENTS[self.current_stage]["builds"]

        artifact_progress = len(artifacts) / len(required_artifacts)
        build_progress = len(builds) / len(required_builds) if required_builds else 1.0

        return (artifact_progress + build_progress) / 2
```

### Pattern 2: Runner Interface with Fakes for Testing

**What:** Abstract interface (`Runner`) with two implementations: `RunnerReal` (wraps existing LangGraph) and `RunnerFake` (returns predictable outputs for tests). Tests never invoke real LLM.

**When to use:** Wrapping expensive/slow external dependencies (LLMs, sandboxes) to enable fast, deterministic tests.

**Trade-offs:**
- **Pro:** Tests run in milliseconds, no API costs, predictable outputs, can simulate failures
- **Con:** Additional abstraction layer, must maintain interface + two implementations

**Example:**
```python
# backend/app/runner/interface.py
from typing import Protocol
from dataclasses import dataclass

@dataclass
class RunnerContext:
    user_id: str
    project_id: str
    current_stage: StartupStage
    goal: str

@dataclass
class RunnerResult:
    success: bool
    artifacts: list[Artifact]
    errors: list[str]
    next_steps: list[str]

class Runner(Protocol):
    async def run(self, context: RunnerContext) -> RunnerResult:
        """Execute agent workflow and return results."""
        ...

# backend/app/runner/real.py
class RunnerReal:
    """Production implementation wrapping LangGraph."""

    async def run(self, context: RunnerContext) -> RunnerResult:
        from app.agent.graph import create_production_graph
        from app.agent.state import create_initial_state

        state = create_initial_state(
            user_id=context.user_id,
            project_id=context.project_id,
            project_path=f"/workspace/{context.project_id}",
            goal=context.goal,
        )

        graph = create_production_graph()
        result = await graph.ainvoke(state)

        return RunnerResult(
            success=not result.get("has_fatal_error"),
            artifacts=self._extract_artifacts(result),
            errors=result.get("active_errors", []),
            next_steps=self._extract_next_steps(result),
        )

# backend/app/runner/fake.py
class RunnerFake:
    """Test implementation with predictable outputs."""

    def __init__(self, canned_results: dict[str, RunnerResult]):
        self.canned_results = canned_results
        self.call_count = 0

    async def run(self, context: RunnerContext) -> RunnerResult:
        self.call_count += 1
        # Return pre-configured result based on goal
        return self.canned_results.get(context.goal, DEFAULT_SUCCESS_RESULT)
```

### Pattern 3: Queue-Based Capacity Model (Slow, Don't Halt)

**What:** Redis-backed priority queue tracks in-flight jobs. When capacity exceeded, new jobs queue with estimated wait time. Work slows down but never blocks founders.

**When to use:** High-concurrency systems (1000+ users) where hard rate limits would frustrate users, but unbounded throughput would cause cost/stability issues.

**Trade-offs:**
- **Pro:** Better UX than "try again later", scales to many users, predictable costs
- **Con:** Requires background workers, queue monitoring, more complex than simple rate limiting

**Example:**
```python
# backend/app/capacity/queue.py
from redis.asyncio import Redis
import json
from datetime import datetime, timedelta

class CapacityQueue:
    def __init__(self, redis: Redis):
        self.redis = redis

    async def submit_job(self, user_id: str, job_type: str, payload: dict) -> str:
        """Submit job to queue, return job_id."""
        job_id = str(uuid.uuid4())

        # Check user's tier capacity
        tier = await get_user_tier(user_id)
        max_concurrent = tier.max_concurrent_jobs

        # Count user's active jobs
        active_key = f"capacity:active:{user_id}"
        active_count = await self.redis.scard(active_key)

        # Priority based on tier + job type
        priority = self._compute_priority(tier, job_type)

        job_data = {
            "job_id": job_id,
            "user_id": user_id,
            "job_type": job_type,
            "payload": payload,
            "submitted_at": datetime.utcnow().isoformat(),
            "priority": priority,
        }

        # Add to sorted set (priority queue)
        await self.redis.zadd("capacity:queue", {json.dumps(job_data): priority})

        # Estimate wait time
        queue_position = await self.redis.zrank("capacity:queue", json.dumps(job_data))
        estimated_wait = self._estimate_wait(queue_position, job_type)

        return job_id, estimated_wait

    async def claim_next_job(self, worker_id: str) -> dict | None:
        """Worker claims next job from queue."""
        # Atomic pop from sorted set
        jobs = await self.redis.zpopmin("capacity:queue", 1)
        if not jobs:
            return None

        job_json, priority = jobs[0]
        job_data = json.loads(job_json)

        # Mark as active
        await self.redis.sadd(f"capacity:active:{job_data['user_id']}", job_data['job_id'])
        await self.redis.hset(f"capacity:job:{job_data['job_id']}", mapping={
            "status": "running",
            "worker_id": worker_id,
            "started_at": datetime.utcnow().isoformat(),
        })

        return job_data
```

### Pattern 4: Versioned Artifacts with Diffs

**What:** Each artifact (Product Brief, MVP Scope, etc.) stored with version history. Versions track timestamp, content snapshot, and diff from previous version.

**When to use:** Documents that evolve over time and users need to see what changed between versions or rollback to previous state.

**Trade-offs:**
- **Pro:** Full audit trail, supports rollback, diffs show decision evolution
- **Con:** Storage overhead, more complex queries (filter by version), diff computation cost

**Example:**
```python
# backend/app/db/models/artifact.py
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import JSONB

class Artifact(Base):
    __tablename__ = "artifacts"

    id = Column(Integer, primary_key=True)
    project_id = Column(UUID, ForeignKey("projects.id"), nullable=False)
    artifact_type = Column(String(50), nullable=False)  # idea_brief, product_brief, etc.

    # Current version (denormalized for fast access)
    current_version = Column(String(20), nullable=False)  # "v0.1"
    current_content = Column(Text, nullable=False)

    # Version history as JSONB array
    versions = Column(JSONB, nullable=False, default=list)
    # Structure: [{"version": "v0.1", "timestamp": "...", "content": "...", "diff": "..."}]

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

# backend/app/artifacts/versioning.py
import difflib

class ArtifactVersioning:
    def create_version(self, artifact: Artifact, new_content: str) -> str:
        """Create new version, compute diff, update artifact."""
        old_version = artifact.current_version
        old_content = artifact.current_content

        # Increment version (v0.1 -> v0.2)
        new_version = self._increment_version(old_version)

        # Compute diff
        diff = self._compute_diff(old_content, new_content)

        # Append to version history
        version_record = {
            "version": new_version,
            "timestamp": datetime.utcnow().isoformat(),
            "content": new_content,
            "diff": diff,
            "diff_summary": self._summarize_diff(diff),
        }

        artifact.versions.append(version_record)
        artifact.current_version = new_version
        artifact.current_content = new_content

        return new_version

    def _compute_diff(self, old: str, new: str) -> str:
        """Unified diff between versions."""
        diff = difflib.unified_diff(
            old.splitlines(keepends=True),
            new.splitlines(keepends=True),
            lineterm="",
        )
        return "".join(diff)
```

## Data Flow

### Request Flow: Founder Starts New Stage

```
[Founder clicks "Begin Validation"]
    ↓
[Frontend] POST /api/state-machine/transition {to_stage: "validated_direction"}
    ↓
[State Machine API]
    ├─→ Check current stage exit criteria (all artifacts complete?)
    ├─→ If not met, return 400 with missing requirements
    └─→ If met, proceed
    ↓
[State Machine Controller]
    ├─→ Update project.startup_stage in database
    ├─→ Emit stage transition event to timeline
    └─→ Return new stage + progress (0%)
    ↓
[Frontend Dashboard]
    ├─→ Update stage card ("Validated Direction")
    ├─→ Show new milestone requirements
    └─→ Enable artifact generation buttons
```

### Request Flow: Generate Artifact via Runner

```
[Founder clicks "Generate Product Brief"]
    ↓
[Frontend] POST /api/runner/submit {job_type: "generate_artifact", artifact_type: "product_brief"}
    ↓
[Runner API]
    ├─→ Authenticate + check subscription tier
    ├─→ Check beta flag for artifact type
    └─→ Submit to capacity queue
    ↓
[Capacity Queue]
    ├─→ Compute priority (tier + job type)
    ├─→ Check user's concurrent job limit
    ├─→ Enqueue job with priority
    ├─→ Estimate wait time from queue position
    └─→ Return {job_id, estimated_wait: "3 minutes"}
    ↓
[Frontend]
    ├─→ Show "Processing... estimated 3 minutes"
    ├─→ Poll GET /api/runner/status/{job_id} every 2 seconds
    └─→ Update UI on status change
    ↓
[Background Worker]
    ├─→ Claim next job from queue
    ├─→ Call RunnerReal.run(context)
        ├─→ Wraps existing LangGraph
        ├─→ Architect node: Generate brief outline
        ├─→ Coder node: Fill in sections
        └─→ Return artifacts
    ├─→ Create Artifact record with v0.1
    ├─→ Update job status to "complete"
    └─→ Emit artifact_created event
    ↓
[Frontend receives SSE or polling result]
    ├─→ Fetch GET /api/artifacts/{artifact_id}
    ├─→ Render ArtifactViewer component
    ├─→ Update stage progress (re-compute from state machine)
    └─→ Show "Product Brief v0.1 complete"
```

### State Management Flow

```
[State Machine Compute Progress]
    ↓
Query artifacts for current stage
    ↓
┌─────────────────────────────────────────┐
│ Thesis Defined stage requires:         │
│ - Idea Brief artifact (v0.1+)          │
│ - Rationalised Idea Brief (v0.1+)     │
│ - Decision Gate 1 (Proceed selected)   │
└─────────────────────────────────────────┘
    ↓
Check each requirement:
├─→ Idea Brief exists? ✓ (v0.1)
├─→ Rationalised Idea Brief exists? ✗ (missing)
└─→ Decision Gate 1 complete? ✗ (pending)
    ↓
Progress = 33.3% (1 of 3 requirements met)
Exit criteria not met → Cannot transition to next stage
    ↓
Return {
  "stage": "thesis_defined",
  "progress": 0.333,
  "requirements": [
    {"name": "Idea Brief", "status": "complete", "version": "v0.1"},
    {"name": "Rationalised Idea Brief", "status": "pending", "action": "Generate"},
    {"name": "Decision Gate 1", "status": "pending", "action": "Review & Decide"}
  ]
}
```

### Key Data Flows

1. **Stage Transition Flow:** State Machine API → PostgreSQL (project.startup_stage) → Timeline SSE Event → Frontend Dashboard
2. **Artifact Generation Flow:** Runner API → Capacity Queue → Worker → LangGraph (RunnerReal) → Artifact DB → Version History → Frontend Viewer
3. **Decision Recording Flow:** Decision Console UI → Strategy API → Neo4j (Decision Node + Edges) → Audit Log → Frontend Graph
4. **Progress Computation Flow:** State Machine → Query Artifacts/Builds → Apply Stage Requirements → Return % → Dashboard UI

## Scaling Considerations

| Scale | Architecture Adjustments |
|-------|--------------------------|
| **0-100 users** | Single ECS task, in-memory queue acceptable, synchronous LangGraph execution |
| **100-1000 users** | Implement Redis queue, add 2-3 background workers, start worker capacity limits, monitor LLM costs closely |
| **1000-10000 users** | Multi-region Redis, dedicated worker pool (separate ECS service), aggressive caching of artifacts, implement request coalescing (multiple founders asking similar questions hit cache), consider Sonnet-only for non-critical paths |

### Scaling Priorities

1. **First bottleneck:** LLM cost at 500+ active users
   - **Fix:** Implement aggressive artifact caching (if founder asks "what's my risk?" twice, second request hits cache for 1 hour)
   - **Fix:** Use Sonnet for all non-strategic decisions (only Opus for Architect and critical decisions)
   - **Fix:** Request coalescing for similar goals (detect via semantic similarity, return cached result if >90% similar)

2. **Second bottleneck:** PostgreSQL write contention on artifacts table at 2000+ concurrent generations
   - **Fix:** Shard artifacts table by project_id (hash-based sharding)
   - **Fix:** Write-through cache in Redis for current artifact versions
   - **Fix:** Batch version history updates (collect diffs, flush every 10 seconds instead of per-version)

3. **Third bottleneck:** E2B sandbox quota limits at 5000+ users (E2B has concurrency limits per account)
   - **Fix:** Multiple E2B accounts with round-robin assignment
   - **Fix:** Sandbox pooling (pre-warm 10 sandboxes, reuse across users)
   - **Fix:** Lazy sandbox creation (only spin up when user actually deploys, not on every artifact generation)

## Anti-Patterns

### Anti-Pattern 1: Direct LangGraph Invocation in Tests

**What people do:** Call `create_cofounder_graph().invoke(state)` directly in unit tests, leading to real LLM calls during tests.

**Why it's wrong:**
- Tests become slow (30+ seconds per test)
- Tests cost money (real Claude API calls)
- Tests are non-deterministic (LLM outputs vary)
- CI/CD pipelines break when API is down

**Do this instead:** Always use RunnerFake in tests. Only RunnerReal should touch LangGraph.

```python
# BAD
async def test_artifact_generation():
    graph = create_cofounder_graph()  # Will call real Claude API
    result = await graph.ainvoke(state)
    assert result["artifacts"]

# GOOD
async def test_artifact_generation():
    runner = RunnerFake(canned_results={
        "Generate product brief": RunnerResult(
            success=True,
            artifacts=[Artifact(type="product_brief", content="...")],
            errors=[],
        )
    })
    result = await runner.run(context)
    assert result.success
    assert result.artifacts[0].type == "product_brief"
```

### Anti-Pattern 2: State Machine Logic in Controllers

**What people do:** Put stage transition logic directly in API route handlers, leading to duplicated business logic and inconsistent state.

**Why it's wrong:**
- Logic duplicated across multiple endpoints
- Business rules (exit criteria) scattered in code
- Impossible to test state machine in isolation
- State transitions happen outside state machine (inconsistent)

**Do this instead:** All state transitions go through StateMachine class. API controllers only validate input and delegate.

```python
# BAD
@router.post("/state-machine/transition")
async def transition_stage(to_stage: str):
    project = get_project()

    # Business logic in controller
    if to_stage == "validated_direction":
        artifacts = get_artifacts(project)
        if len(artifacts) < 2:
            raise HTTPException(400, "Missing artifacts")
        if not get_decision_gate(project, 1):
            raise HTTPException(400, "Decision gate not complete")

    project.startup_stage = to_stage
    await db.commit()
    return {"stage": to_stage}

# GOOD
@router.post("/state-machine/transition")
async def transition_stage(to_stage: str):
    project = get_project()
    machine = StateMachine(project)

    # Delegate to state machine
    if not machine.can_transition_to(to_stage):
        missing = machine.get_missing_requirements(to_stage)
        raise HTTPException(400, {"error": "Cannot transition", "missing": missing})

    await machine.transition_to(to_stage)
    return {"stage": to_stage, "progress": machine.compute_progress()}
```

### Anti-Pattern 3: Synchronous Artifact Generation in Request Handler

**What people do:** Generate artifacts synchronously during HTTP request, leading to 30+ second response times and frontend timeouts.

**Why it's wrong:**
- HTTP request times out (most load balancers timeout at 30s)
- Frontend shows blank screen while waiting
- User closes tab → wasted LLM cost
- Cannot implement queue/capacity limits

**Do this instead:** Always submit artifact generation as background job. Return job_id immediately, frontend polls for completion.

```python
# BAD
@router.post("/artifacts/generate")
async def generate_artifact(artifact_type: str):
    runner = RunnerReal()
    result = await runner.run(context)  # Takes 30+ seconds
    artifact = create_artifact(result)
    return {"artifact_id": artifact.id}

# GOOD
@router.post("/artifacts/generate")
async def generate_artifact(artifact_type: str):
    queue = get_capacity_queue()
    job_id, estimated_wait = await queue.submit_job(
        user_id=user.id,
        job_type="generate_artifact",
        payload={"artifact_type": artifact_type},
    )
    return {"job_id": job_id, "estimated_wait": estimated_wait}

@router.get("/runner/status/{job_id}")
async def get_job_status(job_id: str):
    status = await get_job_status(job_id)
    return {
        "status": status.state,  # "queued", "running", "complete", "failed"
        "result": status.result if status.state == "complete" else None,
    }
```

### Anti-Pattern 4: Hardcoded Stage Requirements

**What people do:** Hardcode stage exit criteria in if/else statements, making it impossible to change requirements without code changes.

**Why it's wrong:**
- Cannot A/B test different stage flows
- Cannot customize per user (some founders skip steps)
- Every requirement change requires code deploy
- Impossible to preview "what if I changed this requirement?"

**Do this instead:** Store stage requirements in database or config, make them data-driven.

```python
# BAD
def can_transition_from_thesis_to_validated(project):
    if not has_artifact(project, "idea_brief"):
        return False
    if not has_artifact(project, "rationalised_idea_brief"):
        return False
    if not has_decision(project, "gate_1"):
        return False
    return True

# GOOD
STAGE_REQUIREMENTS = {
    "thesis_defined": {
        "exit_criteria": [
            {"type": "artifact", "artifact_type": "idea_brief", "min_version": "v0.1"},
            {"type": "artifact", "artifact_type": "rationalised_idea_brief", "min_version": "v0.1"},
            {"type": "decision", "gate": "gate_1", "status": "proceed"},
        ]
    }
}

def can_transition_from(stage: StartupStage, project: Project) -> bool:
    criteria = STAGE_REQUIREMENTS[stage]["exit_criteria"]
    return all(criterion_is_met(criterion, project) for criterion in criteria)
```

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| **E2B Sandbox** | Session-based API client, create on-demand | Existing integration via `backend/app/sandbox/e2b_runtime.py`, preserve as-is |
| **Anthropic Claude** | LangChain ChatAnthropic wrapper with usage callbacks | Existing via `backend/app/core/llm_config.py`, RunnerReal wraps this |
| **Neo4j** | AsyncGraphDatabase driver with Cypher queries | Existing for knowledge graph, parallel Strategy Graph for decisions |
| **Stripe** | Webhook-based subscription events | Existing via `backend/app/api/routes/billing.py`, no changes needed |
| **Clerk** | JWT verification via JWKS endpoint | Existing via `backend/app/core/auth.py`, add beta flag to metadata |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| **State Machine ↔ Runner** | Async method call with RunnerContext | State machine submits jobs, runner executes, state machine processes results |
| **Runner ↔ LangGraph** | RunnerReal wraps existing `create_production_graph().ainvoke()` | Clean boundary — RunnerReal is adapter, LangGraph unchanged |
| **Artifact Generator ↔ LLM** | Template-driven prompts via ChatAnthropic | Use Opus for strategic artifacts (briefs), Sonnet for tactical (scopes) |
| **Capacity Queue ↔ Worker Pool** | Redis pub/sub for job claims, polling for status | Workers poll queue, claim jobs atomically via ZPOPMIN |
| **Frontend ↔ Backend** | REST API + SSE for real-time updates | Existing pattern for chat, extend for state machine events |

## Build Order (Dependency-Driven)

### Phase 1: Foundation (Week 1, Days 1-3)

**Goal:** Set up core abstractions without breaking existing system.

1. **Runner Interface** (1 day)
   - Define `Runner` protocol in `backend/app/runner/interface.py`
   - Implement `RunnerReal` wrapping existing LangGraph
   - Implement `RunnerFake` with canned responses
   - Write tests for both implementations
   - **Why first:** All subsequent components depend on testable runner

2. **State Machine Core** (1 day)
   - Define 5 stages in `backend/app/state_machine/stages.py`
   - Implement `StateMachine` class with transition logic
   - Add `startup_stage` column to `projects` table
   - Write state machine unit tests (using RunnerFake)
   - **Why second:** State machine is central orchestrator, must exist before artifacts/decisions

3. **Artifact Models** (1 day)
   - Create `artifacts` table with JSONB version history
   - Implement `ArtifactVersioning` class
   - Add artifact CRUD API routes
   - Write artifact tests (no generation yet)
   - **Why third:** Artifacts are data dependency for state machine progress computation

### Phase 2: Artifact Generation (Week 1, Days 4-5)

**Goal:** Founders can generate versioned artifacts via background jobs.

4. **Capacity Queue** (1 day)
   - Implement Redis-backed priority queue in `backend/app/capacity/queue.py`
   - Add job submission + claiming logic
   - Write queue tests (Redis mock)
   - **Why fourth:** Needed before running expensive LangGraph operations

5. **Artifact Generator** (1 day)
   - Create Jinja2 templates for each artifact type
   - Implement `ArtifactGenerator` using RunnerReal
   - Add background worker to claim jobs from queue
   - Wire up artifact generation API endpoint
   - **Why fifth:** Combines runner + queue + artifacts into working flow

### Phase 3: State Machine Integration (Week 1, Days 6-7 + Week 2, Days 1-2)

**Goal:** State machine drives founder journey, progress auto-computed.

6. **Progress Computation** (1 day)
   - Implement stage requirement definitions (data-driven)
   - Add `compute_progress()` logic based on artifacts/builds
   - Write progress tests with various artifact combinations
   - **Why sixth:** Progress shown in dashboard, needs accurate computation

7. **State Machine API** (1 day)
   - Add `/state-machine/transition` endpoint
   - Add `/state-machine/progress` endpoint
   - Add stage transition validation (exit criteria checks)
   - Write API integration tests
   - **Why seventh:** Exposes state machine to frontend

8. **Frontend Dashboard** (2 days)
   - Build Company Dashboard page with stage card + progress
   - Add stage transition UI (button + confirmation)
   - Display artifact requirements for current stage
   - Show blocking issues preventing transition
   - **Why eighth:** First user-facing piece of new architecture

### Phase 4: Strategy & Timeline (Week 2, Days 3-5)

**Goal:** Founders see decision history and execution progress.

9. **Strategy Graph** (1 day)
   - Define Decision node schema in Neo4j
   - Implement decision CRUD in `backend/app/strategy/graph.py`
   - Add API routes for decision queries
   - Write Neo4j integration tests
   - **Why ninth:** Independent of state machine, can be built in parallel

10. **Execution Timeline** (1 day)
    - Derive timeline from State Machine + LangGraph plan steps
    - Add Kanban board component in frontend
    - Implement SSE updates for real-time status
    - **Why tenth:** Combines state machine + runner results into view

11. **Decision Console** (1 day)
    - Build templated decision UI (options + tradeoffs)
    - Connect to Strategy Graph API
    - Record decision outcomes in Neo4j
    - **Why eleventh:** Depends on Strategy Graph API

### Phase 5: Polish & Export (Week 2, Days 6-7)

**Goal:** Artifact export, version history, production readiness.

12. **Artifact Export** (1 day)
    - Implement PDF generation from Markdown
    - Add download endpoints for PDF + Markdown
    - Add version history UI in ArtifactViewer
    - **Why twelfth:** Value-add feature, can be last

13. **Integration Testing** (1 day)
    - End-to-end test: Founder flow from thesis to MVP built
    - Load test capacity queue with 100 concurrent jobs
    - Deploy to staging, smoke test all flows
    - **Why thirteenth:** Final validation before production

## Component Dependencies (Build Graph)

```
Runner Interface (1)
    ↓
    ├─→ State Machine Core (2)
    │       ↓
    │       └─→ Progress Computation (6)
    │               ↓
    │               └─→ State Machine API (7)
    │                       ↓
    │                       └─→ Frontend Dashboard (8)
    │
    ├─→ Artifact Models (3)
    │       ↓
    │       ├─→ Capacity Queue (4)
    │       │       ↓
    │       │       └─→ Artifact Generator (5)
    │       │               ↓
    │       │               └─→ Artifact Export (12)
    │       │
    │       └─→ Progress Computation (6)
    │
    └─→ Strategy Graph (9)
            ↓
            ├─→ Decision Console (11)
            └─→ Execution Timeline (10)
```

**Critical Path:** 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 (8 days minimum)

**Parallelizable:** Strategy Graph (9) can start after Runner Interface (1), runs in parallel with State Machine work.

---

*Architecture research for: AI-powered Technical Co-Founder SaaS (Brownfield Migration)*
*Researched: 2026-02-16*
*Confidence: HIGH — based on existing codebase analysis and proven patterns for multi-stage workflows with AI generation*
