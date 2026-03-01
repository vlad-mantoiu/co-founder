"use client";

import { useRef, useEffect } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Ghost, ArrowDown, X } from "lucide-react";
import { ActivityFeedEntry } from "./ActivityFeedEntry";
import { EscalationEntry } from "./EscalationEntry";
import type { FeedEntry } from "@/hooks/useAgentActivityFeed";
import type { Escalation } from "@/hooks/useAgentEscalations";

// ──────────────────────────────────────────────────────────────────────────────
// Props
// ──────────────────────────────────────────────────────────────────────────────

interface AgentActivityFeedProps {
  entries: FeedEntry[];
  escalations: Escalation[];
  isTyping: boolean;
  shouldAutoScroll: boolean;
  onUserScroll: (scrollTop: number, scrollHeight: number, clientHeight: number) => void;
  onJumpToLatest: () => void;
  onResolveEscalation: (
    escalationId: string,
    decision: string,
    guidance?: string,
  ) => Promise<void>;
  filterPhaseId: string | null;
  filterPhaseName?: string;
  onClearFilter?: () => void;
}

// ──────────────────────────────────────────────────────────────────────────────
// AgentActivityFeed
// ──────────────────────────────────────────────────────────────────────────────

/**
 * AgentActivityFeed — Scrollable feed container.
 *
 * Pure presentational component. All data and callbacks come through props.
 * Does NOT call any hooks directly.
 *
 * - Renders ActivityFeedEntry for narration/tool_call/phase_divider/system entries
 * - Renders EscalationEntry for escalation entries (matches by entry.escalationId)
 * - Auto-scrolls to bottom when shouldAutoScroll is true + new entries arrive
 * - Shows "Jump to latest" floating button when shouldAutoScroll is false
 * - Shows animated typing indicator (3 bouncing dots) when isTyping is true
 * - Phase filtering: indicator bar at top with clear button
 * - Empty state when no entries and not typing
 */
export function AgentActivityFeed({
  entries,
  escalations,
  isTyping,
  shouldAutoScroll,
  onUserScroll,
  onJumpToLatest,
  onResolveEscalation,
  filterPhaseId,
  filterPhaseName,
  onClearFilter,
}: AgentActivityFeedProps) {
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  // ── Auto-scroll to bottom when new entries arrive ────────────────────────────

  useEffect(() => {
    if (!shouldAutoScroll) return;
    const container = scrollContainerRef.current;
    if (!container) return;
    // Set scrollTop directly for instant scroll (no jank on rapid updates)
    container.scrollTop = container.scrollHeight;
  }, [entries.length, isTyping, shouldAutoScroll]);

  // ── Scroll event handler ─────────────────────────────────────────────────────

  function handleScroll() {
    const container = scrollContainerRef.current;
    if (!container) return;
    onUserScroll(container.scrollTop, container.scrollHeight, container.clientHeight);
  }

  // ── Jump to latest ───────────────────────────────────────────────────────────

  function handleJumpToLatest() {
    onJumpToLatest();
    const container = scrollContainerRef.current;
    if (container) {
      container.scrollTop = container.scrollHeight;
    }
  }

  // ── Build escalation lookup map ──────────────────────────────────────────────

  const escalationMap = new Map<string, Escalation>(
    escalations.map((e) => [e.id, e]),
  );

  // ── Empty state ───────────────────────────────────────────────────────────────

  const isEmpty = entries.length === 0 && !isTyping;

  // ─────────────────────────────────────────────────────────────────────────────

  return (
    <div className="relative flex flex-col h-full">

      {/* Phase filter indicator */}
      <AnimatePresence>
        {filterPhaseId && (
          <motion.div
            key="filter-bar"
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden shrink-0"
          >
            <div className="flex items-center justify-between gap-2 px-4 py-2 border-b border-white/10 bg-white/[0.03]">
              <span className="text-xs text-white/50">
                Showing:{" "}
                <span className="text-white/70 font-medium">
                  {filterPhaseName ?? filterPhaseId}
                </span>
              </span>
              {onClearFilter && (
                <button
                  type="button"
                  onClick={onClearFilter}
                  className="rounded p-0.5 text-white/30 hover:text-white/60 transition-colors"
                  aria-label="Clear phase filter"
                >
                  <X className="h-3.5 w-3.5" />
                </button>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Scrollable feed area */}
      <div
        ref={scrollContainerRef}
        onScroll={handleScroll}
        className="flex-1 overflow-y-auto py-2"
      >
        {isEmpty ? (
          /* Empty state */
          <div className="flex flex-col items-center justify-center h-full gap-3 py-16 px-4 text-center">
            <Ghost className="h-10 w-10 text-white/15" />
            <p className="text-sm text-white/30 max-w-xs leading-relaxed">
              Activity will appear here as your co-founder works.
            </p>
          </div>
        ) : (
          /* Entry list */
          <>
            {entries.map((entry) => {
              if (entry.type === "escalation") {
                // Find matching escalation by escalationId
                const escalation =
                  entry.escalationId
                    ? escalationMap.get(entry.escalationId)
                    : undefined;

                if (!escalation) {
                  // Escalation not yet loaded — render a subtle placeholder
                  return (
                    <div key={entry.id} className="px-4 py-2">
                      <p className="text-xs italic text-white/25">
                        Loading escalation details...
                      </p>
                    </div>
                  );
                }

                return (
                  <EscalationEntry
                    key={entry.id}
                    escalation={escalation}
                    onResolve={onResolveEscalation}
                  />
                );
              }

              return <ActivityFeedEntry key={entry.id} entry={entry} />;
            })}
          </>
        )}

        {/* Typing indicator */}
        <AnimatePresence>
          {isTyping && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.2 }}
              className="flex items-center gap-1 px-4 py-3"
            >
              <div className="w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center text-xs font-bold text-white mr-3 shrink-0">
                CF
              </div>
              {[0, 1, 2].map((i) => (
                <motion.span
                  key={i}
                  className="w-2 h-2 rounded-full bg-white/40"
                  animate={{ y: [0, -4, 0] }}
                  transition={{
                    repeat: Infinity,
                    duration: 0.6,
                    delay: i * 0.15,
                  }}
                />
              ))}
            </motion.div>
          )}
        </AnimatePresence>

        {/* Invisible scroll anchor */}
        <div ref={bottomRef} />
      </div>

      {/* Jump to latest floating button */}
      <AnimatePresence>
        {!shouldAutoScroll && (
          <motion.div
            key="jump-to-latest"
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 8 }}
            transition={{ duration: 0.2 }}
            className="absolute bottom-4 left-1/2 -translate-x-1/2 z-10"
          >
            <button
              type="button"
              onClick={handleJumpToLatest}
              className="flex items-center gap-1.5 rounded-full border border-white/20 bg-white/10 px-3 py-1.5 text-xs text-white/70 backdrop-blur-sm hover:bg-white/15 hover:text-white transition-all shadow-lg"
            >
              <ArrowDown className="h-3 w-3" />
              Jump to latest
            </button>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
