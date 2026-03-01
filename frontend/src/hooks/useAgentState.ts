"use client";

import { useState, useCallback, useEffect, useRef } from "react";
import { apiFetch } from "@/lib/api";
import type { AgentEvent, EventHandlers } from "./useAgentEvents";

// ──────────────────────────────────────────────────────────────────────────────
// Types
// ──────────────────────────────────────────────────────────────────────────────

export type AgentLifecycleState =
  | "working"
  | "sleeping"
  | "waiting_for_input"
  | "error"
  | "idle"
  | "completed";

export interface AgentStateResult {
  state: AgentLifecycleState;
  elapsedMs: number;
  wakeAt: string | null;
  budgetPct: number | null;
  pendingEscalationCount: number;
  currentPhaseName: string | null;
  eventHandlers: Partial<EventHandlers>;
}

type GetTokenFn = () => Promise<string | null>;

// Maps backend Redis agent_state values to AgentLifecycleState
const BACKEND_STATE_MAP: Record<string, AgentLifecycleState> = {
  working: "working",
  sleeping: "sleeping",
  waiting: "waiting_for_input",
  waiting_for_input: "waiting_for_input",
  error: "error",
  idle: "idle",
  completed: "completed",
};

// ──────────────────────────────────────────────────────────────────────────────
// Hook
// ──────────────────────────────────────────────────────────────────────────────

/**
 * useAgentState — Agent lifecycle state with REST bootstrap + SSE transitions.
 *
 * Fetches initial agent state from GET /api/jobs/{jobId}/status on mount.
 * Exposes `eventHandlers` for the page-level component to merge into the
 * single useAgentEvents call — do NOT call useAgentEvents here.
 */
export function useAgentState(
  jobId: string | null,
  getToken: GetTokenFn,
): AgentStateResult {
  const [state, setState] = useState<AgentLifecycleState>("idle");
  const [elapsedMs, setElapsedMs] = useState(0);
  const [wakeAt, setWakeAt] = useState<string | null>(null);
  const [budgetPct, setBudgetPct] = useState<number | null>(null);
  const [pendingEscalationCount, setPendingEscalationCount] = useState(0);
  const [currentPhaseName, setCurrentPhaseName] = useState<string | null>(null);

  // Track when "working" started for elapsed time calculation
  const workingStartRef = useRef<number | null>(null);
  const elapsedIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // ── Elapsed time tracking ───────────────────────────────────────────────────

  const startElapsedTimer = useCallback(() => {
    workingStartRef.current = Date.now();
    elapsedIntervalRef.current = setInterval(() => {
      if (workingStartRef.current !== null) {
        setElapsedMs(Date.now() - workingStartRef.current);
      }
    }, 1000);
  }, []);

  const stopElapsedTimer = useCallback(() => {
    if (elapsedIntervalRef.current !== null) {
      clearInterval(elapsedIntervalRef.current);
      elapsedIntervalRef.current = null;
    }
    workingStartRef.current = null;
  }, []);

  // ── REST bootstrap ──────────────────────────────────────────────────────────

  useEffect(() => {
    if (!jobId) return;

    // Reset on jobId change
    setState("idle");
    setElapsedMs(0);
    setWakeAt(null);
    setBudgetPct(null);
    setPendingEscalationCount(0);
    setCurrentPhaseName(null);
    stopElapsedTimer();

    let cancelled = false;

    async function fetchAgentState() {
      try {
        const res = await apiFetch(`/api/jobs/${jobId}/status`, getToken);
        if (!res.ok || cancelled) return;

        const data = (await res.json()) as {
          agent_state?: string | null;
          wake_at?: string | null;
          budget_pct?: number | null;
        };

        if (cancelled) return;

        if (data.agent_state) {
          const mapped =
            BACKEND_STATE_MAP[data.agent_state] ?? ("idle" as AgentLifecycleState);
          setState(mapped);
          if (mapped === "working") {
            startElapsedTimer();
          }
        }

        if (data.wake_at) {
          setWakeAt(data.wake_at);
        }

        if (data.budget_pct != null) {
          setBudgetPct(data.budget_pct);
        }
      } catch {
        // Silently fail — SSE events will correct state as they arrive
      }
    }

    fetchAgentState();

    return () => {
      cancelled = true;
      stopElapsedTimer();
    };
  }, [jobId, getToken, startElapsedTimer, stopElapsedTimer]);

  // ── SSE event handlers ──────────────────────────────────────────────────────

  const onAgentThinking = useCallback(
    (_e: AgentEvent) => {
      setState((prev) => {
        if (prev !== "working") {
          startElapsedTimer();
        }
        return "working";
      });
      setWakeAt(null);
    },
    [startElapsedTimer],
  );

  const onAgentToolCalled = useCallback(
    (e: AgentEvent) => {
      setState((prev) => {
        if (prev !== "working") {
          startElapsedTimer();
        }
        return "working";
      });
      // Track current phase name from tool context if available
      if (e.phase_name) {
        setCurrentPhaseName(e.phase_name as string);
      }
    },
    [startElapsedTimer],
  );

  const onAgentSleeping = useCallback(
    (e: AgentEvent) => {
      stopElapsedTimer();
      setElapsedMs(0);
      setState("sleeping");
      setWakeAt((e.wake_at as string) ?? null);
    },
    [stopElapsedTimer],
  );

  const onAgentWaking = useCallback(
    (_e: AgentEvent) => {
      setState("working");
      setWakeAt(null);
      startElapsedTimer();
    },
    [startElapsedTimer],
  );

  const onAgentWaitingForInput = useCallback(
    (_e: AgentEvent) => {
      stopElapsedTimer();
      setState("waiting_for_input");
      setPendingEscalationCount((n) => n + 1);
    },
    [stopElapsedTimer],
  );

  const onAgentBuildPaused = useCallback(
    (_e: AgentEvent) => {
      stopElapsedTimer();
      setState("waiting_for_input");
    },
    [stopElapsedTimer],
  );

  const onAgentBudgetUpdated = useCallback((e: AgentEvent) => {
    if (e.budget_pct != null) {
      setBudgetPct(e.budget_pct as number);
    }
    // budget_exceeded: treat as error state
    if (e.budget_exceeded) {
      setState("error");
    }
  }, []);

  const onAgentEscalationResolved = useCallback((_e: AgentEvent) => {
    setPendingEscalationCount((n) => Math.max(0, n - 1));
  }, []);

  const onGsdPhaseStarted = useCallback((e: AgentEvent) => {
    if (e.phase_name) {
      setCurrentPhaseName(e.phase_name as string);
    }
  }, []);

  // ── Assemble eventHandlers for page-level composition ───────────────────────

  const eventHandlers: Partial<EventHandlers> = {
    onAgentThinking,
    onAgentToolCalled,
    onAgentSleeping,
    onAgentWaking,
    onAgentWaitingForInput,
    onAgentBuildPaused,
    onAgentBudgetUpdated,
    onAgentEscalationResolved,
    onGsdPhaseStarted,
  };

  return {
    state,
    elapsedMs,
    wakeAt,
    budgetPct,
    pendingEscalationCount,
    currentPhaseName,
    eventHandlers,
  };
}
