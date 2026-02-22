"use client";

import { useState, useCallback, useRef, useEffect } from "react";
import { apiFetch } from "@/lib/api";

export interface LogLine {
  id: string;
  ts: string;
  source: "stdout" | "stderr" | "system";
  text: string;
  phase: string;
}

export interface BuildLogsState {
  lines: LogLine[];
  isConnected: boolean;
  isDone: boolean;
  doneStatus: "ready" | "failed" | null;
  hasEarlierLines: boolean;
  oldestId: string | null;
  autoFixAttempt: number | null;
}

type GetTokenFn = () => Promise<string | null>;

const INITIAL_STATE: BuildLogsState = {
  lines: [],
  isConnected: false,
  isDone: false,
  doneStatus: null,
  hasEarlierLines: true, // default true — REST call corrects to false if no history
  oldestId: null,
  autoFixAttempt: null,
};

const AUTO_FIX_REGEX = /auto.fix.*?attempt\s+(\d+)\s+of\s+(\d+)/i;
const CLEAR_AUTO_FIX_REGEX = /running health checks|starting dev server/i;

export function useBuildLogs(
  jobId: string | null,
  getToken: GetTokenFn,
): BuildLogsState & { loadEarlier: () => Promise<void> } {
  const [state, setState] = useState<BuildLogsState>(INITIAL_STATE);

  const abortRef = useRef<AbortController | null>(null);
  const readerRef = useRef<ReadableStreamDefaultReader<Uint8Array> | null>(null);

  const connectSSE = useCallback(async () => {
    if (!jobId) return;

    // Create a fresh AbortController for this invocation
    const controller = new AbortController();
    abortRef.current = controller;

    let response: Response;
    try {
      response = await apiFetch(`/api/jobs/${jobId}/logs/stream`, getToken, {
        signal: controller.signal,
      });
    } catch (err) {
      if ((err as Error).name === "AbortError") return;
      setState((s) => ({ ...s, isConnected: false }));
      return;
    }

    if (!response.ok || !response.body) {
      setState((s) => ({ ...s, isConnected: false }));
      return;
    }

    setState((s) => ({ ...s, isConnected: true }));

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

          if (eventType === "heartbeat") {
            // No-op — keeps connection alive past ALB 60s idle timeout
            continue;
          }

          if (eventType === "done") {
            let parsedStatus: "ready" | "failed" | null = null;
            try {
              const parsed = JSON.parse(dataStr) as { status: "ready" | "failed" };
              parsedStatus = parsed.status;
            } catch {
              // ignore parse error
            }
            setState((s) => ({
              ...s,
              isDone: true,
              isConnected: false,
              doneStatus: parsedStatus,
            }));
            return;
          }

          if (eventType === "log") {
            let logLine: LogLine;
            try {
              logLine = JSON.parse(dataStr) as LogLine;
            } catch {
              continue;
            }

            // Auto-fix detection from system source lines
            if (logLine.source === "system") {
              const autoFixMatch = AUTO_FIX_REGEX.exec(logLine.text);
              if (autoFixMatch) {
                const attempt = parseInt(autoFixMatch[1], 10);
                setState((s) => ({
                  ...s,
                  lines: [...s.lines, logLine],
                  autoFixAttempt: attempt,
                }));
                continue;
              }

              if (CLEAR_AUTO_FIX_REGEX.test(logLine.text)) {
                setState((s) => ({
                  ...s,
                  lines: [...s.lines, logLine],
                  autoFixAttempt: null,
                }));
                continue;
              }
            }

            setState((s) => ({ ...s, lines: [...s.lines, logLine] }));
          }
        }
      }
    } catch (err) {
      if ((err as Error).name === "AbortError") return;
      setState((s) => ({ ...s, isConnected: false }));
    }
  }, [jobId, getToken]);

  useEffect(() => {
    if (!jobId) return;

    // Reset to initial state when jobId changes
    setState(INITIAL_STATE);

    connectSSE();

    return () => {
      abortRef.current?.abort();
      readerRef.current?.cancel();
    };
  }, [jobId, connectSSE]);

  const loadEarlier = useCallback(async () => {
    if (!jobId) return;

    const oldestId = state.oldestId;
    const url = oldestId
      ? `/api/jobs/${jobId}/logs?before_id=${encodeURIComponent(oldestId)}&limit=100`
      : `/api/jobs/${jobId}/logs?limit=100`;

    try {
      const response = await apiFetch(url, getToken);
      if (!response.ok) return;

      const data = (await response.json()) as {
        lines: LogLine[];
        has_more: boolean;
        oldest_id: string | null;
      };

      setState((s) => ({
        ...s,
        lines: [...data.lines, ...s.lines],
        hasEarlierLines: data.has_more,
        oldestId: data.oldest_id,
      }));
    } catch {
      // Silently fail — user can retry
    }
  }, [jobId, getToken, state.oldestId]);

  return { ...state, loadEarlier };
}
