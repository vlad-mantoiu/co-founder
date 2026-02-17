"use client";

import { CheckSquare, ChevronRight, Star } from "lucide-react";
import { cn } from "@/lib/utils";

export interface DeployPathOption {
  id: string;
  name: string;
  description: string;
  difficulty: string;
  cost: string;
  tradeoffs: string[];
  steps: string[];
}

interface DeployPathCardProps {
  path: DeployPathOption;
  recommended: boolean;
  onSelect: () => void;
  selected?: boolean;
}

const DIFFICULTY_STYLES: Record<string, string> = {
  Easy: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
  Medium: "bg-amber-500/10 text-amber-400 border-amber-500/20",
  Hard: "bg-red-500/10 text-red-400 border-red-500/20",
};

export function DeployPathCard({
  path,
  recommended,
  onSelect,
  selected = false,
}: DeployPathCardProps) {
  const difficultyStyle =
    DIFFICULTY_STYLES[path.difficulty] ??
    "bg-white/10 text-white/60 border-white/10";

  return (
    <div
      className={cn(
        "glass-strong rounded-2xl border transition-all duration-200 overflow-hidden",
        selected
          ? "border-brand/50 ring-1 ring-brand/20"
          : "border-white/10 hover:border-white/20",
        recommended && !selected && "border-brand/30",
      )}
    >
      {/* Card header */}
      <div className="p-5 space-y-3">
        {/* Top row: name + badges */}
        <div className="flex items-start justify-between gap-3">
          <h3 className="text-base font-semibold text-white">{path.name}</h3>
          <div className="flex items-center gap-2 flex-shrink-0">
            {recommended && (
              <span className="flex items-center gap-1 px-2 py-0.5 rounded-full bg-brand/15 border border-brand/30 text-xs text-brand font-medium">
                <Star className="w-3 h-3" />
                Recommended
              </span>
            )}
            <span
              className={cn(
                "px-2 py-0.5 rounded-full border text-xs font-medium",
                difficultyStyle,
              )}
            >
              {path.difficulty}
            </span>
          </div>
        </div>

        {/* Description */}
        <p className="text-sm text-white/60 leading-relaxed">
          {path.description}
        </p>

        {/* Cost */}
        <p className="text-xs text-white/40">
          <span className="text-white/60 font-medium">Cost:</span> {path.cost}
        </p>

        {/* Tradeoffs */}
        {path.tradeoffs.length > 0 && (
          <ul className="space-y-1.5">
            {path.tradeoffs.map((tradeoff, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-white/50">
                <ChevronRight className="w-3.5 h-3.5 mt-0.5 flex-shrink-0 text-white/30" />
                {tradeoff}
              </li>
            ))}
          </ul>
        )}
      </div>

      {/* Steps count + select button */}
      <div className="flex items-center justify-between px-5 py-3 border-t border-white/10 bg-white/3">
        <span className="text-xs text-white/40">
          {path.steps.length} step{path.steps.length !== 1 ? "s" : ""}
        </span>
        <button
          onClick={onSelect}
          className={cn(
            "flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium transition-all",
            selected
              ? "bg-brand/20 border border-brand/40 text-brand"
              : "bg-brand hover:bg-brand/80 text-white",
          )}
        >
          <CheckSquare className="w-3.5 h-3.5" />
          {selected ? "Selected" : "Select this path"}
        </button>
      </div>
    </div>
  );
}
