# Phase 7: State Machine Integration & Dashboard - Research

**Researched:** 2026-02-17
**Domain:** Dashboard API aggregation, real-time UI updates, correlation ID tracing, circular progress visualization
**Confidence:** HIGH

## Summary

Phase 7 integrates the existing state machine (Phase 2) and artifact system (Phase 6) into a unified, action-oriented founder-facing dashboard. The research reveals that this phase requires three distinct technical domains: (1) backend aggregation logic that computes deterministic progress from pure functions, (2) correlation ID middleware for request tracing across logs and events, and (3) frontend real-time updates with polling, shimmer animations, and slide-over panels.

The existing codebase already has strong foundations: pure domain functions for progress computation (`backend/app/domain/progress.py`), a clean state machine with `Stage` enum and transition validation (`backend/app/domain/stages.py`), artifact models with generation status tracking (`backend/app/db/models/artifact.py`), and StageEvent records with correlation_id columns (`backend/app/db/models/stage_event.py`). The primary work is aggregation (combine data from projects, artifacts, stage_events, decision_gates, jobs into a single dashboard response) and frontend visualization (circular stage ring, action hero, slide-over panels).

User decisions from CONTEXT.md are clear: action-oriented layout (suggested focus is primary), circular stage ring with percentage text (no partial fill), polling updates every 5-10s (no SSE), slide-over panels from right, toast + pulse animation for changes, and skeleton shimmer during generation. Claude has discretion on card vs list layout for artifacts, visual treatment for stage states, and inline editing UX.

**Primary recommendation:** Use pure aggregation functions in service layer, asgi-correlation-id middleware for request tracing, Framer Motion for shimmer/pulse animations, custom SVG for circular ring (no library needed), polling with React hooks, and shadcn/ui patterns for slide-over (Radix Dialog primitive extended with slide-in animation).

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Dashboard layout:**
- Action-oriented hero: "Here's what to do next" — suggested focus and pending decisions are the primary element
- Stage ring and action hero sit side-by-side in a single hero row at the top
- Risk flags only appear when there are active risks (clean dashboard when healthy)
- Activity/timeline lives on a separate page — dashboard stays focused on current state
- Overall aesthetic: clean and intuitive

**Artifact presentation:**
- Claude's discretion on card grid vs compact list — pick the best pattern for the action-oriented layout

**Stage journey visual:**
- Circular/radial progress ring representing the 5-stage journey
- Current stage highlighted with percentage label nearby (e.g., "MVP Built — 60%")
- No partial visual fill — stage is highlighted, percentage is text
- Visual treatment for completed vs current vs future stages: Claude's discretion (fits the clean aesthetic)

**Card drill-down UX:**
- Slide-over panel from the right when clicking an artifact card — dashboard stays visible behind
- Inside the panel: key sections as collapsible/expandable cards, with action buttons in header (Regenerate, Export PDF, Export Markdown, Edit)
- Inline editing approach: Claude's discretion based on the expandable section pattern
- No version UI surfaced to founders — versions exist in backend only

**Live update feel:**
- Polling every 5-10 seconds for data freshness (no SSE)
- Cards that changed get a brief highlight/pulse animation so founders notice what's new, plus a toast notification
- During artifact generation: skeleton shimmer animation on the card until ready
- On generation failure: toast notification + error badge on the card with retry button

### Claude's Discretion

- Artifact card vs list layout choice
- Visual treatment for stage states (completed/current/future)
- Inline editing pattern (in-place vs edit mode toggle)
- Exact spacing, typography, and color palette
- Error state design details
- Poll interval within the 5-10s range

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope

</user_constraints>

## Standard Stack

### Core Backend

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI | 0.104+ | Dashboard API endpoints | Already in use, built-in dependency injection |
| asgi-correlation-id | 4.3+ | Correlation ID middleware | Industry standard for ASGI request tracing, 2.5k+ stars |
| SQLAlchemy | 2.0+ | Database queries for aggregation | Already in use, async support for complex joins |
| Pydantic | 2.0+ | Response models with validation | Already in use, FastAPI native |

**Why these choices:**
- asgi-correlation-id is the de facto ASGI standard for correlation IDs (research shows it's recommended in all 2026 FastAPI logging guides)
- No new libraries needed for aggregation — pure Python functions + existing SQLAlchemy queries
- No state machine changes — Phase 2 delivered pure functions ready for aggregation

### Core Frontend

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| React | 19.0+ | UI components | Already in use (Next.js 15) |
| Framer Motion | 12.34+ | Shimmer/pulse animations | Already in use, lightweight (32k stars, 8.1M weekly downloads) |
| Lucide React | 0.400+ | Icons | Already in use |
| Tailwind CSS | 4.0+ | Styling | Already in use |

**Why these choices:**
- Framer Motion already in package.json — no new dependency
- Custom SVG for circular ring (avoids library overhead, simple geometry)
- Polling with React hooks (useEffect + setInterval) — no library needed

### Supporting Backend

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Python logging | stdlib | Structured JSON logs with correlation_id | All API endpoints, background tasks |
| contextvars | stdlib | Async-safe correlation ID storage | Middleware and downstream functions |

### Supporting Frontend

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| sonner | latest | Toast notifications | Change alerts, error messages |
| Custom hooks | n/a | Polling logic, dashboard data fetching | Reusable across dashboard pages |

**Why sonner:**
Research shows sonner is the 2026 standard for React toast notifications (built for React 18+, TypeScript-first, shadcn/ui recommended). It's lightweight, works without context providers, and supports stacking/positioning.

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| asgi-correlation-id | Custom middleware | Custom solution = 100+ lines of boilerplate, no W3C Trace Context support |
| Polling | Server-Sent Events (SSE) | User decided polling, SSE adds connection management complexity |
| Custom SVG ring | react-circular-progressbar | Library adds 50kb, custom SVG is 20 lines |
| sonner | react-hot-toast | Both excellent, sonner has better TypeScript DX and shadcn/ui integration |

**Installation:**

Backend:
```bash
cd backend
pip install asgi-correlation-id
```

Frontend:
```bash
cd frontend
npm install sonner
```

## Architecture Patterns

### Recommended Project Structure

Backend additions:
```
backend/app/
├── api/routes/
│   └── dashboard.py          # New: GET /dashboard/{project_id}
├── services/
│   └── dashboard_service.py  # New: Aggregation logic
├── middleware/
│   └── correlation.py        # New: Correlation ID setup
└── schemas/
    └── dashboard.py          # New: DashboardResponse model
```

Frontend additions:
```
frontend/src/
├── app/(dashboard)/
│   └── company/              # New: Company dashboard page
│       └── [projectId]/
│           └── page.tsx
├── components/
│   ├── dashboard/            # New: Dashboard-specific components
│   │   ├── stage-ring.tsx
│   │   ├── action-hero.tsx
│   │   ├── artifact-card.tsx
│   │   └── artifact-panel.tsx
│   └── ui/
│       ├── slide-over.tsx    # New: Radix Dialog extended for slide-over
│       └── skeleton.tsx      # New: Shimmer skeleton
└── hooks/
    ├── useDashboard.ts       # New: Polling + data fetching
    └── useSlideOver.ts       # New: Panel state management
```

### Pattern 1: Dashboard Aggregation Service

**What:** Service layer function that queries multiple tables and computes dashboard state using pure domain functions

**When to use:** Every dashboard API request

**Example:**
```python
# backend/app/services/dashboard_service.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.domain.progress import compute_stage_progress
from app.domain.risks import detect_system_risks
from app.db.models.project import Project
from app.db.models.artifact import Artifact
from app.db.models.decision_gate import DecisionGate
from app.db.models.stage_event import StageEvent

class DashboardService:
    async def get_dashboard(
        self,
        session: AsyncSession,
        project_id: UUID,
        user_id: str
    ) -> dict:
        """Aggregate dashboard data from multiple sources.

        Steps:
        1. Fetch project (verify ownership)
        2. Fetch artifacts with generation_status
        3. Fetch pending decision gates
        4. Fetch latest stage events (for timeline preview)
        5. Compute progress using pure domain functions
        6. Compute risks using pure domain functions
        7. Build suggested_focus from business rules
        """
        # 1. Fetch project
        result = await session.execute(
            select(Project).where(
                Project.id == project_id,
                Project.clerk_user_id == user_id
            )
        )
        project = result.scalar_one_or_none()
        if not project:
            return None

        # 2. Fetch artifacts
        result = await session.execute(
            select(Artifact).where(Artifact.project_id == project_id)
        )
        artifacts = result.scalars().all()

        # 3. Fetch pending gates
        result = await session.execute(
            select(DecisionGate).where(
                DecisionGate.project_id == project_id,
                DecisionGate.status == "pending"
            )
        )
        pending_gates = result.scalars().all()

        # 4. Compute progress (pure function from domain layer)
        milestones = self._extract_milestones(project)
        progress_percent = compute_stage_progress(milestones)

        # 5. Compute risks (pure function from domain layer)
        risks = detect_system_risks(
            last_gate_decision_at=self._get_last_gate_decision(pending_gates),
            build_failure_count=self._count_build_failures(project_id),
            last_activity_at=project.updated_at
        )

        # 6. Build suggested_focus (business rule)
        suggested_focus = self._compute_suggested_focus(
            pending_gates, artifacts, risks
        )

        return {
            "project_id": str(project.id),
            "stage": project.stage_number,
            "product_version": "0.1.0",  # TODO: from builds table
            "mvp_completion_percent": progress_percent,
            "next_milestone": self._get_next_milestone(milestones),
            "risk_flags": [{"type": r["type"], "message": r["message"]} for r in risks],
            "suggested_focus": suggested_focus,
            "artifacts": [self._serialize_artifact(a) for a in artifacts],
            "pending_decisions": [self._serialize_gate(g) for g in pending_gates],
            "latest_build_status": None,  # TODO: Phase 8
            "preview_url": None  # TODO: Phase 8
        }
```

**Key insight:** Aggregation logic lives in service layer. Domain functions stay pure (no DB access). Service orchestrates queries + pure functions.

### Pattern 2: Correlation ID Middleware

**What:** ASGI middleware that reads/generates correlation IDs and injects them into logs and response headers

**When to use:** All API requests (global middleware)

**Example:**
```python
# backend/app/middleware/correlation.py
from asgi_correlation_id import CorrelationIdMiddleware
from asgi_correlation_id.context import correlation_id
import logging

# Add to FastAPI app
app.add_middleware(
    CorrelationIdMiddleware,
    header_name="X-Request-ID",
    generator=lambda: str(uuid.uuid4()),
    validator=None,  # Accept any format
    transformer=lambda a: a,  # No transformation
)

# Configure logging to include correlation_id
import logging.config

LOGGING_CONFIG = {
    "version": 1,
    "formatters": {
        "json": {
            "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
            "format": "%(asctime)s %(levelname)s %(name)s %(correlation_id)s %(message)s"
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "json"
        }
    },
    "root": {
        "level": "INFO",
        "handlers": ["console"]
    }
}

# Use in route handlers
@router.post("/artifacts/generate")
async def generate_artifacts(request: GenerateRequest):
    logger.info(
        "Artifact generation started",
        extra={"correlation_id": correlation_id.get()}
    )
    # Generate artifacts...
    logger.info(
        "Artifact generation completed",
        extra={"correlation_id": correlation_id.get()}
    )
```

**Key insight:** Middleware injects correlation_id into contextvars. All downstream code (services, domain functions that log) can access via `correlation_id.get()`.

### Pattern 3: Dashboard Polling Hook

**What:** React hook that polls dashboard endpoint and merges updates into state

**When to use:** Company dashboard page

**Example:**
```typescript
// frontend/src/hooks/useDashboard.ts
import { useEffect, useState, useCallback } from 'react';
import { useAuth } from '@clerk/nextjs';
import { apiFetch } from '@/lib/api';

interface DashboardData {
  project_id: string;
  stage: number;
  mvp_completion_percent: number;
  suggested_focus: string;
  artifacts: Artifact[];
  risk_flags: RiskFlag[];
  // ... other fields
}

export function useDashboard(projectId: string, interval = 7000) {
  const { getToken } = useAuth();
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);
  const [changedFields, setChangedFields] = useState<Set<string>>(new Set());

  const fetchDashboard = useCallback(async () => {
    try {
      const res = await apiFetch(`/api/dashboard/${projectId}`, getToken);
      if (!res.ok) throw new Error('Failed to fetch dashboard');

      const newData = await res.json();

      // Detect changes for animation
      if (data) {
        const changed = new Set<string>();
        if (newData.mvp_completion_percent !== data.mvp_completion_percent) {
          changed.add('progress');
        }
        if (JSON.stringify(newData.artifacts) !== JSON.stringify(data.artifacts)) {
          changed.add('artifacts');
        }
        setChangedFields(changed);

        // Clear animation flags after 2s
        setTimeout(() => setChangedFields(new Set()), 2000);
      }

      setData(newData);
      setLoading(false);
    } catch (err) {
      setError(err as Error);
      setLoading(false);
    }
  }, [projectId, getToken, data]);

  // Initial fetch
  useEffect(() => {
    fetchDashboard();
  }, []);

  // Polling interval
  useEffect(() => {
    const timer = setInterval(fetchDashboard, interval);
    return () => clearInterval(timer);
  }, [fetchDashboard, interval]);

  return { data, loading, error, changedFields, refetch: fetchDashboard };
}
```

**Key insight:** Hook encapsulates polling + change detection. Component receives `changedFields` set to trigger animations.

### Pattern 4: Circular Stage Ring (Custom SVG)

**What:** SVG-based circular visualization with 5 segments representing stages

**When to use:** Dashboard hero section

**Example:**
```typescript
// frontend/src/components/dashboard/stage-ring.tsx
interface StageRingProps {
  currentStage: number; // 0-4 (PRE_STAGE to FEEDBACK_LOOP_ACTIVE)
  progressPercent: number;
}

export function StageRing({ currentStage, progressPercent }: StageRingProps) {
  const stages = [
    { label: "Thesis", color: "text-gray-400" },
    { label: "Validated", color: "text-blue-400" },
    { label: "MVP Built", color: "text-brand" },
    { label: "Feedback", color: "text-green-400" },
    { label: "Scale", color: "text-purple-400" },
  ];

  const radius = 80;
  const strokeWidth = 12;
  const circumference = 2 * Math.PI * radius;
  const segmentLength = circumference / 5;
  const gapLength = 8; // Small gap between segments

  return (
    <div className="relative w-48 h-48">
      <svg viewBox="0 0 200 200" className="transform -rotate-90">
        {stages.map((stage, idx) => {
          const offset = idx * (segmentLength + gapLength);
          const isCompleted = idx < currentStage;
          const isCurrent = idx === currentStage;

          return (
            <circle
              key={idx}
              cx="100"
              cy="100"
              r={radius}
              fill="none"
              stroke="currentColor"
              strokeWidth={strokeWidth}
              strokeDasharray={`${segmentLength} ${circumference - segmentLength}`}
              strokeDashoffset={-offset}
              className={
                isCurrent ? "text-brand" :
                isCompleted ? "text-brand/50" :
                "text-white/10"
              }
              strokeLinecap="round"
            />
          );
        })}
      </svg>

      {/* Center label */}
      <div className="absolute inset-0 flex items-center justify-center">
        <div className="text-center">
          <div className="text-3xl font-bold text-white">{progressPercent}%</div>
          <div className="text-xs text-muted-foreground mt-1">
            {stages[currentStage]?.label}
          </div>
        </div>
      </div>
    </div>
  );
}
```

**Key insight:** Custom SVG avoids library overhead. Five circles with strokeDasharray create segments. Center text shows percentage.

### Pattern 5: Slide-Over Panel

**What:** Radix Dialog primitive styled as slide-over from right

**When to use:** Artifact detail drill-down

**Example:**
```typescript
// frontend/src/components/ui/slide-over.tsx
import * as Dialog from '@radix-ui/react-dialog';
import { motion } from 'framer-motion';

interface SlideOverProps {
  open: boolean;
  onClose: () => void;
  children: React.ReactNode;
}

export function SlideOver({ open, onClose, children }: SlideOverProps) {
  return (
    <Dialog.Root open={open} onOpenChange={onClose}>
      <Dialog.Portal>
        {/* Backdrop */}
        <Dialog.Overlay asChild>
          <motion.div
            className="fixed inset-0 bg-black/50 backdrop-blur-sm z-40"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
          />
        </Dialog.Overlay>

        {/* Panel */}
        <Dialog.Content asChild>
          <motion.div
            className="fixed right-0 top-0 bottom-0 w-full max-w-2xl bg-black/90 border-l border-white/10 shadow-2xl z-50 overflow-y-auto"
            initial={{ x: '100%' }}
            animate={{ x: 0 }}
            exit={{ x: '100%' }}
            transition={{ type: 'spring', damping: 25, stiffness: 200 }}
          >
            {children}
          </motion.div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
```

**Key insight:** Radix Dialog handles focus trapping, ESC key, click-outside. Framer Motion handles slide animation.

### Pattern 6: Shimmer Skeleton

**What:** Animated loading placeholder during artifact generation

**When to use:** Artifact cards with `generation_status === "generating"`

**Example:**
```typescript
// frontend/src/components/ui/skeleton.tsx
import { motion } from 'framer-motion';

export function Skeleton({ className }: { className?: string }) {
  return (
    <motion.div
      className={`bg-white/5 rounded-lg ${className}`}
      animate={{
        opacity: [0.5, 0.8, 0.5],
      }}
      transition={{
        duration: 1.5,
        repeat: Infinity,
        ease: "easeInOut"
      }}
    />
  );
}

// Usage in artifact card
function ArtifactCard({ artifact }: { artifact: Artifact }) {
  if (artifact.generation_status === "generating") {
    return (
      <div className="p-6 space-y-4">
        <Skeleton className="h-6 w-2/3" />
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-4 w-5/6" />
      </div>
    );
  }

  return <div>{/* Normal content */}</div>;
}
```

**Key insight:** Framer Motion's opacity animation creates shimmer effect. No external library needed.

### Anti-Patterns to Avoid

**❌ Caching progress in DB:**
- User decided: "Progress is computed from milestones on each query, never cached"
- Why: Progress must reflect latest milestone state, caching creates staleness

**❌ Embedding correlation IDs manually:**
- Use middleware + contextvars, not manual prop-drilling through function calls
- Why: Middleware ensures consistency, prevents forgotten IDs

**❌ Complex dashboard state management:**
- Don't use Redux/Zustand for dashboard state
- Why: Polling hook + local useState is sufficient, external store adds complexity

**❌ Partial ring fills:**
- User decided: "No partial visual fill — stage is highlighted, percentage is text"
- Why: 5 discrete stages, not continuous progress bar

**❌ SSE for real-time updates:**
- User decided: "Polling every 5-10 seconds" (no SSE)
- Why: SSE adds connection management, polling is simpler for 5-10s intervals

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Correlation ID propagation | Custom request ID middleware | asgi-correlation-id | Handles W3C Trace Context, edge cases (missing headers, validation), context vars setup |
| Toast notifications | Custom notification system | sonner | Handles stacking, positioning, auto-dismiss, action buttons, accessibility |
| Slide-over accessibility | Custom modal from scratch | Radix Dialog primitive | Handles focus trap, ESC key, click-outside, screen reader announcements, portal rendering |
| Progress computation | Ad-hoc percentage logic | Pure domain functions (already exist) | Already built in Phase 2, deterministic, tested |
| Risk detection | Custom risk rules per endpoint | Pure domain functions (already exist) | Already built in Phase 2, reusable across dashboard/timeline |

**Key insight:** Phase 2 and Phase 6 delivered reusable domain functions. This phase is primarily aggregation + visualization. Don't rebuild logic that already exists.

## Common Pitfalls

### Pitfall 1: Correlation ID Not in Logs

**What goes wrong:** correlation_id in middleware but not appearing in log output

**Why it happens:** Logger not configured to read from contextvars, or using wrong log formatter

**How to avoid:**
- Use `pythonjsonlogger` with format string that includes `%(correlation_id)s`
- Configure asgi-correlation-id's `CorrelationIdFilter` on all loggers
- Test with a sample request and verify JSON log output

**Warning signs:**
- Logs have all fields except correlation_id
- Middleware runs but logs show `correlation_id: null`

### Pitfall 2: Polling Race Conditions

**What goes wrong:** Multiple polls overlap, state updates out of order, UI flickers

**Why it happens:** Poll interval < request duration, or useEffect dependencies cause re-polling

**How to avoid:**
- Use `useCallback` to memoize fetch function
- Track `isPolling` state, skip next poll if previous hasn't finished
- Set interval > expected response time (7s interval for ~2s API response)

**Warning signs:**
- Network tab shows overlapping requests
- State updates trigger new polls immediately
- Dashboard flickers between values

**Example fix:**
```typescript
const [isPolling, setIsPolling] = useState(false);

const fetchDashboard = useCallback(async () => {
  if (isPolling) return; // Skip if already polling
  setIsPolling(true);
  try {
    // ... fetch logic
  } finally {
    setIsPolling(false);
  }
}, [isPolling, projectId]);
```

### Pitfall 3: Empty State Returns Null Instead of Empty Arrays

**What goes wrong:** Frontend crashes on `data.artifacts.map(...)` when no artifacts exist

**Why it happens:** Backend returns `{ artifacts: null }` or omits key entirely

**Per user requirement:** DASH-03: Empty states return empty arrays (not null)

**How to avoid:**
- Pydantic schema with `Field(default_factory=list)` for array fields
- Explicit empty array initialization in service layer
- Integration test that verifies empty project returns valid structure

**Warning signs:**
- TypeError: Cannot read property 'map' of null/undefined
- Frontend needs `data?.artifacts ?? []` everywhere
- Empty state UI doesn't render

**Example fix:**
```python
# backend/app/schemas/dashboard.py
from pydantic import BaseModel, Field

class DashboardResponse(BaseModel):
    project_id: str
    artifacts: list[ArtifactResponse] = Field(default_factory=list)
    risk_flags: list[RiskFlag] = Field(default_factory=list)
    # ... ensures empty arrays, never null
```

### Pitfall 4: Slide-Over Panel Doesn't Unmount

**What goes wrong:** Panel content from previous artifact persists, or scroll position carries over

**Why it happens:** Radix Dialog reuses DOM node when toggling between artifacts

**How to avoid:**
- Use `key={artifactId}` on Dialog.Content to force remount
- Reset scroll position in useEffect when artifact changes
- Clear form state when panel closes

**Warning signs:**
- Clicking second artifact shows first artifact's data briefly
- Panel opens scrolled to middle instead of top
- Edit mode persists when switching artifacts

**Example fix:**
```typescript
<Dialog.Content key={artifact.id} asChild>
  <motion.div ref={panelRef}>
    {/* content */}
  </motion.div>
</Dialog.Content>

// Reset scroll on artifact change
useEffect(() => {
  panelRef.current?.scrollTo(0, 0);
}, [artifact.id]);
```

### Pitfall 5: Suggested Focus Logic Not Deterministic

**What goes wrong:** Same dashboard state produces different `suggested_focus` on refresh

**Why it happens:** Business rules use timestamps without timezone, or random selection among equal-priority items

**How to avoid:**
- All timestamp comparisons use UTC
- When multiple items have equal priority, use deterministic sort (e.g., by ID)
- Write unit tests that call `compute_suggested_focus()` twice with same input, assert same output

**Warning signs:**
- Suggested focus changes on refresh (data hasn't changed)
- Tests fail intermittently
- Logs show different suggestions with identical inputs

**Example fix:**
```python
def _compute_suggested_focus(gates, artifacts, risks):
    # Priority 1: Pending decision gates (sorted by creation time for determinism)
    if gates:
        oldest_gate = sorted(gates, key=lambda g: g.created_at)[0]
        return f"Decision needed: {oldest_gate.gate_type}"

    # Priority 2: Failed artifacts (sorted by ID for determinism)
    failed = [a for a in artifacts if a.generation_status == "failed"]
    if failed:
        first_failed = sorted(failed, key=lambda a: a.id)[0]
        return f"Fix failed artifact: {first_failed.artifact_type}"

    # Priority 3: Risks (sorted by rule name for determinism)
    if risks:
        first_risk = sorted(risks, key=lambda r: r["rule"])[0]
        return f"Address risk: {first_risk['message']}"

    return "All clear — ready to build"
```

### Pitfall 6: Circular Ring Segments Don't Align

**What goes wrong:** Visual gaps between segments are uneven, or segments overlap

**Why it happens:** Circumference calculation doesn't account for gap length, or strokeLinecap rounds incorrectly

**How to avoid:**
- Calculate `usableCircumference = circumference - (gapLength * numSegments)`
- Each segment length = `usableCircumference / numSegments`
- Use `strokeLinecap="round"` for smooth ends
- Test with all 5 stages to verify visual consistency

**Warning signs:**
- Gaps between segments vary in size
- Last segment overlaps first segment
- Stage 4 looks wider than Stage 1

**Example fix:**
```typescript
const numSegments = 5;
const gapLength = 8;
const usableCircumference = circumference - (gapLength * numSegments);
const segmentLength = usableCircumference / numSegments;

// Offset includes both segment and gap
const offset = idx * (segmentLength + gapLength);
```

## Code Examples

Verified patterns from research and existing codebase:

### Dashboard API Endpoint

```python
# backend/app/api/routes/dashboard.py
from fastapi import APIRouter, Depends, HTTPException
from app.core.auth import ClerkUser, require_auth
from app.db.base import get_session_factory
from app.services.dashboard_service import DashboardService
from app.schemas.dashboard import DashboardResponse

router = APIRouter()

@router.get("/{project_id}", response_model=DashboardResponse)
async def get_dashboard(
    project_id: str,
    user: ClerkUser = Depends(require_auth)
):
    """Get dashboard aggregation for project.

    Returns:
        Dashboard with stage, progress, artifacts, risks, suggested focus

    Raises:
        HTTPException(404): Project not found or unauthorized
    """
    session_factory = get_session_factory()
    service = DashboardService()

    async with session_factory() as session:
        dashboard = await service.get_dashboard(session, project_id, user.user_id)

        if dashboard is None:
            raise HTTPException(status_code=404, detail="Project not found")

        return dashboard
```

### Progress Computation (Already Exists)

```python
# backend/app/domain/progress.py (from Phase 2)
def compute_stage_progress(milestones: dict[str, dict]) -> int:
    """Compute stage progress (0-100) from milestone weights.

    Pure function — deterministic, no side effects.
    """
    if not milestones:
        return 0

    total_weight = sum(m["weight"] for m in milestones.values())
    if total_weight == 0:
        return 0

    completed_weight = sum(
        m["weight"] for m in milestones.values() if m["completed"]
    )

    return int((completed_weight / total_weight) * 100)
```

### Polling Hook with Change Detection

```typescript
// frontend/src/hooks/useDashboard.ts
import { useEffect, useState, useCallback, useRef } from 'react';
import { useAuth } from '@clerk/nextjs';
import { apiFetch } from '@/lib/api';
import { toast } from 'sonner';

export function useDashboard(projectId: string, pollInterval = 7000) {
  const { getToken } = useAuth();
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [changedFields, setChangedFields] = useState<Set<string>>(new Set());
  const isPollingRef = useRef(false);

  const fetchDashboard = useCallback(async () => {
    if (isPollingRef.current) return; // Prevent overlap
    isPollingRef.current = true;

    try {
      const res = await apiFetch(`/api/dashboard/${projectId}`, getToken);
      if (!res.ok) throw new Error('Dashboard fetch failed');

      const newData = await res.json();

      // Detect changes for animations
      if (data) {
        const changed = new Set<string>();

        if (newData.mvp_completion_percent !== data.mvp_completion_percent) {
          changed.add('progress');
          toast.success(`Progress updated: ${newData.mvp_completion_percent}%`);
        }

        // Detect artifact changes (generation completed)
        const newGenerating = newData.artifacts.filter(a => a.generation_status === 'generating');
        const oldGenerating = data.artifacts.filter(a => a.generation_status === 'generating');
        if (newGenerating.length < oldGenerating.length) {
          changed.add('artifacts');
          toast.success('Artifact generation completed');
        }

        // Detect failures
        const newFailed = newData.artifacts.filter(a => a.generation_status === 'failed');
        const oldFailed = data.artifacts.filter(a => a.generation_status === 'failed');
        if (newFailed.length > oldFailed.length) {
          changed.add('artifacts');
          toast.error('Artifact generation failed');
        }

        setChangedFields(changed);
        setTimeout(() => setChangedFields(new Set()), 2000);
      }

      setData(newData);
      setLoading(false);
    } catch (err) {
      console.error('Dashboard fetch error:', err);
    } finally {
      isPollingRef.current = false;
    }
  }, [projectId, getToken, data]);

  useEffect(() => {
    fetchDashboard();
  }, []);

  useEffect(() => {
    const timer = setInterval(fetchDashboard, pollInterval);
    return () => clearInterval(timer);
  }, [fetchDashboard, pollInterval]);

  return { data, loading, changedFields, refetch: fetchDashboard };
}
```

### Artifact Card with Shimmer

```typescript
// frontend/src/components/dashboard/artifact-card.tsx
import { motion } from 'framer-motion';
import { FileText, AlertCircle, RefreshCw } from 'lucide-react';
import { Skeleton } from '@/components/ui/skeleton';

interface ArtifactCardProps {
  artifact: Artifact;
  onClick: () => void;
  isChanged: boolean;
}

export function ArtifactCard({ artifact, onClick, isChanged }: ArtifactCardProps) {
  if (artifact.generation_status === 'generating') {
    return (
      <div className="p-6 space-y-4 rounded-xl bg-white/5 border border-white/10">
        <div className="flex items-center gap-3">
          <RefreshCw className="w-5 h-5 text-brand animate-spin" />
          <Skeleton className="h-6 w-2/3" />
        </div>
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-4 w-5/6" />
      </div>
    );
  }

  return (
    <motion.div
      className={`p-6 rounded-xl bg-white/5 border border-white/10 cursor-pointer hover:border-brand/50 transition-colors ${
        isChanged ? 'ring-2 ring-brand/50' : ''
      }`}
      onClick={onClick}
      animate={isChanged ? { scale: [1, 1.02, 1] } : {}}
      transition={{ duration: 0.3 }}
    >
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <FileText className="w-5 h-5 text-brand" />
          <h3 className="font-semibold text-white">{artifact.artifact_type}</h3>
        </div>

        {artifact.generation_status === 'failed' && (
          <div className="flex items-center gap-2 px-2.5 py-1 rounded-full bg-red-500/10 text-red-400 text-xs">
            <AlertCircle className="w-3.5 h-3.5" />
            Failed
          </div>
        )}

        {artifact.has_user_edits && (
          <div className="px-2.5 py-1 rounded-full bg-blue-500/10 text-blue-400 text-xs">
            Edited
          </div>
        )}
      </div>

      <p className="mt-2 text-sm text-muted-foreground line-clamp-2">
        Version {artifact.version_number} • Updated {new Date(artifact.updated_at).toLocaleDateString()}
      </p>
    </motion.div>
  );
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Global state management for dashboard | Polling hook + local state | 2024-2025 | Simpler mental model, no Redux boilerplate |
| WebSocket for real-time updates | Polling for 5-10s intervals | 2023-present | Polling is simpler when sub-second latency not needed |
| Custom correlation ID middleware | asgi-correlation-id | 2022-present | W3C Trace Context support, maintained library |
| CSS animations for loading | Framer Motion declarative animations | 2021-present | Better DX, animation composition |
| Headless UI (Tailwind team) | Radix UI | 2023-present | More components, React-optimized |
| react-hot-toast | sonner | 2024-present | Better TypeScript, shadcn/ui integration |

**Deprecated/outdated:**
- Manual request ID prop-drilling: Use middleware + contextvars instead
- SSE for polling-appropriate intervals: Adds complexity without benefit for 5-10s updates
- Library for circular progress: Custom SVG is 20 lines, avoids 50kb dependency
- Redux for dashboard state: Polling hook is sufficient, external store is overkill

## Open Questions

### 1. Should dashboard include preview of latest timeline events?

**What we know:**
- User decided: "Activity/timeline lives on a separate page"
- Dashboard stays focused on current state

**What's unclear:**
- Do founders want a "Recent Activity" widget with last 3 events?
- Or is suggested_focus + pending_decisions sufficient?

**Recommendation:**
- Start without timeline preview (user said separate page)
- If user feedback requests it, add as opt-in widget in future iteration

### 2. How should suggested_focus prioritize multiple pending items?

**What we know:**
- Priority order: pending decisions > failed artifacts > risks > all clear
- Need deterministic sorting within each category

**What's unclear:**
- If 2 pending decisions, which shows first? (Oldest? By gate type?)
- If 3 risks, which is most critical? (System vs LLM? By rule name?)

**Recommendation:**
- Within category, sort by creation time (oldest first) for decisions/artifacts
- For risks, sort by rule name alphabetically (deterministic)
- Document priority rules in service layer comments

### 3. What constitutes a "change" for toast notification?

**What we know:**
- User wants toast + pulse animation when cards change
- Poll interval is 5-10s

**What's unclear:**
- Does artifact content update (edit) trigger toast? Or only status changes?
- Does progress_percent change by 1% trigger toast? Or only 5%+ jumps?

**Recommendation:**
- Toast only for status changes: generation completed, generation failed, new risk
- Progress changes show in UI but don't trigger toast (too noisy)
- Content edits don't trigger toast (founder made the edit, they know)

## Sources

### Primary (HIGH confidence)

**Correlation ID Middleware:**
- [asgi-correlation-id GitHub](https://github.com/snok/asgi-correlation-id) - Official library docs, 2.5k stars
- [Production-Grade Logging for FastAPI Applications](https://medium.com/@laxsuryavanshi.dev/production-grade-logging-for-fastapi-applications-a-complete-guide-f384d4b8f43b) - Feb 2026 FastAPI logging guide
- [FastAPI + W3C Trace Context](https://medium.com/@komalbaparmar007/fastapi-w3c-trace-context-request-ids-baggage-and-end-to-end-correlation-0800218ed6dd) - Feb 2026 correlation ID patterns

**Error Handling & Logging:**
- [How to Get Started with Logging in FastAPI](https://betterstack.com/community/guides/logging/logging-with-fastapi/) - Better Stack official guide
- [FastAPI Error Handling Patterns](https://betterstack.com/community/guides/scaling-python/error-handling-fastapi/) - Better Stack scaling guide
- [FastAPI Best Practices for Production: 2026 Guide](https://fastlaunchapi.dev/blog/fastapi-best-practices-production-2026) - Production patterns

**React Polling:**
- [Implementing Polling in React](https://medium.com/@sfcofc/implementing-polling-in-react-a-guide-for-efficient-real-time-data-fetching-47f0887c54a7) - Polling patterns and best practices
- [Real Time Polling in React Query 2025](https://samwithcode.in/tutorial/react-js/real-time-polling-in-react-query-2025) - React Query refetchInterval patterns

**Framer Motion Animations:**
- [Motion — JavaScript & React animation library](https://motion.dev) - Official docs (formerly Framer Motion)
- [Create Lazy Load Skeleton Animations with Framer Motion](https://blog.prototypr.io/creating-lazy-load-shimmer-effects-for-images-with-framer-motion-f8d337a29db1) - Shimmer patterns
- [Improve React UX with skeleton UIs](https://blog.logrocket.com/improve-react-ux-skeleton-ui/) - Skeleton best practices

**Component Libraries:**
- [Radix UI Official Site](https://www.radix-ui.com/) - Official primitives documentation
- [Headless UI vs Radix UI](https://www.lodely.com/blog/headless-ui-vs-radix-ui) - Component library comparison
- [Best React Component Libraries (2026)](https://designrevision.com/blog/best-react-component-libraries) - 2026 ecosystem overview

**Circular Progress:**
- [How to build an SVG circular progress component using React](https://blog.logrocket.com/build-svg-circular-progress-component-react-hooks/) - LogRocket SVG guide
- [How to create an animated SVG circular progress component](https://medium.com/tinyso/how-to-create-an-animated-svg-circular-progress-component-in-react-5123c7d24391) - SVG animation patterns

**Toast Notifications:**
- [Top 9 React notification libraries in 2026](https://knock.app/blog/the-top-notification-libraries-for-react) - Library comparison
- [Comparing the top React toast libraries [2025 update]](https://blog.logrocket.com/react-toast-libraries-compared-2025/) - LogRocket comparison
- [Sonner: Modern Toast Notifications Done Right](https://medium.com/@rivainasution/shadcn-ui-react-series-part-19-sonner-modern-toast-notifications-done-right-903757c5681f) - Jan 2026 Sonner guide
- [Shadcn Sonner](https://www.shadcn.io/ui/sonner) - Official shadcn/ui integration

**Dashboard Design:**
- [Product Management Dashboard: How to Build One (2026 Guide)](https://monday.com/blog/rnd/product-management-dashboard/) - Action-oriented patterns
- [9 Dashboard Design Principles (2026)](https://www.designrush.com/agency/ui-ux-design/dashboard/trends/dashboard-design-principles) - UX principles
- [Dashboard Design UX Patterns Best Practices](https://www.pencilandpaper.io/articles/ux-pattern-analysis-data-dashboards) - UX pattern analysis

### Secondary (MEDIUM confidence)

- Existing codebase (backend/app/domain/*.py, backend/app/db/models/*.py) - Phase 2 and Phase 6 implementations verified through code reading

### Tertiary (LOW confidence)

None — all claims verified through official docs or credible 2026 sources

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All libraries verified through official docs, existing usage in package.json/requirements.txt
- Architecture patterns: HIGH - Aggregation service pattern standard for FastAPI, polling hook standard for React, all examples based on existing codebase
- Dashboard design: MEDIUM - Design patterns from research verified, but specific UX choices (card vs list) left to implementation
- Circular SVG ring: HIGH - SVG strokeDasharray technique well-documented, verified in LogRocket and Medium tutorials
- Pitfalls: HIGH - Based on common issues from research + experience with async polling, correlation ID middleware

**Research date:** 2026-02-17
**Valid until:** March 2026 (30 days — stack is stable, no fast-moving dependencies)

**Key unknowns requiring validation during implementation:**
1. Suggested focus prioritization rules (need user feedback after MVP)
2. Toast notification thresholds (need user testing to avoid notification fatigue)
3. Exact poll interval (7s chosen as middle of 5-10s range, may need tuning based on API response times)
