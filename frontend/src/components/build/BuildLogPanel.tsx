"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { ChevronDown, ChevronUp, LoaderCircle } from "lucide-react";
import type { LogLine } from "@/hooks/useBuildLogs";

interface BuildLogPanelProps {
  lines: LogLine[];
  isConnected: boolean;
  hasEarlierLines: boolean;
  onLoadEarlier: () => Promise<void>;
}

export function BuildLogPanel({
  lines,
  isConnected,
  hasEarlierLines,
  onLoadEarlier,
}: BuildLogPanelProps) {
  const [open, setOpen] = useState(false);
  const [isLoadingEarlier, setIsLoadingEarlier] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const hasLoadedInitial = useRef(false);

  // Auto-load initial history batch on first panel open
  useEffect(() => {
    if (open && !hasLoadedInitial.current) {
      hasLoadedInitial.current = true;
      onLoadEarlier();
    }
  }, [open, onLoadEarlier]);

  // Check if user is near bottom of the log container
  const shouldAutoScroll = useCallback((): boolean => {
    const el = containerRef.current;
    if (!el) return true;
    return el.scrollHeight - el.scrollTop - el.clientHeight < 50;
  }, []);

  // Smart auto-scroll — pauses when user has scrolled up
  useEffect(() => {
    if (!open) return;
    if (shouldAutoScroll()) {
      bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }
  }, [lines.length, open, shouldAutoScroll]);

  const handleLoadEarlier = async () => {
    setIsLoadingEarlier(true);
    try {
      await onLoadEarlier();
    } finally {
      setIsLoadingEarlier(false);
    }
  };

  return (
    <div className="w-full">
      {/* Toggle button */}
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center justify-between rounded-xl border border-white/10 bg-white/5 px-4 py-2.5 text-sm text-white/50 transition-colors hover:bg-white/[0.08] hover:text-white/70"
        type="button"
        aria-expanded={open}
      >
        <span className="flex items-center gap-2">
          {isConnected && (
            <LoaderCircle className="h-3.5 w-3.5 animate-spin text-white/40" />
          )}
          <span>Technical details</span>
        </span>
        {open ? (
          <ChevronUp className="h-4 w-4 text-white/30" />
        ) : (
          <ChevronDown className="h-4 w-4 text-white/30" />
        )}
      </button>

      {/* Expandable log panel */}
      <AnimatePresence>
        {open && (
          <motion.div
            key="log-panel"
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.25, ease: "easeInOut" }}
            className="overflow-hidden"
          >
            <div className="mt-1 rounded-xl border border-white/10 bg-black/30">
              {/* Load earlier button */}
              {hasEarlierLines && (
                <div className="border-b border-white/5">
                  <button
                    onClick={handleLoadEarlier}
                    disabled={isLoadingEarlier}
                    className="w-full px-3 py-1.5 text-xs text-white/30 transition-colors hover:text-white/50 disabled:cursor-not-allowed disabled:opacity-50"
                    type="button"
                  >
                    {isLoadingEarlier ? "Loading..." : "Load earlier output"}
                  </button>
                </div>
              )}

              {/* Log lines */}
              <div
                ref={containerRef}
                className="max-h-64 overflow-y-auto p-3 font-mono text-xs leading-relaxed"
              >
                {lines.length === 0 ? (
                  <div className="text-white/20">No output yet...</div>
                ) : (
                  lines.map((line) => (
                    <div
                      key={line.id}
                      className={[
                        "border-l-2 py-0.5 pl-2",
                        line.source === "stderr"
                          ? "border-orange-500/60 text-orange-300/80"
                          : line.source === "system"
                            ? "border-blue-500/40 text-blue-300/60"
                            : "border-transparent text-white/60",
                      ].join(" ")}
                    >
                      {line.text}
                    </div>
                  ))
                )}
                <div ref={bottomRef} />
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
