"use client";

import { StageCard } from "./StageCard";
import type { StageState } from "./types";

interface WorkStreamPanelProps {
  stages: StageState[];
}

export function WorkStreamPanel({ stages }: WorkStreamPanelProps) {
  return (
    <div className="relative space-y-3">
      {/* Connecting line */}
      <div className="absolute left-[1.85rem] top-4 bottom-4 w-px bg-gradient-to-b from-brand/30 via-white/10 to-transparent" />

      {stages.map((stage, i) => (
        <StageCard key={stage.id} stage={stage} index={i} />
      ))}
    </div>
  );
}
