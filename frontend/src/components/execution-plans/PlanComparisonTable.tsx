"use client";

import { cn } from "@/lib/utils";
import type { ExecutionOption } from "@/hooks/useExecutionPlans";

interface PlanComparisonTableProps {
  options: ExecutionOption[];
  onSelect: (optionId: string) => void;
  onRegenerate: () => void;
  isGenerating: boolean;
}

/**
 * Feature-by-feature comparison grid for execution plan options.
 *
 * Shows 4 critical comparison rows:
 * - Time to Ship
 * - Engineering Cost
 * - Risk Level (colored badge)
 * - Scope Coverage (% with progress bar)
 *
 * Recommended option has badge + brand-colored border.
 */
export function PlanComparisonTable({
  options,
  onSelect,
  onRegenerate,
  isGenerating,
}: PlanComparisonTableProps) {
  const COMPARISON_ROWS = [
    { key: "time_to_ship" as const, label: "Time to Ship" },
    { key: "engineering_cost" as const, label: "Engineering Cost" },
    { key: "risk_level" as const, label: "Risk Level" },
    { key: "scope_coverage" as const, label: "Scope Coverage" },
  ];

  const getRiskBadgeColor = (level: string) => {
    switch (level) {
      case "low":
        return "bg-green-500/20 text-green-400";
      case "medium":
        return "bg-yellow-500/20 text-yellow-400";
      case "high":
        return "bg-red-500/20 text-red-400";
      default:
        return "bg-white/10 text-white";
    }
  };

  if (isGenerating) {
    return (
      <div className="space-y-4">
        {/* Skeleton shimmer */}
        <div className="space-y-3">
          {[1, 2, 3, 4].map((i) => (
            <div
              key={i}
              className="h-16 rounded-lg bg-white/5 animate-pulse"
              style={{ width: `${90 + i * 2}%` }}
            />
          ))}
        </div>
      </div>
    );
  }

  if (options.length === 0) {
    return null;
  }

  return (
    <div className="space-y-6">
      {/* Comparison Grid */}
      <div className="overflow-x-auto">
        <table className="w-full border-collapse">
          <thead>
            <tr className="border-b border-white/10">
              <th className="text-left p-4 font-semibold text-white text-sm">
                Feature
              </th>
              {options.map((option) => (
                <th
                  key={option.id}
                  className={cn(
                    "text-center p-4 border-l border-white/5",
                    option.is_recommended && "bg-brand/5"
                  )}
                >
                  <div className="space-y-2">
                    <div className="font-display text-lg text-white">
                      {option.name}
                    </div>
                    {option.is_recommended && (
                      <div className="inline-flex px-2.5 py-1 rounded-full bg-brand/20 text-brand text-xs font-semibold">
                        Recommended
                      </div>
                    )}
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {COMPARISON_ROWS.map((row) => (
              <tr key={row.key} className="border-b border-white/5">
                <td className="p-4 font-medium text-sm text-white">
                  {row.label}
                </td>
                {options.map((option) => (
                  <td
                    key={option.id}
                    className={cn(
                      "p-4 text-center border-l border-white/5",
                      option.is_recommended && "bg-brand/5"
                    )}
                  >
                    {row.key === "risk_level" ? (
                      <div className="inline-flex px-3 py-1.5 rounded-full text-xs font-semibold">
                        <span className={getRiskBadgeColor(option.risk_level)}>
                          {option.risk_level.toUpperCase()}
                        </span>
                      </div>
                    ) : row.key === "scope_coverage" ? (
                      <div className="flex flex-col items-center gap-2">
                        <span className="text-sm text-white">
                          {option.scope_coverage}%
                        </span>
                        <div className="w-full max-w-[120px] h-2 bg-white/10 rounded-full overflow-hidden">
                          <div
                            className="h-full bg-brand transition-all"
                            style={{ width: `${option.scope_coverage}%` }}
                          />
                        </div>
                      </div>
                    ) : (
                      <span className="text-sm text-muted-foreground">
                        {option[row.key]}
                      </span>
                    )}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Select buttons row */}
      <div className="flex items-center justify-center gap-4">
        {options.map((option) => (
          <button
            key={option.id}
            onClick={() => onSelect(option.id)}
            className={cn(
              "px-6 py-2.5 rounded-xl text-sm font-semibold transition-all",
              option.is_recommended
                ? "bg-brand text-white shadow-glow hover:bg-brand/90"
                : "bg-white/5 text-white border border-white/10 hover:bg-white/10"
            )}
          >
            Select {option.name}
          </button>
        ))}
      </div>

      {/* Regenerate button */}
      <div className="text-center pt-4 border-t border-white/5">
        <button
          onClick={onRegenerate}
          className="px-6 py-2.5 rounded-xl text-sm font-medium text-muted-foreground hover:text-white hover:bg-white/5 transition-colors"
        >
          Generate Different Options
        </button>
      </div>
    </div>
  );
}
