# Phase 10: Export, Deploy Readiness & E2E Testing - Research

**Researched:** 2026-02-17
**Domain:** Generation loop orchestration, E2B sandbox preview URLs, build versioning, Solidification Gate 2, iteration/Change Request flow, deploy readiness, beta gating, response contracts, chat floating widget, E2E pytest flow
**Confidence:** HIGH

## Summary

Phase 10 is the closing loop of the founder journey — it wires the generation pipeline (already stubbed in the worker) to real LangGraph execution, provisions E2B sandbox previews, adds build versioning, implements Solidification Gate 2 with scope creep detection, handles iteration Change Requests, provides deploy readiness assessment, and validates the entire flow with E2E tests.

The core technical challenge is threefold: (1) connecting the existing `JobStateMachine` + `process_next_job` worker (which already transitions through SCAFFOLD/CODE/DEPS/CHECKS/READY states) to the real LangGraph pipeline and persisting workspace files to E2B sandbox; (2) building Solidification Gate 2 as a second `DecisionGate` record using the existing `GateService` pattern, with alignment scoring computed as a pure domain function; (3) creating a meaningful E2E test that exercises the full founder flow (idea → brief → plan → build → preview) using `RunnerFake` so it runs in CI without calling Anthropic.

The existing codebase already has all the plumbing in place: `JobStateMachine` FSM with 8 states, `E2BSandboxRuntime` with `get_host(port)` returning `https://{port}-{sandbox_id}.e2b.app`, `require_feature` dependency for beta gating, `GateService` DI pattern, `IterationTracker`, `DashboardService` (with `product_version` and `mvp_completion_percent` stubs), and `TimelineService`. Phase 10 primarily wires these pieces together, adds new domain logic (alignment scoring, deploy readiness rules), and builds the floating chat widget as an ephemeral overlay component.

**Primary recommendation:** Extend `process_next_job` to accept a `workspace_files` output from `RunnerReal.run()`, write to E2B sandbox, persist `sandbox_id` + `preview_url` to the `Job` DB record (requires new columns), and expose via dashboard. Gate 2 reuses the `GateService` create/resolve pattern with a `gate_type="solidification"`. Chat widget is a standalone `FloatingChat` React component rendered in the dashboard layout — no new library needed.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### Build progress & failure
- Step-by-step progress bar with named stages (Scaffolding… Writing code… Installing deps… Running checks…) — no raw terminal output
- On failure: friendly summary with retry button ("We hit an issue with dependency installation. Want us to try again?") — no technical details unless founder expands
- Build cancellation supported with confirmation dialog — stops agent and cleans up partial work
- On success: quick summary of what was built (files, features, stack) with preview link below — context before clicking

#### Post-MVP decision flow
- Solidification Gate 2 auto-prompts after the founder visits the preview ("You've seen your MVP. Ready to decide what's next?")
- Iteration change requests use conversational input — short back-and-forth with the AI to clarify the change before submitting, like talking to a co-founder
- Scope creep shown as visual alignment score (e.g., 85% aligned with original plan) — quantifies drift without blocking
- Iteration depth visible with tier limit: "Iteration 2 of 5 (Partner tier)" — makes remaining iterations clear and ties to subscription

#### Deploy readiness & launch
- Traffic light summary (Green/Yellow/Red) for overall deploy status with expandable details on demand
- 2-3 deploy path options with tradeoffs (e.g., Vercel: free/easy, AWS: scalable/complex, Railway: balanced) — founder picks
- Instructions only for MVP — no one-click deploy automation, provide clear step-by-step guide for chosen path
- Blocking issues show specific actionable guidance: "Add STRIPE_KEY to your environment variables" — copy-pasteable instructions per blocker

#### Chat integration
- Floating chat button in bottom-right corner (like Intercom/Crisp) — overlays any page, always accessible
- Chat can answer questions AND trigger actions (kick off builds, navigate to pages, submit change requests) — a command interface
- Full project context awareness — chat knows current project state, artifacts, decisions ("What's blocking my deploy?" works)
- Ephemeral conversations — no persistence across sessions, decisions live in artifacts not chat history

### Claude's Discretion
- Loading skeleton/animation design during build stages
- Exact alignment score calculation methodology
- Chat action routing implementation (how chat commands map to platform actions)
- Beta gating middleware approach
- Response contract validation strategy
- E2E test scenario design and coverage

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope
</user_constraints>

## Standard Stack

### Core Backend
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI BackgroundTasks | built-in | Async job worker dispatch | Already used in `jobs.py` — no new infra needed for MVP |
| e2b-code-interpreter | 2.4.1 (installed) | Sandbox create/file-write/run/get_host | Already installed and working in `e2b_runtime.py` |
| SQLAlchemy asyncpg | 2.0.x (installed) | Job model + new columns (sandbox_id, preview_url, build_version) | Existing pattern |
| Alembic | 1.13.x (installed) | DB migration for new Job columns | Existing migration pattern (8 existing migrations) |
| Pydantic v2 | 2.10+ | Response contract schemas | Project-wide standard |
| redis[asyncio] | 5.2.x (installed) | Job state machine pub/sub | Existing infrastructure |
| pytest + fakeredis | 8.3.x / 2.26.x (installed) | E2E test using RunnerFake | Existing test pattern |

### Core Frontend
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| React useState/useRef | built-in (React 19) | Floating chat local state (ephemeral) | No external state needed — conversations are ephemeral |
| framer-motion | 12.x (installed) | Build progress stage transitions, chat panel open/close | Already installed |
| lucide-react | 0.400.x (installed) | MessageCircle icon for chat bubble | Already installed |
| Clerk useAuth | 6.x (installed) | Auth token for chat API calls | Existing pattern |
| sonner | 2.x (installed) | Toast notifications for build events | Already installed |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| shadcn/ui Dialog | via existing patterns | Cancellation confirm dialog, Gate 2 modal | Use existing modal pattern |
| Tailwind CSS | 4.x (installed) | Traffic light colors, progress bar stages | Existing styling system |

### No New Dependencies Required
Phase 10 intentionally uses only what is already installed. The floating chat widget is built from React primitives + Tailwind. Build progress uses React state + framer-motion. No new npm packages are needed.

**Installation:**
```bash
# No new packages needed — everything already installed
```

## Architecture Patterns

### Recommended Project Structure

New files to create:
```
backend/app/
├── api/routes/
│   ├── generation.py          # POST /generation/start, GET /generation/{job_id}/status
│   ├── deploy_readiness.py    # GET /deploy-readiness/{project_id}
│   └── change_requests.py     # POST /change-requests (iteration loop)
├── services/
│   ├── generation_service.py  # Wires worker → E2B → build versioning
│   ├── deploy_readiness_service.py
│   └── change_request_service.py
├── domain/
│   ├── alignment.py           # Pure function: compute_alignment_score(original_scope, change_request)
│   └── deploy_checks.py       # Pure functions: check_env_vars, check_readme, etc.
└── db/models/
    └── change_request.py      # ChangeRequest artifact record

frontend/src/components/
├── build/
│   ├── BuildProgressBar.tsx   # Named stage progress (Scaffolding → Writing code → ...)
│   ├── BuildSummary.tsx       # Success: files/features/stack + preview link
│   └── BuildFailureCard.tsx   # Friendly error + retry button + expandable details
├── chat/
│   └── FloatingChat.tsx       # Fixed bottom-right chat bubble + panel
└── deploy/
    ├── DeployReadinessPanel.tsx  # Traffic light + expandable + path options
    └── DeployPathCard.tsx     # Individual deploy option card with tradeoffs

tests/e2e/
└── test_founder_flow.py       # Full E2E: idea → brief → plan → build → preview
```

### Pattern 1: Generation Loop Orchestration (GENR-01 through GENR-07)

**What:** The existing `process_next_job` in `worker.py` already has the full FSM transition sequence (SCAFFOLD → CODE → DEPS → CHECKS → READY) but only simulates it. Phase 10 replaces the simulation with real execution via `RunnerReal`, writes output files to E2B sandbox, and persists the sandbox_id + preview_url back to the Job record.

**The `Job` DB model needs new columns:**
```python
# backend/app/db/models/job.py — add these columns
sandbox_id = Column(String(255), nullable=True)      # E2B sandbox ID for reconnection
preview_url = Column(Text, nullable=True)             # https://{port}-{sandbox_id}.e2b.app
build_version = Column(String(50), nullable=True)     # "build_v0_1", "build_v0_2"
workspace_path = Column(String(500), nullable=True)   # /home/user/project path in sandbox
```

**Updated worker flow:**
```python
# backend/app/queue/worker.py — replace the simulated loop with:
async def _execute_job_with_e2b(job_id, job_data, state_machine, user_sem, project_sem, runner):
    """Execute job: scaffold → code → deps → checks → provision E2B → ready."""
    from app.sandbox.e2b_runtime import E2BSandboxRuntime
    from app.agent.state import create_initial_state

    # Transition to STARTING
    await state_machine.transition(job_id, JobStatus.STARTING, "Starting job execution")

    # Scaffold stage
    await state_machine.transition(job_id, JobStatus.SCAFFOLD, "Scaffolding workspace...")
    state = create_initial_state(
        user_id=job_data["user_id"],
        project_id=job_data["project_id"],
        project_path=f"/home/user/project",
        goal=job_data["goal"],
        session_id=job_id,
    )

    # Code stage — invoke LangGraph pipeline
    await state_machine.transition(job_id, JobStatus.CODE, "Writing code...")
    final_state = await runner.run(state)

    # Deps stage — provision E2B sandbox, write files
    await state_machine.transition(job_id, JobStatus.DEPS, "Installing dependencies...")
    runtime = E2BSandboxRuntime(template="base")
    await runtime.start()

    for path, file_change in final_state.get("working_files", {}).items():
        await runtime.write_file(path, file_change["new_content"])

    # Install deps if requirements.txt / package.json present
    await runtime.run_command("pip install -r requirements.txt 2>/dev/null || npm install 2>/dev/null || true")

    # Checks stage — run basic health check
    await state_machine.transition(job_id, JobStatus.CHECKS, "Running checks...")
    check_result = await runtime.run_command("python -c 'import sys; sys.exit(0)' || node -e 'process.exit(0)'")

    # Start the app on port 8080, get preview URL
    await runtime.run_background("python main.py || npm start", cwd="/home/user/project")
    preview_host = runtime._sandbox.get_host(8080)
    preview_url = f"https://{preview_host}"
    sandbox_id = runtime._sandbox.sandbox_id

    # Determine build version
    build_version = await _get_next_build_version(job_data["project_id"])

    # Persist preview_url + sandbox_id + build_version to Job record
    await _persist_sandbox_info(job_id, sandbox_id, preview_url, build_version)

    # Ready
    await state_machine.transition(job_id, JobStatus.READY, f"Build {build_version} ready")
```

**Key insight:** E2B sandbox `get_host(port)` returns `{port}-{sandbox_id}.{sandbox_domain}` and the preview URL is simply `https://{port}-{sandbox_id}.e2b.app`. The sandbox_id must be stored in the Job record so it can be reconnected via `Sandbox.connect(sandbox_id)` for future iteration builds.

### Pattern 2: Build Versioning (GENR-05, GENR-07)

**What:** Each completed build creates a version tag stored on the Job record and as an artifact. The first build is `build_v0_1`, iterations increment the minor version.

**Idempotency:** When a new build starts for a project, the existing sandbox_id is retrieved, `Sandbox.connect(sandbox_id)` reconnects to the running sandbox, and files are patched — not replaced wholesale. If reconnect fails (sandbox expired), a new sandbox is created and re-runs from scratch.

```python
async def _get_next_build_version(project_id: str) -> str:
    """Determine next build version for a project.

    Queries Job table for highest build_version for this project, increments minor version.
    First build: build_v0_1. Second: build_v0_2, etc.
    """
    from app.db.base import get_session_factory
    from app.db.models.job import Job
    from sqlalchemy import select, and_

    factory = get_session_factory()
    async with factory() as session:
        result = await session.execute(
            select(Job.build_version)
            .where(and_(
                Job.project_id == uuid.UUID(project_id),
                Job.build_version.isnot(None),
                Job.status == "ready"
            ))
            .order_by(Job.created_at.desc())
            .limit(1)
        )
        last_version = result.scalar_one_or_none()

    if last_version is None:
        return "build_v0_1"

    # Parse "build_v0_1" → increment minor
    parts = last_version.replace("build_v", "").split("_")
    major, minor = int(parts[0]), int(parts[1])
    return f"build_v{major}_{minor + 1}"
```

### Pattern 3: MVP Built State Transition (MVPS-01 through MVPS-04)

**What:** When `build_v0_1` becomes READY, the project's `stage_number` transitions to a new "MVP Built" stage. This hooks into the existing `JourneyService.transition_stage()` pattern.

**Implementation:** A `post_build_hook` called at the end of `process_next_job` when status = READY and build_version = "build_v0_1":

```python
async def _handle_mvp_built_transition(job_id: str, project_id: str, preview_url: str):
    """Trigger MVP Built state when first build completes."""
    from app.services.journey import JourneyService
    from app.db.base import get_session_factory

    factory = get_session_factory()
    async with factory() as session:
        journey = JourneyService(session)
        # Transition project to stage 3 (Development/MVP Built)
        await journey.transition_stage(
            project_id=uuid.UUID(project_id),
            new_stage=3,
            reason="MVP build completed",
            context={"build_version": "build_v0_1", "preview_url": preview_url}
        )
        # Write MVP timeline event
        await journey.log_event(
            project_id=uuid.UUID(project_id),
            event_type="mvp_built",
            description="First MVP build completed and preview deployed",
            metadata={"preview_url": preview_url, "build_version": "build_v0_1"}
        )
```

### Pattern 4: Solidification Gate 2 (SOLD-01 through SOLD-03)

**What:** Gate 2 is a second `DecisionGate` record with `gate_type="solidification"`. It auto-triggers after the founder views the preview (API call from frontend when preview iframe is first rendered). Gate output includes an alignment score.

**Alignment score** is a pure domain function in `backend/app/domain/alignment.py`:

```python
def compute_alignment_score(
    original_scope: dict,  # From MVP Scope artifact
    requested_changes: list[dict]  # From change request history
) -> int:
    """Compute alignment score (0-100) between current iteration and original MVP scope.

    Algorithm (Claude's discretion — recommended approach):
    1. Extract key features from original MVP scope core_features list
    2. For each requested change, check if it references an existing feature (aligned)
       vs introduces a wholly new capability (scope creep)
    3. Score = (aligned_changes / total_changes) * 100
    4. First build (no changes) = 100

    Returns:
        Integer 0-100. 80+ = Green, 60-79 = Yellow, < 60 = Red (scope creep warning)
    """
    if not requested_changes:
        return 100

    original_features = set(f["name"].lower() for f in original_scope.get("core_features", []))
    aligned = sum(
        1 for change in requested_changes
        if any(feat in change.get("description", "").lower() for feat in original_features)
    )
    return int((aligned / len(requested_changes)) * 100)
```

**Gate 2 creation:** The frontend calls `POST /api/gates` with `gate_type="solidification"` after the preview URL is first viewed. The `GateService.create_gate()` already handles idempotency (409 if pending gate exists).

**Gate 2 options** (different from Gate 1 which has proceed/narrow/pivot/park):
- `"iterate"` — submit a Change Request for the next iteration
- `"ship"` — proceed to deploy readiness assessment
- `"park"` — pause the project

### Pattern 5: Iteration Plan and Change Request (ITER-01 through ITER-03, GENL-01 through GENL-06)

**What:** After Gate 2 is resolved with `"iterate"`, a Change Request artifact is created. This is a new `Artifact` record with `artifact_type="change_request"`.

**Change Request artifact schema:**
```python
# Stored in Artifact.current_content as JSONB
{
    "_schema_version": 1,
    "change_description": "Add user profile page with avatar upload",
    "clarified_description": "...",  # After AI back-and-forth clarification
    "references_build_version": "build_v0_1",
    "goal_reference": "Enhancement to existing User Management feature",
    "iteration_number": 2,
    "tier_limit": 5,  # From TIER_ITERATION_DEPTH
    "alignment_score": 85,  # From compute_alignment_score()
    "scope_creep_detected": False,
    "created_at": "2026-02-17T..."
}
```

**Conversational clarification flow:** The frontend sends the change request to `POST /api/agent/clarify` which uses the existing streaming agent endpoint. The agent responds with clarifying questions (1-2 back-and-forth). Once the founder confirms, the Change Request artifact is created and a new generation job is submitted.

**Patch strategy:** For v0.2 builds, the worker fetches the existing `sandbox_id` from the previous job, reconnects via `Sandbox.connect(sandbox_id)`, and applies the patch on top of the existing workspace. If the sandbox has expired, it re-runs from scratch.

### Pattern 6: Deploy Readiness Assessment (DEPL-01 through DEPL-03)

**What:** `GET /api/deploy-readiness/{project_id}` returns a readiness assessment. This is a pure domain function driven by checking the workspace files in the E2B sandbox.

**Domain function structure** (`backend/app/domain/deploy_checks.py`):

```python
@dataclass
class DeployCheck:
    id: str
    title: str
    status: Literal["pass", "warn", "fail"]
    message: str
    fix_instruction: str | None = None  # Copy-pasteable if fail/warn

def run_deploy_checks(workspace_files: dict[str, str]) -> list[DeployCheck]:
    """Run deploy readiness checks on workspace files.

    Checks (in order):
    1. README.md exists
    2. .env.example exists (env vars documented)
    3. start script exists (package.json scripts.start or Makefile or Procfile)
    4. No hardcoded secrets (scan for API_KEY=, SECRET=, password= patterns)
    5. requirements.txt or package.json with dependencies pinned
    """
    ...
```

**Response shape:**
```python
class DeployReadinessResponse(BaseModel):
    project_id: str
    overall_status: Literal["green", "yellow", "red"]  # Traffic light
    ready: bool
    blocking_issues: list[DeployIssue]  # Only "fail" items
    warnings: list[DeployIssue]         # "warn" items
    recommended_path: str               # "vercel" | "railway" | "aws"
    deploy_paths: list[DeployPathOption]
```

**Deploy paths** are hardcoded option objects (no LLM needed):
```python
DEPLOY_PATHS = [
    DeployPathOption(
        id="vercel",
        name="Vercel",
        description="Free tier, instant deploy from GitHub, zero config for Next.js",
        difficulty="easy",
        cost="Free → $20/mo",
        tradeoffs=["Vendor lock-in for serverless", "No persistent processes"],
        steps=["Push to GitHub", "Import repo in Vercel", "Add env vars", "Deploy"]
    ),
    DeployPathOption(
        id="railway",
        name="Railway",
        description="Balanced — supports any stack, persistent processes, good free tier",
        difficulty="medium",
        cost="$5/mo → usage-based",
        tradeoffs=["Less free tier than Vercel", "Manual scaling"],
        steps=["Create Railway project", "Connect GitHub", "Add env vars", "railway up"]
    ),
    DeployPathOption(
        id="aws",
        name="AWS ECS",
        description="Production-grade, fully scalable, matches current infrastructure",
        difficulty="hard",
        cost="$50+/mo",
        tradeoffs=["Complex setup", "High cost for small apps"],
        steps=["Build Docker image", "Push to ECR", "Create ECS task", "Configure ALB"]
    ),
]
```

### Pattern 7: Beta Gating (BETA-01, BETA-02)

**What:** Non-MVP features return 403 unless beta enabled. The existing `require_feature(flag)` dependency in `backend/app/core/feature_flags.py` is the complete implementation — no new code needed.

**Usage:**
```python
# Example: Gate a new beta endpoint
@router.post("/generation/v2", dependencies=[Depends(require_feature("generation_v2"))])
async def start_generation_v2(...):
    ...
```

**BETA-02 (API exposes beta flags for UI labeling):** Already implemented via `GET /api/features` which returns `{"features": {"flag_name": True, ...}}`. The frontend fetches this on mount and labels beta features accordingly.

### Pattern 8: Response Contract Validation (CNTR-01, CNTR-02)

**What:** Ensure empty states return `[]` not `null`. This is enforced at the Pydantic model level using `default_factory`:

```python
class DashboardResponse(BaseModel):
    artifacts: list[ArtifactSummary] = Field(default_factory=list)  # Never null
    pending_decisions: list[PendingDecision] = Field(default_factory=list)
    risk_flags: list[RiskFlagResponse] = Field(default_factory=list)
```

**Contract tests:** A dedicated test file verifies response shapes remain stable:
```python
# tests/api/test_response_contracts.py
def test_dashboard_returns_empty_arrays_not_null(api_client, fake_project):
    """CNTR-02: Dashboard empty states return [] not null."""
    response = api_client.get(f"/api/dashboard/{fake_project.id}")
    data = response.json()
    assert isinstance(data["artifacts"], list)       # Never null
    assert isinstance(data["pending_decisions"], list)
    assert isinstance(data["risk_flags"], list)
```

### Pattern 9: Floating Chat Widget (CHAT-01, CHAT-02)

**What:** A `FloatingChat` component renders in the `DashboardLayout` as a fixed bottom-right overlay. It uses local React state for the conversation (ephemeral — cleared on page refresh). The chat can trigger actions via a simple intent dispatch system.

**Implementation pattern:**
```tsx
// frontend/src/components/chat/FloatingChat.tsx
"use client";
import { useState, useRef } from "react";
import { MessageCircle, X, Send } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  action?: ChatAction;  // Optional action to trigger
}

type ChatAction =
  | { type: "navigate"; path: string }
  | { type: "start_build"; project_id: string }
  | { type: "submit_change_request"; description: string };

export function FloatingChat({ projectId }: { projectId?: string }) {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const router = useRouter();

  const handleAction = (action: ChatAction) => {
    if (action.type === "navigate") router.push(action.path);
    if (action.type === "start_build") { /* dispatch build */ }
    if (action.type === "submit_change_request") { /* submit CR */ }
  };
  // ...
}
```

**Chat de-emphasis in nav (CHAT-02):** The existing `/chat` nav link in `brand-nav.tsx` is demoted — it stays in the nav but moves to the end of the list and uses a visually dimmer style (lower opacity, smaller font). The floating chat bubble becomes the primary chat entry point. The nav route link is kept for backwards compatibility but styled as secondary.

**Context awareness:** When the chat sends a message, it includes a `project_context` payload with current project state (stage, artifacts, build version, deploy status). This is fetched once when the chat panel opens.

### Pattern 10: E2E Founder Flow Test (Plan 10-10)

**What:** A single comprehensive test in `tests/e2e/test_founder_flow.py` that exercises the complete flow using `RunnerFake` and `FakeAsyncRedis`.

**Test sequence:**
```python
# tests/e2e/test_founder_flow.py
async def test_full_founder_flow(api_client, fake_redis, fake_db_session):
    """
    E2E: Complete founder flow from idea to preview.

    Steps:
    1. POST /api/onboarding/start — capture idea, get questions
    2. POST /api/onboarding/{session_id}/submit — submit answers
    3. POST /api/understanding/start — begin understanding interview
    4. POST /api/understanding/{session_id}/submit — submit understanding answers
    5. POST /api/understanding/{session_id}/generate-brief — generate idea brief artifact
    6. POST /api/gates (type=direction) — create Gate 1
    7. POST /api/gates/{gate_id}/resolve (decision=proceed) — resolve Gate 1
    8. POST /api/plans — generate execution plan options
    9. POST /api/plans/{plan_id}/select — select fast-mvp option
    10. POST /api/jobs — submit generation job
    11. (worker processes via RunnerFake + FakeSandboxRuntime)
    12. GET /api/jobs/{job_id} — verify status=ready, preview_url exists
    13. GET /api/dashboard/{project_id} — verify stage=3 (MVP Built), product_version=v0.1
    14. GET /api/timeline/{project_id} — verify MVP built entry exists
    15. Verify success criteria (GENR-01 through MVPS-04)
    """
```

**Key test double:** `FakeSandboxRuntime` that implements the `E2BSandboxRuntime` interface without calling E2B API:
```python
class FakeSandboxRuntime:
    """Test double for E2BSandboxRuntime."""
    def __init__(self):
        self.files = {}
        self.sandbox_id = "fake-sandbox-001"
        self._started = False

    async def start(self): self._started = True
    async def write_file(self, path, content): self.files[path] = content
    async def run_command(self, cmd, **kwargs): return {"stdout": "ok", "stderr": "", "exit_code": 0}
    async def run_background(self, cmd, **kwargs): return "fake-pid-001"

    class _FakeSandbox:
        sandbox_id = "fake-sandbox-001"
        def get_host(self, port): return f"{port}-fake-sandbox-001.e2b.app"

    @property
    def _sandbox(self): return self._FakeSandbox()
    async def stop(self): pass
```

### Anti-Patterns to Avoid

- **Don't call `runner.run()` synchronously in the FastAPI request handler.** The generation job MUST go through the queue + BackgroundTasks to avoid blocking the event loop. The worker process is where LangGraph runs.
- **Don't store E2B sandbox files in PostgreSQL.** The sandbox is the workspace. Only store `sandbox_id` and `preview_url` in the Job record.
- **Don't leave sandbox running indefinitely.** Set `timeout=3600` (1 hour) on sandbox creation. Extend with `set_timeout()` only when an iteration build starts.
- **Don't use None for empty response arrays.** All list fields in Pydantic models MUST use `default_factory=list`. Audit all existing response models.
- **Don't add Gate 2 as a new gate type that bypasses `GateService`.** Use `GateService.create_gate(gate_type="solidification")` — it already has idempotency and ownership checks.
- **Don't make the E2E test call real Anthropic or E2B APIs.** Use `RunnerFake` + `FakeSandboxRuntime` + `FakeAsyncRedis` for the E2E test.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Beta gating | Custom middleware | `require_feature(flag)` from `feature_flags.py` | Already implemented, handles admin bypass + per-user JSONB overrides |
| Job state machine | New state tracking | Existing `JobStateMachine` in `queue/state_machine.py` | 8-state FSM already tested and proven |
| Job SSE streaming | Custom pub/sub | Existing `stream_job_status` Redis pubsub in `jobs.py` | Already subscribes to `job:{job_id}:events` channel |
| Gate ownership checks | Manual queries | `GateService.create_gate()` + `GateService.resolve_gate()` | DI pattern with ownership checks already in place |
| Deploy path text | LLM generation | Hardcoded `DEPLOY_PATHS` constant | Options are stable, LLM adds latency and non-determinism |
| Iteration depth tracking | New counter | `IterationTracker` in `queue/state_machine.py` | Already handles tier-based limits, confirmation, hard cap |

**Key insight:** This phase is almost entirely integration and wiring, not new core infrastructure. The most novel net-new domain logic is: alignment score calculation, deploy readiness checks, and the floating chat widget.

## Common Pitfalls

### Pitfall 1: E2B Sandbox Expiry on Iteration Builds
**What goes wrong:** The previous build's sandbox expires (default 5 min) before the founder submits an iteration request. `Sandbox.connect(sandbox_id)` fails.
**Why it happens:** E2B sandboxes have a 5-minute default timeout. The founder may take 30+ minutes to review the preview and decide on changes.
**How to avoid:** When starting an iteration build, always attempt `Sandbox.connect(sandbox_id)` first. If it raises an exception, fall back to creating a new sandbox and running the full pipeline from scratch (not just the patch). Store the fallback behavior in the error message.
**Warning signs:** `SandboxError: Failed to connect to sandbox` in worker logs.

### Pitfall 2: Sandbox set_timeout() Not Called During Long Ops
**What goes wrong:** Worker starts E2B sandbox but the LangGraph pipeline takes > 5 minutes. Sandbox expires mid-build.
**Why it happens:** `E2BSandboxRuntime.start()` uses `Sandbox.create()` which defaults to 5-minute timeout. The heartbeat in `process_next_job` only extends Redis semaphores, not the E2B sandbox.
**How to avoid:** After `await runtime.start()`, immediately call `runtime._sandbox.set_timeout(3600)` to extend to 1 hour. Then call it again before each major stage.
**Warning signs:** `502 Timeout Error` from E2B during the DEPS or CHECKS stage.

### Pitfall 3: `process_next_job` Runs in FastAPI BackgroundTasks (Blocking Risk)
**What goes wrong:** LangGraph + E2B provisioning takes 2-5 minutes per job. If two jobs run concurrently in BackgroundTasks, they share the same event loop and can starve each other.
**Why it happens:** FastAPI `BackgroundTasks` runs in the same event loop as the request handler. Awaitable operations are cooperative but CPU-bound tasks (LangGraph model invocations) can still block.
**How to avoid:** Keep using BackgroundTasks for MVP (locked decision). Ensure all E2B calls use `run_in_executor` as they already do in `e2b_runtime.py`. LangGraph `ainvoke` is already async-native.
**Warning signs:** P95 response time for `GET /api/jobs/{id}` exceeds 5 seconds.

### Pitfall 4: Response Contract Nulls from Empty Projects
**What goes wrong:** A brand new project has no artifacts, no gates, no timeline. Dashboard endpoint returns `null` instead of `[]` for list fields.
**Why it happens:** SQLAlchemy `scalars().all()` returns `[]` (correct), but if a Pydantic field has `Optional[list] = None`, serialization produces `null`.
**How to avoid:** Audit all response model list fields to use `Field(default_factory=list)` not `Optional[list] = None`. Run `test_response_contracts.py` against a fresh empty project.
**Warning signs:** Frontend TypeScript errors when `artifacts.map(...)` fails on null.

### Pitfall 5: E2E Test Uses Real DB (Migration State Mismatch)
**What goes wrong:** E2E test runs against a local Postgres DB that has different migration state from CI.
**Why it happens:** E2E test requires real DB session, and CI may not have run all migrations.
**How to avoid:** E2E test uses the same SQLite + `aiosqlite` in-memory pattern used by existing API tests (see `conftest.py` pattern). The `FakeSandboxRuntime` and `FakeAsyncRedis` cover the non-DB dependencies.
**Warning signs:** `alembic.util.CommandError: Target database is not up to date` in CI.

### Pitfall 6: Chat Widget Context Fetch on Every Message
**What goes wrong:** Every chat message triggers a fresh `GET /api/dashboard/{project_id}` call to fetch project context. At high message frequency, this floods the dashboard endpoint.
**Why it happens:** Naive implementation re-fetches context inline with each message.
**How to avoid:** Fetch project context once when the chat panel opens, store in React state. Refresh context only when the panel is re-opened or an action (build, navigation) is executed.
**Warning signs:** Repeated identical dashboard API calls in network tab.

## Code Examples

### E2B Preview URL Generation
```python
# Source: code inspection of e2b 2.13.2 / e2b_code_interpreter 2.4.1
# backend/app/sandbox/e2b_runtime.py
import os
import asyncio
from e2b_code_interpreter import Sandbox

async def provision_sandbox_preview(files: dict[str, str]) -> dict:
    """Write files to E2B sandbox and return preview URL.

    Returns:
        {
            "sandbox_id": "i62mff4ahtrdfdkyn2esc",
            "preview_url": "https://8080-i62mff4ahtrdfdkyn2esc.e2b.app",
        }
    """
    os.environ["E2B_API_KEY"] = get_settings().e2b_api_key
    loop = asyncio.get_event_loop()

    sandbox = await loop.run_in_executor(
        None,
        lambda: Sandbox.create(timeout=3600)  # 1 hour
    )

    # Write files
    for path, content in files.items():
        abs_path = f"/home/user/{path}" if not path.startswith("/") else path
        await loop.run_in_executor(None, lambda: sandbox.files.write(abs_path, content))

    # Get preview URL (port 8080 is conventional for generated apps)
    host = sandbox.get_host(8080)  # Returns "{port}-{sandbox_id}.e2b.app"
    preview_url = f"https://{host}"

    return {
        "sandbox_id": sandbox.sandbox_id,
        "preview_url": preview_url,
    }
```

### Alignment Score — Pure Domain Function
```python
# Source: Claude's discretion (see Architecture Patterns section)
# backend/app/domain/alignment.py

def compute_alignment_score(
    original_scope: dict,
    requested_changes: list[dict],
) -> tuple[int, bool]:
    """Compute how aligned iterations are with original MVP scope.

    Returns:
        (score: int 0-100, scope_creep_detected: bool)
        score >= 80: aligned (green)
        score 60-79: drifting (yellow)
        score < 60: scope creep (red)
    """
    if not requested_changes:
        return 100, False

    # Extract original feature set (lowercase for fuzzy matching)
    original_features = {
        f["name"].lower()
        for f in original_scope.get("core_features", [])
    }

    if not original_features:
        return 75, False  # No features to compare against — neutral score

    aligned_count = 0
    for change in requested_changes:
        desc = change.get("description", "").lower()
        # Check if change references an existing feature by name
        if any(feat in desc for feat in original_features):
            aligned_count += 1

    score = int((aligned_count / len(requested_changes)) * 100)
    scope_creep = score < 60
    return score, scope_creep
```

### Build Progress SSE in Frontend
```typescript
// Source: existing pattern in useAgentStream.ts + jobs.py SSE endpoint
// frontend/src/hooks/useBuildProgress.ts

const STAGE_LABELS: Record<string, string> = {
  queued: "Waiting in queue...",
  starting: "Starting build...",
  scaffold: "Scaffolding workspace...",
  code: "Writing code...",
  deps: "Installing dependencies...",
  checks: "Running checks...",
  ready: "Build complete!",
  failed: "Build failed",
};

export function useBuildProgress(jobId: string | null) {
  const [status, setStatus] = useState<string>("queued");
  const [label, setLabel] = useState<string>("Waiting in queue...");
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);

  useEffect(() => {
    if (!jobId) return;
    const eventSource = new EventSource(`/api/jobs/${jobId}/stream`);

    eventSource.onmessage = (event) => {
      const data = JSON.parse(event.data);
      setStatus(data.status);
      setLabel(STAGE_LABELS[data.status] ?? data.status);
      if (data.status === "ready" && data.preview_url) {
        setPreviewUrl(data.preview_url);
      }
      if (data.status === "ready" || data.status === "failed") {
        eventSource.close();
      }
    };

    return () => eventSource.close();
  }, [jobId]);

  return { status, label, previewUrl };
}
```

Note: The existing `stream_job_status` SSE endpoint only emits `{job_id, status, message, timestamp}`. It needs to be extended to include `preview_url` in the READY event payload.

### FloatingChat Component Structure
```tsx
// frontend/src/components/chat/FloatingChat.tsx
// Source: Claude's discretion — built from React primitives + Tailwind + framer-motion

export function FloatingChat({ projectContext }: { projectContext?: ProjectContext }) {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  // Context fetched once on open, not on every message
  const [loadedContext, setLoadedContext] = useState<ProjectContext | null>(null);

  const handleOpen = async () => {
    setOpen(true);
    if (!loadedContext) {
      // Fetch fresh context when opening
      const ctx = await fetchProjectContext(projectContext?.projectId);
      setLoadedContext(ctx);
    }
  };

  return (
    <>
      {/* Floating bubble — fixed bottom-right */}
      <button
        onClick={handleOpen}
        className="fixed bottom-6 right-6 z-50 w-14 h-14 bg-brand rounded-full
                   shadow-glow flex items-center justify-center hover:scale-105
                   transition-transform"
        aria-label="Open co-founder chat"
      >
        <MessageCircle className="w-6 h-6 text-white" />
      </button>

      {/* Chat panel — slides up from bottom-right */}
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: 20, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 20, scale: 0.95 }}
            className="fixed bottom-24 right-6 z-50 w-96 h-[500px]
                       glass-strong border border-white/10 rounded-2xl
                       flex flex-col overflow-hidden"
          >
            {/* Header */}
            <div className="flex items-center justify-between p-4 border-b border-white/5">
              <span className="font-semibold text-white text-sm">Co-Founder Chat</span>
              <button onClick={() => setOpen(false)}><X className="w-4 h-4" /></button>
            </div>
            {/* Messages */}
            {/* Input */}
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}
```

### Gate 2 (Solidification) Creation Pattern
```python
# Source: existing GateService pattern — gate_type="solidification" is new but mechanism is same
# backend/app/api/routes/generation.py

@router.post("/generation/{job_id}/preview-viewed")
async def record_preview_viewed(
    job_id: str,
    user: ClerkUser = Depends(require_auth),
    session_factory: async_sessionmaker = Depends(get_session_factory),
    runner: Runner = Depends(get_runner),
):
    """Trigger Solidification Gate 2 after founder views the preview.

    Called by frontend when the preview iframe is first rendered.
    Creates Gate 2 if it doesn't already exist (idempotent via GateService).
    """
    gate_service = GateService(runner=runner, session_factory=session_factory)

    # Get project_id from job
    job_data = await get_job_project_id(job_id)

    try:
        gate = await gate_service.create_gate(
            clerk_user_id=user.user_id,
            project_id=job_data["project_id"],
            gate_type="solidification",
        )
    except HTTPException as e:
        if e.status_code == 409:
            # Gate already exists — return existing gate
            return {"status": "gate_already_created"}
        raise

    return {"gate_id": gate.gate_id, "status": "gate_created"}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| E2B SDK v0.x (sync-only) | E2B SDK v2.x with `Sandbox.create()` + `run_in_executor` | 2024 | Already handled in existing `e2b_runtime.py` |
| LangGraph callbacks for streaming | LangGraph `ainvoke` + Redis pub/sub for status | 2024 | Already in place — SSE stream reads from Redis pubsub |
| Single gate per project | Multiple gate types (direction, solidification) | Phase 10 | Use `gate_type` discriminator, same table |
| Chat as primary nav item | Chat as floating overlay + secondary nav item | Phase 10 | CHAT-02 requirement |

**Deprecated/outdated:**
- `E2BSandboxRuntime.session()` context manager: Works for short-lived ops, but for long-running preview sandboxes, use `start()`/`stop()` directly (or don't call `stop()` if sandbox should persist for the founder to view the preview)

## Open Questions

1. **E2B sandbox lifecycle after preview**
   - What we know: `Sandbox.create(timeout=3600)` keeps sandbox alive 1 hour. Founder can view preview in that window.
   - What's unclear: When founder requests iteration build 30+ minutes later, sandbox may be expired. `Sandbox.connect(sandbox_id)` will fail for expired sandboxes.
   - Recommendation: On iteration build start, always try `Sandbox.connect(sandbox_id)`, catch exception, fall back to full rebuild. Store `sandbox_expired=True` flag in job metadata for observability. This is a known design choice — document in code comments.

2. **Preview URL sandbox domain for production**
   - What we know: `sandbox.get_host(8080)` returns `{port}-{sandbox_id}.{sandbox_domain}`. Default `sandbox_domain` is `e2b.app`.
   - What's unclear: Does `e2b.app` subdomain work in iframes without CSP issues? Is there a custom domain option for enterprise E2B plans?
   - Recommendation: For MVP, use direct `e2b.app` URL. Add CSP header `frame-src https://*.e2b.app` to the Next.js config. If iframe embedding is blocked, use `window.open()` instead.

3. **Runner protocol needs new methods for Phase 10**
   - What we know: Current `Runner` protocol has 10 methods, none for generation clarification.
   - What's unclear: Should `clarify_change_request()` be a new Runner method, or does it reuse the existing streaming `chat` endpoint?
   - Recommendation: Add `clarify_change_request(description: str, project_context: dict) -> AsyncGenerator[str, None]` to the Runner protocol and `RunnerFake`. The `RunnerFake` returns 2 deterministic clarifying questions. This keeps the TDD approach consistent.

4. **Dashboard `product_version` and `mvp_completion_percent` stubs**
   - What we know: `DashboardService` has `product_version = "v0.1"` hardcoded and `latest_build_status = None`.
   - What's unclear: Should product_version be derived from build_version on the Job record?
   - Recommendation: Yes — query the latest READY Job for the project, map `build_v0_1` → `v0.1`, `build_v0_2` → `v0.2`. Update `DashboardService.get_dashboard()` to include this query.

## Sources

### Primary (HIGH confidence)
- Code inspection of `backend/app/sandbox/e2b_runtime.py` — existing E2B integration pattern
- Code inspection of `backend/app/queue/worker.py` + `state_machine.py` — existing FSM states and worker loop
- Code inspection of `backend/app/services/gate_service.py` — GateService DI pattern, idempotency, ownership checks
- Code inspection of `backend/app/core/feature_flags.py` — `require_feature` dependency
- Python introspection: `e2b_code_interpreter 2.4.1` `Sandbox.get_host(port)` → `{port}-{sandbox_id}.{sandbox_domain}`
- Python introspection: `Sandbox.create(timeout=3600)` — timeout parameter confirmed
- Python introspection: `Sandbox.connect(sandbox_id)` — reconnect method confirmed
- Code inspection of `backend/tests/api/test_jobs_integration.py` — existing E2E test patterns with FakeAsyncRedis + RunnerFake
- Code inspection of `frontend/src/components/ui/brand-nav.tsx` — current Chat nav item location

### Secondary (MEDIUM confidence)
- [E2B Docs — Sandbox](https://e2b.dev/docs/sandbox): Default timeout 5 min, max 1h (Hobby) / 24h (Pro), `set_timeout()` for extension
- [E2B Python SDK Reference](https://e2b.dev/docs/sdk-reference/python-sdk/v1.0.0/sandbox_sync): `Sandbox.connect()`, `files`, `commands` modules

### Tertiary (LOW confidence)
- WebSearch: "pytest FastAPI E2E end-to-end test" — confirms TestClient + dependency overrides as standard pattern (already used in existing tests)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — everything already installed, confirmed from pyproject.toml and package.json
- E2B sandbox URL generation: HIGH — confirmed via Python introspection of installed e2b 2.13.2
- Architecture patterns: HIGH — derived from existing codebase patterns (GateService, JobStateMachine, RunnerFake)
- Alignment score algorithm: MEDIUM — Claude's discretion (no official standard), recommended simple keyword-matching approach
- Deploy readiness checks: MEDIUM — standard pre-flight list, specific checks derived from common deploy pitfalls
- Chat widget: HIGH — React primitives + Tailwind + framer-motion (all installed), no new dependencies

**Research date:** 2026-02-17
**Valid until:** 2026-03-17 (E2B SDK stable; internal patterns very stable)
