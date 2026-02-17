"use client";

import { AlertTriangle } from "lucide-react";
import { RiskFlag } from "@/hooks/useDashboard";

interface RiskFlagsProps {
  risks: RiskFlag[];
}

export function RiskFlags({ risks }: RiskFlagsProps) {
  // Only render when risks are present
  if (risks.length === 0) {
    return null;
  }

  return (
    <div className="bg-amber-500/10 border border-amber-500/20 rounded-xl p-4">
      <div className="flex items-center gap-2 mb-3">
        <AlertTriangle className="w-5 h-5 text-amber-500" />
        <h3 className="font-medium text-amber-500">Risk Alerts</h3>
      </div>

      <div className="space-y-2">
        {risks.map((risk, idx) => (
          <div
            key={idx}
            className="flex items-start gap-3 text-sm text-amber-200/90"
          >
            <div className="w-1.5 h-1.5 rounded-full bg-amber-500 mt-1.5 flex-shrink-0" />
            <p>{risk.message}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
