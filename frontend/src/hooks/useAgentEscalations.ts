"use client";

import { useState, useCallback, useEffect } from "react";
import { apiFetch } from "@/lib/api";
import type { AgentEvent, EventHandlers } from "./useAgentEvents";

// ──────────────────────────────────────────────────────────────────────────────
// Types
// ──────────────────────────────────────────────────────────────────────────────

export interface EscalationAttempt {
  attempt: number;
  approach: string;
  result: string;
}

export interface EscalationOption {
  id: string;
  label: string;
  description?: string;
}

export interface Escalation {
  id: string;
  session_id: string;
  job_id: string;
  project_id: string;
  error_type: string;
  error_signature: string;
  plain_english_problem: string;
  attempts_summary: EscalationAttempt[];
  recommended_action: string;
  options: EscalationOption[];
  status: "pending" | "resolved";
  founder_decision: string | null;
  founder_guidance: string | null;
  created_at: string;
  resolved_at: string | null;
}

export interface AgentEscalationsState {
  escalations: Escalation[];
  pendingCount: number;
  resolve: (
    escalationId: string,
    decision: string,
    guidance?: string,
  ) => Promise<void>;
  eventHandlers: Partial<EventHandlers>;
}

type GetTokenFn = () => Promise<string | null>;

// ──────────────────────────────────────────────────────────────────────────────
// Hook
// ──────────────────────────────────────────────────────────────────────────────

/**
 * useAgentEscalations — Escalation CRUD with resolve mutation.
 *
 * Fetches escalations from GET /api/jobs/{jobId}/escalations on mount.
 * Exposes `eventHandlers` for the page-level component to merge into the
 * single useAgentEvents call — do NOT call useAgentEvents here.
 *
 * resolve() POSTs to /api/escalations/{id}/resolve and updates local state
 * optimistically so the UI responds immediately without waiting for SSE confirm.
 */
export function useAgentEscalations(
  jobId: string | null,
  getToken: GetTokenFn,
): AgentEscalationsState {
  const [escalations, setEscalations] = useState<Escalation[]>([]);

  // ── REST bootstrap ──────────────────────────────────────────────────────────

  useEffect(() => {
    if (!jobId) return;

    setEscalations([]);
    let cancelled = false;

    async function fetchEscalations() {
      try {
        const res = await apiFetch(`/api/jobs/${jobId}/escalations`, getToken);
        if (!res.ok || cancelled) return;

        const data = (await res.json()) as Escalation[];
        if (!cancelled) {
          // Backend returns UUID objects — normalize id to string
          setEscalations(
            data.map((e) => ({ ...e, id: String(e.id) })),
          );
        }
      } catch {
        // Silently fail — SSE will trigger re-fetch on new escalations
      }
    }

    fetchEscalations();

    return () => {
      cancelled = true;
    };
  }, [jobId, getToken]);

  // ── Resolve mutation ────────────────────────────────────────────────────────

  const resolve = useCallback(
    async (
      escalationId: string,
      decision: string,
      guidance?: string,
    ): Promise<void> => {
      try {
        const res = await apiFetch(
          `/api/escalations/${escalationId}/resolve`,
          getToken,
          {
            method: "POST",
            body: JSON.stringify({ decision, guidance: guidance ?? null }),
          },
        );

        if (!res.ok) return;

        // Optimistic local update — show resolved state immediately
        setEscalations((prev) =>
          prev.map((e) =>
            e.id === escalationId
              ? {
                  ...e,
                  status: "resolved" as const,
                  founder_decision: decision,
                  founder_guidance: guidance ?? null,
                  resolved_at: new Date().toISOString(),
                }
              : e,
          ),
        );
      } catch {
        // Silently fail — let the caller handle UI feedback
      }
    },
    [getToken],
  );

  // ── SSE event handlers ──────────────────────────────────────────────────────

  const onAgentWaitingForInput = useCallback(
    (_e: AgentEvent) => {
      // A new escalation was created — re-fetch from REST to get full details
      if (!jobId) return;

      async function refetch() {
        try {
          const res = await apiFetch(`/api/jobs/${jobId}/escalations`, getToken);
          if (!res.ok) return;
          const data = (await res.json()) as Escalation[];
          setEscalations(data.map((e) => ({ ...e, id: String(e.id) })));
        } catch {
          // Silently fail
        }
      }

      refetch();
    },
    [jobId, getToken],
  );

  const onAgentEscalationResolved = useCallback((e: AgentEvent) => {
    const escalationId = e.escalation_id as string | undefined;
    if (!escalationId) return;

    setEscalations((prev) =>
      prev.map((esc) =>
        esc.id === escalationId
          ? { ...esc, status: "resolved" as const }
          : esc,
      ),
    );
  }, []);

  // ── Derived state ───────────────────────────────────────────────────────────

  const pendingCount = escalations.filter((e) => e.status === "pending").length;

  const eventHandlers: Partial<EventHandlers> = {
    onAgentWaitingForInput,
    onAgentEscalationResolved,
  };

  return {
    escalations,
    pendingCount,
    resolve,
    eventHandlers,
  };
}
