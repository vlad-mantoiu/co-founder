"use client";

import { useEffect, useRef, useState } from "react";
import { motion } from "framer-motion";
import {
  Wand2,
  Code2,
  Package,
  Play,
  CheckCircle2,
  Check,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { cn } from "@/lib/utils";

// ──────────────────────────────────────────────────────────────────────────────
// Stage bar items — maps backend STAGE_ORDER indices to user-facing labels
// STAGE_ORDER = queued(0), starting(1), scaffold(2), code(3), deps(4), checks(5), ready(6)
// ──────────────────────────────────────────────────────────────────────────────

interface StageBarItem {
  key: string;
  label: string;
  icon: LucideIcon;
  backendIndex: number; // Index in STAGE_ORDER from useBuildProgress
}

const STAGE_BAR_ITEMS: StageBarItem[] = [
  { key: "scaffold", label: "Designing", icon: Wand2, backendIndex: 2 },
  { key: "code", label: "Writing code", icon: Code2, backendIndex: 3 },
  {
    key: "deps",
    label: "Installing dependencies",
    icon: Package,
    backendIndex: 4,
  },
  { key: "checks", label: "Starting app", icon: Play, backendIndex: 5 },
  { key: "ready", label: "Ready", icon: CheckCircle2, backendIndex: 6 },
];

// ──────────────────────────────────────────────────────────────────────────────
// Elapsed time formatter — "M:SS"
// ──────────────────────────────────────────────────────────────────────────────

function formatElapsed(seconds: number): string {
  return `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, "0")}`;
}

// ──────────────────────────────────────────────────────────────────────────────
// Props
// ──────────────────────────────────────────────────────────────────────────────

interface BuildProgressBarProps {
  stageIndex: number; // From useBuildProgress (STAGE_ORDER index)
  totalStages: number; // From useBuildProgress
  label: string; // From useBuildProgress (status label — shown as subtitle)
  status: string; // From useBuildProgress (current status string)
  autoFixAttempt?: number | null; // Non-null when auto-fix is retrying — renders amber highlight
}

// ──────────────────────────────────────────────────────────────────────────────
// Component — horizontal segmented bar with 5 user-facing stages
// ──────────────────────────────────────────────────────────────────────────────

export function BuildProgressBar({
  stageIndex,
  label,
  status,
  autoFixAttempt,
}: BuildProgressBarProps) {
  const isBuilding = status !== "ready" && status !== "failed";
  const isAutoFix = autoFixAttempt != null && isBuilding;

  // ── Elapsed timer ──
  const startTimeRef = useRef<number | null>(null);
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    if (!isBuilding) {
      setElapsed(0);
      startTimeRef.current = null;
      return;
    }

    // Start timer when building begins
    if (startTimeRef.current === null) {
      startTimeRef.current = Date.now();
    }

    const interval = setInterval(() => {
      if (startTimeRef.current !== null) {
        setElapsed(Math.floor((Date.now() - startTimeRef.current) / 1000));
      }
    }, 1000);

    return () => clearInterval(interval);
  }, [isBuilding]);

  return (
    <div className="w-full">
      {/* Horizontal segmented bar */}
      <div className="flex w-full gap-1">
        {STAGE_BAR_ITEMS.map((item) => {
          const isComplete = stageIndex > item.backendIndex;
          const isActive = stageIndex === item.backendIndex;
          const isPending = stageIndex < item.backendIndex;

          // Active segment color: amber during auto-fix, brand otherwise
          const activeColor = isAutoFix ? "bg-amber-500" : "bg-brand";
          const activeIconColor = isAutoFix ? "text-amber-400" : "text-white";
          const activeLabelColor = isAutoFix
            ? "text-amber-300"
            : "text-white";

          return (
            <div key={item.key} className="flex-1 flex flex-col">
              {/* Top: fill bar segment */}
              {isComplete ? (
                <div className="h-1.5 rounded-full bg-brand" />
              ) : isActive ? (
                <motion.div
                  className={cn("h-1.5 rounded-full", activeColor)}
                  animate={{ opacity: [0.6, 1, 0.6] }}
                  transition={{
                    duration: 1.5,
                    repeat: Infinity,
                    ease: "easeInOut",
                  }}
                />
              ) : (
                <div className="h-1.5 rounded-full bg-white/10" />
              )}

              {/* Bottom: icon + label */}
              <div className="flex flex-col items-center mt-3 gap-1">
                {/* Icon */}
                {isComplete ? (
                  <motion.div
                    initial={{ scale: 0 }}
                    animate={{ scale: 1 }}
                    transition={{
                      type: "spring",
                      stiffness: 300,
                      damping: 20,
                    }}
                  >
                    <Check
                      className="w-4 h-4 text-brand"
                      strokeWidth={2.5}
                    />
                  </motion.div>
                ) : isActive ? (
                  <item.icon className={cn("w-4 h-4", activeIconColor)} />
                ) : (
                  <item.icon className="w-4 h-4 text-white/30" />
                )}

                {/* Label */}
                <span
                  className={cn(
                    "text-xs text-center leading-tight",
                    isComplete && "text-brand",
                    isActive && activeLabelColor,
                    isPending && "text-white/30"
                  )}
                >
                  {item.label}
                </span>
              </div>
            </div>
          );
        })}
      </div>

      {/* Elapsed timer — shown only while building and after first second */}
      {isBuilding && elapsed > 0 && (
        <p className="text-sm text-white/40 font-mono mt-4 text-center">
          Building... {formatElapsed(elapsed)}
        </p>
      )}

      {/* Backend status label — subtle subtitle below timer */}
      {isBuilding && (
        <p className="text-xs text-white/30 mt-1 text-center">{label}</p>
      )}
    </div>
  );
}
