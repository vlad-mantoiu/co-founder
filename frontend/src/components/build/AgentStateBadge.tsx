"use client";

import { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import {
  AlertCircle,
  CheckCircle2,
  Loader2,
  Moon,
  XCircle,
  X,
} from "lucide-react";
import { cn } from "@/lib/utils";
import type { AgentLifecycleState } from "@/hooks/useAgentState";

// ──────────────────────────────────────────────────────────────────────────────
// Types
// ──────────────────────────────────────────────────────────────────────────────

export interface AgentStateBadgeProps {
  state: AgentLifecycleState;
  elapsedMs: number;
  wakeAt: string | null;
  budgetPct: number | null;
  pendingEscalationCount: number;
  currentPhaseName: string | null;
  phasesCompleted: number;
  phasesTotal: number;
  onWakeNow?: () => void;
  onPauseAfterPhase?: () => void;
}

// ──────────────────────────────────────────────────────────────────────────────
// Helpers
// ──────────────────────────────────────────────────────────────────────────────

export function formatElapsed(ms: number): string {
  const totalSeconds = Math.floor(ms / 1000);
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);

  if (hours > 0) {
    return `${hours}h ${minutes}m`;
  }
  if (minutes > 0) {
    return `${minutes}m`;
  }
  return "< 1m";
}

export function formatCountdown(wakeAt: string): string {
  const remaining = new Date(wakeAt).getTime() - Date.now();

  if (remaining <= 0) {
    return "now";
  }

  const totalSeconds = Math.floor(remaining / 1000);
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;

  if (hours > 0) {
    return `${hours}h ${minutes}m`;
  }
  if (minutes > 0) {
    return `${minutes}m ${seconds}s`;
  }
  return `${seconds}s`;
}

// ──────────────────────────────────────────────────────────────────────────────
// State config
// ──────────────────────────────────────────────────────────────────────────────

interface StateConfig {
  bgClass: string;
  icon: React.ElementType;
  iconClass: string;
  pulseClass?: string;
}

const STATE_CONFIGS: Record<AgentLifecycleState, StateConfig> = {
  working: {
    bgClass: "bg-blue-600",
    icon: Loader2,
    iconClass: "animate-spin",
  },
  sleeping: {
    bgClass: "bg-indigo-800",
    icon: Moon,
    iconClass: "",
  },
  waiting_for_input: {
    bgClass: "bg-amber-600",
    icon: AlertCircle,
    iconClass: "",
    pulseClass: "animate-pulse",
  },
  error: {
    bgClass: "bg-red-600",
    icon: XCircle,
    iconClass: "",
  },
  idle: {
    bgClass: "bg-green-600",
    icon: CheckCircle2,
    iconClass: "",
  },
  completed: {
    bgClass: "bg-green-600",
    icon: CheckCircle2,
    iconClass: "",
  },
};

// ──────────────────────────────────────────────────────────────────────────────
// Badge label builder
// ──────────────────────────────────────────────────────────────────────────────

function getBadgeLabel(
  state: AgentLifecycleState,
  elapsedMs: number,
  wakeAt: string | null,
  pendingEscalationCount: number,
  currentPhaseName: string | null,
  countdown: string,
): string {
  switch (state) {
    case "working": {
      const elapsed = formatElapsed(elapsedMs);
      const phasePart = currentPhaseName ? `: ${currentPhaseName}` : "";
      return `Building${phasePart} (${elapsed})`;
    }
    case "sleeping":
      return wakeAt ? `Resting — wakes in ${countdown}` : "Resting";
    case "waiting_for_input":
      return pendingEscalationCount > 1
        ? `Needs input (${pendingEscalationCount})`
        : "Needs input";
    case "error":
      return "Error";
    case "idle":
    case "completed":
      return "Build complete";
    default:
      return "Idle";
  }
}

// ──────────────────────────────────────────────────────────────────────────────
// Popover content
// ──────────────────────────────────────────────────────────────────────────────

function PopoverContent({
  state,
  elapsedMs,
  wakeAt,
  budgetPct,
  pendingEscalationCount,
  currentPhaseName,
  phasesCompleted,
  phasesTotal,
  onWakeNow,
  onPauseAfterPhase,
  countdown,
  onClose,
}: AgentStateBadgeProps & {
  countdown: string;
  onClose: () => void;
}) {
  const stateLabel: Record<AgentLifecycleState, string> = {
    working: "Working",
    sleeping: "Sleeping",
    waiting_for_input: "Waiting for input",
    error: "Error",
    idle: "Idle",
    completed: "Build complete",
  };

  return (
    <div className="w-72 rounded-2xl border border-white/10 bg-[#0d0e1a] shadow-xl overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-4 pt-4 pb-3 border-b border-white/5">
        <span className="text-sm font-semibold text-white">
          Agent Status
        </span>
        <button
          type="button"
          onClick={onClose}
          className="p-1 rounded-lg text-white/30 hover:text-white/60 hover:bg-white/5 transition-colors"
        >
          <X className="w-3.5 h-3.5" />
        </button>
      </div>

      {/* Body */}
      <div className="px-4 py-3 space-y-3">
        {/* State label */}
        <div>
          <p className="text-xs text-white/40 mb-0.5">Current state</p>
          <p
            className={cn(
              "text-base font-semibold",
              state === "working" && "text-blue-400",
              state === "sleeping" && "text-indigo-400",
              state === "waiting_for_input" && "text-amber-400",
              state === "error" && "text-red-400",
              (state === "idle" || state === "completed") && "text-green-400",
            )}
          >
            {stateLabel[state]}
          </p>
        </div>

        {/* Current phase */}
        {currentPhaseName && (
          <div>
            <p className="text-xs text-white/40 mb-0.5">Current phase</p>
            <p className="text-sm text-white/80">{currentPhaseName}</p>
          </div>
        )}

        {/* Phase progress */}
        {phasesTotal > 0 && (
          <div>
            <p className="text-xs text-white/40 mb-0.5">Phase progress</p>
            <p className="text-sm text-white/70 font-mono">
              {phasesCompleted}/{phasesTotal} phases
            </p>
          </div>
        )}

        {/* Elapsed time (working only) */}
        {state === "working" && elapsedMs > 0 && (
          <div>
            <p className="text-xs text-white/40 mb-0.5">Elapsed</p>
            <p className="text-sm text-white/70 font-mono">
              {formatElapsed(elapsedMs)}
            </p>
          </div>
        )}

        {/* Countdown (sleeping only) */}
        {state === "sleeping" && wakeAt && (
          <div>
            <p className="text-xs text-white/40 mb-0.5">Wakes in</p>
            <p className="text-sm text-indigo-300 font-mono">{countdown}</p>
          </div>
        )}

        {/* Token budget */}
        {budgetPct != null && (
          <div>
            <div className="flex items-center justify-between mb-1">
              <p className="text-xs text-white/40">Budget remaining</p>
              <p
                className={cn(
                  "text-xs font-mono",
                  budgetPct > 30
                    ? "text-white/60"
                    : budgetPct > 10
                      ? "text-amber-400"
                      : "text-red-400",
                )}
              >
                {Math.round(budgetPct)}%
              </p>
            </div>
            <div className="h-1.5 rounded-full bg-white/10 overflow-hidden">
              <div
                className={cn(
                  "h-full rounded-full transition-all duration-500",
                  budgetPct > 30
                    ? "bg-green-500"
                    : budgetPct > 10
                      ? "bg-amber-500"
                      : "bg-red-500",
                )}
                style={{ width: `${Math.min(100, Math.max(0, budgetPct))}%` }}
              />
            </div>
          </div>
        )}

        {/* Pending escalations */}
        {pendingEscalationCount > 0 && (
          <div className="flex items-center gap-2 rounded-lg bg-amber-500/10 border border-amber-500/20 px-3 py-2">
            <AlertCircle className="w-3.5 h-3.5 text-amber-400 shrink-0" />
            <p className="text-xs text-amber-300">
              {pendingEscalationCount} pending decision
              {pendingEscalationCount > 1 ? "s" : ""} — scroll up to review
            </p>
          </div>
        )}
      </div>

      {/* Control actions */}
      {(state === "sleeping" || state === "working") && (
        <div className="px-4 pb-4 space-y-2">
          {state === "sleeping" && onWakeNow && (
            <button
              type="button"
              onClick={() => {
                onWakeNow();
                onClose();
              }}
              className="w-full rounded-xl bg-indigo-600 hover:bg-indigo-500 transition-colors px-4 py-2 text-sm font-medium text-white"
            >
              Wake now
            </button>
          )}
          {state === "working" && onPauseAfterPhase && (
            <button
              type="button"
              onClick={() => {
                onPauseAfterPhase();
                onClose();
              }}
              className="w-full rounded-xl border border-white/10 hover:bg-white/5 transition-colors px-4 py-2 text-sm font-medium text-white/70"
            >
              Pause after current phase
            </button>
          )}
        </div>
      )}
    </div>
  );
}

// ──────────────────────────────────────────────────────────────────────────────
// Main component
// ──────────────────────────────────────────────────────────────────────────────

export function AgentStateBadge(props: AgentStateBadgeProps) {
  const {
    state,
    elapsedMs,
    wakeAt,
    pendingEscalationCount,
    currentPhaseName,
  } = props;

  const [isPopoverOpen, setIsPopoverOpen] = useState(false);
  const [countdown, setCountdown] = useState("");
  const badgeRef = useRef<HTMLDivElement>(null);

  // ── Countdown timer (sleeping state) ────────────────────────────────────────

  useEffect(() => {
    if (state !== "sleeping" || !wakeAt) {
      setCountdown("");
      return;
    }

    // Set immediately
    setCountdown(formatCountdown(wakeAt));

    const interval = setInterval(() => {
      setCountdown(formatCountdown(wakeAt));
    }, 1000);

    return () => clearInterval(interval);
  }, [state, wakeAt]);

  // ── Click-outside to close popover ──────────────────────────────────────────

  useEffect(() => {
    if (!isPopoverOpen) return;

    function handleClick(e: MouseEvent) {
      if (badgeRef.current && !badgeRef.current.contains(e.target as Node)) {
        setIsPopoverOpen(false);
      }
    }

    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, [isPopoverOpen]);

  // ── State config ─────────────────────────────────────────────────────────────

  const config = STATE_CONFIGS[state] ?? STATE_CONFIGS.idle;
  const Icon = config.icon;
  const label = getBadgeLabel(
    state,
    elapsedMs,
    wakeAt,
    pendingEscalationCount,
    currentPhaseName,
    countdown,
  );

  return (
    <div
      ref={badgeRef}
      className="fixed bottom-6 right-6 z-50 flex flex-col items-end gap-2"
    >
      {/* ── Popover (above badge, right-aligned) ─────────────────────────────── */}
      <AnimatePresence>
        {isPopoverOpen && (
          <motion.div
            key="popover"
            initial={{ opacity: 0, y: 8, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 8, scale: 0.95 }}
            transition={{ duration: 0.15, ease: "easeOut" }}
          >
            <PopoverContent
              {...props}
              countdown={countdown}
              onClose={() => setIsPopoverOpen(false)}
            />
          </motion.div>
        )}
      </AnimatePresence>

      {/* ── Badge pill ───────────────────────────────────────────────────────── */}
      <button
        type="button"
        onClick={() => setIsPopoverOpen((v) => !v)}
        className={cn(
          "flex items-center gap-2 rounded-full px-4 py-2 shadow-lg",
          "text-sm font-medium text-white",
          "transition-all duration-200 hover:scale-105 active:scale-95",
          config.bgClass,
          config.pulseClass,
        )}
      >
        <Icon className={cn("w-4 h-4 shrink-0", config.iconClass)} />
        <span className="max-w-[220px] truncate">{label}</span>
      </button>
    </div>
  );
}
