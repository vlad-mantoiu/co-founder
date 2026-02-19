"use client";

interface AnalysisDepthMeterProps {
  progress: number;
}

export function AnalysisDepthMeter({ progress }: AnalysisDepthMeterProps) {
  const pct = Math.min(100, Math.max(0, Math.round(progress)));

  return (
    <div className="flex items-center gap-3">
      <span className="shrink-0 text-[10px] font-bold uppercase tracking-widest text-white/40">
        Analysis Depth
      </span>
      <div className="relative h-1.5 flex-1 overflow-hidden rounded-full bg-white/5">
        <div
          className="h-full rounded-full bg-brand transition-all duration-500"
          style={{ width: `${pct}%` }}
        />
        <div className="absolute inset-0 animate-shimmer bg-gradient-to-r from-transparent via-white/10 to-transparent" />
      </div>
      <span className="shrink-0 text-[10px] font-bold uppercase tracking-widest text-white/40">
        {pct}% Complete
      </span>
    </div>
  );
}
