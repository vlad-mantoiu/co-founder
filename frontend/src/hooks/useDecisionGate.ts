"use client";

import { useState, useCallback } from "react";
import { useAuth } from "@clerk/nextjs";
import { apiFetch } from "@/lib/api";

/**
 * Gate option from backend GATE_1_OPTIONS constant.
 */
export interface GateOption {
  value: string;
  title: string;
  description: string;
  what_happens_next: string;
  pros: string[];
  cons: string[];
  why_choose: string;
}

/**
 * Decision gate state.
 */
interface DecisionGateState {
  isOpen: boolean;
  gateId: string | null;
  options: GateOption[];
  selectedOption: string | null;
  isResolving: boolean;
  error: string | null;
  resolution: {
    decision: string;
    summary: string;
  } | null;
}

const INITIAL_STATE: DecisionGateState = {
  isOpen: false,
  gateId: null,
  options: [],
  selectedOption: null,
  isResolving: false,
  error: null,
  resolution: null,
};

/**
 * Hook for managing Decision Gate 1 lifecycle.
 *
 * Workflow:
 * 1. openGate(projectId) - Check for pending gate or create one
 * 2. selectOption(value) - Set selected option locally
 * 3. resolveGate(actionText?, parkNote?) - Submit decision to API
 * 4. closeGate() - Reset state
 */
export function useDecisionGate() {
  const { getToken } = useAuth();
  const [state, setState] = useState<DecisionGateState>(INITIAL_STATE);

  /**
   * Open Decision Gate 1 for a project.
   * Checks for existing pending gate, creates one if none exists.
   */
  const openGate = useCallback(
    async (projectId: string) => {
      setState((s) => ({ ...s, error: null }));

      try {
        // Check for pending gate
        const checkResponse = await apiFetch(
          `/api/gates/project/${projectId}/pending`,
          getToken,
          { method: "GET" }
        );

        if (checkResponse.ok) {
          const existingGate = await checkResponse.json();

          if (existingGate && existingGate.status === "pending") {
            // Use existing pending gate
            setState((s) => ({
              ...s,
              isOpen: true,
              gateId: existingGate.gate_id,
              options: existingGate.options || [],
            }));
            return;
          }
        }

        // No pending gate - create one
        const createResponse = await apiFetch("/api/gates/create", getToken, {
          method: "POST",
          body: JSON.stringify({
            project_id: projectId,
            gate_type: "stage_advance",
          }),
        });

        if (!createResponse.ok) {
          const errorData = await createResponse.json();
          throw new Error(errorData.detail || `API error: ${createResponse.status}`);
        }

        const gateData = await createResponse.json();
        setState((s) => ({
          ...s,
          isOpen: true,
          gateId: gateData.gate_id,
          options: gateData.options || [],
        }));
      } catch (err) {
        setState((s) => ({
          ...s,
          error: (err as Error).message,
        }));
      }
    },
    [getToken]
  );

  /**
   * Select an option locally (no API call yet).
   */
  const selectOption = useCallback((value: string) => {
    setState((s) => ({
      ...s,
      selectedOption: value,
      error: null,
    }));
  }, []);

  /**
   * Resolve the gate with the selected decision.
   *
   * @param actionText - Required for "narrow" or "pivot" decisions
   * @param parkNote - Optional note for "park" decision
   */
  const resolveGate = useCallback(
    async (actionText?: string, parkNote?: string) => {
      if (!state.gateId || !state.selectedOption) {
        setState((s) => ({
          ...s,
          error: "No gate or option selected",
        }));
        return;
      }

      setState((s) => ({ ...s, isResolving: true, error: null }));

      try {
        const payload: Record<string, unknown> = {
          decision: state.selectedOption,
        };

        if (actionText) {
          payload.action_text = actionText;
        }

        if (parkNote) {
          payload.park_note = parkNote;
        }

        const response = await apiFetch(
          `/api/gates/${state.gateId}/resolve`,
          getToken,
          {
            method: "POST",
            body: JSON.stringify(payload),
          }
        );

        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.detail || `API error: ${response.status}`);
        }

        const data = await response.json();
        setState((s) => ({
          ...s,
          resolution: {
            decision: data.decision,
            summary: data.resolution_summary,
          },
          isResolving: false,
        }));

        // Close modal after brief delay
        setTimeout(() => {
          setState((s) => ({ ...s, isOpen: false }));
        }, 500);
      } catch (err) {
        setState((s) => ({
          ...s,
          error: (err as Error).message,
          isResolving: false,
        }));
      }
    },
    [getToken, state.gateId, state.selectedOption]
  );

  /**
   * Close gate and reset state.
   */
  const closeGate = useCallback(() => {
    setState(INITIAL_STATE);
  }, []);

  /**
   * Check if gate is blocking operations for a project.
   */
  const checkBlocking = useCallback(
    async (projectId: string): Promise<boolean> => {
      try {
        const response = await apiFetch(
          `/api/gates/project/${projectId}/check-blocking`,
          getToken,
          { method: "GET" }
        );

        if (!response.ok) {
          return false;
        }

        const data = await response.json();
        return data.blocking === true;
      } catch {
        return false;
      }
    },
    [getToken]
  );

  return {
    state,
    openGate,
    selectOption,
    resolveGate,
    closeGate,
    checkBlocking,
  };
}
