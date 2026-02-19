"use client";

import { motion } from "framer-motion";
import { Check, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { TerminalOutput } from "./TerminalOutput";
import type { StageState } from "./types";

interface StageCardProps {
  stage: StageState;
  index: number;
}

export function StageCard({ stage, index }: StageCardProps) {
  const { status, label, logs, summary, durationMs, metrics } = stage;

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, delay: index * 0.05 }}
      className={cn(
        "relative rounded-xl border p-4 transition-all",
        status === "active" &&
          "border-brand/50 bg-brand/5 animate-pulse-border",
        status === "complete" && "border-white/5 bg-white/[0.02] opacity-70",
        status === "queued" && "border-dashed border-white/10 bg-transparent",
      )}
    >
      <div className="flex items-center gap-3">
        {/* Icon */}
        <div
          className={cn(
            "flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-xs font-bold",
            status === "complete" && "bg-neon-green/20 text-neon-green",
            status === "active" && "bg-brand/20 text-brand",
            status === "queued" &&
              "border border-dashed border-white/20 text-white/30",
          )}
        >
          {status === "complete" && <Check className="h-3.5 w-3.5" />}
          {status === "active" && (
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
          )}
          {status === "queued" && <span>{index + 1}</span>}
        </div>

        {/* Label + badge */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span
              className={cn(
                "text-sm font-medium truncate",
                status === "active" && "text-white",
                status === "complete" && "text-white/60",
                status === "queued" && "text-white/40",
              )}
            >
              {label}
            </span>
            {status === "active" && (
              <span className="shrink-0 rounded-full bg-brand/20 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider text-brand">
                Processing
              </span>
            )}
            {status === "complete" && durationMs !== undefined && (
              <span className="shrink-0 text-[10px] font-medium uppercase tracking-wider text-neon-green/70">
                Done {durationMs}ms
              </span>
            )}
            {status === "queued" && (
              <span className="shrink-0 text-[10px] font-medium uppercase tracking-wider text-white/20">
                Waiting
              </span>
            )}
          </div>
          {status === "complete" && summary && (
            <p className="mt-1 text-xs text-white/40 line-clamp-1">
              {summary}
            </p>
          )}
        </div>
      </div>

      {/* Expanded content for active stage */}
      {status === "active" && logs.length > 0 && (
        <div className="mt-3 space-y-3">
          <TerminalOutput lines={logs} maxHeight="180px" />
          {metrics && Object.keys(metrics).length > 0 && (
            <div className="grid grid-cols-3 gap-2">
              {Object.entries(metrics).map(([key, val]) => (
                <div
                  key={key}
                  className="rounded-lg bg-white/[0.03] px-2.5 py-1.5 text-center"
                >
                  <div className="text-[10px] uppercase tracking-wider text-white/30">
                    {key}
                  </div>
                  <div className="text-xs font-medium text-white/70">{val}</div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </motion.div>
  );
}
