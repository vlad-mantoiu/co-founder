"use client";

import { motion } from "framer-motion";
import { CheckCircle2, Network, Plus } from "lucide-react";

interface AnalysisOutputProps {
  output: string;
  sessionId: string | null;
  onNewAnalysis: () => void;
}

export function AnalysisOutput({
  output,
  sessionId,
  onNewAnalysis,
}: AnalysisOutputProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="mx-auto w-full max-w-2xl"
    >
      <div className="glass rounded-2xl p-6 space-y-4">
        {/* Success header */}
        <div className="flex items-center gap-3">
          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-neon-green/20">
            <CheckCircle2 className="h-4 w-4 text-neon-green" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-white">
              Analysis Complete
            </h3>
            <p className="text-xs text-white/40">
              All stages processed successfully
            </p>
          </div>
        </div>

        {/* Output text */}
        <div className="rounded-xl bg-white/[0.03] p-4">
          <p className="whitespace-pre-wrap text-sm leading-relaxed text-white/80">
            {output}
          </p>
        </div>

        {/* CTAs */}
        <div className="flex items-center gap-3">
          {sessionId && (
            <a
              href={`/architecture?session=${sessionId}`}
              className="flex items-center gap-2 rounded-xl bg-brand px-4 py-2.5 text-sm font-medium text-white hover:bg-brand-dark transition-colors"
            >
              <Network className="h-4 w-4" />
              View Architecture
            </a>
          )}
          <button
            onClick={onNewAnalysis}
            className="flex items-center gap-2 rounded-xl border border-white/10 px-4 py-2.5 text-sm font-medium text-white/70 hover:border-white/20 hover:text-white transition-colors"
          >
            <Plus className="h-4 w-4" />
            New Analysis
          </button>
        </div>
      </div>
    </motion.div>
  );
}
