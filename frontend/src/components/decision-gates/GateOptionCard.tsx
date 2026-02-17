"use client";

import { Check } from "lucide-react";
import { cn } from "@/lib/utils";
import type { GateOption } from "@/hooks/useDecisionGate";

interface GateOptionCardProps {
  option: GateOption;
  isSelected: boolean;
  onSelect: () => void;
}

/**
 * Rich card for one Decision Gate option.
 *
 * Layout:
 * - Header: title + Selected badge when active
 * - Description text
 * - "What happens next" section
 * - Pros/Cons in 2-column grid
 * - "Why you might choose this" blurb at bottom
 *
 * Selected state: ring-2 ring-brand shadow-glow border
 * Hover state: ring-1 ring-white/20
 */
export function GateOptionCard({
  option,
  isSelected,
  onSelect,
}: GateOptionCardProps) {
  return (
    <button
      onClick={onSelect}
      className={cn(
        "w-full p-6 rounded-2xl glass-strong border transition-all text-left",
        "hover:ring-1 hover:ring-white/20",
        isSelected
          ? "ring-2 ring-brand shadow-glow border-brand/50"
          : "border-white/5"
      )}
    >
      {/* Header */}
      <div className="flex items-start justify-between mb-3">
        <h3 className="font-display text-xl text-white">{option.title}</h3>
        {isSelected && (
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-brand/20 text-brand text-xs font-semibold">
            <Check className="w-3.5 h-3.5" />
            Selected
          </div>
        )}
      </div>

      {/* Description */}
      <p className="text-sm text-muted-foreground mb-4">{option.description}</p>

      {/* What happens next */}
      <div className="mb-4 p-3 rounded-lg bg-white/5">
        <p className="text-xs font-semibold text-white mb-1">
          What happens next:
        </p>
        <p className="text-xs text-muted-foreground">
          {option.what_happens_next}
        </p>
      </div>

      {/* Pros/Cons Grid */}
      <div className="grid grid-cols-2 gap-4 mb-4">
        {/* Pros */}
        <div>
          <p className="text-xs font-semibold text-green-400 mb-2">Pros</p>
          <ul className="space-y-1">
            {option.pros.map((pro, i) => (
              <li key={i} className="flex items-start gap-1.5 text-xs text-muted-foreground">
                <span className="text-green-400 mt-0.5">•</span>
                <span>{pro}</span>
              </li>
            ))}
          </ul>
        </div>

        {/* Cons */}
        <div>
          <p className="text-xs font-semibold text-red-400 mb-2">Cons</p>
          <ul className="space-y-1">
            {option.cons.map((con, i) => (
              <li key={i} className="flex items-start gap-1.5 text-xs text-muted-foreground">
                <span className="text-red-400 mt-0.5">•</span>
                <span>{con}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>

      {/* Why choose separator */}
      <div className="pt-4 border-t border-white/5">
        <p className="text-xs text-muted-foreground italic">{option.why_choose}</p>
      </div>
    </button>
  );
}
