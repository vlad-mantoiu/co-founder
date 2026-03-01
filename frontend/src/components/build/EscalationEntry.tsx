"use client";

import { useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import {
  ChevronDown,
  CheckCircle,
  AlertTriangle,
  LoaderCircle,
} from "lucide-react";
import type { Escalation } from "@/hooks/useAgentEscalations";

// ──────────────────────────────────────────────────────────────────────────────
// Props
// ──────────────────────────────────────────────────────────────────────────────

interface EscalationEntryProps {
  escalation: Escalation;
  onResolve: (escalationId: string, decision: string, guidance?: string) => Promise<void>;
}

// ──────────────────────────────────────────────────────────────────────────────
// EscalationEntry
// ──────────────────────────────────────────────────────────────────────────────

export function EscalationEntry({ escalation, onResolve }: EscalationEntryProps) {
  const [attemptsOpen, setAttemptsOpen] = useState(false);
  const [resolvedOpen, setResolvedOpen] = useState(false);
  const [resolvingId, setResolvingId] = useState<string | null>(null);
  const [guidanceText, setGuidanceText] = useState("");
  const [guidanceOptionId, setGuidanceOptionId] = useState<string | null>(null);

  const isResolved = escalation.status === "resolved";

  const handleOptionClick = async (optionId: string) => {
    // If this option is "provide_guidance" and guidance input isn't shown yet,
    // reveal the guidance text input instead of resolving immediately.
    const option = escalation.options.find((o) => o.id === optionId);
    const isGuidanceOption =
      option?.id === "provide_guidance" ||
      (option?.label ?? "").toLowerCase().includes("guidance");

    if (isGuidanceOption && guidanceOptionId !== optionId) {
      setGuidanceOptionId(optionId);
      return;
    }

    setResolvingId(optionId);
    try {
      await onResolve(
        escalation.id,
        optionId,
        guidanceOptionId === optionId ? guidanceText || undefined : undefined,
      );
    } finally {
      setResolvingId(null);
    }
  };

  // ── Resolved state ──────────────────────────────────────────────────────────

  if (isResolved) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        className="mx-4 my-2 rounded-xl border border-green-500/30 bg-green-950/20 overflow-hidden"
      >
        {/* Collapsed header */}
        <button
          type="button"
          className="w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-white/[0.03] transition-colors"
          onClick={() => setResolvedOpen((v) => !v)}
          aria-expanded={resolvedOpen}
        >
          <CheckCircle className="h-4 w-4 text-green-400 shrink-0" />
          <span className="flex-1 text-sm text-green-300/80 truncate">
            Resolved: {escalation.founder_decision ?? "Decision made"}
          </span>
          <motion.div
            animate={{ rotate: resolvedOpen ? 180 : 0 }}
            transition={{ duration: 0.2 }}
          >
            <ChevronDown className="h-3.5 w-3.5 text-white/20" />
          </motion.div>
        </button>

        {/* Expandable full details */}
        <AnimatePresence initial={false}>
          {resolvedOpen && (
            <motion.div
              key="resolved-details"
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: "auto", opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.2, ease: "easeInOut" }}
              className="overflow-hidden"
            >
              <div className="border-t border-green-500/20 px-4 py-3 space-y-3">
                <p className="text-sm text-white/70">
                  {escalation.plain_english_problem}
                </p>

                {escalation.attempts_summary.length > 0 && (
                  <div className="space-y-1.5">
                    <p className="text-xs font-medium text-white/40 uppercase tracking-wider">
                      What I tried
                    </p>
                    <ol className="space-y-1.5">
                      {escalation.attempts_summary.map((attempt) => (
                        <li key={attempt.attempt} className="flex gap-2 text-xs text-white/40">
                          <span className="shrink-0 font-medium text-white/30">
                            {attempt.attempt}.
                          </span>
                          <span>
                            {attempt.approach}
                            {attempt.result && (
                              <span className="text-white/25"> — {attempt.result}</span>
                            )}
                          </span>
                        </li>
                      ))}
                    </ol>
                  </div>
                )}

                <div className="flex items-center gap-2 pt-1">
                  <CheckCircle className="h-3.5 w-3.5 text-green-400 shrink-0" />
                  <p className="text-xs text-green-300/70">
                    Decision: {escalation.founder_decision}
                    {escalation.founder_guidance && (
                      <span className="text-white/30"> — "{escalation.founder_guidance}"</span>
                    )}
                  </p>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </motion.div>
    );
  }

  // ── Pending state ───────────────────────────────────────────────────────────

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, ease: "easeOut" }}
      className="mx-4 my-3 rounded-xl border border-amber-500/40 bg-amber-950/20 overflow-hidden"
    >
      <div className="p-4 space-y-4">
        {/* Header */}
        <div className="flex items-start gap-3">
          <AlertTriangle className="h-4 w-4 text-amber-400 shrink-0 mt-0.5" />
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-amber-200/90 leading-snug">
              {escalation.plain_english_problem}
            </p>
          </div>
        </div>

        {/* What I tried — collapsible */}
        {escalation.attempts_summary.length > 0 && (
          <div>
            <button
              type="button"
              className="flex items-center gap-1.5 text-xs text-white/40 hover:text-white/60 transition-colors"
              onClick={() => setAttemptsOpen((v) => !v)}
              aria-expanded={attemptsOpen}
            >
              <motion.div
                animate={{ rotate: attemptsOpen ? 90 : 0 }}
                transition={{ duration: 0.15 }}
              >
                <ChevronDown className="h-3 w-3" />
              </motion.div>
              What I tried ({escalation.attempts_summary.length} attempts)
            </button>

            <AnimatePresence initial={false}>
              {attemptsOpen && (
                <motion.div
                  key="attempts"
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: "auto", opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }}
                  transition={{ duration: 0.2, ease: "easeInOut" }}
                  className="overflow-hidden"
                >
                  <ol className="mt-2 space-y-2">
                    {escalation.attempts_summary.map((attempt) => (
                      <li key={attempt.attempt} className="flex gap-2 text-xs text-white/40">
                        <span className="shrink-0 font-medium text-white/30 w-4">
                          {attempt.attempt}.
                        </span>
                        <span className="leading-relaxed">
                          {attempt.approach}
                          {attempt.result && (
                            <span className="block text-white/25 mt-0.5">
                              Result: {attempt.result}
                            </span>
                          )}
                        </span>
                      </li>
                    ))}
                  </ol>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        )}

        {/* Recommended action callout */}
        {escalation.recommended_action && (
          <div className="rounded-lg border-l-2 border-blue-500 bg-blue-900/30 px-3 py-2">
            <p className="text-xs font-medium text-blue-300/80 mb-0.5">
              Recommended
            </p>
            <p className="text-sm text-blue-200/70">{escalation.recommended_action}</p>
          </div>
        )}

        {/* Decision buttons */}
        <div className="space-y-2">
          {escalation.options.map((option) => {
            const isGuidanceOption =
              option.id === "provide_guidance" ||
              option.label.toLowerCase().includes("guidance");
            const isThisResolving = resolvingId === option.id;
            const anyResolving = resolvingId !== null;
            const showGuidanceInput = guidanceOptionId === option.id;

            return (
              <div key={option.id}>
                <button
                  type="button"
                  disabled={anyResolving}
                  onClick={() => handleOptionClick(option.id)}
                  className={[
                    "w-full flex items-center justify-between gap-2 rounded-lg border px-3 py-2.5 text-sm text-left transition-all",
                    anyResolving
                      ? "cursor-not-allowed opacity-50"
                      : "cursor-pointer hover:bg-white/[0.06]",
                    showGuidanceInput && isGuidanceOption
                      ? "border-blue-500/50 bg-blue-950/30 text-blue-200/80"
                      : "border-white/15 bg-white/[0.04] text-white/75",
                  ].join(" ")}
                >
                  <span className="flex-1">
                    <span className="font-medium">{option.label}</span>
                    {option.description && (
                      <span className="block text-xs text-white/40 mt-0.5">
                        {option.description}
                      </span>
                    )}
                  </span>

                  {isThisResolving && (
                    <LoaderCircle className="h-4 w-4 animate-spin text-white/40 shrink-0" />
                  )}

                  {isGuidanceOption && !isThisResolving && (
                    <ChevronDown
                      className={[
                        "h-3.5 w-3.5 shrink-0 text-white/30 transition-transform",
                        showGuidanceInput ? "rotate-180" : "",
                      ].join(" ")}
                    />
                  )}
                </button>

                {/* Guidance text input — only for guidance option */}
                <AnimatePresence initial={false}>
                  {showGuidanceInput && (
                    <motion.div
                      key="guidance-input"
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: "auto", opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      transition={{ duration: 0.2, ease: "easeInOut" }}
                      className="overflow-hidden"
                    >
                      <div className="mt-2 flex gap-2">
                        <input
                          type="text"
                          value={guidanceText}
                          onChange={(e) => setGuidanceText(e.target.value)}
                          placeholder="Describe what you'd like me to try..."
                          className="flex-1 rounded-lg border border-white/15 bg-white/[0.06] px-3 py-2 text-sm text-white/80 placeholder-white/25 outline-none focus:border-blue-500/50 focus:ring-1 focus:ring-blue-500/30 transition-colors"
                          onKeyDown={(e) => {
                            if (e.key === "Enter" && guidanceText.trim()) {
                              handleOptionClick(option.id);
                            }
                          }}
                          autoFocus
                        />
                        <button
                          type="button"
                          disabled={!guidanceText.trim() || anyResolving}
                          onClick={() => handleOptionClick(option.id)}
                          className="rounded-lg border border-blue-500/40 bg-blue-600/20 px-3 py-2 text-sm text-blue-300 hover:bg-blue-600/30 disabled:cursor-not-allowed disabled:opacity-40 transition-colors"
                        >
                          Submit
                        </button>
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            );
          })}
        </div>
      </div>
    </motion.div>
  );
}
