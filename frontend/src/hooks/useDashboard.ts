"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { useAuth } from "@clerk/nextjs";
import { apiFetch } from "@/lib/api";

// TypeScript interfaces matching backend DashboardResponse
export interface RiskFlag {
  type: string;
  rule: string;
  message: string;
}

export interface ArtifactSummary {
  id: string;
  artifact_type: string;
  generation_status: string;
  version_number: number;
  has_user_edits: boolean;
  updated_at: string;
}

export interface PendingDecision {
  id: string;
  gate_type: string;
  status: string;
  created_at: string;
}

export interface DashboardData {
  project_id: string;
  stage: number;
  stage_name: string;
  product_version: string;
  mvp_completion_percent: number;
  next_milestone: string | null;
  risk_flags: RiskFlag[];
  suggested_focus: string;
  artifacts: ArtifactSummary[];
  pending_decisions: PendingDecision[];
  latest_build_status: string | null;
  preview_url: string | null;
}

interface UseDashboardReturn {
  data: DashboardData | null;
  loading: boolean;
  error: Error | null;
  changedFields: Set<string>;
  refetch: () => Promise<void>;
}

export function useDashboard(
  projectId: string,
  pollInterval: number = 7000
): UseDashboardReturn {
  const { getToken } = useAuth();
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);
  const [changedFields, setChangedFields] = useState<Set<string>>(new Set());

  // Prevent overlapping requests (research pitfall 2)
  const isPollingRef = useRef(false);

  // Store previous data for change detection without causing re-renders
  const previousDataRef = useRef<DashboardData | null>(null);

  // Timeout ref for clearing changedFields highlight
  const changeTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  const fetchDashboard = useCallback(async () => {
    // Skip if already polling (prevent overlap)
    if (isPollingRef.current) {
      return;
    }

    try {
      isPollingRef.current = true;

      const response = await apiFetch(
        `/api/dashboard/${projectId}`,
        getToken
      );

      if (!response.ok) {
        throw new Error(`Dashboard fetch failed: ${response.statusText}`);
      }

      const dashboardData: DashboardData = await response.json();

      // Change detection: compare with previous data
      const changes = new Set<string>();

      if (previousDataRef.current) {
        // Track progress changes
        if (previousDataRef.current.mvp_completion_percent !== dashboardData.mvp_completion_percent) {
          changes.add("progress");
        }

        // Track artifact generation status changes
        const prevArtifacts = previousDataRef.current.artifacts;
        const newArtifacts = dashboardData.artifacts;

        const statusChanged = newArtifacts.some((newArt: ArtifactSummary) => {
          const prevArt = prevArtifacts.find((a) => a.id === newArt.id);
          return prevArt && prevArt.generation_status !== newArt.generation_status;
        });

        if (statusChanged || prevArtifacts.length !== newArtifacts.length) {
          changes.add("artifacts");
        }
      }

      // Update state
      setData(dashboardData);
      setError(null);

      if (changes.size > 0) {
        setChangedFields(changes);

        // Clear changed fields after 2 seconds
        if (changeTimeoutRef.current) {
          clearTimeout(changeTimeoutRef.current);
        }
        changeTimeoutRef.current = setTimeout(() => {
          setChangedFields(new Set());
        }, 2000);
      }

      // Update previous data ref for next comparison
      previousDataRef.current = dashboardData;

      // Clear loading state on first successful fetch
      if (loading) {
        setLoading(false);
      }
    } catch (err) {
      // On error: set error state, don't update data (keep last known state)
      setError(err instanceof Error ? err : new Error("Failed to fetch dashboard"));

      // Clear loading state even on error
      if (loading) {
        setLoading(false);
      }
    } finally {
      isPollingRef.current = false;
    }
  }, [projectId, getToken, loading]);

  // Initial fetch on mount
  useEffect(() => {
    fetchDashboard();
  }, [fetchDashboard]);

  // Polling interval
  useEffect(() => {
    const intervalId = setInterval(() => {
      fetchDashboard();
    }, pollInterval);

    return () => {
      clearInterval(intervalId);
      if (changeTimeoutRef.current) {
        clearTimeout(changeTimeoutRef.current);
      }
    };
  }, [fetchDashboard, pollInterval]);

  return {
    data,
    loading,
    error,
    changedFields,
    refetch: fetchDashboard,
  };
}
