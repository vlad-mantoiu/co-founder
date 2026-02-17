"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { AlertTriangle, RefreshCw, ChevronDown, ChevronUp } from "lucide-react";
import { cn } from "@/lib/utils";

// ──────────────────────────────────────────────────────────────────────────────
// Props
// ──────────────────────────────────────────────────────────────────────────────

interface BuildFailureCardProps {
  errorMessage: string;
  debugId: string;
  onRetry: () => void;
  className?: string;
}

// ──────────────────────────────────────────────────────────────────────────────
// Component — friendly failure + retry (locked decision: no tech details unless expanded)
// ──────────────────────────────────────────────────────────────────────────────

export function BuildFailureCard({
  errorMessage,
  debugId,
  onRetry,
  className,
}: BuildFailureCardProps) {
  const [detailsOpen, setDetailsOpen] = useState(false);

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, ease: "easeOut" }}
      className={cn(
        "glass rounded-2xl border border-red-500/20 p-8 flex flex-col items-center gap-6 text-center",
        className
      )}
    >
      {/* Icon */}
      <motion.div
        initial={{ scale: 0 }}
        animate={{ scale: 1 }}
        transition={{ delay: 0.1, type: "spring", stiffness: 250, damping: 20 }}
        className="w-16 h-16 rounded-full bg-red-500/10 border border-red-500/20 flex items-center justify-center"
      >
        <AlertTriangle className="w-8 h-8 text-red-400" />
      </motion.div>

      {/* Friendly message */}
      <div className="space-y-1">
        <h2 className="text-xl font-display font-semibold text-white">
          We hit an issue.
        </h2>
        <p className="text-sm text-white/60">
          Want us to try again? We&apos;ll pick up from where things left off.
        </p>
      </div>

      {/* Retry button */}
      <motion.button
        onClick={onRetry}
        whileHover={{ scale: 1.02 }}
        whileTap={{ scale: 0.97 }}
        className="inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-brand hover:bg-brand-dark text-white font-semibold text-sm transition-colors shadow-glow"
      >
        <RefreshCw className="w-4 h-4" />
        Try again
      </motion.button>

      {/* Expandable details — collapsed by default (locked decision) */}
      <div className="w-full max-w-sm">
        <button
          onClick={() => setDetailsOpen((v) => !v)}
          className="w-full flex items-center justify-between px-4 py-2.5 rounded-xl bg-white/5 hover:bg-white/8 border border-white/10 text-sm text-white/50 hover:text-white/70 transition-colors"
        >
          <span>View details</span>
          {detailsOpen ? (
            <ChevronUp className="w-4 h-4" />
          ) : (
            <ChevronDown className="w-4 h-4" />
          )}
        </button>

        <AnimatePresence>
          {detailsOpen && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: "auto", opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.25, ease: "easeInOut" }}
              className="overflow-hidden"
            >
              <div className="mt-3 px-4 py-3 rounded-xl bg-white/3 border border-white/8 text-left space-y-3">
                {/* Error message */}
                {errorMessage && (
                  <div>
                    <span className="text-xs text-white/40 uppercase tracking-wider font-mono block mb-1">
                      Error
                    </span>
                    <p className="text-xs text-white/70 font-mono break-words leading-relaxed">
                      {errorMessage}
                    </p>
                  </div>
                )}

                {/* Debug ID for support reference */}
                <div className="border-t border-white/8 pt-3">
                  <span className="text-xs text-white/40 uppercase tracking-wider font-mono block mb-1">
                    Debug ID
                  </span>
                  <p className="text-xs text-white/50 font-mono select-all">
                    {debugId}
                  </p>
                  <p className="text-xs text-white/30 mt-1">
                    Share this with support if the issue persists.
                  </p>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </motion.div>
  );
}
