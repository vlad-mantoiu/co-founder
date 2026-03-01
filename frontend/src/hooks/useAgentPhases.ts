"use client";

import { useState, useCallback, useEffect } from "react";
import { apiFetch } from "@/lib/api";
import type { AgentEvent, EventHandlers } from "./useAgentEvents";

// ──────────────────────────────────────────────────────────────────────────────
// Types
// ──────────────────────────────────────────────────────────────────────────────

export interface GsdPhase {
  phase_id: string;
  phase_name: string;
  phase_description?: string;
  status: "pending" | "in_progress" | "completed";
  started_at?: string;
  completed_at?: string;
  plan_count?: number;
  plans_completed?: number;
}

export interface AgentPhasesState {
  phases: GsdPhase[];
  filterPhaseId: string | null;
  setFilterPhaseId: (id: string | null) => void;
  activePhaseId: string | null;
  eventHandlers: Partial<EventHandlers>;
}

type GetTokenFn = () => Promise<string | null>;

// ──────────────────────────────────────────────────────────────────────────────
// Hook
// ──────────────────────────────────────────────────────────────────────────────

/**
 * useAgentPhases — GSD phase list with REST bootstrap + SSE live updates.
 *
 * Fetches the initial phase list from GET /api/jobs/{jobId}/phases on mount.
 * Exposes `eventHandlers` for the page-level component to merge into the
 * single useAgentEvents call — do NOT call useAgentEvents here.
 */
export function useAgentPhases(
  jobId: string | null,
  getToken: GetTokenFn,
): AgentPhasesState {
  const [phases, setPhases] = useState<GsdPhase[]>([]);
  const [filterPhaseId, setFilterPhaseId] = useState<string | null>(null);

  // ── REST bootstrap ──────────────────────────────────────────────────────────

  useEffect(() => {
    if (!jobId) return;

    // Reset on jobId change
    setPhases([]);
    setFilterPhaseId(null);

    let cancelled = false;

    async function fetchPhases() {
      try {
        const res = await apiFetch(`/api/jobs/${jobId}/phases`, getToken);
        if (!res.ok || cancelled) return;

        const data = (await res.json()) as {
          phases: GsdPhase[];
        };

        if (!cancelled) {
          setPhases(data.phases ?? []);
        }
      } catch {
        // Silently fail — SSE updates will populate phases as they arrive
      }
    }

    fetchPhases();

    return () => {
      cancelled = true;
    };
  }, [jobId, getToken]);

  // ── SSE event handlers ──────────────────────────────────────────────────────

  const onGsdPhaseStarted = useCallback((e: AgentEvent) => {
    const phaseId = e.phase_id as string | undefined;
    const phaseName = e.phase_name as string | undefined;
    if (!phaseId || !phaseName) return;

    setPhases((prev) => {
      const existing = prev.find((p) => p.phase_id === phaseId);
      if (existing) {
        // Update in place — mark as in_progress if it was pending
        return prev.map((p) =>
          p.phase_id === phaseId
            ? {
                ...p,
                status: "in_progress" as const,
                phase_name: phaseName,
                phase_description: (e.phase_description as string) ?? p.phase_description,
                started_at: (e.timestamp as string) ?? p.started_at,
              }
            : p,
        );
      }
      // New phase — append
      const newPhase: GsdPhase = {
        phase_id: phaseId,
        phase_name: phaseName,
        phase_description: e.phase_description as string | undefined,
        status: "in_progress",
        started_at: e.timestamp as string | undefined,
      };
      return [...prev, newPhase];
    });
  }, []);

  const onGsdPhaseCompleted = useCallback((e: AgentEvent) => {
    const phaseId = e.phase_id as string | undefined;
    if (!phaseId) return;

    setPhases((prev) =>
      prev.map((p) =>
        p.phase_id === phaseId
          ? {
              ...p,
              status: "completed" as const,
              completed_at: (e.timestamp as string) ?? p.completed_at,
            }
          : p,
      ),
    );
  }, []);

  // ── Derived state ───────────────────────────────────────────────────────────

  const activePhaseId =
    phases.find((p) => p.status === "in_progress")?.phase_id ?? null;

  const eventHandlers: Partial<EventHandlers> = {
    onGsdPhaseStarted,
    onGsdPhaseCompleted,
  };

  return {
    phases,
    filterPhaseId,
    setFilterPhaseId,
    activePhaseId,
    eventHandlers,
  };
}
