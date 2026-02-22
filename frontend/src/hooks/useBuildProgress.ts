"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { apiFetch } from "@/lib/api";

// ──────────────────────────────────────────────────────────────────────────────
// Stage metadata — mirrors backend STAGE_LABELS (locked decision)
// ──────────────────────────────────────────────────────────────────────────────

export const STAGE_LABELS: Record<string, string> = {
  queued: "Waiting in queue...",
  starting: "Starting build...",
  scaffold: "Scaffolding workspace...",
  code: "Writing code...",
  deps: "Installing dependencies...",
  checks: "Running checks...",
  ready: "Build complete!",
  failed: "Build failed",
  scheduled: "Scheduled",
};

// Display-friendly stage names for the progress bar stepper
export const STAGE_DISPLAY_NAMES: Record<string, string> = {
  queued: "Queued",
  starting: "Starting",
  scaffold: "Scaffolding",
  code: "Writing code",
  deps: "Installing deps",
  checks: "Running checks",
  ready: "Complete",
};

// Ordered build stages (excludes terminal states queued/scheduled handled separately)
export const STAGE_ORDER = [
  "queued",
  "starting",
  "scaffold",
  "code",
  "deps",
  "checks",
  "ready",
] as const;

export type BuildStatus =
  | "queued"
  | "starting"
  | "scaffold"
  | "code"
  | "deps"
  | "checks"
  | "ready"
  | "failed"
  | "scheduled"
  | "unknown";

export interface BuildProgressState {
  status: BuildStatus;
  label: string;
  previewUrl: string | null;
  buildVersion: string | null;
  error: string | null;
  debugId: string | null;
  sandboxExpiresAt: string | null;
  stageIndex: number;
  totalStages: number;
  isTerminal: boolean;
}

// ──────────────────────────────────────────────────────────────────────────────
// Generation status response from GET /api/generation/{job_id}/status
// ──────────────────────────────────────────────────────────────────────────────

interface GenerationStatusResponse {
  job_id: string;
  status: string;
  stage_label: string;
  preview_url?: string | null;
  build_version?: string | null;
  error_message?: string | null;
  debug_id?: string | null;
  sandbox_expires_at?: string | null;
}

const TERMINAL_STATUSES = new Set(["ready", "failed"]);

export function statusToStageIndex(status: string): number {
  const idx = STAGE_ORDER.indexOf(status as (typeof STAGE_ORDER)[number]);
  return idx >= 0 ? idx : 0;
}

// ──────────────────────────────────────────────────────────────────────────────
// Hook — authenticated long-polling via apiFetch instead of EventSource
// ──────────────────────────────────────────────────────────────────────────────

export function useBuildProgress(
  jobId: string | null,
  getToken: () => Promise<string | null>
): BuildProgressState & { connectionFailed: boolean } {
  const [state, setState] = useState<BuildProgressState>({
    status: "queued",
    label: STAGE_LABELS["queued"],
    previewUrl: null,
    buildVersion: null,
    error: null,
    debugId: null,
    sandboxExpiresAt: null,
    stageIndex: 0,
    totalStages: STAGE_ORDER.length,
    isTerminal: false,
  });
  const [connectionFailed, setConnectionFailed] = useState(false);

  // Refs for synchronous terminal tracking and failure counting
  const isTerminalRef = useRef(false);
  const failureCountRef = useRef(0);

  const fetchStatus = useCallback(async () => {
    if (!jobId) return;

    try {
      const res = await apiFetch(`/api/generation/${jobId}/status`, getToken);
      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`);
      }
      const data: GenerationStatusResponse = await res.json();

      const status = (data.status ?? "unknown") as BuildStatus;
      const label = STAGE_LABELS[status] ?? data.stage_label ?? status;
      const isTerminal = TERMINAL_STATUSES.has(status);

      // Update terminal ref synchronously so interval can check it
      isTerminalRef.current = isTerminal;

      // Reset failure tracking on success
      failureCountRef.current = 0;
      setConnectionFailed(false);

      setState({
        status,
        label,
        previewUrl: data.preview_url ?? null,
        buildVersion: data.build_version ?? null,
        error: data.error_message ?? null,
        debugId: data.debug_id ?? null,
        sandboxExpiresAt: data.sandbox_expires_at ?? null,
        stageIndex: statusToStageIndex(status),
        totalStages: STAGE_ORDER.length,
        isTerminal,
      });
    } catch {
      failureCountRef.current += 1;
      if (failureCountRef.current >= 3) {
        setConnectionFailed(true);
      }
    }
  }, [jobId, getToken]);

  useEffect(() => {
    if (!jobId) return;

    // Reset state when jobId changes
    isTerminalRef.current = false;
    failureCountRef.current = 0;
    setConnectionFailed(false);

    // Immediate fetch on mount
    fetchStatus();

    // Polling interval — 5s, stops when terminal
    const interval = setInterval(() => {
      if (isTerminalRef.current) {
        clearInterval(interval);
        return;
      }
      fetchStatus();
    }, 5000);

    // Tab-focus refetch — immediately re-fetch when user returns to tab
    function handleVisibility() {
      if (!document.hidden) {
        fetchStatus();
      }
    }
    document.addEventListener("visibilitychange", handleVisibility);

    return () => {
      clearInterval(interval);
      document.removeEventListener("visibilitychange", handleVisibility);
    };
  }, [jobId, fetchStatus]);

  return { ...state, connectionFailed };
}
