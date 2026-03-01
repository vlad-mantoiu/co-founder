# Phase 46: UI Integration - Research

**Researched:** 2026-03-01
**Domain:** Real-time SSE frontend, React state management, new /projects/[id]/build page
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Kanban Timeline (left sidebar panel)**
- Vertical timeline in a fixed-width (~280px) left sidebar panel
- Rich cards showing: phase name, status icon, plan progress (e.g. 2/3 plans), elapsed time, one-liner goal description
- Completed phases collapse to one-liner (expandable on click)
- Future/pending phases shown dimmed with phase name only
- Green/blue/gray status colors: complete = green, in-progress = blue (animated), pending = gray
- Vertical connecting line with colored dot nodes at each phase — classic timeline feel
- Smooth animation on state transitions (color/icon transitions subtly)
- Auto-scroll to active phase when a new phase starts
- Clicking a phase card: expands inline with details AND filters the activity feed to that phase
- Progress bar at top of sidebar showing overall milestone completion (e.g. "v0.7 — 80%")
- Fixed width sidebar, not resizable

**Activity Feed (main center area)**
- Chat-bubble style narration entries — agent has a named avatar and speaks in first person
- Casual co-founder tone: "Starting on the login page — setting up the auth flow first."
- Per-entry expand arrow to reveal verbose tool details underneath — no global toggle
- Verbose entries show human label + summary: "Wrote 47 lines to app/auth/login.tsx" — no raw JSON
- Phase dividers: thin horizontal divider with phase name when a new phase starts
- Auto-scroll to latest entries, stops if user scrolls up manually — "Jump to latest" button appears
- Typing indicator (animated dots) at bottom of feed when agent is between actions
- Error/escalation entries have distinct colored left border (red/amber tint)
- Feed loads from backend on page refresh — full history persists, not SSE-only
- Phase-only filtering via timeline sidebar click — no filter dropdowns or search

**Agent State Card (floating badge)**
- Floating badge in bottom-right corner of the viewport
- Building: shows current phase name + elapsed time ("Building: Auth System (42m)")
- Resting: countdown to next wake ("Resting — wakes in 2h 15m") with moon/sleep icon
- Needs input: amber badge with subtle pulse animation ("Needs input")
- Error: red badge — visually distinct from needs-input amber
- Clicking badge opens a popover: full details, current state, current phase, plan progress, elapsed time, token budget remaining, pending escalations
- Popover includes control actions: "Wake now" when resting, "Pause after current phase" when building

**Escalation Flow**
- Escalations appear inline in the activity feed as special entries
- Entry shows: plain English problem summary, collapsible "What I tried" section (3 attempts), multiple-choice decision buttons
- Agent's recommended action highlighted above options — founder can still pick any option
- Free-text guidance field only when founder selects "Provide guidance" option
- After resolution: entry updates in-place to "resolved" state — buttons disappear, green check
- Multiple pending escalations stack in feed with badge count ("Needs input (3)")
- Global threshold (build paused): floating badge turns red + feed entry explaining why — not a modal
- Resolved escalations remain in feed history as collapsed entries — expandable for full context

**Empty/Initial States**
- Before any build: friendly illustration + "Your co-founder is ready to build" + prominent "Start Build" CTA
- First activation: empty state fades out, timeline phases animate in one by one, feed shows first narration
- Planning phase (no plans yet): skeleton/shimmer card where plan progress would be
- Build complete: celebration moment (confetti/success animation) — canvas-confetti already installed
- Returning to running build: load full history from backend + scroll to most recent active entry
- Returning with pending escalations: attention banner at top: "Your co-founder needs your input on N items"
- Theme: follows existing app theme (light/dark), no separate toggle

**Responsive/Mobile**
- Desktop-first, basic mobile support
- Below 768px (md breakpoint): sidebar collapses to compact horizontal strip at top showing phase dots — tap to reveal full vertical timeline overlay
- Escalation resolution fully functional on mobile
- Floating state badge same position (bottom-right) on mobile
- Per-entry verbose expand works on mobile

**Page Layout & Navigation**
- New page at `/projects/[id]/build` — replaces current build page (the existing page becomes the pre-build view and autonomous agent view)
- Breadcrumb navigation: "Projects > My App > Build" + back button
- Compact header bar: breadcrumb, project name, preview toggle button
- Preview tab/split view: three columns when preview active — timeline | feed | preview iframe
- Preview auto-refreshes when agent deploys or updates sandbox

**Notifications Beyond UI**
- Browser push notifications for escalations only (Web Notifications API)
- No sound effects — visual indicators only
- Notification permission prompt triggered on first escalation, not during onboarding
- Email notifications deferred to future phase

### Claude's Discretion
- Exact animation timings and easing curves
- Loading skeleton design specifics
- Exact spacing, typography, and component styling within shadcn/ui system
- How to handle preview iframe loading states
- SSE reconnection and error recovery logic

### Deferred Ideas (OUT OF SCOPE)
- Email notifications for escalations — separate phase (requires email service, preferences, templates)
- Search/filter across activity feed — future enhancement
- Agent personality customization — future enhancement
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| UIAG-01 | GSD phases created by agent appear on Kanban Timeline with live status (pending/in-progress/complete) | New `gsd.phase.started` and `gsd.phase.completed` SSE events must be added to backend state_machine.py; new `AgentPhase` concept tracked in Redis per job_id; frontend `useAgentPhases` hook subscribes to events stream; GSD vertical timeline sidebar component renders from phase list |
| UIAG-02 | Activity feed shows phase-level summaries by default ("Planning authentication system...", "Building login page...") | narrate() tool already emits to Redis log stream (xadd) and existing `/api/jobs/{job_id}/logs/stream` SSE endpoint; feed needs to render narration entries as chat-bubble style with per-entry verbose expand arrow |
| UIAG-03 | Verbose toggle in activity feed reveals tool-level detail (individual file writes, bash commands, screenshots) | Tool calls need to emit `agent.tool.called` SSE events with human-readable labels; verbose expand per-entry (not global toggle) reveals tool summary inline |
| UIAG-04 | Dashboard displays agent state: working, sleeping, waiting-for-input, error | Backend already emits `agent.sleeping`, `agent.waking`, `agent.waiting_for_input`, `agent.build_paused` events via state_machine.publish_event(); need `agent.thinking` event added; `useAgentState` hook consumes these from events/stream SSE; floating badge + popover components |
| UIAG-05 | New SSE event types stream agent actions to frontend: agent.thinking, agent.tool.called, agent.sleeping, gsd.phase.started, gsd.phase.completed | Most events already emitted by backend (agent.sleeping, agent.waking, agent.waiting_for_input); 3 new events needed: agent.thinking (before each THINK phase), agent.tool.called (after each tool dispatch), gsd.phase.started / gsd.phase.completed (new concept wrapping TAOR narration phases); frontend hooks ignore unknown event types |
</phase_requirements>

## Summary

Phase 46 is a frontend-heavy phase that builds a new `/projects/[id]/build` page at the autonomous agent build dashboard. The current build page at this URL handles non-autonomous builds with polling — this phase replaces it with an SSE-driven, three-panel layout: vertical Kanban Timeline sidebar, Activity Feed, and (optional) Preview pane.

The backend is 80% ready for this phase. The SSE infrastructure (`/api/jobs/{job_id}/events/stream`), narration log streaming (`/api/jobs/{job_id}/logs/stream`), escalation CRUD endpoints (`GET/POST /escalations/*`, `GET /jobs/{id}/escalations`), and most event types (`agent.sleeping`, `agent.waking`, `agent.waiting_for_input`, `agent.build_paused`, `agent.budget_updated`) are already emitted by the TAOR loop. What is missing from the backend: three new SSE event types (`agent.thinking`, `agent.tool.called`, `gsd.phase.started`, `gsd.phase.completed`), a Redis-backed phase tracking store per job (so phases can be fetched on page load rather than replayed from events), and a REST endpoint to fetch current phases for a job.

The frontend work is entirely new. The existing `/projects/[id]/build/page.tsx` contains a `PreBuildView` (pre-build plan + "Start Build" CTA) and a `BuildPage` (for the non-autonomous pipeline with polling). The new autonomous build view goes on the same route but renders when the job type is autonomous. All new components go under `frontend/src/components/build/` following the established pattern. The stack is locked: Next.js 15, React 19, Tailwind 4, framer-motion 12, lucide-react, shadcn/ui pattern (glass-card + alert-dialog already available).

**Primary recommendation:** Build in four waves — (1) backend new SSE events + phase store API, (2) frontend SSE hooks that consume all event types, (3) Kanban Timeline sidebar + Agent State Badge, (4) Activity Feed with escalation entries. Each wave is independently testable.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Next.js | ^15.0.0 | App framework, routing | Already in use |
| React | ^19.0.0 | UI rendering | Already in use |
| Tailwind CSS | ^4.0.0 | Styling | Already in use |
| framer-motion | ^12.34.0 | Animations, transitions | Already in use (build page, chat) |
| lucide-react | ^0.400.0 | Icons | Already in use |
| canvas-confetti | ^1.9.4 | Build complete celebration | Already installed |
| @clerk/nextjs | ^6.0.0 | Auth / getToken | Already in use |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| sonner | ^2.0.7 | Toast notifications | Push notification fallback, non-critical alerts |
| apiFetch | (internal) | Authenticated fetch wrapper | All API calls — proxied through Next.js rewrites |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| framer-motion AnimatePresence | CSS transitions only | framer-motion already imported; provides cleaner entry/exit for phase cards |
| polling for agent state | SSE only | SSE is already established pattern; polling is fallback only for reconnect |
| Web Push API (browser notifications) | sonner toasts | Web Push is locked decision; sonner for in-app non-critical alerts |

**Installation:**
```bash
# Nothing new needed — all dependencies already in package.json
```

## Architecture Patterns

### Recommended Project Structure
```
frontend/src/
├── app/(dashboard)/projects/[id]/
│   └── build/
│       └── page.tsx                    # MODIFY: add AutonomousBuildView branch
├── components/build/
│   ├── AutonomousBuildView.tsx         # NEW: top-level layout for autonomous build
│   ├── GsdPhaseSidebar.tsx             # NEW: vertical Kanban timeline sidebar
│   ├── GsdPhaseCard.tsx                # NEW: single phase card (expanded/collapsed)
│   ├── AgentActivityFeed.tsx           # NEW: chat-bubble activity feed
│   ├── ActivityFeedEntry.tsx           # NEW: single feed entry with verbose expand
│   ├── EscalationEntry.tsx             # NEW: escalation inline entry with decision buttons
│   ├── AgentStateBadge.tsx             # NEW: floating bottom-right badge + popover
│   └── [existing build components]     # UNCHANGED
└── hooks/
    ├── useAgentEvents.ts               # NEW: SSE event stream consumer
    ├── useAgentPhases.ts               # NEW: GSD phase state slice
    ├── useAgentState.ts                # NEW: agent lifecycle state (working/sleeping/etc.)
    ├── useAgentActivityFeed.ts         # NEW: activity feed state (narrations + tool calls)
    ├── useAgentEscalations.ts          # NEW: escalation CRUD and resolution
    └── [existing hooks]                # UNCHANGED
```

### Pattern 1: SSE Event Consumer Hook
**What:** Single `useAgentEvents` hook subscribes to `/api/jobs/{job_id}/events/stream` and dispatches events to multiple state slices via callbacks.
**When to use:** Single SSE connection shared across all consumers; avoids multiple concurrent connections.
**Example:**
```typescript
// frontend/src/hooks/useAgentEvents.ts
// Follows useBuildLogs.ts pattern (same SSE parsing, apiFetch, AbortController)

type AgentEvent = {
  type: string;
  job_id: string;
  timestamp: string;
  [key: string]: unknown;
};

type EventHandlers = {
  onAgentThinking?: (e: AgentEvent) => void;
  onAgentToolCalled?: (e: AgentEvent) => void;
  onAgentSleeping?: (e: AgentEvent) => void;
  onAgentWaking?: (e: AgentEvent) => void;
  onAgentWaitingForInput?: (e: AgentEvent) => void;
  onAgentBuildPaused?: (e: AgentEvent) => void;
  onAgentBudgetUpdated?: (e: AgentEvent) => void;
  onGsdPhaseStarted?: (e: AgentEvent) => void;
  onGsdPhaseCompleted?: (e: AgentEvent) => void;
  onBuildStageStarted?: (e: AgentEvent) => void;  // existing narration events
};
// Unknown event types: silently ignored (no console.warn, per UIAG-05)
```

### Pattern 2: Page-Level State Composition
**What:** `AutonomousBuildView` owns all state via hooks; child components are pure/presentational.
**When to use:** Keeps state management at top level; allows phase sidebar click to filter feed.
**Example:**
```typescript
// AutonomousBuildView receives jobId, projectId, getToken
// Composes hooks:
const { phases } = useAgentPhases(jobId, getToken);
const { state, elapsedMs, wakeAt, pendingEscalations } = useAgentState(jobId, getToken);
const { entries, isTyping, filterPhaseId } = useAgentActivityFeed(jobId, getToken);
const { escalations, resolve } = useAgentEscalations(jobId, getToken);
// Connects: sidebar phase click → setFilterPhaseId → feed filters
```

### Pattern 3: Backend Phase Store (Redis)
**What:** Agent emits `gsd.phase.started` / `gsd.phase.completed` events via `state_machine.publish_event()`; the phase list is also written to Redis hash `job:{job_id}:phases` so it survives page refresh.
**When to use:** REST endpoint `GET /api/jobs/{job_id}/phases` reads from Redis for initial page load; subsequent updates via SSE.
**Example:**
```python
# In runner_autonomous.py, before each narrate() call for a major phase:
await state_machine.publish_event(job_id, {
    "type": SSEEventType.GSD_PHASE_STARTED,
    "phase_id": "auth_system",
    "phase_name": "Authentication System",
    "phase_description": "Setting up user auth with Clerk",
})
# Also write to Redis:
await redis.hset(f"job:{job_id}:phases", phase_id, json.dumps({...}))
```

### Pattern 4: Activity Feed History on Page Load
**What:** On page mount, fetch full activity history from `/api/jobs/{job_id}/logs` REST endpoint (existing); then subscribe to SSE for live updates. Follows useBuildLogs.ts loadEarlier pattern.
**When to use:** Avoids losing history on page refresh; SSE-only feed would lose all history.

### Pattern 5: Per-Entry Verbose Expand
**What:** Each `ActivityFeedEntry` has local `expanded` state; no global verbose toggle.
**When to use:** Per CONTEXT.md decision — per-entry expand arrow, not global toggle.
**Example:**
```typescript
// ActivityFeedEntry.tsx
const [verboseOpen, setVerboseOpen] = useState(false);
// Shows narration text by default
// Expand arrow reveals tool_call details (human label + summary, NOT raw JSON)
```

### Anti-Patterns to Avoid
- **Multiple SSE connections:** Only one `useAgentEvents` hook per page instance. All state slices receive dispatched events from a single connection.
- **Global verbose mode:** Context.md locked this as per-entry expand. Do not add a global toggle.
- **Polling agent state:** Agent state comes from SSE events. Polling is only a fallback for initial load on page mount.
- **Rendering raw JSON tool_use blocks:** Verbose entries MUST show human-readable labels, not raw JSON.
- **Closing SSE on terminal job status:** Unlike useBuildLogs, agent events stream stays open while agent is sleeping (not terminal). Only close when job reaches `ready` or `failed`.
- **Blocking feed scroll on new entries:** Auto-scroll halts when user scrolls up. Track a `userScrolledUp` ref to prevent forced scroll.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Animated dots typing indicator | Custom CSS | Tailwind CSS `animate-pulse` or framer-motion | 3-dot sequence is 1-2 lines with animate-bounce stagger |
| Countdown timer | Custom time math | `setInterval` + `Date.now()` relative to `wake_at` field from SSE event | Simple, already in codebase for other timers |
| Confetti on build complete | Custom particle system | `canvas-confetti` (already installed) | Already a dependency |
| SSE reconnection | Custom retry loop | Follow `useBuildLogs.ts` pattern + `useEffect` cleanup | Established codebase pattern |
| Elapsed time display | Custom | `setInterval` + elapsed_ms tracking from phase start time | Same pattern as build page elapsed time display |
| Popover for agent state badge | Build custom | `@radix-ui/react-popover` via shadcn pattern or framer-motion AnimatePresence | AlertDialog pattern already used in build page |

**Key insight:** The hardest parts of this phase are data modeling (what events carry what data) and SSE event routing, not UI animations. Use existing Tailwind/framer-motion primitives for all visual polish.

## Common Pitfalls

### Pitfall 1: SSE Stream Not Closing for Sleeping Agent
**What goes wrong:** If the frontend closes SSE connection on `agent.sleeping` event (like it does for `ready`/`failed`), the founder never sees the wake event and the UI gets stuck showing "Sleeping".
**Why it happens:** Copying the terminal-state-close pattern from `useBuildLogs.ts` without recognizing sleeping is a transient state.
**How to avoid:** Only close SSE when job status is `ready` or `failed`. Agent sleeping/waking are lifecycle transitions, not terminal states.
**Warning signs:** Badge stuck at "Sleeping" after wake event arrives.

### Pitfall 2: Phase List Disappears on Page Refresh
**What goes wrong:** Phase sidebar is blank when founder returns to a running build, even though the agent is mid-build.
**Why it happens:** If phases only exist in SSE event history (not persisted), a page refresh loses them.
**How to avoid:** Backend must write phase data to Redis hash `job:{job_id}:phases` on `gsd.phase.started`. REST endpoint `GET /api/jobs/{job_id}/phases` reads from this hash. Frontend loads phases via REST on mount, then updates via SSE events.
**Warning signs:** Empty sidebar on refresh but correct state in floating badge.

### Pitfall 3: Feed Entry ID Collisions
**What goes wrong:** React key collisions cause entries to flicker or duplicate.
**Why it happens:** SSE events have timestamps but may arrive in batches; using index as key causes re-renders.
**How to avoid:** Use `entry.id` = Redis stream entry ID (from xadd which returns a unique `{ms}-{seq}` ID). Backend must include this ID in log events.
**Warning signs:** Activity feed flickering or showing duplicate entries.

### Pitfall 4: Escalation In-Place Update
**What goes wrong:** After founder resolves escalation, the entry still shows decision buttons.
**Why it happens:** Frontend doesn't update local state after `POST /escalations/{id}/resolve` succeeds.
**How to avoid:** After successful resolve API call, update the local entry in `useAgentEscalations` state to `status: "resolved"` and hide buttons. The backend also emits `agent.escalation_resolved` SSE event as a confirmation signal.
**Warning signs:** Resolved escalation still shows active buttons on same page load.

### Pitfall 5: Three-Column Layout Breaking on Narrow Viewport
**What goes wrong:** Three-column layout (sidebar + feed + preview) overflows on smaller desktop widths.
**Why it happens:** Fixed 280px sidebar + min preview width + feed leaves no room.
**How to avoid:** Preview panel is toggle-only (not default). Default layout is two-column (sidebar + feed). Sidebar collapses below 768px per locked decision.
**Warning signs:** Horizontal scrollbar on 1280px screens.

### Pitfall 6: New SSE Events Rejected by Old Frontend Code
**What goes wrong:** Adding `gsd.phase.started` event to backend breaks existing frontend that doesn't handle it.
**Why it happens:** Frontend hook tries to parse or route every event type.
**How to avoid:** `useAgentEvents` must silently ignore unknown event types (UIAG-05). Already the case in `useBuildLogs.ts` — apply same pattern. Existing `build.stage.started` events continue working unchanged.
**Warning signs:** TypeScript errors or runtime crashes when new event type arrives.

### Pitfall 7: Agent State from SSE vs. REST Bootstrap
**What goes wrong:** Floating badge shows wrong initial state (e.g., "Working" when agent is sleeping) until first SSE event arrives.
**Why it happens:** SSE only delivers events going forward — misses state set before SSE connect.
**How to avoid:** On mount, fetch current agent state via REST `GET /api/jobs/{job_id}/status` (existing endpoint has `status` field) AND a new `GET /api/jobs/{job_id}/agent-state` endpoint that reads `cofounder:agent:{session_id}:state` from Redis. Fall back to "Building" if unknown.
**Warning signs:** Badge briefly shows "Building" then jumps to "Sleeping" on page load for a sleeping agent.

## Code Examples

Verified patterns from codebase:

### SSE Consumer Pattern (from useBuildLogs.ts)
```typescript
// frontend/src/hooks/useAgentEvents.ts
// Source: /Users/vladcortex/co-founder/frontend/src/hooks/useBuildLogs.ts

const connectSSE = useCallback(async () => {
  const controller = new AbortController();
  abortRef.current = controller;

  let response: Response;
  try {
    response = await apiFetch(`/api/jobs/${jobId}/events/stream`, getToken, {
      signal: controller.signal,
    });
  } catch (err) {
    if ((err as Error).name === "AbortError") return;
    return;
  }

  const reader = response.body!.getReader();
  const decoder = new TextDecoder("utf-8", { fatal: false });
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const blocks = buffer.split("\n\n");
    buffer = blocks.pop() ?? "";

    for (const block of blocks) {
      let eventType = "message";
      let dataStr = "";
      for (const line of block.split("\n")) {
        if (line.startsWith("event:")) eventType = line.slice(6).trim();
        else if (line.startsWith("data:")) dataStr = line.slice(5).trim();
      }
      if (eventType === "heartbeat") continue;

      let event: AgentEvent;
      try { event = JSON.parse(dataStr); }
      catch { continue; }  // silently ignore malformed

      // Route by type — unknown types silently ignored (UIAG-05)
      switch (event.type) {
        case "agent.thinking": handlers.onAgentThinking?.(event); break;
        case "agent.tool.called": handlers.onAgentToolCalled?.(event); break;
        case "agent.sleeping": handlers.onAgentSleeping?.(event); break;
        case "agent.waking": handlers.onAgentWaking?.(event); break;
        case "agent.waiting_for_input": handlers.onAgentWaitingForInput?.(event); break;
        case "agent.build_paused": handlers.onAgentBuildPaused?.(event); break;
        case "agent.budget_updated": handlers.onAgentBudgetUpdated?.(event); break;
        case "gsd.phase.started": handlers.onGsdPhaseStarted?.(event); break;
        case "gsd.phase.completed": handlers.onGsdPhaseCompleted?.(event); break;
        case "build.stage.started": handlers.onBuildStageStarted?.(event); break;
        // default: silently ignored
      }
    }
  }
}, [jobId, getToken, handlers]);
```

### Backend New SSE Event Types (extends state_machine.py)
```python
# backend/app/queue/state_machine.py — add to SSEEventType class
GSD_PHASE_STARTED = "gsd.phase.started"
GSD_PHASE_COMPLETED = "gsd.phase.completed"
AGENT_THINKING = "agent.thinking"
AGENT_TOOL_CALLED = "agent.tool.called"
```

### Backend Phase Tracking (runner_autonomous.py emit point)
```python
# Emit gsd.phase.started before each major agent phase narration
# Payload: {type, job_id, phase_id, phase_name, phase_description, timestamp}
if state_machine:
    await state_machine.publish_event(job_id, {
        "type": SSEEventType.GSD_PHASE_STARTED,
        "phase_id": "auth_system",
        "phase_name": "Authentication System",
        "phase_description": "...",
    })
# Write to Redis hash for persistence:
if redis:
    await redis.hset(f"job:{job_id}:phases", "auth_system", json.dumps({...}))
```

### Backend agent.thinking + agent.tool.called (runner_autonomous.py)
```python
# agent.thinking: emit before THINK step (before self._client.messages.stream call)
if state_machine:
    await state_machine.publish_event(job_id, {"type": "agent.thinking"})

# agent.tool.called: emit after successful dispatcher.dispatch()
if state_machine:
    await state_machine.publish_event(job_id, {
        "type": SSEEventType.AGENT_TOOL_CALLED,
        "tool_name": tool_name,
        "tool_label": _human_tool_label(tool_name, tool_input),
        "tool_summary": _summarize_tool_result(result),
    })
```

### Resolve Escalation API (from escalations.py)
```typescript
// POST /api/escalations/{id}/resolve
const res = await apiFetch(
  `/api/escalations/${escalationId}/resolve`,
  getToken,
  {
    method: "POST",
    body: JSON.stringify({ decision: "provide_guidance", guidance: "..." }),
  }
);
```

### Typing Indicator with framer-motion
```typescript
// Three animated dots — framer-motion stagger
<AnimatePresence>
  {isTyping && (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="flex items-center gap-1 px-4 py-2"
    >
      {[0, 1, 2].map((i) => (
        <motion.span
          key={i}
          className="w-2 h-2 rounded-full bg-white/40"
          animate={{ y: [0, -4, 0] }}
          transition={{ repeat: Infinity, duration: 0.6, delay: i * 0.15 }}
        />
      ))}
    </motion.div>
  )}
</AnimatePresence>
```

### Web Push Notification Permission
```typescript
// Trigger on first escalation arrival, not during onboarding
// Only fires if Notification.permission === "default"
if ("Notification" in window && Notification.permission === "default") {
  const permission = await Notification.requestPermission();
  if (permission === "granted") {
    new Notification("Your co-founder needs your help", {
      body: "A permission issue needs your decision.",
      icon: "/icon.png",
    });
  }
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| LangGraph pipeline (RunnerReal) | TAOR loop (AutonomousRunner) | Phase 40 | Existing `/projects/[id]/build` page was built for old pipeline; needs new AutonomousBuildView branch |
| Stage-based build (queued/scaffold/code/deps) | Phase-based build (GSD phases) | Phase 46 | Kanban Timeline replaces build stage progress bar for autonomous builds |
| Global verbose mode consideration | Per-entry expand | Phase 46 CONTEXT.md | No global toggle needed |
| Modal for escalations | Inline feed entries | Phase 46 CONTEXT.md | Escalations appear in feed, not as blocking modal overlay |

**Deprecated/outdated for autonomous builds:**
- `BuildProgressBar` component: not used in autonomous view (shows stage progression, not GSD phases)
- `STAGE_ORDER` / `STAGE_LABELS` from `useBuildProgress.ts`: irrelevant for autonomous build monitoring
- Polling pattern from `useBuildProgress.ts`: autonomous view uses SSE + event-driven state

## Open Questions

1. **How does the agent know which GSD phase it's in?**
   - What we know: `context.get("current_phase")` is passed to `run_agent_loop()` but is currently `None` in practice. The agent narrates phase transitions via `narrate()` tool.
   - What's unclear: Should `gsd.phase.started` / `gsd.phase.completed` be emitted by the agent itself (via the `narrate()` tool detecting phase-level narrations) or by the runner wrapping the dispatcher?
   - Recommendation: The agent calls `narrate()` at phase boundaries (per system prompt instructions). The dispatcher's `_narrate()` method should detect phase-level narrations and emit `gsd.phase.started` when `tone: "phase_start"` is included in the tool call. Alternatively — simpler — add a `phase_name` parameter to the `narrate()` tool definition so the agent explicitly signals phase transitions.

2. **REST endpoint for initial phase load on page refresh**
   - What we know: Phases must be loadable on page refresh (cannot rely on SSE replay). Redis hash `job:{job_id}:phases` is the proposed storage.
   - What's unclear: Whether to add a new `/api/jobs/{job_id}/phases` endpoint or extend the existing `/api/jobs/{job_id}` response.
   - Recommendation: Add `GET /api/jobs/{job_id}/phases` endpoint (consistent with `/api/jobs/{job_id}/escalations` pattern already in escalations.py).

3. **Initial agent state REST endpoint**
   - What we know: `cofounder:agent:{session_id}:state` Redis key exists but there's no REST endpoint to read it. The session_id = job_id in current implementation.
   - What's unclear: Whether `GET /api/jobs/{job_id}/status` should be extended with agent_state or a new endpoint created.
   - Recommendation: Extend `GET /api/jobs/{job_id}/status` response to include `agent_state` field (reads `cofounder:agent:{job_id}:state` from Redis). Minimal backend change, no new route.

4. **Token budget remaining in agent state popover**
   - What we know: `agent.budget_updated` event carries `budget_pct`. AgentCheckpoint stores `session_cost_microdollars` and `daily_budget_microdollars`.
   - What's unclear: Is the `budget_pct` in SSE events sufficient, or does the popover need a REST call?
   - Recommendation: Track last-seen `budget_pct` from `agent.budget_updated` events in `useAgentState` hook. No REST call needed; the SSE events are sufficient for the popover display.

## Sources

### Primary (HIGH confidence)
- Codebase: `/Users/vladcortex/co-founder/backend/app/queue/state_machine.py` — SSEEventType constants, publish_event() API, existing event types
- Codebase: `/Users/vladcortex/co-founder/backend/app/agent/runner_autonomous.py` — TAOR loop, emit points, agent state Redis keys
- Codebase: `/Users/vladcortex/co-founder/backend/app/api/routes/escalations.py` — Escalation CRUD API, request/response schemas
- Codebase: `/Users/vladcortex/co-founder/backend/app/db/models/agent_escalation.py` — AgentEscalation model fields
- Codebase: `/Users/vladcortex/co-founder/backend/app/db/models/agent_checkpoint.py` — agent_state field values
- Codebase: `/Users/vladcortex/co-founder/frontend/src/hooks/useBuildLogs.ts` — SSE consumer pattern, apiFetch, AbortController
- Codebase: `/Users/vladcortex/co-founder/frontend/src/app/(dashboard)/projects/[id]/build/page.tsx` — Existing build page, PreBuildView pattern
- Codebase: `/Users/vladcortex/co-founder/frontend/src/components/build/` — Existing build components pattern
- Codebase: `/Users/vladcortex/co-founder/frontend/src/components/timeline/` — Existing KanbanBoard, TimelineItem type
- Codebase: `/Users/vladcortex/co-founder/frontend/src/components/decision-gates/DecisionGateModal.tsx` — Existing decision UI pattern
- Codebase: `/Users/vladcortex/co-founder/frontend/src/app/globals.css` — Brand colors, animation keyframes, design system tokens

### Secondary (MEDIUM confidence)
- Context7 / knowledge: Web Notifications API — requestPermission() + new Notification() constructor
- Context7 / knowledge: framer-motion AnimatePresence + stagger for typing indicator

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all dependencies verified in package.json and active codebase usage
- Architecture: HIGH — patterns verified from existing useBuildLogs.ts, escalations.py, state_machine.py
- Pitfalls: HIGH — all identified from actual codebase patterns and CONTEXT.md decisions
- Open questions: MEDIUM — implementation options, not blockers

**Research date:** 2026-03-01
**Valid until:** 2026-04-01 (stable stack; dependencies unlikely to change in 30 days)
