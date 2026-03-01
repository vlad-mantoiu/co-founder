"use client";

import { useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import {
  ChevronDown,
  Bot,
  FileText,
  Terminal,
  Search,
  Camera,
  MessageCircle,
} from "lucide-react";
import type { FeedEntry } from "@/hooks/useAgentActivityFeed";

// ──────────────────────────────────────────────────────────────────────────────
// Helpers
// ──────────────────────────────────────────────────────────────────────────────

/**
 * Returns relative time string like "just now", "2m ago", "1h ago"
 */
function relativeTime(timestamp: string): string {
  const diffMs = Date.now() - new Date(timestamp).getTime();
  const diffSec = Math.floor(diffMs / 1000);

  if (diffSec < 10) return "just now";
  if (diffSec < 60) return `${diffSec}s ago`;

  const diffMin = Math.floor(diffSec / 60);
  if (diffMin < 60) return `${diffMin}m ago`;

  const diffHr = Math.floor(diffMin / 60);
  if (diffHr < 24) return `${diffHr}h ago`;

  return `${Math.floor(diffHr / 24)}d ago`;
}

/**
 * Maps tool name to a matching lucide-react icon component.
 */
function ToolIcon({ toolName }: { toolName?: string }) {
  const name = (toolName ?? "").toLowerCase();

  if (name === "bash" || name === "run_command") {
    return <Terminal className="h-3.5 w-3.5" />;
  }
  if (name.includes("search") || name.includes("grep") || name.includes("glob")) {
    return <Search className="h-3.5 w-3.5" />;
  }
  if (name.includes("screenshot")) {
    return <Camera className="h-3.5 w-3.5" />;
  }
  if (name === "narrate" || name === "document") {
    return <MessageCircle className="h-3.5 w-3.5" />;
  }
  // read_file, write_file, edit_file, etc.
  return <FileText className="h-3.5 w-3.5" />;
}

// ──────────────────────────────────────────────────────────────────────────────
// ActivityFeedEntry
// ──────────────────────────────────────────────────────────────────────────────

interface ActivityFeedEntryProps {
  entry: FeedEntry;
}

export function ActivityFeedEntry({ entry }: ActivityFeedEntryProps) {
  const [verboseOpen, setVerboseOpen] = useState(false);

  // ── Phase divider ───────────────────────────────────────────────────────────

  if (entry.type === "phase_divider") {
    return (
      <div className="relative flex items-center py-4 px-4">
        <div className="flex-1 border-t border-white/10" />
        <span className="mx-3 text-xs text-white/40 uppercase tracking-wider font-medium whitespace-nowrap">
          {entry.text}
        </span>
        <div className="flex-1 border-t border-white/10" />
      </div>
    );
  }

  // ── System entry ────────────────────────────────────────────────────────────

  if (entry.type === "system") {
    return (
      <div className="px-4 py-2">
        <p className="text-xs italic text-white/35">{entry.text}</p>
      </div>
    );
  }

  // ── Tool call entry (standalone — subtler style) ─────────────────────────────

  if (entry.type === "tool_call") {
    return (
      <div className="flex items-start gap-3 px-4 py-2">
        {/* Indent + icon */}
        <div className="flex items-center gap-1.5 mt-0.5 text-white/30 shrink-0 ml-11">
          <ToolIcon toolName={entry.toolName} />
          <span className="text-xs font-medium text-white/40">
            {entry.toolLabel ?? entry.text}
          </span>
        </div>
        {entry.toolSummary && (
          <span className="text-xs text-white/25 mt-0.5 truncate">
            {entry.toolSummary}
          </span>
        )}
      </div>
    );
  }

  // ── Narration entry (chat-bubble style) ─────────────────────────────────────

  const hasToolDetails = Boolean(entry.toolName ?? entry.toolLabel ?? entry.toolSummary);

  return (
    <div className="flex items-start gap-3 px-4 py-3">
      {/* Agent avatar */}
      <div className="shrink-0 w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center text-xs font-bold text-white">
        <Bot className="h-4 w-4" />
      </div>

      {/* Bubble */}
      <div className="flex-1 min-w-0">
        {/* Narration text + timestamp row */}
        <div className="flex items-start justify-between gap-2">
          <p className="text-sm text-white/85 leading-relaxed">{entry.text}</p>

          <div className="flex items-center gap-1.5 shrink-0 mt-0.5">
            <span className="text-xs text-white/25 whitespace-nowrap">
              {relativeTime(entry.timestamp)}
            </span>

            {/* Per-entry expand arrow — only when there are tool details */}
            {hasToolDetails && (
              <button
                type="button"
                onClick={() => setVerboseOpen((v) => !v)}
                className="p-0.5 rounded text-white/20 hover:text-white/60 transition-colors"
                aria-label={verboseOpen ? "Collapse tool details" : "Expand tool details"}
              >
                <motion.div
                  animate={{ rotate: verboseOpen ? 180 : 0 }}
                  transition={{ duration: 0.2 }}
                >
                  <ChevronDown className="h-3.5 w-3.5" />
                </motion.div>
              </button>
            )}
          </div>
        </div>

        {/* Verbose tool details — per-entry expand */}
        <AnimatePresence initial={false}>
          {verboseOpen && hasToolDetails && (
            <motion.div
              key="verbose"
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: "auto", opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.2, ease: "easeInOut" }}
              className="overflow-hidden"
            >
              <div className="mt-2 rounded-lg border border-white/8 bg-white/[0.04] px-3 py-2">
                <div className="flex items-start gap-2 text-white/50">
                  <ToolIcon toolName={entry.toolName} />
                  <div className="flex-1 min-w-0">
                    {entry.toolLabel && (
                      <p className="text-xs font-medium text-white/60">
                        {entry.toolLabel}
                      </p>
                    )}
                    {entry.toolSummary && (
                      <p className="text-xs text-white/35 mt-0.5">
                        {entry.toolSummary}
                      </p>
                    )}
                  </div>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
