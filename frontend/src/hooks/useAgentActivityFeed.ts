"use client";

import { useState, useCallback, useRef, useEffect } from "react";
import { apiFetch } from "@/lib/api";
import type { AgentEvent, EventHandlers } from "./useAgentEvents";

// ──────────────────────────────────────────────────────────────────────────────
// Types
// ──────────────────────────────────────────────────────────────────────────────

export interface FeedEntry {
  id: string;
  type: "narration" | "tool_call" | "phase_divider" | "escalation" | "system";
  timestamp: string;
  text: string;
  phaseId?: string;
  // Tool call specific
  toolName?: string;
  toolLabel?: string;
  toolSummary?: string;
  // Escalation specific
  escalationId?: string;
}

export interface AgentActivityFeedState {
  entries: FeedEntry[];
  isTyping: boolean;
  filterPhaseId: string | null;
  setFilterPhaseId: (id: string | null) => void;
  jumpToLatest: () => void;
  shouldAutoScroll: boolean;
  onUserScroll: (scrollTop: number, scrollHeight: number, clientHeight: number) => void;
  eventHandlers: Partial<EventHandlers>;
}

type GetTokenFn = () => Promise<string | null>;

// ──────────────────────────────────────────────────────────────────────────────
// Helpers
// ──────────────────────────────────────────────────────────────────────────────

function generateId(): string {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
}

function nowIso(): string {
  return new Date().toISOString();
}

// ──────────────────────────────────────────────────────────────────────────────
// Hook
// ──────────────────────────────────────────────────────────────────────────────

/**
 * useAgentActivityFeed — Activity feed entries from REST history + SSE live updates.
 *
 * Fetches narration history from GET /api/jobs/{jobId}/logs on mount.
 * Exposes `eventHandlers` for the page-level component to merge into the
 * single useAgentEvents call — do NOT call useAgentEvents here.
 *
 * Supports phase filtering (from timeline sidebar click) and typing indicator.
 * Tracks user scroll position to pause/resume auto-scroll.
 */
export function useAgentActivityFeed(
  jobId: string | null,
  getToken: GetTokenFn,
): AgentActivityFeedState {
  const [allEntries, setAllEntries] = useState<FeedEntry[]>([]);
  const [isTyping, setIsTyping] = useState(false);
  const [filterPhaseId, setFilterPhaseId] = useState<string | null>(null);
  const [shouldAutoScroll, setShouldAutoScroll] = useState(true);

  // Track whether user has scrolled up — ref for synchronous access in event handler
  const userScrolledUpRef = useRef(false);

  // ── REST bootstrap: load narration history ─────────────────────────────────

  useEffect(() => {
    if (!jobId) return;

    // Reset on jobId change
    setAllEntries([]);
    setIsTyping(false);
    setFilterPhaseId(null);
    setShouldAutoScroll(true);
    userScrolledUpRef.current = false;

    let cancelled = false;

    async function fetchHistory() {
      try {
        // Use existing logs endpoint — returns narration entries from Redis stream
        const res = await apiFetch(`/api/jobs/${jobId}/logs?limit=200`, getToken);
        if (!res.ok || cancelled) return;

        const data = (await res.json()) as {
          lines?: Array<{
            id: string;
            ts: string;
            source: string;
            text: string;
            phase?: string;
          }>;
        };

        if (cancelled) return;

        const historicEntries: FeedEntry[] = (data.lines ?? [])
          .filter((l) => l.text && l.text.trim().length > 0)
          .map((l) => ({
            id: l.id ?? generateId(),
            type: (l.source === "system" ? "system" : "narration") as FeedEntry["type"],
            timestamp: l.ts ?? nowIso(),
            text: l.text,
            phaseId: l.phase ?? undefined,
          }));

        if (!cancelled && historicEntries.length > 0) {
          setAllEntries(historicEntries);
        }
      } catch {
        // Silently fail — SSE will populate entries as they arrive live
      }
    }

    fetchHistory();

    return () => {
      cancelled = true;
    };
  }, [jobId, getToken]);

  // ── Auto-scroll control ─────────────────────────────────────────────────────

  const onUserScroll = useCallback(
    (scrollTop: number, scrollHeight: number, clientHeight: number) => {
      const atBottom = scrollHeight - scrollTop - clientHeight < 48;
      userScrolledUpRef.current = !atBottom;
      setShouldAutoScroll(atBottom);
    },
    [],
  );

  const jumpToLatest = useCallback(() => {
    userScrolledUpRef.current = false;
    setShouldAutoScroll(true);
  }, []);

  // ── SSE event handlers ──────────────────────────────────────────────────────

  const onAgentThinking = useCallback((_e: AgentEvent) => {
    setIsTyping(true);
  }, []);

  const onBuildStageStarted = useCallback((e: AgentEvent) => {
    setIsTyping(false);
    const text = (e.narration as string) ?? (e.stage as string) ?? "Agent is working...";
    const entry: FeedEntry = {
      id: generateId(),
      type: "narration",
      timestamp: (e.timestamp as string) ?? nowIso(),
      text,
      phaseId: (e.phase_id as string) ?? undefined,
    };
    setAllEntries((prev) => [...prev, entry]);
  }, []);

  const onAgentToolCalled = useCallback((e: AgentEvent) => {
    setIsTyping(false);
    const entry: FeedEntry = {
      id: generateId(),
      type: "tool_call",
      timestamp: (e.timestamp as string) ?? nowIso(),
      text: (e.tool_label as string) ?? (e.tool_name as string) ?? "Tool called",
      phaseId: (e.phase_id as string) ?? undefined,
      toolName: e.tool_name as string | undefined,
      toolLabel: e.tool_label as string | undefined,
      toolSummary: e.tool_summary as string | undefined,
    };
    setAllEntries((prev) => [...prev, entry]);
  }, []);

  const onGsdPhaseStarted = useCallback((e: AgentEvent) => {
    const phaseName = e.phase_name as string | undefined;
    if (!phaseName) return;

    const divider: FeedEntry = {
      id: generateId(),
      type: "phase_divider",
      timestamp: (e.timestamp as string) ?? nowIso(),
      text: phaseName,
      phaseId: e.phase_id as string | undefined,
    };
    setAllEntries((prev) => [...prev, divider]);
  }, []);

  const onAgentWaitingForInput = useCallback((e: AgentEvent) => {
    setIsTyping(false);
    const escalationId = e.escalation_id as string | undefined;
    const entry: FeedEntry = {
      id: generateId(),
      type: "escalation",
      timestamp: (e.timestamp as string) ?? nowIso(),
      text: (e.plain_english_problem as string) ?? "Your co-founder needs your input.",
      phaseId: (e.phase_id as string) ?? undefined,
      escalationId,
    };
    setAllEntries((prev) => [...prev, entry]);
  }, []);

  // ── Derived: filtered entries ───────────────────────────────────────────────

  const entries =
    filterPhaseId === null
      ? allEntries
      : allEntries.filter(
          (e) => e.phaseId === filterPhaseId || e.type === "phase_divider",
        );

  // ── Assemble eventHandlers for page-level composition ───────────────────────

  const eventHandlers: Partial<EventHandlers> = {
    onAgentThinking,
    onBuildStageStarted,
    onAgentToolCalled,
    onGsdPhaseStarted,
    onAgentWaitingForInput,
  };

  return {
    entries,
    isTyping,
    filterPhaseId,
    setFilterPhaseId,
    jumpToLatest,
    shouldAutoScroll,
    onUserScroll,
    eventHandlers,
  };
}
