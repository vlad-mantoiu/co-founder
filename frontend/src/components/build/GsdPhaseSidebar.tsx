"use client";

import { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { X } from "lucide-react";
import { cn } from "@/lib/utils";
import type { GsdPhase } from "@/hooks/useAgentPhases";
import { GsdPhaseCard } from "./GsdPhaseCard";

// ──────────────────────────────────────────────────────────────────────────────
// Dot node — colored circle on the timeline line
// ──────────────────────────────────────────────────────────────────────────────

function TimelineDot({
  status,
}: {
  status: GsdPhase["status"];
}) {
  if (status === "completed") {
    return (
      <div className="w-3 h-3 rounded-full bg-green-500 border-2 border-green-400 shrink-0" />
    );
  }
  if (status === "in_progress") {
    return (
      <div className="relative shrink-0 w-3 h-3">
        {/* Outer ring pulse */}
        <motion.div
          className="absolute inset-0 rounded-full bg-blue-500/30"
          animate={{ scale: [1, 1.8, 1], opacity: [0.6, 0, 0.6] }}
          transition={{ duration: 1.5, repeat: Infinity, ease: "easeInOut" }}
        />
        {/* Inner dot */}
        <div className="relative w-3 h-3 rounded-full bg-blue-500 border-2 border-blue-300" />
      </div>
    );
  }
  // Pending
  return (
    <div className="w-3 h-3 rounded-full border-2 border-white/20 shrink-0" />
  );
}

// ──────────────────────────────────────────────────────────────────────────────
// Props
// ──────────────────────────────────────────────────────────────────────────────

export interface GsdPhaseSidebarProps {
  phases: GsdPhase[];
  activePhaseId: string | null;
  selectedPhaseId: string | null;
  onPhaseClick: (phaseId: string | null) => void;
  overallProgress: number;
}

// ──────────────────────────────────────────────────────────────────────────────
// Mobile horizontal strip — compact dot row for small screens
// ──────────────────────────────────────────────────────────────────────────────

function MobilePhaseStrip({
  phases,
  activePhaseId,
  selectedPhaseId,
  onPhaseClick,
  overallProgress,
}: GsdPhaseSidebarProps) {
  const [overlayOpen, setOverlayOpen] = useState(false);

  const completedCount = phases.filter((p) => p.status === "completed").length;
  const inProgressPhase = phases.find((p) => p.status === "in_progress");

  return (
    <>
      {/* Horizontal strip */}
      <div className="md:hidden w-full bg-black/40 border-b border-white/10 px-4 py-2">
        <div className="flex items-center gap-2">
          {/* Progress summary */}
          <span className="text-xs text-white/40 shrink-0">
            {completedCount}/{phases.length}
          </span>

          {/* Dot row */}
          <div className="flex items-center gap-1 flex-1 overflow-x-auto scrollbar-thin py-1">
            {phases.map((phase) => (
              <button
                key={phase.phase_id}
                type="button"
                onClick={() => setOverlayOpen(true)}
                className="shrink-0 p-0.5"
                title={phase.phase_name}
              >
                <TimelineDot status={phase.status} />
              </button>
            ))}
          </div>

          {/* Active phase name */}
          {inProgressPhase && (
            <button
              type="button"
              onClick={() => setOverlayOpen(true)}
              className="text-xs text-blue-400 truncate max-w-[120px] shrink-0 hover:text-blue-300"
            >
              {inProgressPhase.phase_name}
            </button>
          )}

          {/* Expand button */}
          <button
            type="button"
            onClick={() => setOverlayOpen(true)}
            className="shrink-0 text-xs text-white/30 hover:text-white/60 ml-1 underline"
          >
            Show all
          </button>
        </div>
      </div>

      {/* Slide-in overlay (full vertical timeline) */}
      <AnimatePresence>
        {overlayOpen && (
          <>
            {/* Backdrop */}
            <motion.div
              key="overlay-backdrop"
              className="md:hidden fixed inset-0 z-40 bg-black/60"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setOverlayOpen(false)}
            />

            {/* Panel */}
            <motion.div
              key="overlay-panel"
              className="md:hidden fixed top-0 left-0 bottom-0 z-50 w-[280px] bg-obsidian-light border-r border-white/10 overflow-y-auto scrollbar-thin"
              initial={{ x: -280 }}
              animate={{ x: 0 }}
              exit={{ x: -280 }}
              transition={{ type: "spring", stiffness: 300, damping: 30 }}
            >
              {/* Close button */}
              <div className="flex justify-end p-3">
                <button
                  type="button"
                  onClick={() => setOverlayOpen(false)}
                  className="p-1 rounded-lg text-white/40 hover:text-white/70 hover:bg-white/5"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>

              {/* Full sidebar content */}
              <SidebarInner
                phases={phases}
                activePhaseId={activePhaseId}
                selectedPhaseId={selectedPhaseId}
                onPhaseClick={(id) => {
                  onPhaseClick(id);
                  setOverlayOpen(false);
                }}
                overallProgress={overallProgress}
              />
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </>
  );
}

// ──────────────────────────────────────────────────────────────────────────────
// Inner sidebar content — shared between desktop and mobile overlay
// ──────────────────────────────────────────────────────────────────────────────

function SidebarInner({
  phases,
  activePhaseId,
  selectedPhaseId,
  onPhaseClick,
  overallProgress,
}: GsdPhaseSidebarProps) {
  // Refs for each phase card — used for auto-scroll
  const phaseRefs = useRef<Map<string, HTMLDivElement>>(new Map());
  const prevActivePhaseIdRef = useRef<string | null>(null);

  // Auto-scroll to active phase when it changes
  useEffect(() => {
    if (
      activePhaseId &&
      activePhaseId !== prevActivePhaseIdRef.current
    ) {
      prevActivePhaseIdRef.current = activePhaseId;
      const el = phaseRefs.current.get(activePhaseId);
      if (el) {
        el.scrollIntoView({ behavior: "smooth", block: "nearest" });
      }
    }
  }, [activePhaseId]);

  const completedCount = phases.filter(
    (p) => p.status === "completed",
  ).length;

  return (
    <div className="flex flex-col h-full">
      {/* ── Progress bar ──────────────────────────────────────────────────────── */}
      <div className="px-4 pt-4 pb-3 border-b border-white/5">
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs font-medium text-white/60">
            Build Progress
          </span>
          <span className="text-xs font-mono text-white/40">
            v0.7 — {overallProgress}%
          </span>
        </div>

        {/* Progress bar */}
        <div className="h-1.5 rounded-full bg-white/10 overflow-hidden">
          <motion.div
            className="h-full rounded-full bg-gradient-to-r from-brand to-brand-light"
            initial={{ width: 0 }}
            animate={{ width: `${Math.min(100, Math.max(0, overallProgress))}%` }}
            transition={{ duration: 0.4, ease: "easeOut" }}
          />
        </div>

        {/* Phase count */}
        {phases.length > 0 && (
          <p className="text-xs text-white/30 mt-1.5">
            {completedCount} of {phases.length} phases complete
          </p>
        )}

        {/* Filter indicator */}
        {selectedPhaseId && (
          <button
            type="button"
            onClick={() => onPhaseClick(null)}
            className="mt-2 flex items-center gap-1.5 text-xs text-brand hover:text-brand-light transition-colors"
          >
            <X className="w-3 h-3" />
            Clear filter
          </button>
        )}
      </div>

      {/* ── Timeline list ──────────────────────────────────────────────────────── */}
      <div className="flex-1 overflow-y-auto scrollbar-thin py-3 px-3">
        {phases.length === 0 ? (
          <div className="px-1 py-6 text-center">
            <p className="text-xs text-white/20">No phases started yet</p>
          </div>
        ) : (
          <div className="relative">
            {/* Vertical connecting line */}
            <div className="absolute left-[22px] top-4 bottom-4 w-0.5 flex flex-col">
              {phases.map((phase, index) => {
                const isLast = index === phases.length - 1;
                const segmentColor =
                  phase.status === "completed"
                    ? "bg-green-500/50"
                    : phase.status === "in_progress"
                      ? "bg-blue-500/50"
                      : "bg-white/10";

                return (
                  <div
                    key={phase.phase_id}
                    className={cn(
                      "flex-1 w-full",
                      segmentColor,
                      isLast && "opacity-0",
                    )}
                  />
                );
              })}
            </div>

            {/* Phase rows */}
            <div className="space-y-1">
              {phases.map((phase) => {
                const isActive = phase.phase_id === activePhaseId;
                const isSelected = phase.phase_id === selectedPhaseId;

                return (
                  <div
                    key={phase.phase_id}
                    ref={(el) => {
                      if (el) {
                        phaseRefs.current.set(phase.phase_id, el);
                      } else {
                        phaseRefs.current.delete(phase.phase_id);
                      }
                    }}
                    className="flex items-start gap-2"
                  >
                    {/* Dot node — left column */}
                    <div className="flex flex-col items-center mt-3 shrink-0 w-5">
                      <TimelineDot status={phase.status} />
                    </div>

                    {/* Phase card — right column */}
                    <div className="flex-1 min-w-0">
                      <GsdPhaseCard
                        phase={phase}
                        isActive={isActive}
                        isSelected={isSelected}
                        onClick={() =>
                          onPhaseClick(
                            isSelected ? null : phase.phase_id,
                          )
                        }
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// ──────────────────────────────────────────────────────────────────────────────
// Main export — desktop sidebar + mobile strip
// ──────────────────────────────────────────────────────────────────────────────

export function GsdPhaseSidebar(props: GsdPhaseSidebarProps) {
  return (
    <>
      {/* Desktop: fixed-width vertical sidebar */}
      <div className="hidden md:flex flex-col w-[280px] shrink-0 h-full border-r border-white/10 bg-black/20">
        <SidebarInner {...props} />
      </div>

      {/* Mobile: compact horizontal strip + slide-in overlay */}
      <MobilePhaseStrip {...props} />
    </>
  );
}
