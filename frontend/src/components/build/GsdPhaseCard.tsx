"use client";

import { useRef } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { CheckCircle2, Circle, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";
import type { GsdPhase } from "@/hooks/useAgentPhases";

// ──────────────────────────────────────────────────────────────────────────────
// Re-export GsdPhase for convenience so consumers can import from this file
// ──────────────────────────────────────────────────────────────────────────────

export type { GsdPhase };

// ──────────────────────────────────────────────────────────────────────────────
// Helpers
// ──────────────────────────────────────────────────────────────────────────────

function formatElapsed(startedAt: string): string {
  const ms = Date.now() - new Date(startedAt).getTime();
  const minutes = Math.floor(ms / 60_000);
  const hours = Math.floor(minutes / 60);
  if (hours > 0) {
    return `${hours}h ${minutes % 60}m`;
  }
  return `${minutes}m`;
}

// ──────────────────────────────────────────────────────────────────────────────
// Props
// ──────────────────────────────────────────────────────────────────────────────

export interface GsdPhaseCardProps {
  phase: GsdPhase;
  isActive: boolean;
  isSelected: boolean;
  onClick: () => void;
}

// ──────────────────────────────────────────────────────────────────────────────
// Component
// ──────────────────────────────────────────────────────────────────────────────

export function GsdPhaseCard({
  phase,
  isActive,
  isSelected,
  onClick,
}: GsdPhaseCardProps) {
  const isCompleted = phase.status === "completed";
  const isInProgress = phase.status === "in_progress";
  const isPending = phase.status === "pending";

  // Completed phases can be toggled open/closed by click (expand details)
  // In-progress is always expanded. Pending is always collapsed.
  // We track expanded state via internal ref for completed phases.
  // Using a simple approach: isSelected controls the expanded state for completed phases.

  const hasPlanProgress =
    phase.plan_count != null && phase.plan_count > 0;

  return (
    <button
      type="button"
      onClick={isPending ? undefined : onClick}
      disabled={isPending}
      className={cn(
        "w-full text-left rounded-xl border transition-all duration-200",
        // Base
        "px-3 py-2.5",
        // Pending: dimmed, non-interactive
        isPending && "opacity-40 cursor-default border-white/5 bg-transparent",
        // Completed: subtle green tint
        isCompleted &&
          !isSelected &&
          "border-white/10 bg-white/[0.02] hover:bg-white/[0.05] hover:border-green-500/20 cursor-pointer",
        isCompleted &&
          isSelected &&
          "border-green-500/30 bg-green-500/5 cursor-pointer",
        // In-progress: blue animated border
        isInProgress &&
          !isSelected &&
          "border-blue-500/30 bg-blue-500/5 cursor-pointer",
        isInProgress &&
          isSelected &&
          "border-blue-400/50 bg-blue-500/10 cursor-pointer",
        // Animate-pulse-border on in-progress (uses CSS from globals.css)
        isInProgress && "animate-pulse-border",
      )}
    >
      {/* ── Header row: icon + name ─────────────────────────────────────────── */}
      <div className="flex items-center gap-2">
        {/* Status icon */}
        {isCompleted && (
          <CheckCircle2
            className={cn(
              "w-4 h-4 shrink-0",
              isSelected ? "text-green-400" : "text-green-500/60",
            )}
          />
        )}
        {isInProgress && (
          <Loader2
            className={cn(
              "w-4 h-4 shrink-0 animate-spin",
              isSelected ? "text-blue-300" : "text-blue-400",
            )}
          />
        )}
        {isPending && (
          <Circle className="w-4 h-4 shrink-0 text-white/20" />
        )}

        {/* Phase name */}
        <span
          className={cn(
            "text-sm font-medium truncate leading-tight",
            isCompleted && "text-white/70",
            isInProgress && "text-white",
            isPending && "text-white/40",
          )}
        >
          {phase.phase_name}
        </span>
      </div>

      {/* ── Expanded details: in-progress always visible, completed when selected ── */}
      <AnimatePresence initial={false}>
        {(isInProgress || (isCompleted && isSelected)) && (
          <motion.div
            key="details"
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2, ease: "easeInOut" }}
            className="overflow-hidden"
          >
            <div className="mt-2 space-y-1">
              {/* Phase description / goal */}
              {phase.phase_description && (
                <p
                  className={cn(
                    "text-xs leading-relaxed",
                    isInProgress ? "text-white/50" : "text-white/40",
                  )}
                >
                  {phase.phase_description}
                </p>
              )}

              {/* Plan progress */}
              {hasPlanProgress && (
                <p
                  className={cn(
                    "text-xs font-mono",
                    isInProgress ? "text-blue-300/70" : "text-white/40",
                  )}
                >
                  {phase.plans_completed ?? 0}/{phase.plan_count} plans
                </p>
              )}

              {/* Elapsed time (in-progress only) */}
              {isInProgress && phase.started_at && (
                <p className="text-xs text-white/30 font-mono">
                  {formatElapsed(phase.started_at)} elapsed
                </p>
              )}

              {/* Completed at (completed + selected) */}
              {isCompleted && phase.completed_at && (
                <p className="text-xs text-green-500/50 font-mono">
                  Completed
                </p>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </button>
  );
}
