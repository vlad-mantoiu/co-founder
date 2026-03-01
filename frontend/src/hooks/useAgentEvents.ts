"use client";

import { useState, useCallback, useRef, useEffect } from "react";
import { apiFetch } from "@/lib/api";

// ──────────────────────────────────────────────────────────────────────────────
// Types
// ──────────────────────────────────────────────────────────────────────────────

export type AgentEvent = {
  type: string;
  job_id?: string;
  timestamp?: string;
  [key: string]: unknown;
};

export type EventHandlers = {
  onAgentThinking?: (e: AgentEvent) => void;
  onAgentToolCalled?: (e: AgentEvent) => void;
  onAgentSleeping?: (e: AgentEvent) => void;
  onAgentWaking?: (e: AgentEvent) => void;
  onAgentWaitingForInput?: (e: AgentEvent) => void;
  onAgentBuildPaused?: (e: AgentEvent) => void;
  onAgentBudgetUpdated?: (e: AgentEvent) => void;
  onGsdPhaseStarted?: (e: AgentEvent) => void;
  onGsdPhaseCompleted?: (e: AgentEvent) => void;
  onBuildStageStarted?: (e: AgentEvent) => void;
  onAgentEscalationResolved?: (e: AgentEvent) => void;
};

type GetTokenFn = () => Promise<string | null>;

const RECONNECT_DELAY_MS = 3000;
const TERMINAL_JOB_STATUSES = new Set(["ready", "failed"]);

// ──────────────────────────────────────────────────────────────────────────────
// Hook
// ──────────────────────────────────────────────────────────────────────────────

/**
 * useAgentEvents — Single SSE consumer for /api/jobs/{jobId}/events/stream.
 *
 * Dispatches each event to the appropriate handler callback. Unknown event
 * types are silently ignored (UIAG-05). SSE stays open while agent is sleeping
 * (transient state). Only closes when job reaches "ready" or "failed" status.
 *
 * IMPORTANT: Call this hook exactly ONCE per page. Each domain hook
 * (useAgentPhases, useAgentState, etc.) exposes an `eventHandlers` object;
 * the page-level component merges them and passes them here.
 */
export function useAgentEvents(
  jobId: string | null,
  getToken: GetTokenFn,
  handlers: EventHandlers,
): { isConnected: boolean } {
  const [isConnected, setIsConnected] = useState(false);

  const abortRef = useRef<AbortController | null>(null);
  const readerRef = useRef<ReadableStreamDefaultReader<Uint8Array> | null>(null);
  // Stable ref so the connectSSE callback can always access the latest handlers
  // without being recreated on each render.
  const handlersRef = useRef<EventHandlers>(handlers);
  handlersRef.current = handlers;

  const connectSSE = useCallback(async () => {
    if (!jobId) return;

    const controller = new AbortController();
    abortRef.current = controller;

    let response: Response;
    try {
      response = await apiFetch(`/api/jobs/${jobId}/events/stream`, getToken, {
        signal: controller.signal,
      });
    } catch (err) {
      if ((err as Error).name === "AbortError") return;
      setIsConnected(false);
      return;
    }

    if (!response.ok || !response.body) {
      setIsConnected(false);
      return;
    }

    setIsConnected(true);

    const reader = response.body.getReader();
    readerRef.current = reader;
    const decoder = new TextDecoder("utf-8", { fatal: false });
    let buffer = "";

    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        // Split on double newline — SSE block separator
        const blocks = buffer.split("\n\n");
        // Keep the last potentially-incomplete segment in buffer
        buffer = blocks.pop() ?? "";

        for (const block of blocks) {
          if (!block.trim()) continue;

          // Parse named SSE fields
          let eventType = "message";
          let dataStr = "";

          for (const line of block.split("\n")) {
            if (line.startsWith("event:")) {
              eventType = line.slice(6).trim();
            } else if (line.startsWith("data:")) {
              dataStr = line.slice(5).trim();
            }
          }

          // No-op — keeps connection alive past ALB 60s idle timeout
          if (eventType === "heartbeat") continue;

          // Parse event payload
          let event: AgentEvent;
          try {
            event = JSON.parse(dataStr) as AgentEvent;
          } catch {
            // Silently ignore malformed JSON
            continue;
          }

          // Terminal job statuses close the stream
          if (
            eventType === "done" ||
            (event.status && TERMINAL_JOB_STATUSES.has(event.status as string))
          ) {
            setIsConnected(false);
            return;
          }

          // Route by event.type — unknown types silently ignored (UIAG-05)
          const h = handlersRef.current;
          switch (event.type) {
            case "agent.thinking":
              h.onAgentThinking?.(event);
              break;
            case "agent.tool.called":
              h.onAgentToolCalled?.(event);
              break;
            case "agent.sleeping":
              // NOT a terminal state — do NOT close SSE (Pitfall 1)
              h.onAgentSleeping?.(event);
              break;
            case "agent.waking":
              h.onAgentWaking?.(event);
              break;
            case "agent.waiting_for_input":
              h.onAgentWaitingForInput?.(event);
              break;
            case "agent.build_paused":
              h.onAgentBuildPaused?.(event);
              break;
            case "agent.budget_updated":
              h.onAgentBudgetUpdated?.(event);
              break;
            case "gsd.phase.started":
              h.onGsdPhaseStarted?.(event);
              break;
            case "gsd.phase.completed":
              h.onGsdPhaseCompleted?.(event);
              break;
            case "build.stage.started":
              h.onBuildStageStarted?.(event);
              break;
            case "agent.escalation_resolved":
              h.onAgentEscalationResolved?.(event);
              break;
            default:
              // Silently ignore unknown event types (UIAG-05)
              break;
          }
        }
      }
    } catch (err) {
      if ((err as Error).name === "AbortError") return;
      setIsConnected(false);
    }

    // Stream ended without explicit abort — schedule reconnect
    if (!controller.signal.aborted) {
      setTimeout(() => {
        if (!controller.signal.aborted) {
          connectSSE();
        }
      }, RECONNECT_DELAY_MS);
    }
  }, [jobId, getToken]);

  useEffect(() => {
    if (!jobId) return;

    setIsConnected(false);
    connectSSE();

    return () => {
      abortRef.current?.abort();
      readerRef.current?.cancel();
    };
  }, [jobId, connectSSE]);

  return { isConnected };
}
