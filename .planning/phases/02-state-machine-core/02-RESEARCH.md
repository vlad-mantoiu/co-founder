# Phase 2: State Machine Core - Research

**Researched:** 2026-02-16
**Domain:** Finite State Machine, PostgreSQL persistence, deterministic progress computation
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### Stage Definitions
- Projects start in a **pre-stage state** (no stage assigned) -- they exist but haven't entered the journey
- Entry into Stage 1 (Thesis Defined) happens **after the first decision gate is passed** (founder chooses Proceed)
- Stage 5 (Scale & Optimize) is **visible but locked** -- exists in the model so founders see the full path, marked as "Coming Soon" / inaccessible in MVP
- Exit criteria use a **template + dynamic** model: base template of required criteria per stage, plus optional criteria generated from the project's specifics

#### Transition Rules
- **Backward transitions allowed** -- a Pivot can send a project back to an earlier stage (e.g., Pivot from Stage 3 -> Stage 1)
- **Parked** projects move to a **special "Parked" status** separate from the 5 stages -- effectively shelved, can be resumed later
- **Multiple decision gates can coexist** -- a project can have more than one pending gate at a time (e.g., direction gate + build path gate)
- **Narrowing re-validates exit criteria** -- when a founder chooses "Narrow", some exit criteria may reset since the brief changed, and progress may decrease

#### Progress Computation
- **Both per-stage and global progress** -- each stage has its own 0-100%, plus an overall journey percentage
- Progress is based on **weighted milestones** per stage (e.g., "brief generated" = 30%, "gate passed" = 20%, "build ready" = 50%)
- Milestone weights are **configurable per project** -- can be adjusted based on project type or complexity
- **Progress can decrease** -- if a pivot invalidates artifacts, progress drops to reflect reality

#### Risk & Focus Signals
- Blocking risks use **both system-defined rules AND LLM-assessed risks** -- system rules catch obvious blockers (no decision in 7 days, build failed 3x, stale project), LLM adds nuanced assessment (scope too broad for MVP)
- Suggested focus is **context-aware** -- LLM considers project state, risks, and time to suggest the highest-impact next action
- Risk flags are **dismissible** -- founder can acknowledge and dismiss, won't show again unless conditions worsen

### Claude's Discretion
- Event storage approach for correlation_id observability (separate timeline table vs JSONB event log)
- Exact FSM library choice (transitions, custom, etc.)
- Internal data model for milestone weights
- How to compute global progress from per-stage progress (equal stage weight vs weighted by complexity)

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

## Summary

This phase builds the core state machine engine for a five-stage startup journey. The domain is well-understood: finite state machines with database-persisted state, event logging, and deterministic progress computation. No UI or API endpoints -- pure domain logic with PostgreSQL persistence.

The existing codebase uses async SQLAlchemy 2.0+ with asyncpg, Pydantic settings, and a TDD pattern established in Phase 1 with RunnerFake. The Project model already exists with basic fields (id, clerk_user_id, name, description, status). Phase 2 extends this with stage tracking, decision gates, milestones, exit criteria, risk signals, and an event timeline. All new models follow the existing pattern: UUID primary keys, timezone-aware timestamps, and the shared `Base` class from `app.db.base`.

The key technical decisions are: (1) use a custom FSM implementation rather than the `transitions` library, because our FSM is simple (6 states including pre-stage and parked) and tightly coupled to database persistence, making a library add complexity without value; (2) use a separate `stage_events` timeline table for correlation_id observability rather than JSONB, because it enables efficient querying, indexing, and audit trails; (3) store milestone weights as a JSONB column on a per-stage configuration, defaulting from templates; (4) compute global progress as a weighted average where each stage's weight equals its milestone count relative to total milestones.

**Primary recommendation:** Build a custom FSM as pure Python domain logic (no library dependency) with PostgreSQL-persisted state, a dedicated event timeline table, and deterministic progress computation functions that are trivially testable without a database.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| SQLAlchemy | >=2.0.0 | ORM for state machine models | Already in project, async support, mature |
| asyncpg | >=0.30.0 | PostgreSQL async driver | Already in project, fastest async PG driver |
| Pydantic | >=2.10.0 | Validation for state transitions, gate decisions | Already in project, type-safe |
| Python enum | stdlib | Stage and status enums | No dependency, maps to PG enum via SQLAlchemy |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Alembic | >=1.13.0 | Database migrations | Already in pyproject.toml deps, needs init |
| pytest-asyncio | >=0.24.0 | Async test support | All domain tests are async |
| uuid (stdlib) | - | UUID generation for correlation_ids | Event tracking |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Custom FSM | `transitions` v0.9.3 | Library adds AsyncMachine with callbacks, but our FSM has 6 states and ~10 transitions -- a library would add abstraction without reducing complexity. Custom is simpler, fully testable, no dependency. |
| Custom FSM | `sqlalchemy-fsm` | Last released Aug 2022, unmaintained, does not support SQLAlchemy 2.0 async. Not viable. |
| Custom FSM | `python-statemachine` v2.5 | Declarative API is nice but designed for in-memory state; persistence integration is manual anyway. |
| Timeline table | JSONB event log on Project | JSONB makes querying events across projects hard, no indexing on individual event fields, append-only semantics are awkward in JSONB |

**Installation:**
```bash
# No new dependencies needed -- all already in pyproject.toml
# Alembic is already listed but needs `alembic init` setup
```

## Discretion Recommendations

### 1. FSM Library: Use Custom Implementation (RECOMMENDED)

**Rationale:** The state machine has exactly 6 states (PreStage, Stage1-4, Parked; Stage5 is locked/visible-only) and approximately 10 valid transitions. The `transitions` library (v0.9.3, released July 2025) provides AsyncMachine with callbacks, hierarchical states, and diagram generation. However:

- Our transitions are gated by decision gates, not simple trigger methods
- State is persisted in PostgreSQL, not in-memory objects
- The library's model-attachment pattern (`machine.model`) conflicts with SQLAlchemy models
- Testing a custom FSM is trivial; testing through a library adds indirection
- Total custom code: ~100 lines for the transition validator

The `transitions` library shines for complex in-memory state machines with many states and dynamic behavior. For a 6-state DB-persisted FSM, it adds a dependency without meaningful benefit.

### 2. Event Storage: Separate Timeline Table (RECOMMENDED)

**Rationale:** A dedicated `stage_events` table with structured columns beats JSONB for this use case:

- **Queryability**: `SELECT * FROM stage_events WHERE project_id = ? ORDER BY created_at` is trivial
- **Indexing**: Composite index on `(project_id, created_at)` for fast timeline queries
- **correlation_id**: First-class column, indexable for tracing related events
- **Type safety**: Enum column for event_type, not string matching in JSON
- **Append-only**: INSERT-only table, never UPDATE -- natural audit trail
- **Cross-project queries**: "All projects that pivoted in the last week" is a simple WHERE clause

JSONB would require `jsonb_array_elements()` for queries, cannot be indexed per-event, and makes correlation_id lookups expensive at scale.

### 3. Milestone Weight Storage: JSONB on StageConfig (RECOMMENDED)

**Rationale:** Store milestone weights as a JSONB column on a per-project-stage configuration record:

```python
# Example milestone_weights JSONB structure
{
    "brief_generated": {"weight": 30, "completed": false},
    "gate_passed": {"weight": 20, "completed": false},
    "build_ready": {"weight": 50, "completed": false}
}
```

This allows:
- Template defaults loaded from a static dict per stage
- Per-project customization by updating the JSONB
- Adding/removing milestones without schema changes
- Progress computation: `sum(w for w in weights if completed) / sum(all_weights) * 100`

### 4. Global Progress: Weighted by Stage Milestone Count (RECOMMENDED)

**Rationale:** Each stage's contribution to global progress should be proportional to its total milestone weight, not equal (1/5 each). This ensures stages with more work contribute more to overall progress.

```python
# Example: Stage 1 has 100 total weight, Stage 2 has 150, etc.
# Global = sum(stage_progress * stage_total_weight) / sum(all_stage_total_weights)
```

This naturally handles the fact that Stage 3 (MVP Built) involves far more work than Stage 1 (Thesis Defined). Equal weighting would make the progress bar jump unevenly.

## Architecture Patterns

### Recommended Project Structure
```
backend/app/
├── domain/                    # NEW: Pure domain logic (no DB, no API)
│   ├── __init__.py
│   ├── stages.py             # Stage enum, StageConfig, transition rules
│   ├── progress.py           # Deterministic progress computation
│   ├── gates.py              # Decision gate logic
│   └── risks.py              # Risk detection rules
├── db/
│   ├── models/
│   │   ├── project.py        # MODIFIED: Add stage_number, stage_status, etc.
│   │   ├── stage_config.py   # NEW: Per-project stage configuration
│   │   ├── decision_gate.py  # NEW: Decision gate records
│   │   ├── stage_event.py    # NEW: Timeline/observability events
│   │   └── milestone.py      # NEW: Milestone completion tracking
│   └── ...
└── services/                  # NEW: Orchestration layer (uses domain + db)
    ├── __init__.py
    └── journey.py            # NEW: JourneyService coordinates domain + persistence
```

### Pattern 1: Domain Logic Separation
**What:** All state machine rules, progress computation, and validation live in `app/domain/` as pure functions with no database or I/O dependencies.
**When to use:** Always. This is the core testability pattern.
**Why:** Pure functions are trivially testable without fixtures, mocks, or databases. The service layer orchestrates persistence.

```python
# app/domain/stages.py
from enum import Enum

class Stage(int, Enum):
    """Five-stage startup journey. Values are ordinal for comparison."""
    PRE_STAGE = 0
    THESIS_DEFINED = 1
    VALIDATED_DIRECTION = 2
    MVP_BUILT = 3
    FEEDBACK_LOOP_ACTIVE = 4
    SCALE_AND_OPTIMIZE = 5  # Locked in MVP

class ProjectStatus(str, Enum):
    """Project lifecycle status, orthogonal to stage."""
    ACTIVE = "active"
    PARKED = "parked"

class TransitionResult:
    """Result of a transition attempt."""
    def __init__(self, allowed: bool, reason: str = "", new_stage: Stage | None = None):
        self.allowed = allowed
        self.reason = reason
        self.new_stage = new_stage

def validate_transition(
    current_stage: Stage,
    target_stage: Stage,
    current_status: ProjectStatus,
    gate_decisions: list[dict],
) -> TransitionResult:
    """Validate whether a stage transition is allowed.

    Pure function -- no side effects, no DB access.
    """
    if current_status == ProjectStatus.PARKED:
        return TransitionResult(False, "Cannot transition while parked")

    if target_stage == Stage.SCALE_AND_OPTIMIZE:
        return TransitionResult(False, "Stage 5 is locked in MVP")

    if target_stage == Stage.PRE_STAGE:
        return TransitionResult(False, "Cannot return to pre-stage")

    # Forward transitions require gate decision
    if target_stage.value > current_stage.value:
        if not any(g.get("decision") == "proceed" for g in gate_decisions):
            return TransitionResult(False, "Forward transition requires gate decision")

    # Backward transitions (pivot) are always allowed
    return TransitionResult(True, new_stage=target_stage)
```

### Pattern 2: Deterministic Progress Computation
**What:** Progress is a pure function of milestone completion state, never stored directly.
**When to use:** Every time progress needs to be displayed or compared.

```python
# app/domain/progress.py
def compute_stage_progress(milestones: dict[str, dict]) -> int:
    """Compute stage progress (0-100) from milestone weights.

    Args:
        milestones: {"milestone_key": {"weight": int, "completed": bool}}

    Returns:
        Integer percentage 0-100

    Pure function -- deterministic, no side effects.
    """
    total_weight = sum(m["weight"] for m in milestones.values())
    if total_weight == 0:
        return 0
    completed_weight = sum(
        m["weight"] for m in milestones.values() if m["completed"]
    )
    return int((completed_weight / total_weight) * 100)


def compute_global_progress(stages: list[dict]) -> int:
    """Compute overall journey progress from all stages.

    Args:
        stages: [{"stage": Stage, "milestones": {...}, "progress": int}]

    Returns:
        Integer percentage 0-100

    Uses weighted average where each stage weight = sum of its milestone weights.
    """
    total_weight = 0
    weighted_progress = 0
    for stage_data in stages:
        stage_total = sum(m["weight"] for m in stage_data["milestones"].values())
        total_weight += stage_total
        weighted_progress += stage_data["progress"] * stage_total
    if total_weight == 0:
        return 0
    return int(weighted_progress / total_weight)
```

### Pattern 3: Event Sourcing Lite (Timeline Table)
**What:** Every state change is recorded as an immutable event in `stage_events`.
**When to use:** All transitions, gate decisions, milestone completions, risk changes.

```python
# app/db/models/stage_event.py
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from app.db.base import Base

class StageEvent(Base):
    __tablename__ = "stage_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False, index=True)
    correlation_id = Column(UUID(as_uuid=True), nullable=False, default=uuid.uuid4, index=True)

    event_type = Column(String(50), nullable=False)  # transition, gate_decision, milestone, risk_change
    from_stage = Column(String(50), nullable=True)    # null for initial events
    to_stage = Column(String(50), nullable=True)
    actor = Column(String(50), nullable=False)         # "system", "founder", "llm"
    detail = Column(JSONB, nullable=False, default=dict)  # event-specific payload
    reason = Column(Text, nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )
```

### Pattern 4: Template + Dynamic Exit Criteria
**What:** Each stage has a base template of required exit criteria, plus the ability to add project-specific criteria dynamically.
**When to use:** Stage configuration initialization and narrowing/pivot operations.

```python
# Default templates -- loaded once per stage at project creation
STAGE_TEMPLATES: dict[int, dict] = {
    1: {  # Thesis Defined
        "milestones": {
            "brief_generated": {"weight": 40, "completed": False, "template": True},
            "gate_proceed": {"weight": 30, "completed": False, "template": True},
            "risks_identified": {"weight": 30, "completed": False, "template": True},
        }
    },
    2: {  # Validated Direction
        "milestones": {
            "direction_chosen": {"weight": 25, "completed": False, "template": True},
            "validation_complete": {"weight": 35, "completed": False, "template": True},
            "scope_narrowed": {"weight": 20, "completed": False, "template": True},
            "gate_proceed": {"weight": 20, "completed": False, "template": True},
        }
    },
    # ... stages 3-5
}
```

### Anti-Patterns to Avoid
- **Storing computed progress in DB**: Progress must be computed from milestones, never cached in a column that can drift from reality. The `progress_percent` column on the Project model (from requirements) should be a computed property or recomputed on every read.
- **Using ORM events for FSM transitions**: SQLAlchemy `before_update` hooks create hidden coupling. Transition logic must be explicit in the service layer.
- **Mixing domain logic with persistence**: The `validate_transition()` function must never import SQLAlchemy. Domain logic and DB models stay in separate layers.
- **Auto-incrementing stage on artifact completion**: Stages transition ONLY via explicit decision gates, never automatically. Even if all exit criteria are met, the founder must choose "Proceed."

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| UUID generation | Custom ID schemes | `uuid.uuid4()` stdlib | Standard, no collisions, PostgreSQL native |
| Timezone handling | Manual UTC conversion | `datetime.now(timezone.utc)` | Phase 1 already fixed this pattern project-wide |
| JSON validation | Manual dict checking | Pydantic models for gate decisions | Type safety, automatic validation, serialization |
| Enum-to-DB mapping | String columns with manual checks | Python `Enum` + SQLAlchemy `Enum()` type | DB-level constraint, type safety in Python |
| Database migrations | `Base.metadata.create_all` (current) | Alembic | Reversible migrations, production-safe schema changes |

**Key insight:** The project currently uses `Base.metadata.create_all` which is fine for development but will break in production when schemas need to evolve. Phase 2 adds significant new tables and should set up Alembic properly. However, this is a structural concern -- the core FSM logic does not depend on the migration tool.

## Common Pitfalls

### Pitfall 1: Progress Stored as Denormalized Column
**What goes wrong:** Storing `progress_percent` in the projects table and updating it on every milestone change. It drifts when events are missed, pivot doesn't reset it, or concurrent updates race.
**Why it happens:** Seems simpler than computing on read.
**How to avoid:** Compute progress from milestone state every time. If performance matters, use a materialized view or cache with explicit invalidation.
**Warning signs:** Tests that assert progress after setting a column value instead of completing milestones.

### Pitfall 2: Transition Validation in the Wrong Layer
**What goes wrong:** Putting transition rules inside SQLAlchemy model methods or ORM event hooks. Tests then require database fixtures, are slow, and miss edge cases.
**Why it happens:** It feels natural to put `can_transition()` on the model.
**How to avoid:** Domain logic in `app/domain/`, service orchestration in `app/services/`, models are data containers only.
**Warning signs:** Model methods that import from services or call other models.

### Pitfall 3: PostgreSQL Enum Migration Pain
**What goes wrong:** Using `sqlalchemy.Enum` mapped to PostgreSQL native ENUM type. Adding a new enum value requires `ALTER TYPE ... ADD VALUE` which is not transactional in PostgreSQL (cannot be rolled back).
**Why it happens:** SQLAlchemy defaults to native PG enum types.
**How to avoid:** Use `String(50)` for columns that might change (like `event_type`), and native PostgreSQL ENUM only for truly fixed enums (Stage is unlikely to change). For Stage, use an integer column mapping to the Python enum's int value.
**Warning signs:** Alembic migration that uses `op.execute("ALTER TYPE ... ADD VALUE")`.

### Pitfall 4: Concurrent Gate Decisions
**What goes wrong:** Two users (or system + user) submit conflicting gate decisions simultaneously. Both read the project as "pending," both write a decision, one is lost.
**Why it happens:** No optimistic or pessimistic locking on gate records.
**How to avoid:** Use `SELECT ... FOR UPDATE` on the gate record before writing a decision, or use an optimistic concurrency check (version column).
**Warning signs:** Tests that never test concurrent access paths.

### Pitfall 5: Parked State Leaking Into Stage Logic
**What goes wrong:** Treating "Parked" as stage 0 or stage 6. Parked projects still have a stage -- they just aren't progressing. When unparked, they resume at their previous stage.
**Why it happens:** Conflating "current position in journey" with "is the journey active."
**How to avoid:** Model Parked as a `ProjectStatus` orthogonal to `Stage`. A parked project has `status=PARKED` and `stage=THESIS_DEFINED` (its stage when parked). Unpark restores `status=ACTIVE`.
**Warning signs:** Code that checks `stage == PARKED` instead of `status == PARKED`.

### Pitfall 6: Narrowing Without Criteria Reset
**What goes wrong:** Founder narrows scope, but exit criteria from the broader scope remain completed. Progress shows 80% when the new scope is actually 20% done.
**Why it happens:** Only adding new criteria without re-evaluating existing ones.
**How to avoid:** When narrowing occurs, mark affected milestones as `completed: False` and log a `milestone_reset` event in the timeline. Progress computation automatically reflects the decrease.
**Warning signs:** Narrow operation that only adds criteria without touching existing ones.

## Code Examples

### Project Model Extensions

```python
# app/db/models/project.py -- MODIFIED
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from app.db.base import Base


class Project(Base):
    __tablename__ = "projects"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    clerk_user_id = Column(String(255), nullable=False, index=True)

    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=False, default="")
    github_repo = Column(String(255), nullable=True)

    # Journey state -- NEW
    status = Column(String(50), nullable=False, default="active")  # active, parked
    stage_number = Column(Integer, nullable=True, default=None)     # None = pre-stage
    stage_entered_at = Column(DateTime(timezone=True), nullable=True)

    # Computed fields stored for query convenience (recomputed, not source of truth)
    progress_percent = Column(Integer, nullable=False, default=0)

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
```

### Decision Gate Model

```python
# app/db/models/decision_gate.py -- NEW
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from app.db.base import Base


class DecisionGate(Base):
    __tablename__ = "decision_gates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False, index=True)

    gate_type = Column(String(50), nullable=False)  # "stage_advance", "direction", "build_path"
    stage_number = Column(Integer, nullable=False)   # Which stage this gate belongs to
    status = Column(String(50), nullable=False, default="pending")  # pending, decided, expired

    # Decision details (filled when decided)
    decision = Column(String(50), nullable=True)     # "proceed", "pivot", "narrow", "park"
    decided_by = Column(String(50), nullable=True)   # "founder" or "system"
    decided_at = Column(DateTime(timezone=True), nullable=True)
    reason = Column(Text, nullable=True)

    # Context for the gate (what's being decided)
    context = Column(JSONB, nullable=False, default=dict)

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
```

### Stage Configuration Model

```python
# app/db/models/stage_config.py -- NEW
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from app.db.base import Base


class StageConfig(Base):
    __tablename__ = "stage_configs"
    __table_args__ = (
        UniqueConstraint("project_id", "stage_number", name="uq_project_stage"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id"), nullable=False, index=True)
    stage_number = Column(Integer, nullable=False)

    # Milestones with weights: {"key": {"weight": int, "completed": bool, "template": bool}}
    milestones = Column(JSONB, nullable=False, default=dict)

    # Exit criteria: ["criterion text 1", "criterion text 2"]
    exit_criteria = Column(JSONB, nullable=False, default=list)

    # Blocking risks: [{"type": "system"|"llm", "message": str, "dismissed": bool}]
    blocking_risks = Column(JSONB, nullable=False, default=list)

    # LLM-generated suggested focus
    suggested_focus = Column(JSONB, nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
```

### Risk Detection (System Rules)

```python
# app/domain/risks.py
from datetime import datetime, timezone, timedelta


def detect_system_risks(
    project_created_at: datetime,
    last_gate_decision_at: datetime | None,
    build_failure_count: int,
    last_activity_at: datetime,
) -> list[dict]:
    """Detect blocking risks based on system-defined rules.

    Pure function -- no DB, no LLM, deterministic.

    Returns:
        List of risk dicts: [{"type": "system", "rule": str, "message": str}]
    """
    now = datetime.now(timezone.utc)
    risks = []

    # Rule: No decision in 7 days
    if last_gate_decision_at:
        days_since_decision = (now - last_gate_decision_at).days
        if days_since_decision >= 7:
            risks.append({
                "type": "system",
                "rule": "stale_decision",
                "message": f"No gate decision in {days_since_decision} days",
            })

    # Rule: Build failed 3+ times
    if build_failure_count >= 3:
        risks.append({
            "type": "system",
            "rule": "build_failures",
            "message": f"Build has failed {build_failure_count} times consecutively",
        })

    # Rule: Stale project (no activity in 14 days)
    days_inactive = (now - last_activity_at).days
    if days_inactive >= 14:
        risks.append({
            "type": "system",
            "rule": "stale_project",
            "message": f"No project activity in {days_inactive} days",
        })

    return risks
```

### Testing Pattern: Pure Domain Functions

```python
# tests/domain/test_progress.py
from app.domain.progress import compute_stage_progress, compute_global_progress


def test_empty_milestones_returns_zero():
    assert compute_stage_progress({}) == 0


def test_no_milestones_completed():
    milestones = {
        "brief": {"weight": 40, "completed": False},
        "gate": {"weight": 60, "completed": False},
    }
    assert compute_stage_progress(milestones) == 0


def test_all_milestones_completed():
    milestones = {
        "brief": {"weight": 40, "completed": True},
        "gate": {"weight": 60, "completed": True},
    }
    assert compute_stage_progress(milestones) == 100


def test_partial_completion():
    milestones = {
        "brief": {"weight": 30, "completed": True},
        "gate": {"weight": 20, "completed": False},
        "build": {"weight": 50, "completed": False},
    }
    assert compute_stage_progress(milestones) == 30


def test_progress_decreases_after_reset():
    """Simulating a pivot: milestone was completed, now reset."""
    before = {"brief": {"weight": 40, "completed": True}, "gate": {"weight": 60, "completed": True}}
    after = {"brief": {"weight": 40, "completed": False}, "gate": {"weight": 60, "completed": True}}
    assert compute_stage_progress(before) == 100
    assert compute_stage_progress(after) == 60
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `sqlalchemy-fsm` for ORM-integrated FSM | Custom domain logic + service layer | 2022 (lib abandoned) | Must build own transition logic |
| `datetime.utcnow()` | `datetime.now(timezone.utc)` | Python 3.12 deprecation | Already fixed in Phase 1 |
| `Base.metadata.create_all` | Alembic migrations | Best practice always | Project needs migration setup |
| SQLAlchemy 1.x `Column()` style | SQLAlchemy 2.0 `Mapped[]` style | 2023 | Project uses Column() style, keep consistent |

**Deprecated/outdated:**
- `sqlalchemy-fsm`: Last release Aug 2022, does not support async SQLAlchemy 2.0. Do not use.
- `datetime.utcnow()`: Deprecated in Python 3.12, already fixed in Phase 1.

**Note on SQLAlchemy style:** The existing codebase uses the `Column()` declarative style (SQLAlchemy 1.x compatible). While SQLAlchemy 2.0 introduced `Mapped[]` annotations, the existing models use `Column()`. For consistency, new models should continue using `Column()` style. Migrating to `Mapped[]` is out of scope.

## Open Questions

1. **Alembic Setup Timing**
   - What we know: Alembic is a dependency but has no `alembic.ini` or `migrations/` directory. The project uses `create_all` for table creation.
   - What's unclear: Should Phase 2 initialize Alembic, or should that be a prerequisite? Adding 4-5 new tables is the right time to set up proper migrations.
   - Recommendation: Initialize Alembic as the first task of Phase 2. Create an initial migration that captures all existing tables, then add migrations for new tables. This is a one-time setup cost that pays dividends immediately.

2. **LLM-Assessed Risks and Suggested Focus**
   - What we know: System rules are deterministic and testable. LLM assessment requires the Runner.
   - What's unclear: Should Phase 2 implement LLM risk assessment, or just the system rules with an extension point for LLM?
   - Recommendation: Implement system rules fully. Create the data model and service interface for LLM risks, but defer the actual LLM integration to a later phase. The `blocking_risks` JSONB structure supports both types. Mark the LLM risk service method as a stub that returns empty list.

3. **Existing `status` Column on Project**
   - What we know: Project model already has `status = Column(String(50), default="active")`. This overlaps with the new `ProjectStatus` enum.
   - What's unclear: Is any code currently depending on specific status values?
   - Recommendation: Audit usages of `Project.status`, then extend the column to support "active" and "parked" values. Do not create a separate column -- reuse the existing one.

## Sources

### Primary (HIGH confidence)
- Existing codebase: `backend/app/db/models/project.py`, `backend/app/db/base.py`, `backend/app/agent/runner.py` -- read directly
- Existing codebase: `backend/pyproject.toml` -- dependency versions verified
- Existing codebase: `backend/tests/` -- test patterns and conftest verified
- [SQLAlchemy 2.0 docs](https://docs.sqlalchemy.org/en/21/) -- async engine, JSONB, Enum support

### Secondary (MEDIUM confidence)
- [pytransitions/transitions GitHub](https://github.com/pytransitions/transitions) -- v0.9.3, AsyncMachine capabilities verified
- [transitions on PyPI](https://pypi.org/project/transitions/) -- release date July 2, 2025 verified
- [presslabs/sqlalchemy-fsm GitHub](https://github.com/presslabs/sqlalchemy-fsm) -- last release Aug 2022, confirmed unmaintained
- [PostgreSQL Enum migration patterns](https://roman.pt/posts/alembic-enums/) -- ALTER TYPE limitations verified

### Tertiary (LOW confidence)
- Weighted milestone method concept from [project-management-knowledge.com](https://project-management-knowledge.com/definitions/w/weighted-milestone-method/) -- general pattern, adapted for our use case
- Event sourcing patterns from [breadcrumbscollector.tech](https://breadcrumbscollector.tech/implementing-event-sourcing-in-python-part-2-robust-event-store-atop-postgresql/) -- informing timeline table design

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all libraries already in project, versions verified from pyproject.toml
- Architecture: HIGH -- patterns derived from existing codebase conventions, domain logic separation is well-established
- FSM library decision: HIGH -- transitions library verified, sqlalchemy-fsm confirmed dead, custom FSM is right choice for 6-state machine
- Event storage decision: HIGH -- timeline table vs JSONB is well-understood tradeoff
- Progress computation: HIGH -- pure math, trivially testable
- Pitfalls: MEDIUM -- concurrent gate decisions need validation during implementation
- LLM risk integration: LOW -- deferred, interface defined but implementation details unclear

**Research date:** 2026-02-16
**Valid until:** 2026-03-16 (stable domain, no fast-moving dependencies)
