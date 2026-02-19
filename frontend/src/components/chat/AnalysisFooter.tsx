"use client";

import { Pause, Square, Wifi } from "lucide-react";

interface AnalysisFooterProps {
  latencyMs: number;
  onPause?: () => void;
  onAbort?: () => void;
  isPaused?: boolean;
}

export function AnalysisFooter({
  latencyMs,
  onPause,
  onAbort,
  isPaused,
}: AnalysisFooterProps) {
  return (
    <div className="flex items-center justify-between border-t border-white/5 px-4 py-2.5">
      <div className="flex items-center gap-2">
        {onPause && (
          <button
            onClick={onPause}
            className="flex items-center gap-1.5 rounded-lg border border-white/10 px-3 py-1.5 text-xs text-white/50 hover:border-white/20 hover:text-white/80 transition-colors"
          >
            <Pause className="h-3 w-3" />
            {isPaused ? "Resume" : "Pause"}
          </button>
        )}
        {onAbort && (
          <button
            onClick={onAbort}
            className="flex items-center gap-1.5 rounded-lg border border-red-500/20 px-3 py-1.5 text-xs text-red-400/60 hover:border-red-500/40 hover:text-red-400 transition-colors"
          >
            <Square className="h-3 w-3" />
            Abort
          </button>
        )}
      </div>

      <div className="flex items-center gap-3 text-[10px] uppercase tracking-widest text-white/30">
        <span className="flex items-center gap-1.5">
          <Wifi className="h-3 w-3 text-neon-green" />
          System: Online
        </span>
        <span className="text-white/10">|</span>
        <span>Latency: {latencyMs}ms</span>
      </div>
    </div>
  );
}
