"use client";

import { motion } from "framer-motion";
import { Check } from "lucide-react";
import { cn } from "@/lib/utils";
import { STAGE_ORDER, STAGE_DISPLAY_NAMES } from "@/hooks/useBuildProgress";

// ──────────────────────────────────────────────────────────────────────────────
// Stepper stages (excludes terminal "ready" — shown via BuildSummary instead)
// We use the middle stages that represent active build work
// ──────────────────────────────────────────────────────────────────────────────

const STEPPER_STAGES = [
  "scaffold",
  "code",
  "deps",
  "checks",
] as const;

type StepperStage = (typeof STEPPER_STAGES)[number];

const STEPPER_DISPLAY_NAMES: Record<StepperStage, string> = {
  scaffold: "Scaffolding",
  code: "Writing code",
  deps: "Installing deps",
  checks: "Running checks",
};

// Map full STAGE_ORDER index → stepper stage index
// Stages before "scaffold" (queued/starting) → stepper index 0 (not yet started)
// "ready"/"failed" handled by parent — pass stageIndex from STAGE_ORDER
function stageOrderIndexToStepperIndex(stageIndex: number): number {
  // STAGE_ORDER = queued(0), starting(1), scaffold(2), code(3), deps(4), checks(5), ready(6)
  // Stepper: scaffold=0, code=1, deps=2, checks=3
  const offset = 2; // STAGE_ORDER index where scaffold lives
  return Math.max(0, stageIndex - offset);
}

// ──────────────────────────────────────────────────────────────────────────────
// Props
// ──────────────────────────────────────────────────────────────────────────────

interface BuildProgressBarProps {
  stageIndex: number;
  totalStages: number;
  label: string;
  status: string;
}

// ──────────────────────────────────────────────────────────────────────────────
// Component
// ──────────────────────────────────────────────────────────────────────────────

export function BuildProgressBar({
  stageIndex,
  label,
  status,
}: BuildProgressBarProps) {
  const stepperIndex = stageOrderIndexToStepperIndex(stageIndex);
  const isBuilding = status !== "ready" && status !== "failed";

  return (
    <div className="w-full">
      {/* Label */}
      <motion.p
        key={label}
        initial={{ opacity: 0, y: 4 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
        className="text-center text-sm text-white/70 mb-6 font-mono"
      >
        {label}
      </motion.p>

      {/* Stepper */}
      <div className="relative flex items-center justify-between">
        {STEPPER_STAGES.map((stage, idx) => {
          const isComplete = stepperIndex > idx;
          const isActive = stepperIndex === idx && isBuilding;
          const isFuture = stepperIndex < idx;

          return (
            <div
              key={stage}
              className="relative flex flex-col items-center flex-1"
            >
              {/* Connector line (before each step except first) */}
              {idx > 0 && (
                <div
                  className="absolute top-4 right-1/2 w-full h-0.5 -translate-y-1/2"
                  style={{ left: "-50%" }}
                >
                  <div
                    className={cn(
                      "h-full w-full transition-colors duration-500",
                      isComplete
                        ? "bg-brand"
                        : "bg-white/10"
                    )}
                  />
                </div>
              )}

              {/* Stage circle */}
              <motion.div
                className={cn(
                  "relative z-10 w-8 h-8 rounded-full flex items-center justify-center border-2 transition-all duration-500",
                  isComplete &&
                    "bg-brand border-brand shadow-glow",
                  isActive &&
                    "border-brand bg-brand/20",
                  isFuture &&
                    "border-white/20 bg-white/5"
                )}
                animate={
                  isActive
                    ? {
                        boxShadow: [
                          "0 0 0px rgba(100,103,242,0)",
                          "0 0 16px rgba(100,103,242,0.6)",
                          "0 0 0px rgba(100,103,242,0)",
                        ],
                      }
                    : {}
                }
                transition={
                  isActive
                    ? { duration: 1.6, repeat: Infinity, ease: "easeInOut" }
                    : {}
                }
              >
                {isComplete ? (
                  <Check className="w-4 h-4 text-white" strokeWidth={2.5} />
                ) : isActive ? (
                  <motion.div
                    className="w-2.5 h-2.5 rounded-full bg-brand"
                    animate={{ scale: [1, 1.3, 1] }}
                    transition={{
                      duration: 1.2,
                      repeat: Infinity,
                      ease: "easeInOut",
                    }}
                  />
                ) : (
                  <div className="w-2 h-2 rounded-full bg-white/20" />
                )}
              </motion.div>

              {/* Stage label */}
              <span
                className={cn(
                  "mt-2 text-xs font-medium transition-colors duration-300 text-center leading-tight",
                  isComplete && "text-brand",
                  isActive && "text-white",
                  isFuture && "text-white/30"
                )}
              >
                {STEPPER_DISPLAY_NAMES[stage]}
              </span>
            </div>
          );
        })}
      </div>

      {/* Pulsing bar below stepper when building */}
      {isBuilding && (
        <motion.div
          className="mt-6 h-0.5 w-full bg-white/5 rounded-full overflow-hidden"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.3 }}
        >
          <motion.div
            className="h-full bg-gradient-to-r from-transparent via-brand to-transparent w-1/3 rounded-full"
            animate={{ x: ["-100%", "400%"] }}
            transition={{
              duration: 1.8,
              repeat: Infinity,
              ease: "easeInOut",
            }}
          />
        </motion.div>
      )}
    </div>
  );
}
