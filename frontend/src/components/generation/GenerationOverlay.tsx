"use client";

import { useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Loader2, CheckCircle2, XCircle, Sparkles } from "lucide-react";
import { useGenerationStatus } from "@/hooks/useGenerationStatus";

interface GenerationOverlayProps {
  projectId: string;
  onComplete: () => void;
  onFailed: () => void;
}

interface StepConfig {
  key: string;
  generatingLabel: string;
  completeLabel: string;
}

const STEPS: StepConfig[] = [
  {
    key: "strategy_graph",
    generatingLabel: "Building your strategy...",
    completeLabel: "Strategy built",
  },
  {
    key: "mvp_timeline",
    generatingLabel: "Creating your timeline...",
    completeLabel: "Timeline created",
  },
  {
    key: "app_architecture",
    generatingLabel: "Designing your architecture...",
    completeLabel: "Architecture designed",
  },
];

function StepIndicator({
  step,
  artifactStatus,
}: {
  step: StepConfig;
  artifactStatus?: { status: string; has_content: boolean };
}) {
  const status = artifactStatus?.status ?? "not_started";

  const isGenerating = status === "generating" || status === "not_started";
  const isComplete = status === "idle" && (artifactStatus?.has_content ?? false);
  const isFailed = status === "failed";

  return (
    <motion.div
      className="flex items-center gap-3"
      initial={{ opacity: 0, x: -10 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.3 }}
    >
      <div className="flex-shrink-0 w-6 h-6 flex items-center justify-center">
        <AnimatePresence mode="wait">
          {isComplete && (
            <motion.div
              key="check"
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              exit={{ scale: 0 }}
              transition={{ type: "spring", stiffness: 300, damping: 20 }}
            >
              <CheckCircle2 className="w-6 h-6 text-emerald-400" />
            </motion.div>
          )}
          {isFailed && (
            <motion.div
              key="x"
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              exit={{ scale: 0 }}
            >
              <XCircle className="w-6 h-6 text-red-400" />
            </motion.div>
          )}
          {isGenerating && (
            <motion.div
              key="spinner"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
            >
              <Loader2 className="w-5 h-5 text-brand animate-spin" />
            </motion.div>
          )}
        </AnimatePresence>
      </div>
      <span
        className={`text-sm font-medium transition-colors duration-300 ${
          isComplete
            ? "text-emerald-400"
            : isFailed
              ? "text-red-400"
              : "text-white/70"
        }`}
      >
        {isComplete ? step.completeLabel : isFailed ? `${step.completeLabel.replace("built", "failed").replace("created", "failed").replace("designed", "failed")}` : step.generatingLabel}
      </span>
    </motion.div>
  );
}

export function GenerationOverlay({
  projectId,
  onComplete,
  onFailed,
}: GenerationOverlayProps) {
  const { status, startPolling } = useGenerationStatus(projectId);

  useEffect(() => {
    startPolling();
  }, [startPolling]);

  const isAllComplete = status?.all_complete ?? false;
  const isAnyFailed = status?.any_failed ?? false;
  const isDone = isAllComplete || isAnyFailed;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm">
      <motion.div
        className="relative max-w-md w-full mx-4 bg-[#0f0f14] border border-white/10 rounded-2xl p-8 shadow-2xl"
        initial={{ opacity: 0, scale: 0.95, y: 20 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        transition={{ duration: 0.4, ease: "easeOut" }}
      >
        {/* Icon */}
        <div className="flex justify-center mb-6">
          <div className="relative">
            <div className="w-16 h-16 rounded-2xl bg-brand/10 border border-brand/20 flex items-center justify-center">
              <AnimatePresence mode="wait">
                {isAllComplete ? (
                  <motion.div
                    key="complete"
                    initial={{ scale: 0 }}
                    animate={{ scale: 1 }}
                    transition={{ type: "spring", stiffness: 300, damping: 20 }}
                  >
                    <CheckCircle2 className="w-8 h-8 text-brand" />
                  </motion.div>
                ) : isAnyFailed ? (
                  <motion.div key="failed" initial={{ scale: 0 }} animate={{ scale: 1 }}>
                    <XCircle className="w-8 h-8 text-red-400" />
                  </motion.div>
                ) : (
                  <motion.div
                    key="generating"
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                  >
                    <Sparkles className="w-8 h-8 text-brand animate-pulse" />
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
            {/* Pulse ring while generating */}
            {!isDone && (
              <motion.div
                className="absolute inset-0 rounded-2xl border border-brand/30"
                animate={{ scale: [1, 1.15, 1], opacity: [0.5, 0, 0.5] }}
                transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
              />
            )}
          </div>
        </div>

        {/* Title */}
        <AnimatePresence mode="wait">
          <motion.h2
            key={isAllComplete ? "complete" : isAnyFailed ? "failed" : "generating"}
            className="text-xl font-display font-semibold text-white text-center mb-2"
            initial={{ opacity: 0, y: 5 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -5 }}
            transition={{ duration: 0.2 }}
          >
            {isAllComplete
              ? "Your plan is ready!"
              : isAnyFailed
                ? "Some artifacts couldn't be generated"
                : "Analyzing your idea..."}
          </motion.h2>
        </AnimatePresence>

        <p className="text-sm text-white/40 text-center mb-8">
          {isAllComplete
            ? "We've transformed your answers into a personalized plan."
            : isAnyFailed
              ? "We'll show you what we were able to generate."
              : "Turning your answers into a personalized strategy, timeline, and architecture."}
        </p>

        {/* Steps */}
        <div className="space-y-4 mb-8">
          {STEPS.map((step) => (
            <StepIndicator
              key={step.key}
              step={step}
              artifactStatus={status?.artifacts?.[step.key]}
            />
          ))}
        </div>

        {/* CTA */}
        <AnimatePresence>
          {isDone && (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3, delay: 0.2 }}
            >
              <button
                onClick={isAllComplete ? onComplete : onFailed}
                className={`w-full py-3 px-6 rounded-xl font-semibold text-white transition-all duration-200 ${
                  isAllComplete
                    ? "bg-brand hover:bg-brand/90 shadow-glow"
                    : "bg-white/10 hover:bg-white/20"
                }`}
              >
                {isAllComplete ? "See your results" : "Continue anyway"}
              </button>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Animated dots while generating */}
        {!isDone && (
          <div className="flex justify-center gap-1.5">
            {[0, 1, 2].map((i) => (
              <motion.div
                key={i}
                className="w-1.5 h-1.5 rounded-full bg-brand/50"
                animate={{ opacity: [0.3, 1, 0.3], scale: [0.8, 1.2, 0.8] }}
                transition={{
                  duration: 1.2,
                  repeat: Infinity,
                  delay: i * 0.2,
                  ease: "easeInOut",
                }}
              />
            ))}
          </div>
        )}
      </motion.div>
    </div>
  );
}
