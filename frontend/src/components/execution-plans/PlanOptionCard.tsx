"use client";

import { cn } from "@/lib/utils";
import type { ExecutionOption } from "@/hooks/useExecutionPlans";

interface PlanOptionCardProps {
  option: ExecutionOption;
  isRecommended: boolean;
  onSelect: () => void;
}

/**
 * Detailed breakdown card for one execution plan option.
 *
 * Shows:
 * - Technical approach (1-2 sentence summary)
 * - Pros/Cons in 2-column grid
 * - Tradeoffs list
 * - Engineering impact + cost note (DCSN-02 fields)
 * - Select button
 *
 * Recommended card has ring-2 ring-brand border treatment.
 */
export function PlanOptionCard({
  option,
  isRecommended,
  onSelect,
}: PlanOptionCardProps) {
  return (
    <div
      className={cn(
        "p-6 rounded-2xl glass-strong border transition-all",
        isRecommended
          ? "ring-2 ring-brand border-brand/50"
          : "border-white/5"
      )}
    >
      {/* Header */}
      <div className="flex items-start justify-between mb-4">
        <h3 className="font-display text-xl text-white">{option.name}</h3>
        {isRecommended && (
          <div className="px-2.5 py-1 rounded-full bg-brand/20 text-brand text-xs font-semibold">
            Recommended
          </div>
        )}
      </div>

      {/* Technical Approach */}
      <div className="mb-4 p-4 rounded-lg bg-white/5">
        <p className="text-xs font-semibold text-white mb-2">
          Technical Approach
        </p>
        <p className="text-sm text-muted-foreground">
          {option.technical_approach}
        </p>
      </div>

      {/* Pros/Cons Grid */}
      <div className="grid grid-cols-2 gap-4 mb-4">
        {/* Pros */}
        <div>
          <p className="text-xs font-semibold text-green-400 mb-2">Pros</p>
          <ul className="space-y-1.5">
            {option.pros.map((pro, i) => (
              <li
                key={i}
                className="flex items-start gap-1.5 text-xs text-muted-foreground"
              >
                <span className="text-green-400 mt-0.5">•</span>
                <span>{pro}</span>
              </li>
            ))}
          </ul>
        </div>

        {/* Cons */}
        <div>
          <p className="text-xs font-semibold text-red-400 mb-2">Cons</p>
          <ul className="space-y-1.5">
            {option.cons.map((con, i) => (
              <li
                key={i}
                className="flex items-start gap-1.5 text-xs text-muted-foreground"
              >
                <span className="text-red-400 mt-0.5">•</span>
                <span>{con}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>

      {/* Tradeoffs (if present) */}
      {option.tradeoffs && option.tradeoffs.length > 0 && (
        <div className="mb-4">
          <p className="text-xs font-semibold text-white mb-2">Tradeoffs</p>
          <ul className="space-y-1.5">
            {option.tradeoffs.map((tradeoff, i) => (
              <li
                key={i}
                className="flex items-start gap-1.5 text-xs text-muted-foreground"
              >
                <span className="text-brand mt-0.5">•</span>
                <span>{tradeoff}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Engineering Impact + Cost Note (DCSN-02 fields) */}
      {(option.engineering_impact || option.cost_note) && (
        <div className="mb-4 p-4 rounded-lg bg-white/5 border border-white/5 space-y-2">
          {option.engineering_impact && (
            <div>
              <p className="text-xs font-semibold text-white mb-1">
                Engineering Impact
              </p>
              <p className="text-xs text-muted-foreground">
                {option.engineering_impact}
              </p>
            </div>
          )}
          {option.cost_note && (
            <div>
              <p className="text-xs font-semibold text-white mb-1">
                Cost Note
              </p>
              <p className="text-xs text-muted-foreground">
                {option.cost_note}
              </p>
            </div>
          )}
        </div>
      )}

      {/* Select Button */}
      <button
        onClick={onSelect}
        className={cn(
          "w-full px-6 py-2.5 rounded-xl text-sm font-semibold transition-all",
          isRecommended
            ? "bg-brand text-white shadow-glow hover:bg-brand/90"
            : "bg-white/5 text-white border border-white/10 hover:bg-white/10"
        )}
      >
        Select This Plan
      </button>
    </div>
  );
}
