"use client";

import { CheckCircle, AlertCircle } from "lucide-react";

interface ConfidenceIndicatorProps {
  confidence: "strong" | "moderate" | "needs_depth";
}

/**
 * ConfidenceIndicator: Badge showing section confidence level.
 *
 * Displays icon and label for strong/moderate/needs_depth confidence scores.
 */
export function ConfidenceIndicator({ confidence }: ConfidenceIndicatorProps) {
  const config = {
    strong: {
      icon: CheckCircle,
      label: "Strong",
      className: "bg-green-500/20 text-green-400 border-green-500/30",
    },
    moderate: {
      icon: AlertCircle,
      label: "Needs refinement",
      className: "bg-yellow-500/20 text-yellow-400 border-yellow-500/30",
    },
    needs_depth: {
      icon: AlertCircle,
      label: "Needs depth",
      className: "bg-red-500/20 text-red-400 border-red-500/30",
    },
  };

  const { icon: Icon, label, className } = config[confidence];

  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full border text-xs font-medium ${className}`}>
      <Icon className="h-3 w-3" />
      <span>{label}</span>
    </span>
  );
}
