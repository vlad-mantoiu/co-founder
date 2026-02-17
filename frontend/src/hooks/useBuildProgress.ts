"use client";

import { useState, useEffect } from "react";

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
  stageIndex: number;
  totalStages: number;
  isTerminal: boolean;
}

// ──────────────────────────────────────────────────────────────────────────────
// SSE event shape from /api/jobs/{job_id}/stream
// ──────────────────────────────────────────────────────────────────────────────

interface JobStreamEvent {
  job_id: string;
  status: string;
  message?: string;
  preview_url?: string;
  build_version?: string;
  error_message?: string;
  debug_id?: string;
}

const TERMINAL_STATUSES = new Set(["ready", "failed"]);

function statusToStageIndex(status: string): number {
  const idx = STAGE_ORDER.indexOf(status as (typeof STAGE_ORDER)[number]);
  return idx >= 0 ? idx : 0;
}

// ──────────────────────────────────────────────────────────────────────────────
// Hook
// ──────────────────────────────────────────────────────────────────────────────

export function useBuildProgress(jobId: string | null): BuildProgressState {
  const [state, setState] = useState<BuildProgressState>({
    status: "queued",
    label: STAGE_LABELS["queued"],
    previewUrl: null,
    buildVersion: null,
    error: null,
    debugId: null,
    stageIndex: 0,
    totalStages: STAGE_ORDER.length,
    isTerminal: false,
  });

  useEffect(() => {
    if (!jobId) return;

    const apiUrl =
      process.env.NEXT_PUBLIC_API_URL ?? "";
    const eventSource = new EventSource(
      `${apiUrl}/api/jobs/${jobId}/stream`
    );

    eventSource.onmessage = (event: MessageEvent<string>) => {
      let data: JobStreamEvent;
      try {
        data = JSON.parse(event.data) as JobStreamEvent;
      } catch {
        return;
      }

      const status = (data.status ?? "unknown") as BuildStatus;
      const label =
        STAGE_LABELS[status] ?? data.message ?? status;
      const isTerminal = TERMINAL_STATUSES.has(status);

      setState({
        status,
        label,
        previewUrl: data.preview_url ?? null,
        buildVersion: data.build_version ?? null,
        error: data.error_message ?? null,
        debugId: data.debug_id ?? null,
        stageIndex: statusToStageIndex(status),
        totalStages: STAGE_ORDER.length,
        isTerminal,
      });

      // Close once we hit a terminal state
      if (isTerminal) {
        eventSource.close();
      }
    };

    eventSource.onerror = () => {
      // On connection error, mark as terminal so UI can handle gracefully
      setState((prev) => ({
        ...prev,
        status: "failed",
        label: STAGE_LABELS["failed"],
        error: "Lost connection to build server. Please refresh.",
        isTerminal: true,
      }));
      eventSource.close();
    };

    return () => {
      eventSource.close();
    };
  }, [jobId]);

  return state;
}
