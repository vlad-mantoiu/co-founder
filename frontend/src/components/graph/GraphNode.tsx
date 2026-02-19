"use client";

import { motion } from "framer-motion";
import { Check, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

export type GraphNodeStatus = "completed" | "active" | "queued" | "inactive";

export interface GraphNodeData {
  id: string;
  label: string;
  description?: string;
  status: GraphNodeStatus;
  agent?: string;
  x: number;
  y: number;
  connections: string[];
}

interface GraphNodeProps {
  node: GraphNodeData;
  selected: boolean;
  onClick: (id: string) => void;
}

export function GraphNode({ node, selected, onClick }: GraphNodeProps) {
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      className={cn(
        "absolute w-56 cursor-pointer select-none rounded-xl border p-4 transition-all",
        node.status === "completed" &&
          "border-neon-green/30 bg-neon-green/5",
        node.status === "active" &&
          "border-brand/50 bg-brand/10 animate-pulse-border",
        node.status === "queued" &&
          "border-dashed border-white/15 bg-white/[0.02]",
        node.status === "inactive" &&
          "border-white/5 bg-white/[0.01] opacity-40",
        selected && "ring-2 ring-brand/60",
      )}
      style={{ left: node.x, top: node.y }}
      onClick={() => onClick(node.id)}
    >
      {/* Header */}
      <div className="flex items-center gap-2">
        <StatusIcon status={node.status} />
        <span
          className={cn(
            "text-sm font-medium truncate",
            node.status === "inactive" ? "text-white/30" : "text-white",
          )}
        >
          {node.label}
        </span>
      </div>

      {/* Description */}
      {node.description && (
        <p className="mt-1.5 text-xs text-white/40 line-clamp-2">
          {node.description}
        </p>
      )}

      {/* Agent badge */}
      {node.agent && node.status === "active" && (
        <div className="mt-2 flex items-center gap-1.5">
          <Loader2 className="h-3 w-3 animate-spin text-brand" />
          <span className="text-[10px] font-bold uppercase tracking-wider text-brand">
            Building
          </span>
        </div>
      )}
    </motion.div>
  );
}

function StatusIcon({ status }: { status: GraphNodeStatus }) {
  if (status === "completed") {
    return (
      <div className="flex h-5 w-5 items-center justify-center rounded-full bg-neon-green/20">
        <Check className="h-3 w-3 text-neon-green" />
      </div>
    );
  }
  if (status === "active") {
    return (
      <div className="flex h-5 w-5 items-center justify-center rounded-full bg-brand/20">
        <Loader2 className="h-3 w-3 animate-spin text-brand" />
      </div>
    );
  }
  return (
    <div
      className={cn(
        "h-5 w-5 rounded-full border",
        status === "queued"
          ? "border-dashed border-white/20"
          : "border-white/10",
      )}
    />
  );
}
