"use client";

import { useState, useCallback } from "react";
import { useAuth } from "@clerk/nextjs";
import { apiFetch } from "@/lib/api";

/**
 * Execution plan option from backend.
 */
export interface ExecutionOption {
  id: string;
  name: string;
  is_recommended: boolean;
  time_to_ship: string;
  engineering_cost: string;
  risk_level: "low" | "medium" | "high";
  scope_coverage: number; // 0-100%
  pros: string[];
  cons: string[];
  technical_approach: string;
  tradeoffs?: string[];
  engineering_impact?: string;
  cost_note?: string;
}

/**
 * Execution plan state.
 */
interface ExecutionPlanState {
  options: ExecutionOption[];
  recommendedId: string | null;
  selectedId: string | null;
  isGenerating: boolean;
  isSelecting: boolean;
  planSetId: string | null;
  error: string | null;
}

const INITIAL_STATE: ExecutionPlanState = {
  options: [],
  recommendedId: null,
  selectedId: null,
  isGenerating: false,
  isSelecting: false,
  planSetId: null,
  error: null,
};

/**
 * Hook for managing execution plan generation and selection.
 *
 * Workflow:
 * 1. generatePlans(projectId, feedback?) - Generate or regenerate plans
 * 2. selectPlan(projectId, optionId) - Select one plan
 * 3. loadExistingPlans(projectId) - Load previously generated plans
 */
export function useExecutionPlans() {
  const { getToken } = useAuth();
  const [state, setState] = useState<ExecutionPlanState>(INITIAL_STATE);

  /**
   * Generate execution plan options.
   * Handles 409 errors (gate not resolved) with helpful message.
   */
  const generatePlans = useCallback(
    async (projectId: string, feedback?: string) => {
      setState((s) => ({ ...s, isGenerating: true, error: null }));

      try {
        const endpoint = feedback ? "/api/plans/regenerate" : "/api/plans/generate";
        const body: Record<string, string> = { project_id: projectId };
        if (feedback) {
          body.feedback = feedback;
        }

        const response = await apiFetch(endpoint, getToken, {
          method: "POST",
          body: JSON.stringify(body),
        });

        if (response.status === 409) {
          const errorData = await response.json();
          setState((s) => ({
            ...s,
            error:
              errorData.detail ||
              "Decision Gate 1 must be resolved before generating execution plans. Please complete the gate decision first.",
            isGenerating: false,
          }));
          return;
        }

        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.detail || `API error: ${response.status}`);
        }

        const data = await response.json();
        setState((s) => ({
          ...s,
          options: data.options || [],
          recommendedId: data.recommended_id || null,
          planSetId: data.plan_set_id || null,
          isGenerating: false,
        }));
      } catch (err) {
        setState((s) => ({
          ...s,
          error: (err as Error).message,
          isGenerating: false,
        }));
      }
    },
    [getToken]
  );

  /**
   * Select an execution plan option.
   */
  const selectPlan = useCallback(
    async (projectId: string, optionId: string) => {
      setState((s) => ({ ...s, isSelecting: true, error: null }));

      try {
        const response = await apiFetch(`/api/plans/${projectId}/select`, getToken, {
          method: "POST",
          body: JSON.stringify({ option_id: optionId }),
        });

        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.detail || `API error: ${response.status}`);
        }

        setState((s) => ({
          ...s,
          selectedId: optionId,
          isSelecting: false,
        }));
      } catch (err) {
        setState((s) => ({
          ...s,
          error: (err as Error).message,
          isSelecting: false,
        }));
      }
    },
    [getToken]
  );

  /**
   * Regenerate plans with feedback.
   */
  const regeneratePlans = useCallback(
    async (projectId: string, feedback: string) => {
      // Regenerate uses same logic as generate with feedback
      await generatePlans(projectId, feedback);
    },
    [generatePlans]
  );

  /**
   * Load existing execution plans.
   */
  const loadExistingPlans = useCallback(
    async (projectId: string) => {
      setState((s) => ({ ...s, isGenerating: true, error: null }));

      try {
        const response = await apiFetch(`/api/plans/${projectId}`, getToken, {
          method: "GET",
        });

        if (response.status === 404) {
          // No plans exist yet
          setState((s) => ({ ...s, isGenerating: false }));
          return;
        }

        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.detail || `API error: ${response.status}`);
        }

        const data = await response.json();

        // Check for selected plan
        const selectedResponse = await apiFetch(
          `/api/plans/${projectId}/selected`,
          getToken,
          { method: "GET" }
        );

        let selectedId: string | null = null;
        if (selectedResponse.ok) {
          const selectedData = await selectedResponse.json();
          selectedId = selectedData.selected_option?.id || null;
        }

        setState((s) => ({
          ...s,
          options: data.options || [],
          recommendedId: data.recommended_id || null,
          planSetId: data.plan_set_id || null,
          selectedId,
          isGenerating: false,
        }));
      } catch (err) {
        setState((s) => ({
          ...s,
          error: (err as Error).message,
          isGenerating: false,
        }));
      }
    },
    [getToken]
  );

  return {
    state,
    generatePlans,
    selectPlan,
    regeneratePlans,
    loadExistingPlans,
  };
}
