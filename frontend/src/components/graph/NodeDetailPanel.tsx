"use client";

import { motion, AnimatePresence } from "framer-motion";
import { X, Pause, Eye, FileCode } from "lucide-react";
import { TerminalOutput } from "@/components/chat/TerminalOutput";
import type { GraphNodeData } from "./GraphNode";
import type { LogLine } from "@/components/chat/types";

interface NodeDetailPanelProps {
  node: GraphNodeData | null;
  logs: LogLine[];
  files: string[];
  considerations: string[];
  onClose: () => void;
}

export function NodeDetailPanel({
  node,
  logs,
  files,
  considerations,
  onClose,
}: NodeDetailPanelProps) {
  return (
    <AnimatePresence>
      {node && (
        <motion.aside
          initial={{ x: 380, opacity: 0 }}
          animate={{ x: 0, opacity: 1 }}
          exit={{ x: 380, opacity: 0 }}
          transition={{ type: "spring", damping: 25, stiffness: 250 }}
          className="absolute right-0 top-0 z-20 h-full w-[380px] glass-strong border-l border-white/5 flex flex-col overflow-hidden"
        >
          {/* Header */}
          <div className="flex items-center justify-between border-b border-white/5 px-4 py-3">
            <div>
              <h3 className="text-sm font-semibold text-white">
                {node.label}
              </h3>
              {node.agent && (
                <p className="text-xs text-white/40">Agent: {node.agent}</p>
              )}
            </div>
            <button
              onClick={onClose}
              className="rounded-lg p-1.5 text-white/40 hover:bg-white/5 hover:text-white transition-colors"
            >
              <X className="h-4 w-4" />
            </button>
          </div>

          {/* Content */}
          <div className="flex-1 overflow-y-auto scrollbar-thin p-4 space-y-4">
            {/* Agent Thoughts */}
            <section>
              <SectionHeader label="Agent Thoughts" />
              <TerminalOutput lines={logs} maxHeight="240px" />
            </section>

            {/* Generated Files */}
            {files.length > 0 && (
              <section>
                <SectionHeader label="Generated Files" />
                <ul className="space-y-1">
                  {files.map((f) => (
                    <li
                      key={f}
                      className="flex items-center gap-2 rounded-lg bg-white/[0.03] px-3 py-2 text-xs text-white/60"
                    >
                      <FileCode className="h-3.5 w-3.5 text-brand" />
                      <span className="font-mono truncate">{f}</span>
                    </li>
                  ))}
                </ul>
              </section>
            )}

            {/* Considerations */}
            {considerations.length > 0 && (
              <section>
                <SectionHeader label="Considerations" />
                <ul className="space-y-1.5">
                  {considerations.map((c, i) => (
                    <li
                      key={i}
                      className="text-xs leading-relaxed text-white/50"
                    >
                      <span className="mr-1.5 text-brand">*</span>
                      {c}
                    </li>
                  ))}
                </ul>
              </section>
            )}
          </div>

          {/* Footer actions */}
          <div className="border-t border-white/5 px-4 py-3 flex items-center gap-2">
            <button className="flex items-center gap-1.5 rounded-lg border border-white/10 px-3 py-1.5 text-xs text-white/50 hover:text-white/80 transition-colors">
              <Pause className="h-3 w-3" />
              Pause
            </button>
            <button className="flex items-center gap-1.5 rounded-lg border border-white/10 px-3 py-1.5 text-xs text-white/50 hover:text-white/80 transition-colors">
              <Eye className="h-3 w-3" />
              Open Logic View
            </button>
          </div>
        </motion.aside>
      )}
    </AnimatePresence>
  );
}

function SectionHeader({ label }: { label: string }) {
  return (
    <h4 className="mb-2 text-[10px] font-bold uppercase tracking-widest text-white/30">
      {label}
    </h4>
  );
}
