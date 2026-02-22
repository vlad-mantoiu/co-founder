# Phase 30: Frontend Build UX - Research

**Researched:** 2026-02-22
**Domain:** React 19, Next.js 15, fetch + ReadableStreamDefaultReader SSE, framer-motion 12, lucide-react, canvas-confetti
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### Stage presentation
- Horizontal segmented progress bar across the top of the build page
- Friendly plain-English labels with icons (no emojis): Designing, Writing code, Installing dependencies, Starting app, Ready
- Smooth transitions: active segment fills/pulses, completed segments get a checkmark animation
- Elapsed time counter shown during the build ("Building... 0:42") — no estimates or predictions

#### Log panel design
- Collapsed by default behind a "Technical details" expander — non-technical founders don't need npm output
- Color-coded by source: stderr in red/orange, stdout in default, system events in blue/muted
- Auto-scroll to latest line when open

#### Auto-fix feedback
- Separate yellow/orange banner above the stage bar: "We found an issue and are fixing it automatically (attempt 2 of 5)"
- Reassuring tone — founder shouldn't worry. Calm, confident messaging
- Stage bar resets/rewinds to the failing stage when a retry starts — visually shows the retry is re-running that part
- Attempt counter visible and incrementing in the banner

#### Failure experience
- Short friendly error message at top + expandable "What went wrong" section with sanitized error info
- Recovery actions: "Try again" button and "Contact support" link — two clear paths
- Log panel stays collapsed on failure — error summary is enough, founder can expand manually if curious

#### Success experience
- Celebration moment: confetti or animation, "Your app is live!" with prominent preview button
- Reward the wait — this is the payoff of the entire flow

#### Prior decision (from additional context)
- Use fetch() + ReadableStreamDefaultReader for SSE — ALB/Service Connect kills native EventSource at 15s

### Claude's Discretion
- Log panel layout approach (bottom drawer vs inline expandable) — pick what works best with the stage bar
- "Load earlier" button for history vs live-only — decide based on Phase 29 backend capabilities (REST pagination endpoint exists)
- Whether auto-fix system lines appear in the log panel — LogStreamer already emits system events, decide if they add value

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| BUILD-02 | Frontend log panel — expandable raw log panel in build UI with auto-scroll, fetch-based SSE (not EventSource) | Phase 29 provides `GET /api/jobs/{id}/logs/stream` (SSE) and `GET /api/jobs/{id}/logs` (REST pagination). The existing `useAgentStream.ts` hook proves fetch + ReadableStreamDefaultReader works in this codebase. A new `useBuildLogs` hook is needed that handles named SSE events (`event: log`, `event: heartbeat`, `event: done`). |
| BUILD-03 | Build progress stages — high-level stage indicators (Designing → Writing code → Installing deps → Starting app → Ready) | `useBuildProgress.ts` already polls `GET /api/generation/{job_id}/status` and returns `status` + `stageIndex`. Existing `BuildProgressBar.tsx` exists but uses circles/nodes. Decision requires refactoring to a horizontal segmented bar with icons. Stage mapping: current STAGE_ORDER = [queued, starting, scaffold, code, deps, checks, ready]. The 5 user-facing labels map to: scaffold="Designing", code="Writing code", deps="Installing dependencies", checks/starting="Starting app", ready="Ready". |
| BUILD-04 | Auto-retry visibility — distinct "Auto-fixing..." UI state when Debugger agent retries, attempt counter display | The backend agent `debugger_node` updates `retry_count` in state on each attempt (max 5). The `system` source log lines from `LogStreamer.write_event()` are already emitted at stage transitions. The auto-fix signal must come from the SSE log stream — a `system`-source log line matching "Auto-fixing" pattern, OR a new dedicated `event: autofix` SSE event emitted from the generation service when the debugger runs. This is the key open question: detection mechanism from stream. |
</phase_requirements>

---

## Summary

Phase 30 is a pure frontend phase. The backend SSE endpoint (`GET /api/jobs/{id}/logs/stream`) and REST pagination endpoint (`GET /api/jobs/{id}/logs`) are already built and verified by Phase 29. Phase 30 connects the build page to these endpoints and renders the output as a polished UI experience.

The build page (`/projects/[id]/build`) already exists with a `useBuildProgress` hook (polling status every 5s) and a `BuildProgressBar` component (circle-node stepper). Phase 30 replaces the visual design of `BuildProgressBar` to match the decided horizontal segmented bar, adds a `useBuildLogs` hook consuming the SSE log stream, adds the "Technical details" collapsible panel, the auto-fix banner, the elapsed timer, the confetti success celebration, and updates `BuildFailureCard` to add a "Contact support" link.

The key architectural insight: Phase 30 runs two parallel data sources — the existing 5s polling status hook (for stage advancement) and the new SSE log hook (for raw log lines). The stage bar is driven by the polling hook, not the SSE stream. The SSE stream feeds the log panel only. The auto-fix banner is driven by detecting `system`-source lines with "Auto-fixing" content in the SSE stream.

**Primary recommendation:** Implement `useBuildLogs` as a fetch + ReadableStreamDefaultReader hook following the existing `useAgentStream.ts` pattern, add proper named-event parsing (event + data field extraction), and wire it into a refactored `BuildProgressBar` + new `BuildLogPanel` + new `AutoFixBanner`. Use `canvas-confetti` for success celebration. No new backend changes needed — all required APIs exist from Phase 29.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `framer-motion` | 12.34.0 (installed) | Stage bar animations, panel expand/collapse, success moment | Already the project animation library; used in all existing build components |
| `lucide-react` | ^0.400.0 (installed) | Stage icons (Wand2, Code2, Package, Play, CheckCircle2, Wrench, Sparkles) | Already the project icon library; verified icons exist in installed version |
| `canvas-confetti` | 1.x (not installed, needs npm install) | Confetti burst on build success | Lightweight (7KB gzipped), framework-agnostic, TypeScript typings bundled — de-facto standard for celebration moments |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| React `useRef`, `useEffect`, `useCallback` | React 19 (installed) | Auto-scroll in log panel, SSE reader lifecycle | Standard React primitives — no library needed |
| `cn()` from `@/lib/utils` | (installed) | Conditional class merging | Already used across all components |
| `apiFetch` from `@/lib/api` | (installed) | Authenticated fetch wrapper with Clerk JWT | Already handles token injection; use for SSE fetch |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `canvas-confetti` | framer-motion particle burst | framer-motion has no built-in confetti; hand-rolling particle animation is 200+ lines. canvas-confetti is 7KB and designed exactly for this. Use canvas-confetti. |
| `canvas-confetti` | `react-confetti` | react-confetti fills the viewport, is heavier (SVG-based), and less customizable. canvas-confetti gives burst control (fireworks, cannons). Use canvas-confetti. |
| Polling for auto-fix signal | Dedicated SSE event type | System log lines are already emitted by LogStreamer. Parsing them avoids any backend change. Use system log parsing (see Architecture Patterns). |
| Full SSE log stream for stage bar | Keep existing polling | The polling hook already works and is tested. Stage advancement from SSE would be a big refactor with no user benefit. Keep polling for stages, SSE for logs only. |

**Installation:**
```bash
npm install canvas-confetti
npm install --save-dev @types/canvas-confetti
```

---

## Architecture Patterns

### File Structure (new and modified files)

```
frontend/src/
├── hooks/
│   ├── useBuildProgress.ts       # EXISTING — no changes needed (polling status)
│   └── useBuildLogs.ts           # NEW — SSE log streaming + "load earlier" REST
├── components/build/
│   ├── BuildProgressBar.tsx      # MODIFY — horizontal segmented bar, icons, elapsed timer
│   ├── BuildLogPanel.tsx         # NEW — collapsible Technical details panel
│   ├── AutoFixBanner.tsx         # NEW — yellow/orange retry banner
│   ├── BuildSummary.tsx          # MODIFY — add confetti trigger on mount
│   └── BuildFailureCard.tsx      # MODIFY — add "Contact support" link
└── app/(dashboard)/projects/[id]/build/
    └── page.tsx                  # MODIFY — wire up useBuildLogs, AutoFixBanner, BuildLogPanel
```

### Pattern 1: useBuildLogs Hook — Named SSE Event Parsing

The existing `useAgentStream.ts` only parses `data:` prefix lines. The Phase 29 SSE endpoint emits named events:
- `event: log\ndata: {"ts":"...","source":"stdout|stderr|system","text":"...","phase":"..."}\n\n`
- `event: heartbeat\ndata: {}\n\n`
- `event: done\ndata: {"status":"ready|failed"}\n\n`

The hook must parse both `event:` and `data:` fields from each SSE block (blocks separated by `\n\n`):

```typescript
// Source: Derived from existing useAgentStream.ts pattern + SSE spec (named events)
// File: frontend/src/hooks/useBuildLogs.ts
"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { apiFetch } from "@/lib/api";

export interface LogLine {
  id: string;       // Redis Stream message ID
  ts: string;       // ISO timestamp
  source: "stdout" | "stderr" | "system";
  text: string;
  phase: string;
}

export interface BuildLogsState {
  lines: LogLine[];
  isConnected: boolean;
  isDone: boolean;
  doneStatus: "ready" | "failed" | null;
  hasEarlierLines: boolean;   // REST endpoint returned has_more=true
  oldestId: string | null;    // Cursor for "Load earlier"
  autoFixAttempt: number | null;  // null = no auto-fix in progress; 1-5 = active attempt
}

export function useBuildLogs(
  jobId: string | null,
  getToken: () => Promise<string | null>,
): BuildLogsState & {
  loadEarlier: () => Promise<void>;
} {
  const [lines, setLines] = useState<LogLine[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [isDone, setIsDone] = useState(false);
  const [doneStatus, setDoneStatus] = useState<"ready" | "failed" | null>(null);
  const [hasEarlierLines, setHasEarlierLines] = useState(false);
  const [oldestId, setOldestId] = useState<string | null>(null);
  const [autoFixAttempt, setAutoFixAttempt] = useState<number | null>(null);

  const readerRef = useRef<ReadableStreamDefaultReader<Uint8Array> | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const connectSSE = useCallback(async () => {
    if (!jobId) return;

    abortRef.current = new AbortController();

    try {
      const response = await apiFetch(`/api/jobs/${jobId}/logs/stream`, getToken, {
        signal: abortRef.current.signal,
      });

      if (!response.ok || !response.body) return;

      setIsConnected(true);
      const reader = response.body.getReader();
      readerRef.current = reader;
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        // SSE events are separated by \n\n
        const blocks = buffer.split("\n\n");
        buffer = blocks.pop() ?? "";

        for (const block of blocks) {
          if (!block.trim()) continue;

          // Parse event type and data from block lines
          let eventType = "message";
          let dataStr = "";

          for (const line of block.split("\n")) {
            if (line.startsWith("event: ")) {
              eventType = line.slice(7).trim();
            } else if (line.startsWith("data: ")) {
              dataStr = line.slice(6).trim();
            }
          }

          if (eventType === "heartbeat") continue;  // no-op

          if (eventType === "done") {
            try {
              const payload = JSON.parse(dataStr) as { status: "ready" | "failed" };
              setDoneStatus(payload.status);
            } catch {}
            setIsDone(true);
            setIsConnected(false);
            return;
          }

          if (eventType === "log" && dataStr) {
            try {
              const line = JSON.parse(dataStr) as LogLine;
              setLines((prev) => [...prev, line]);

              // Detect auto-fix attempt from system lines
              // Example: "--- Auto-fixing (attempt 2 of 5) ---"
              if (line.source === "system") {
                const match = line.text.match(/auto.fix.*?attempt\s+(\d+)\s+of\s+(\d+)/i);
                if (match) {
                  setAutoFixAttempt(parseInt(match[1], 10));
                }
                // Clear auto-fix banner when returning to normal stage
                if (/running health checks|starting dev server/i.test(line.text)) {
                  setAutoFixAttempt(null);
                }
              }
            } catch {}
          }
        }
      }
    } catch (err) {
      if ((err as Error).name === "AbortError") return;
      setIsConnected(false);
    }
  }, [jobId, getToken]);

  useEffect(() => {
    if (!jobId) return;
    connectSSE();
    return () => {
      abortRef.current?.abort();
      readerRef.current?.cancel();
    };
  }, [jobId, connectSSE]);

  // "Load earlier" — fetch historical lines via REST pagination
  const loadEarlier = useCallback(async () => {
    if (!jobId || !oldestId) return;
    try {
      const res = await apiFetch(
        `/api/jobs/${jobId}/logs?before_id=${encodeURIComponent(oldestId)}&limit=100`,
        getToken,
      );
      if (!res.ok) return;
      const data = await res.json() as {
        lines: LogLine[];
        has_more: boolean;
        oldest_id: string | null;
      };
      setLines((prev) => [...data.lines, ...prev]);  // prepend
      setHasEarlierLines(data.has_more);
      setOldestId(data.oldest_id);
    } catch {}
  }, [jobId, getToken, oldestId]);

  return {
    lines,
    isConnected,
    isDone,
    doneStatus,
    hasEarlierLines,
    oldestId,
    autoFixAttempt,
    loadEarlier,
  };
}
```

**Key insight:** The SSE block parsing (`buffer.split("\n\n")`) is critical. Incomplete blocks must be retained in `buffer`. Both `event:` and `data:` fields must be parsed from each block. The existing `useAgentStream.ts` only handles `data:` prefix — it cannot be reused for named events.

### Pattern 2: Auto-Fix Signal Detection

The backend `debugger_node` in `app/agent/nodes/debugger.py` updates `retry_count` and emits `status_message = "Debug analysis complete (attempt N/max_retries)"`. The `GenerationService.execute_build()` runs `self.runner.run(agent_state)` which is the full agent graph. When the graph cycles through the debugger, it emits log lines via `LogStreamer.write_event()`.

**Key finding:** The `LogStreamer.write_event()` with `source="system"` is already called at stage transitions, but the debugger cycling through the graph happens inside `self.runner.run()` — the LogStreamer is not directly wired into the agent graph loop. System events marking debugger retries do NOT currently exist.

**Resolution:** Two options:
1. Add a `system` log line from `generation_service.py` after the runner finishes if `final_state.get("retry_count") > 0` — post-hoc signal (misses intermediate retries)
2. Emit system lines from within the runner's streaming callback, if the runner supports progress events (check if needed)

**Recommended approach for Phase 30:** Parse the existing `status_message` from the job status polling. The `GenerationStatusResponse` already includes `stage_label` from the state machine. A simpler path is to check if `stage_label` contains "attempt" from the debugger's status message: `"Debug analysis complete (attempt 2/5)"` — this is set via `state_machine.transition(job_id, status, message)` on each status update, but debugger runs inside `runner.run()` so it does NOT transition the state machine.

**Revised resolution — the simplest correct approach:**
- In `generation_service.py`, after `await self.runner.run(agent_state)`, check `final_state.get("retry_count", 0)`. If > 0, emit a system log line: `await streamer.write_event(f"--- Auto-fixing (attempt {final_state['retry_count']} of {final_state['max_retries']}) ---")`.
- BUT this happens after the run completes — too late for live display.

**The real solution:** Phase 30 must add a callback mechanism in `GenerationService.execute_build()` that emits an intermediate system event BEFORE `runner.run()` returns, specifically when the debugger node runs. This requires either:
a. Streaming mode in the runner that yields per-node events (complex, multi-phase work)
b. Detecting auto-fix from the final_state `retry_count` and surfacing it in the next status poll

**Pragmatic Phase 30 approach:** Add `retry_count` to the `GenerationStatusResponse` from `GET /api/generation/{job_id}/status` by reading it from job data in Redis. When `retry_count > 0` on a non-terminal status, the frontend shows the auto-fix banner. This avoids SSE complexity and leverages the existing 5s polling loop.

**Confidence:** MEDIUM — this requires a small backend change (add `retry_count` field to the status endpoint), but it's the most reliable detection mechanism.

### Pattern 3: BuildLogPanel — Collapsible with Auto-Scroll

```typescript
// File: frontend/src/components/build/BuildLogPanel.tsx
// Source: Derived from existing TerminalOutput.tsx auto-scroll pattern + Radix collapsible
"use client";

import { useRef, useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ChevronDown, ChevronUp, LoaderCircle } from "lucide-react";
import { cn } from "@/lib/utils";
import type { LogLine } from "@/hooks/useBuildLogs";

interface BuildLogPanelProps {
  lines: LogLine[];
  isConnected: boolean;
  hasEarlierLines: boolean;
  onLoadEarlier: () => Promise<void>;
}

export function BuildLogPanel({ lines, isConnected, hasEarlierLines, onLoadEarlier }: BuildLogPanelProps) {
  const [open, setOpen] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new lines arrive and panel is open
  useEffect(() => {
    if (open && bottomRef.current) {
      bottomRef.current.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }
  }, [lines.length, open]);

  return (
    <div className="w-full mt-4">
      <button
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center justify-between px-4 py-2.5 rounded-xl
                   bg-white/5 hover:bg-white/8 border border-white/10
                   text-sm text-white/50 hover:text-white/70 transition-colors"
      >
        <span className="flex items-center gap-2">
          {isConnected && <LoaderCircle className="w-3.5 h-3.5 animate-spin text-white/30" />}
          Technical details
        </span>
        {open ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
      </button>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.25, ease: "easeInOut" }}
            className="overflow-hidden"
          >
            <div className="mt-2 rounded-xl bg-black/40 border border-white/8 overflow-hidden">
              {/* Load earlier button */}
              {hasEarlierLines && (
                <button
                  onClick={onLoadEarlier}
                  className="w-full py-2 text-xs text-white/30 hover:text-white/50 text-center
                             border-b border-white/5 transition-colors"
                >
                  Load earlier output
                </button>
              )}

              {/* Log lines */}
              <div className="overflow-y-auto max-h-64 p-3 font-mono text-xs leading-relaxed">
                {lines.map((line) => (
                  <div
                    key={line.id}
                    className={cn(
                      "py-0.5 pl-2 border-l-2",
                      line.source === "stderr"  && "border-orange-500/60 text-orange-300/80",
                      line.source === "system"  && "border-blue-500/40 text-blue-300/60",
                      line.source === "stdout"  && "border-transparent text-white/60",
                    )}
                  >
                    {line.text}
                  </div>
                ))}
                <div ref={bottomRef} />
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
```

**Layout decision (Claude's Discretion):** Inline expandable below the stage bar. A bottom drawer would cover the stage bar and confuse the visual hierarchy. Inline expandable keeps the stage bar always visible and the log panel is subordinate.

**"Load earlier" decision (Claude's Discretion):** YES — include the "Load earlier" button. Phase 29's REST endpoint (`GET /api/jobs/{id}/logs`) with `before_id` cursor pagination is ready. Founders who open the log panel after the build starts will miss earlier output — "Load earlier" gives them access to it. Wire it to the `loadEarlier()` callback from `useBuildLogs`.

**System events in log panel (Claude's Discretion):** YES — show system events in the log panel. They provide meaningful context (stage transitions like "--- Installing dependencies ---"). Color them blue/muted so they read as informational, not errors. This helps technical founders understand the build flow.

### Pattern 4: AutoFixBanner Component

```typescript
// File: frontend/src/components/build/AutoFixBanner.tsx
"use client";

import { motion } from "framer-motion";
import { Wrench } from "lucide-react";

interface AutoFixBannerProps {
  attempt: number;    // 1-5
  maxAttempts: number; // default 5
}

export function AutoFixBanner({ attempt, maxAttempts = 5 }: AutoFixBannerProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: -8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -8 }}
      transition={{ duration: 0.3 }}
      className="w-full mb-4 px-4 py-3 rounded-xl
                 bg-amber-500/10 border border-amber-500/25
                 flex items-center gap-3"
    >
      <Wrench className="w-4 h-4 text-amber-400 flex-shrink-0" />
      <div className="flex-1 min-w-0">
        <p className="text-sm text-amber-300 font-medium">
          We found a small issue and are fixing it automatically
        </p>
        <p className="text-xs text-amber-400/70 mt-0.5">
          Attempt {attempt} of {maxAttempts} — this is normal, sit tight
        </p>
      </div>
    </motion.div>
  );
}
```

### Pattern 5: Stage Bar — Horizontal Segmented with Icons

The current `BuildProgressBar.tsx` uses circles and connectors. Phase 30 replaces this with a horizontal segmented bar. The stage mapping to user-facing labels:

```typescript
// Map from backend status values to user-facing labels + icons
// Backend stages in STAGE_ORDER: queued, starting, scaffold, code, deps, checks, ready
// User-facing BUILD-03 stages: Designing, Writing code, Installing dependencies, Starting app, Ready

import { Wand2, Code2, Package, Play, CheckCircle2 } from "lucide-react";

const STAGE_BAR_ITEMS = [
  { key: "scaffold",  label: "Designing",               icon: Wand2 },
  { key: "code",      label: "Writing code",             icon: Code2 },
  { key: "deps",      label: "Installing dependencies",  icon: Package },
  { key: "checks",    label: "Starting app",             icon: Play },
  { key: "ready",     label: "Ready",                    icon: CheckCircle2 },
] as const;

// A stage is "complete" if stageIndex > its index in STAGE_BAR_ITEMS
// A stage is "active" if stageIndex === its index
// A stage is "pending" if stageIndex < its index
// stageIndex comes from useBuildProgress → statusToStageIndex(status)
// Adjust: scaffold=index 2 in STAGE_ORDER, so offset by 2
```

**Elapsed timer implementation:**
```typescript
// In build page or useBuildProgress — simple elapsed counter
const [elapsed, setElapsed] = useState(0);
const startTimeRef = useRef<number | null>(null);

useEffect(() => {
  if (isBuilding && !startTimeRef.current) {
    startTimeRef.current = Date.now();
  }
  if (!isBuilding) return;
  const interval = setInterval(() => {
    if (startTimeRef.current) {
      setElapsed(Math.floor((Date.now() - startTimeRef.current) / 1000));
    }
  }, 1000);
  return () => clearInterval(interval);
}, [isBuilding]);

// Format elapsed: "0:42" — minutes:seconds
function formatElapsed(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}:${String(s).padStart(2, "0")}`;
}
// Display: "Building... {formatElapsed(elapsed)}"
```

**Stage bar rewind on auto-fix:** When `autoFixAttempt` is non-null, the active stage index in the bar should rewind to `deps` (index 2 in STAGE_BAR_ITEMS, equivalent to the install/checks stage where the error occurred). This is visual only — the actual `stageIndex` from `useBuildProgress` continues advancing as the backend processes.

### Pattern 6: Canvas Confetti on Build Success

```typescript
// In BuildSummary.tsx — trigger confetti on mount when shown
// Source: canvas-confetti docs (version agnostic — stable API since v1.3)
"use client";

import { useEffect } from "react";

// Dynamic import to avoid SSR issues — canvas APIs are browser-only
async function triggerConfetti() {
  const confetti = (await import("canvas-confetti")).default;

  // Cannon burst from bottom center
  confetti({
    particleCount: 80,
    spread: 70,
    origin: { x: 0.5, y: 0.8 },
    colors: ["#6467f2", "#8183f5", "#0df2f2", "#ffffff"],
    zIndex: 9999,
  });

  // Small follow-up burst 300ms later for lingering effect
  setTimeout(() => {
    confetti({
      particleCount: 40,
      spread: 50,
      origin: { x: 0.4, y: 0.75 },
      colors: ["#6467f2", "#8183f5"],
      zIndex: 9999,
    });
  }, 300);
}

// In BuildSummary component:
useEffect(() => {
  triggerConfetti();
}, []); // Fire once on mount
```

**TypeScript note:** `@types/canvas-confetti` is a separate dev dependency. The type is `import type confetti from "canvas-confetti"` — but the default export works without explicit typing when dynamically imported.

### Anti-Patterns to Avoid

- **Using native EventSource:** Prior locked decision — ALB kills it at 15s. The existing `useAgentStream.ts` already demonstrates the correct fetch + ReadableStreamDefaultReader pattern.
- **Parsing only `data:` lines:** Named events from Phase 29 use `event: log`, `event: heartbeat`, `event: done`. Must parse `event:` field from each SSE block or heartbeats will be rendered as log lines.
- **Single `\n` as SSE block separator:** SSE blocks are separated by `\n\n` (double newline). Splitting by single `\n` will corrupt multi-field events.
- **Using a single data stream for both stage bar and log panel:** Stage bar uses the polling hook; log panel uses SSE. Mixing them in one hook complicates state management. Keep them separate.
- **Triggering confetti inside useEffect with deps:** Canvas-confetti fires on every dep change. Use `useEffect(() => { triggerConfetti(); }, [])` — empty deps, fire once on mount.
- **Auto-scrolling unconditionally:** Only auto-scroll when the log panel is open. If the panel is collapsed, there's nothing to scroll to and the `scrollIntoView` call wastes cycles.
- **Not cleaning up SSE reader on unmount:** Must call `reader.cancel()` and `abortController.abort()` in useEffect cleanup. Without cleanup, the reader keeps running after navigation, causing memory leaks. Pattern already established in `useAgentStream.ts`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Confetti burst animation | Custom CSS particle system | `canvas-confetti` | 80+ particles with physics is 500+ lines of custom code; canvas-confetti is 7KB, proven, handles requestAnimationFrame correctly |
| SSE named event parsing | Custom streaming protocol | Standard SSE block parsing (event:/data: fields) | Already established; one buffer split pattern handles all named event types |
| Collapsible panel animation | CSS height: auto transitions | `framer-motion AnimatePresence` with height animation | CSS `height: auto` transitions don't animate. framer-motion handles this correctly. Pattern already in `BuildFailureCard.tsx`. |
| Elapsed timer formatting | Custom date library | Simple `Math.floor(seconds / 60)` | No library needed for `M:SS` format. 5 lines of code. |

**Key insight:** The project already has all UI animation infrastructure (framer-motion, lucide-react, shadcn/ui patterns). Only `canvas-confetti` is missing.

---

## Common Pitfalls

### Pitfall 1: SSE Block Parsing — Incomplete Chunks

**What goes wrong:** Network delivers partial SSE blocks. A single `reader.read()` call may return `"event: log\ndata: {\"ts\": \"2026"` — cut mid-JSON. Parsing this throws `JSON.parse` error and the log line is lost.

**Why it happens:** The ReadableStream reader yields chunks as they arrive over the network. TCP packet boundaries don't align with SSE message boundaries.

**How to avoid:** Buffer all incoming text. Split buffer by `"\n\n"` to extract complete blocks. Keep the last segment (potentially incomplete) in the buffer. Only parse complete blocks. This is the same pattern as `useAgentStream.ts` — verify the implementation follows it.

**Warning signs:** Log panel shows partial JSON strings or some log lines are missing from the display even though the SSE endpoint is sending them.

### Pitfall 2: Stage Bar and Auto-Fix Banner Fighting

**What goes wrong:** Auto-fix banner says "attempt 2 of 5" but stage bar shows "Writing code" (where the fix is being applied). The visual story is incoherent.

**Why it happens:** The stage bar is driven by polling status; auto-fix detection is driven by SSE log lines. They update at different rates.

**How to avoid:** When `autoFixAttempt` is non-null, visually highlight the `deps` segment in the stage bar (or the stage where the error occurs — typically `checks`/`deps`) as "retry in progress." This is a visual-only override — don't change the actual stage data. Use a separate style class like `is-retrying` that pulsates in amber/yellow.

**Warning signs:** Stage bar shows "Ready" while auto-fix banner shows "Fixing attempt 1."

### Pitfall 3: canvas-confetti in SSR/Next.js 15

**What goes wrong:** `import confetti from "canvas-confetti"` at module level causes `window is not defined` error during SSR, crashing the page.

**Why it happens:** Next.js 15 renders components server-side by default. `canvas-confetti` uses `document.createElement("canvas")` which doesn't exist on the server.

**How to avoid:** Dynamic import inside an async function, called only from `useEffect` (which is client-only). The pattern: `const confetti = (await import("canvas-confetti")).default`. This is a runtime import, not a module-level import. The `"use client"` directive on `BuildSummary.tsx` is also required (already present).

**Warning signs:** `ReferenceError: window is not defined` or `document is not defined` on build or page load.

### Pitfall 4: Auto-Scroll Jumps When User Has Scrolled Up

**What goes wrong:** Founder opens log panel, manually scrolls up to read earlier output. New log lines arrive, auto-scroll fires, jumps back to bottom — interrupting the read.

**Why it happens:** Auto-scroll `useEffect` on `lines.length` fires on every new line regardless of user scroll position.

**How to avoid:** Track whether the user has manually scrolled away from the bottom. Only auto-scroll if `containerEl.scrollHeight - containerEl.scrollTop - containerEl.clientHeight < threshold` (e.g., 50px). If the user is near the bottom, auto-scroll. If they've scrolled up, pause auto-scroll.

```typescript
// Check if user is near bottom before auto-scrolling
const shouldAutoScroll = () => {
  const el = containerRef.current;
  if (!el) return false;
  return el.scrollHeight - el.scrollTop - el.clientHeight < 50;
};

useEffect(() => {
  if (open && shouldAutoScroll()) {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }
}, [lines.length, open]);
```

**Warning signs:** Founders complain they can't read earlier log output — it keeps jumping to the bottom.

### Pitfall 5: useBuildLogs Reconnect on jobId Change

**What goes wrong:** User navigates away and back to the build page. `useBuildLogs` effect runs with the old jobId first, starts a reader, then cleanup fires, then reruns with the new jobId. If cleanup aborts before the new connection starts, there's a race where the abort signal propagates to the new connection.

**Why it happens:** React `useEffect` cleanup and re-run ordering — the effect closure captures the old abortRef.

**How to avoid:** Create a new `AbortController` inside the effect, not shared across renders. The pattern in `useAgentStream.ts` uses `abortControllerRef.current = new AbortController()` at the start of each invocation — follow this exactly. Don't share the abort controller reference across effect invocations.

**Warning signs:** Log stream connects then immediately disconnects on the first render, or fails silently for the second jobId.

---

## Code Examples

### Named SSE Event Parsing (verified from Phase 29 SSE format)

```typescript
// Source: Phase 29 logs.py — confirmed SSE frame format:
// "event: log\ndata: {json}\n\n"
// "event: heartbeat\ndata: {}\n\n"
// "event: done\ndata: {\"status\": \"ready\"}\n\n"

// Buffer accumulates raw bytes; split on double newline for complete blocks
const blocks = buffer.split("\n\n");
buffer = blocks.pop() ?? "";  // keep incomplete tail

for (const block of blocks) {
  let eventType = "message";
  let dataStr = "";

  for (const line of block.split("\n")) {
    if (line.startsWith("event: ")) eventType = line.slice(7).trim();
    else if (line.startsWith("data: ")) dataStr = line.slice(6).trim();
  }

  if (eventType === "heartbeat") continue;
  if (eventType === "done") { /* handle done */ }
  if (eventType === "log") { /* handle log line */ }
}
```

### Segmented Stage Bar Stage Mapping

```typescript
// Source: existing useBuildProgress.ts STAGE_ORDER + BUILD-03 requirement
// Backend STAGE_ORDER = [queued(0), starting(1), scaffold(2), code(3), deps(4), checks(5), ready(6)]
// User-facing stages start at scaffold (index 2)

type BarSegment = { key: string; label: string; backendIndex: number };

const SEGMENTS: BarSegment[] = [
  { key: "scaffold", label: "Designing",               backendIndex: 2 },
  { key: "code",     label: "Writing code",             backendIndex: 3 },
  { key: "deps",     label: "Installing dependencies",  backendIndex: 4 },
  { key: "checks",   label: "Starting app",             backendIndex: 5 },
  { key: "ready",    label: "Ready",                    backendIndex: 6 },
];

// Usage: segment is complete if stageIndex > segment.backendIndex
//        segment is active if stageIndex === segment.backendIndex
//        segment is pending if stageIndex < segment.backendIndex
```

### Auto-Fix Signal Detection from Status Polling

```typescript
// The status endpoint returns stage_label from state machine transition messages.
// When debugger runs, retry_count is in agent state but NOT in current status response.
//
// Simplest correct approach: add retry_count to GenerationStatusResponse (small backend change)
// OR: detect from log stream system lines (no backend change needed).
//
// Log stream detection — system lines from LogStreamer.write_event():
// The debugger_node sets: status_message = f"Debug analysis complete (attempt {N}/{max})"
// BUT this status_message is not written to LogStreamer — it goes into the state machine.
//
// CONCLUSION: The LogStreamer write_event calls are only at GenerationService stage transitions,
// not at debugger_node cycles. To surface auto-fix, either:
// (a) Backend: add retry_count to status response — read from Redis job data
// (b) Backend: add a write_event call in GenerationService after runner.run() completes
//     if final_state["retry_count"] > 0
// (c) Frontend: parse stage_label from polling for "attempt N" substring

// Option (c) works with current backend if we check stage_label:
// The generation_service doesn't set stage_label to "attempt N"...
// The state machine only sees JobStatus enum values.

// FINAL DECISION: Implement option (b) — add one write_event call in GenerationService
// after runner.run() returns. Emit: "--- Auto-fixing (attempt N of M) ---" to the stream.
// The frontend then parses this from the log stream.
// This is a 3-line backend change in generation_service.py — worth doing to avoid
// polling-based heuristics.
```

### canvas-confetti Success Burst

```typescript
// Source: canvas-confetti docs API (stable since v1.3, version-agnostic)
// Dynamic import to avoid SSR: runs only in useEffect (client-side)

async function burstConfetti() {
  const confetti = (await import("canvas-confetti")).default;
  confetti({
    particleCount: 80,
    spread: 70,
    origin: { x: 0.5, y: 0.8 },
    colors: ["#6467f2", "#8183f5", "#0df2f2", "#ffffff"],
    zIndex: 9999,
  });
}

// In BuildSummary.tsx useEffect:
useEffect(() => { burstConfetti(); }, []);  // empty deps = fires once on mount
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| EventSource for SSE | fetch + ReadableStreamDefaultReader | This project (ALB constraint) | Avoids 15s ALB kill on native EventSource |
| Simple progress bar (single fill) | Segmented step bar with icons | This phase (BUILD-03) | Each stage is individually trackable; clear visual progress |
| Silent spinner during build | Stage labels + elapsed timer + auto-fix banner | This phase | Founder knows what's happening; reassured during waits |
| Polling-only for live data | Polling for status + SSE for log lines | Phase 29 + this phase | Real-time log visibility without over-engineering stage tracking |

**Deprecated/outdated:**
- `EventSource`: Do not use — killed by ALB at 15s. Prior locked decision.
- Circle-node stepper (current `BuildProgressBar.tsx`): Replace with horizontal segmented bar per locked decision.

---

## Open Questions

1. **Auto-fix detection mechanism — backend change needed**
   - What we know: `debugger_node` updates `retry_count` in agent state on each retry. The agent graph cycles autonomously inside `runner.run()`. LogStreamer is NOT called inside the agent graph nodes.
   - What's unclear: Whether adding a `write_event` call to `generation_service.py` (after runner.run()) that writes the retry_count from final_state is sufficient, or whether it happens too late (only surfaces after all retries, not during).
   - Recommendation: Add `write_event` BEFORE each `runner.run()` call isn't possible (count isn't known yet). Post-hoc after `runner.run()` reflects the final retry count — this shows attempt N after the fact, not in real-time. For real-time: the generation service would need to pass a callback into the runner that fires on each debugger cycle. This is complex and out of Phase 30's scope. **Phase 30 decision:** Show the retry count based on `retry_count` from the status poll response (requires adding `retry_count` to status endpoint — a 2-line backend change). Alternatively, start simple: detect from the job's `stage_label` in status, which may contain "attempt" info if state machine transitions during debug cycles.

2. **Stage bar "rewind" visual during auto-fix**
   - What we know: The auto-fix banner should appear when `retry_count > 0` on a non-terminal status. The stage bar "resets/rewinds to the failing stage" (locked decision).
   - What's unclear: The backend stage during auto-fix remains `CODE` (runner is running). The stage bar shows "Writing code" as active. Does "rewind to failing stage" mean the stage bar goes back to `deps`/`checks`? If yes, this requires the frontend to infer what stage failed from context, not just current status.
   - Recommendation: When `autoFixAttempt` is non-null, visually style the active segment in amber (not the normal brand color) and add "Fixing..." sublabel. This communicates "something is being retried here" without moving the active indicator backward (which would be confusing if the retry succeeds and the bar advances). The "resets/rewinds" in the locked decision likely means the active indicator moves back to the stage being retried — implement this: when auto-fix is active, set the active bar segment to `code` (since the debugger returns to coder which returns to executor which is in the CODE stage).

3. **Initial "Load earlier" call on log panel open**
   - What we know: SSE starts from `last_id="$"` (live-only). Founders who join mid-build miss earlier output.
   - What's unclear: Should `loadEarlier` be called automatically when the panel is first opened, or only when the user clicks the button?
   - Recommendation: Automatically trigger `loadEarlier()` when the panel opens for the first time (one auto-load). After that, only load on button click. This gives the best "no empty panel" experience without infinite scrollback loading.

---

## Sources

### Primary (HIGH confidence)
- `/Users/vladcortex/co-founder/frontend/src/hooks/useAgentStream.ts` — existing fetch + ReadableStreamDefaultReader pattern for SSE; ReadableStreamDefaultReader lifecycle (abort, reader.cancel())
- `/Users/vladcortex/co-founder/frontend/src/hooks/useBuildProgress.ts` — existing stage status polling hook; STAGE_ORDER, stage index mapping; confirmed `stageIndex` and `totalStages` API surface
- `/Users/vladcortex/co-founder/frontend/src/components/build/BuildProgressBar.tsx` — current stepper implementation to replace; confirmed icons (lucide-react Check)
- `/Users/vladcortex/co-founder/frontend/src/components/build/BuildSummary.tsx` — success component; `"use client"` confirmed; framer-motion spring animation
- `/Users/vladcortex/co-founder/frontend/src/components/build/BuildFailureCard.tsx` — failure component; AnimatePresence collapse pattern; existing expandable details section
- `/Users/vladcortex/co-founder/frontend/src/components/chat/TerminalOutput.tsx` — auto-scroll pattern via `el.scrollTop = el.scrollHeight`; `useRef` + `useEffect` on `lines.length`
- `/Users/vladcortex/co-founder/frontend/src/app/(dashboard)/projects/[id]/build/page.tsx` — build page orchestrator; jobId from query params; useBuildProgress wiring
- `/Users/vladcortex/co-founder/frontend/src/lib/api.ts` — `apiFetch()` authenticated fetch wrapper; `GetTokenFn` type
- `/Users/vladcortex/co-founder/backend/app/api/routes/logs.py` — Phase 29 SSE endpoint; confirmed event format: `event: log|heartbeat|done\ndata: {json}\n\n`; confirmed REST endpoint `GET /{job_id}/logs` with `before_id` cursor
- `/Users/vladcortex/co-founder/backend/app/agent/nodes/debugger.py` — confirmed `retry_count` incremented per attempt; `max_retries=5`; `needs_human_review` flag at limit
- `/Users/vladcortex/co-founder/backend/app/agent/state.py` — confirmed `retry_count: int` and `max_retries: int = 5` in `CoFounderState`; initial state sets `retry_count=0, max_retries=5`
- `/Users/vladcortex/co-founder/backend/app/services/generation_service.py` — confirmed LogStreamer wiring; `write_event()` calls at stage transitions; no auto-fix signal currently emitted
- `/Users/vladcortex/co-founder/frontend/package.json` — confirmed: framer-motion 12.34.0, lucide-react ^0.400.0, canvas-confetti NOT installed
- Lucide icon verification: `wand-2.js`, `code.js`, `package.js`, `play.js`, `check-circle-2.js`, `sparkles.js`, `wrench.js` all present in installed lucide-react

### Secondary (MEDIUM confidence)
- Phase 29 VERIFICATION.md — confirmed 4/4 success criteria passed; SSE endpoint live and tested; REST pagination confirmed working
- Phase 29 RESEARCH.md — confirmed SSE frame format, heartbeat interval (20s), ALB idle timeout constraint
- WebSearch: canvas-confetti is the standard approach for confetti in React/Next.js apps; `@types/canvas-confetti` for TypeScript

### Tertiary (LOW confidence)
- canvas-confetti bundle size (~7KB gzipped) — from WebSearch; not directly verified against npm registry
- framer-motion 12 does not include built-in confetti — inferred from API docs, not explicitly confirmed for v12.34

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries verified from installed node_modules; only canvas-confetti not yet installed
- Architecture: HIGH — patterns derived directly from existing codebase (useAgentStream, BuildFailureCard, TerminalOutput)
- Pitfalls: HIGH — derived from code inspection and known React/SSE gotchas; auto-scroll race condition derived from TerminalOutput pattern
- Auto-fix detection: MEDIUM — requires a small backend change; the mechanism is clear but the exact implementation needs a decision

**Research date:** 2026-02-22
**Valid until:** 2026-03-22 (stable libraries; backend code changes are code-reviewed before expiry)
