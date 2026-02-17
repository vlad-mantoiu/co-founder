"use client";

import { ArrowRight, AlertTriangle } from "lucide-react";
import { PendingDecision } from "@/hooks/useDashboard";

interface ActionHeroProps {
  suggestedFocus: string;
  pendingDecisions: PendingDecision[];
  nextMilestone: string | null;
}

export function ActionHero({
  suggestedFocus,
  pendingDecisions,
  nextMilestone,
}: ActionHeroProps) {
  const hasPendingDecisions = pendingDecisions.length > 0;

  return (
    <div className="flex-1 bg-white/5 border border-white/10 rounded-xl p-6">
      <h2 className="text-sm font-medium text-white/60 mb-3">What&apos;s Next</h2>

      {/* Primary suggested focus */}
      <div className="flex items-start gap-3 mb-4">
        <ArrowRight className="w-5 h-5 text-blue-500 mt-1 flex-shrink-0" />
        <p className="text-lg font-medium text-white leading-relaxed">
          {suggestedFocus}
        </p>
      </div>

      {/* Pending decisions badge */}
      {hasPendingDecisions && (
        <div className="flex items-center gap-2 mb-3">
          <AlertTriangle className="w-4 h-4 text-amber-500" />
          <span className="text-sm text-amber-500/90">
            {pendingDecisions.length} decision
            {pendingDecisions.length !== 1 ? "s" : ""} pending
          </span>
        </div>
      )}

      {/* Next milestone (secondary info) */}
      {nextMilestone && (
        <div className="text-sm text-white/50 mt-4 pt-4 border-t border-white/5">
          Next milestone: <span className="text-white/70">{nextMilestone}</span>
        </div>
      )}
    </div>
  );
}
