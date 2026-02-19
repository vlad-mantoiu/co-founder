"use client";

import { useState, useCallback, useRef } from "react";
import { useAuth } from "@clerk/nextjs";
import { apiFetch } from "@/lib/api";
import type {
  AnalysisState,
  SSEEvent,
  LogLine,
  StageState,
} from "@/components/chat/types";
import {
  createInitialStages,
  STAGE_MAP,
  ORDERED_STAGES,
} from "@/components/chat/types";

const INITIAL_STATE: AnalysisState = {
  phase: "idle",
  idea: "",
  entities: [],
  stages: createInitialStages(),
  activeStageIndex: -1,
  progress: 0,
  sessionId: null,
  latencyMs: 0,
  finalOutput: null,
  error: null,
};

export function useAgentStream() {
  const { getToken } = useAuth();
  const [state, setState] = useState<AnalysisState>(INITIAL_STATE);
  const readerRef = useRef<ReadableStreamDefaultReader<Uint8Array> | null>(
    null,
  );
  const abortControllerRef = useRef<AbortController | null>(null);

  const reset = useCallback(() => {
    readerRef.current?.cancel();
    abortControllerRef.current?.abort();
    setState(INITIAL_STATE);
  }, []);

  const abort = useCallback(() => {
    readerRef.current?.cancel();
    abortControllerRef.current?.abort();
    setState((s) => ({ ...s, phase: "idle", error: "Analysis aborted" }));
  }, []);

  const start = useCallback(
    async (idea: string) => {
      abortControllerRef.current = new AbortController();

      setState({
        ...INITIAL_STATE,
        phase: "parsing",
        idea,
        entities: [],
      });

      // Brief parsing phase
      await new Promise((r) => setTimeout(r, 800));

      setState((s) => ({
        ...s,
        phase: "analysis",
        stages: createInitialStages(),
        activeStageIndex: 0,
      }));

      try {
        const response = await apiFetch("/api/agent/chat/stream", getToken, {
          method: "POST",
          body: JSON.stringify({
            message: idea,
            project_id: "default",
          }),
          signal: abortControllerRef.current.signal,
        });

        if (!response.ok) {
          throw new Error(`API error: ${response.status}`);
        }

        const reader = response.body?.getReader();
        if (!reader) throw new Error("No reader available");
        readerRef.current = reader;

        const decoder = new TextDecoder();
        const stages: StageState[] = createInitialStages();
        let currentNode = "";
        let lineCount = 0;
        const startTime = Date.now();

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          const chunk = decoder.decode(value);
          const lines = chunk.split("\n");

          for (const line of lines) {
            if (!line.startsWith("data: ")) continue;

            let event: SSEEvent;
            try {
              event = JSON.parse(line.slice(6));
            } catch {
              continue;
            }

            const sessionId = event.session_id;

            if (event.node === "complete") {
              // Mark remaining active stages as complete
              for (const stage of stages) {
                if (stage.status === "active") {
                  stage.status = "complete";
                  stage.summary = "Completed";
                  stage.durationMs = Date.now() - startTime;
                }
              }

              setState((s) => ({
                ...s,
                phase: "complete",
                stages: [...stages],
                progress: 100,
                sessionId,
                finalOutput: event.message,
                latencyMs: Date.now() - startTime,
              }));
              return;
            }

            if (event.node === "error") {
              setState((s) => ({
                ...s,
                phase: "idle",
                error: event.message,
              }));
              return;
            }

            // Map backend node to UI stage
            const stageId = STAGE_MAP[event.node];
            if (!stageId) continue;

            const stageIdx = ORDERED_STAGES.findIndex(
              (s) => s.id === stageId,
            );
            if (stageIdx === -1) continue;

            // Transition to new stage
            if (event.node !== currentNode) {
              // Complete previous stage
              if (currentNode) {
                const prevId = STAGE_MAP[currentNode];
                const prevIdx = ORDERED_STAGES.findIndex(
                  (s) => s.id === prevId,
                );
                if (prevIdx >= 0 && stages[prevIdx].status === "active") {
                  stages[prevIdx].status = "complete";
                  stages[prevIdx].summary =
                    stages[prevIdx].logs[stages[prevIdx].logs.length - 1]
                      ?.text ?? "Completed";
                  stages[prevIdx].durationMs = Date.now() - startTime;
                }
              }

              currentNode = event.node;
              stages[stageIdx].status = "active";
              lineCount = 0;
            }

            // Add log line
            lineCount++;
            const logLine: LogLine = {
              id: `${sessionId}-${stageIdx}-${lineCount}`,
              text: event.message,
              timestamp: Date.now(),
            };
            stages[stageIdx] = {
              ...stages[stageIdx],
              logs: [...stages[stageIdx].logs, logLine],
            };

            const progress =
              ((stageIdx + lineCount / 10) / ORDERED_STAGES.length) * 100;

            setState((s) => ({
              ...s,
              stages: [...stages],
              activeStageIndex: stageIdx,
              progress: Math.min(95, progress),
              sessionId,
              latencyMs: Math.round(Date.now() - startTime),
            }));
          }
        }
      } catch (err) {
        if ((err as Error).name === "AbortError") return;
        setState((s) => ({
          ...s,
          phase: "idle",
          error: (err as Error).message,
        }));
      }
    },
    [getToken],
  );

  return { state, start, reset, abort };
}
