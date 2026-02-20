"use client";

import { AnimatePresence, motion } from "framer-motion";
import { IdeaInput } from "./IdeaInput";
import { ParsingState } from "./ParsingState";
import { WorkStreamPanel } from "./WorkStreamPanel";
import { AnalysisDepthMeter } from "./AnalysisDepthMeter";
import { AnalysisFooter } from "./AnalysisFooter";
import { AnalysisOutput } from "./AnalysisOutput";
import { useDemoSequence } from "@/hooks/useDemoSequence";
import { useAgentStream } from "@/hooks/useAgentStream";

interface ChatWindowProps {
  demoMode?: boolean;
}

export function ChatWindow({ demoMode = false }: ChatWindowProps) {
  const demo = useDemoSequence();
  const real = useAgentStream();
  const { state, start, reset, abort } = demoMode ? demo : real;

  return (
    <div className="flex h-[calc(100vh-7rem)] flex-col glass-strong rounded-2xl overflow-hidden">
      <div className="flex-1 overflow-y-auto scrollbar-thin p-6">
        <AnimatePresence mode="wait">
          {state.phase === "idle" && (
            <motion.div
              key="idle"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
            >
              <IdeaInput onSubmit={start} />
              {state.error && (
                <p className="mt-4 text-center text-sm text-red-400">
                  {state.error}
                </p>
              )}
            </motion.div>
          )}

          {state.phase === "parsing" && (
            <motion.div
              key="parsing"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
            >
              <ParsingState idea={state.idea} entities={state.entities} />
            </motion.div>
          )}

          {state.phase === "analysis" && (
            <motion.div
              key="analysis"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="space-y-4"
            >
              <AnalysisDepthMeter progress={state.progress} />
              <WorkStreamPanel stages={state.stages} />
            </motion.div>
          )}

          {state.phase === "complete" && state.finalOutput && (
            <motion.div
              key="complete"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
            >
              <AnalysisOutput
                output={state.finalOutput}
                onNewAnalysis={reset}
              />
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {state.phase === "analysis" && (
        <AnalysisFooter
          latencyMs={state.latencyMs}
          onPause={undefined}
          onAbort={abort}
        />
      )}
    </div>
  );
}
