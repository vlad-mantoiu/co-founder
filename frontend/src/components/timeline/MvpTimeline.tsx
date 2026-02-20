"use client";

import { Clock, CheckCircle2, Package } from "lucide-react";

interface Milestone {
  week: number;
  title: string;
  deliverables: string[];
  duration_weeks: number;
  description: string;
}

interface RoadmapPhase {
  phase: string;
  title: string;
  description: string;
  estimated_weeks: number;
}

interface MvpTimelineProps {
  milestones: Milestone[];
  longTermRoadmap: RoadmapPhase[];
  totalMvpWeeks: number;
  adaptedFor: string;
}

export function MvpTimeline({
  milestones,
  longTermRoadmap,
  totalMvpWeeks,
  adaptedFor,
}: MvpTimelineProps) {
  return (
    <div className="space-y-8">
      {/* Info bar */}
      <div className="flex items-center gap-3 px-4 py-3 rounded-lg bg-emerald-500/5 border border-emerald-500/20">
        <Clock className="w-4 h-4 text-emerald-400 flex-shrink-0" />
        <div className="flex-1 min-w-0">
          <span className="text-sm font-medium text-emerald-400">
            {totalMvpWeeks} week MVP
          </span>
          {adaptedFor && (
            <span className="text-sm text-white/50 ml-2">— {adaptedFor}</span>
          )}
        </div>
      </div>

      {/* MVP milestones vertical timeline */}
      <div>
        <h2 className="text-base font-semibold text-white mb-6">MVP Milestones</h2>
        <div className="relative">
          {/* Vertical connector line */}
          <div className="absolute left-[18px] top-0 bottom-0 w-px bg-emerald-500/20" />

          <div className="space-y-6">
            {milestones.map((milestone, idx) => {
              const weekEnd = milestone.week + milestone.duration_weeks - 1;
              const weekLabel =
                milestone.duration_weeks === 1
                  ? `Week ${milestone.week}`
                  : `Week ${milestone.week}–${weekEnd}`;

              return (
                <div key={idx} className="relative flex gap-4">
                  {/* Timeline dot */}
                  <div className="flex-shrink-0 w-9 h-9 rounded-full bg-emerald-500/10 border border-emerald-500/40 flex items-center justify-center z-10">
                    <span className="text-xs font-bold text-emerald-400">{idx + 1}</span>
                  </div>

                  {/* Milestone card */}
                  <div className="flex-1 bg-white/[0.03] rounded-xl border border-white/8 p-4 mb-1">
                    {/* Week badge + duration */}
                    <div className="flex items-center gap-2 mb-2">
                      <span className="text-xs px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-medium">
                        {weekLabel}
                      </span>
                      <span className="text-xs text-white/30">
                        {milestone.duration_weeks} week{milestone.duration_weeks !== 1 ? "s" : ""}
                      </span>
                    </div>

                    {/* Title */}
                    <h3 className="text-sm font-semibold text-white mb-1">{milestone.title}</h3>

                    {/* Description */}
                    {milestone.description && (
                      <p className="text-xs text-white/50 mb-3">{milestone.description}</p>
                    )}

                    {/* Deliverables */}
                    {milestone.deliverables && milestone.deliverables.length > 0 && (
                      <div className="flex flex-wrap gap-1.5">
                        {milestone.deliverables.map((deliverable, dIdx) => (
                          <span
                            key={dIdx}
                            className="inline-flex items-center gap-1 text-xs px-2 py-1 rounded-md bg-white/5 border border-white/10 text-white/70"
                          >
                            <CheckCircle2 className="w-3 h-3 text-emerald-400 flex-shrink-0" />
                            {deliverable}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Long-term roadmap */}
      {longTermRoadmap && longTermRoadmap.length > 0 && (
        <div>
          <h2 className="text-base font-semibold text-white/60 mb-4">Long-term Roadmap</h2>
          <div className="space-y-3">
            {longTermRoadmap.map((phase, idx) => (
              <div
                key={idx}
                className="flex gap-4 p-4 rounded-xl border border-dashed border-white/10 opacity-60"
              >
                <div className="flex-shrink-0 w-8 h-8 rounded-lg bg-white/5 flex items-center justify-center">
                  <Package className="w-4 h-4 text-white/40" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-xs font-medium text-white/50 uppercase tracking-wide">
                      {phase.phase}
                    </span>
                    <span className="text-xs text-white/30">·</span>
                    <span className="text-xs text-white/30">
                      ~{phase.estimated_weeks} week{phase.estimated_weeks !== 1 ? "s" : ""}
                    </span>
                  </div>
                  <h3 className="text-sm font-medium text-white/70 mb-0.5">{phase.title}</h3>
                  {phase.description && (
                    <p className="text-xs text-white/40">{phase.description}</p>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
