"use client";

import { motion } from "framer-motion";
import { Check } from "lucide-react";
import { cn } from "@/lib/utils";

interface OnboardingProgressProps {
  current: number;
  total: number;
}

export function OnboardingProgress({ current, total }: OnboardingProgressProps) {
  const pct = Math.round((current / total) * 100);

  return (
    <div className="flex items-center gap-4">
      <div className="flex-1 h-2 rounded-full bg-white/5 overflow-hidden">
        <motion.div
          className="h-full rounded-full bg-brand"
          initial={{ width: 0 }}
          animate={{ width: `${pct}%` }}
          transition={{ duration: 0.6, ease: "easeOut" }}
        />
      </div>
      <span className="text-sm text-muted-foreground whitespace-nowrap">
        {current}/{total} complete
      </span>
    </div>
  );
}

type StepStatus = "pending" | "active" | "completed";

interface OnboardingStepProps {
  icon: React.ReactNode;
  title: string;
  description: string;
  status: StepStatus;
  stepNumber: number;
  cta?: React.ReactNode;
}

export function OnboardingStep({
  icon,
  title,
  description,
  status,
  stepNumber,
  cta,
}: OnboardingStepProps) {
  const isDisabled = status === "pending";

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: stepNumber * 0.1, duration: 0.4 }}
      className={cn(
        "glass-strong rounded-2xl p-6 flex items-start gap-5 transition-all",
        isDisabled && "opacity-50 pointer-events-none",
        status === "active" && "ring-1 ring-brand/40 shadow-glow",
      )}
    >
      {/* Step indicator */}
      <div
        className={cn(
          "flex-shrink-0 w-10 h-10 rounded-xl flex items-center justify-center text-sm font-semibold",
          status === "completed"
            ? "bg-brand text-white"
            : status === "active"
              ? "bg-brand/20 text-brand"
              : "bg-white/5 text-muted-foreground",
        )}
      >
        {status === "completed" ? (
          <motion.div
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            transition={{ type: "spring", stiffness: 300 }}
          >
            <Check className="w-5 h-5" />
          </motion.div>
        ) : (
          icon
        )}
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        <h3 className="font-display font-semibold text-lg leading-tight">
          {title}
        </h3>
        <p className="text-sm text-muted-foreground mt-1">{description}</p>
        {cta && status === "active" && <div className="mt-4">{cta}</div>}
      </div>
    </motion.div>
  );
}
