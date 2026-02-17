"use client";

import { useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { X, ChevronDown, ChevronRight } from "lucide-react";
import { useState } from "react";

const NODE_COLORS = {
  decision: "bg-violet-500/20 text-violet-300 border-violet-500/30",
  milestone: "bg-emerald-500/20 text-emerald-300 border-emerald-500/30",
  artifact: "bg-blue-500/20 text-blue-300 border-blue-500/30",
} as const;

const NODE_TYPE_LABELS = {
  decision: "Decision",
  milestone: "Milestone",
  artifact: "Artifact",
} as const;

export interface NodeDetail {
  id: string;
  title: string;
  type: "decision" | "milestone" | "artifact";
  status: string;
  created_at: string;
  why: string;
  impact_summary: string;
  tradeoffs: string[];
  alternatives: string[];
}

export interface NodeDetailModalProps {
  node: NodeDetail | null;
  onClose: () => void;
  showGraphLink?: boolean;
  onViewInGraph?: (nodeId: string) => void;
}

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
  });
}

interface ExpandableSectionProps {
  title: string;
  items: string[];
}

function ExpandableSection({ title, items }: ExpandableSectionProps) {
  const [expanded, setExpanded] = useState(false);

  if (items.length === 0) return null;

  return (
    <div className="border-t border-white/5 pt-3">
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex items-center gap-2 text-sm font-medium text-white/60 hover:text-white/80 transition-colors w-full text-left"
      >
        {expanded ? (
          <ChevronDown className="w-4 h-4 flex-shrink-0" />
        ) : (
          <ChevronRight className="w-4 h-4 flex-shrink-0" />
        )}
        {title}
        <span className="text-xs text-white/30 ml-auto">{items.length}</span>
      </button>
      {expanded && (
        <ul className="mt-2 space-y-1 pl-6">
          {items.map((item, i) => (
            <li key={i} className="text-sm text-white/60 list-disc">
              {item}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export function NodeDetailModal({
  node,
  onClose,
  showGraphLink = false,
  onViewInGraph,
}: NodeDetailModalProps) {
  // Close on Escape key
  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", handleKey);
    return () => document.removeEventListener("keydown", handleKey);
  }, [onClose]);

  return (
    <AnimatePresence>
      {node && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm"
            onClick={onClose}
          />

          {/* Modal */}
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 pointer-events-none">
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              transition={{ duration: 0.15 }}
              className="relative w-full max-w-lg pointer-events-auto glass-strong border border-white/10 rounded-2xl p-5 shadow-xl"
              onClick={(e) => e.stopPropagation()}
            >
              {/* Close button */}
              <button
                onClick={onClose}
                className="absolute top-4 right-4 p-1.5 rounded-lg text-white/40 hover:text-white hover:bg-white/10 transition-colors"
              >
                <X className="w-4 h-4" />
              </button>

              {/* Type badge */}
              <div className="flex items-center gap-2 mb-3">
                <span
                  className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold border ${NODE_COLORS[node.type]}`}
                >
                  {NODE_TYPE_LABELS[node.type]}
                </span>
                <span className="text-xs text-white/30 bg-white/5 px-2.5 py-1 rounded-full border border-white/10">
                  {node.status}
                </span>
              </div>

              {/* Title */}
              <h2 className="text-xl font-semibold text-white mb-1 pr-8">{node.title}</h2>

              {/* Date */}
              <p className="text-xs text-white/40 mb-4">{formatDate(node.created_at)}</p>

              {/* Why */}
              {node.why && (
                <div className="mb-3">
                  <p className="text-xs font-medium text-white/40 uppercase tracking-wide mb-1">
                    Why
                  </p>
                  <p className="text-sm text-white/80">{node.why}</p>
                </div>
              )}

              {/* Impact summary */}
              {node.impact_summary && (
                <div className="mb-4">
                  <p className="text-xs font-medium text-white/40 uppercase tracking-wide mb-1">
                    Impact
                  </p>
                  <p className="text-sm text-white/60">{node.impact_summary}</p>
                </div>
              )}

              {/* Expandable sections */}
              <div className="space-y-0">
                <ExpandableSection title="Tradeoffs" items={node.tradeoffs} />
                <ExpandableSection title="Alternatives" items={node.alternatives} />
              </div>

              {/* View in graph link */}
              {showGraphLink && onViewInGraph && (
                <div className="mt-4 pt-4 border-t border-white/5">
                  <button
                    onClick={() => onViewInGraph(node.id)}
                    className="text-sm text-brand hover:text-brand/80 transition-colors font-medium"
                  >
                    View in Strategy Graph &rarr;
                  </button>
                </div>
              )}
            </motion.div>
          </div>
        </>
      )}
    </AnimatePresence>
  );
}
