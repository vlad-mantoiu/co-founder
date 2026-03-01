"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import confetti from "canvas-confetti";
import { Eye, EyeOff, Rocket, X } from "lucide-react";
import Link from "next/link";

import { useAgentPhases } from "@/hooks/useAgentPhases";
import { useAgentState } from "@/hooks/useAgentState";
import { useAgentActivityFeed } from "@/hooks/useAgentActivityFeed";
import { useAgentEscalations } from "@/hooks/useAgentEscalations";
import { useAgentEvents } from "@/hooks/useAgentEvents";

import { GsdPhaseSidebar } from "./GsdPhaseSidebar";
import { AgentActivityFeed } from "./AgentActivityFeed";
import { AgentStateBadge } from "./AgentStateBadge";
import { PreviewPane } from "./PreviewPane";
import { apiFetch } from "@/lib/api";

// ──────────────────────────────────────────────────────────────────────────────
// Props
// ──────────────────────────────────────────────────────────────────────────────

export interface AutonomousBuildViewProps {
  jobId: string;
  projectId: string;
  projectName: string;
  getToken: () => Promise<string | null>;
}

// ──────────────────────────────────────────────────────────────────────────────
// Empty state — shown before any build is active
// ──────────────────────────────────────────────────────────────────────────────

function EmptyState({ projectId }: { projectId: string }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="flex flex-col items-center justify-center h-full gap-6 px-4 text-center"
    >
      <motion.div
        initial={{ scale: 0.8, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        transition={{ duration: 0.5, delay: 0.1 }}
        className="flex items-center justify-center w-20 h-20 rounded-3xl bg-brand/10 border border-brand/20"
      >
        <Rocket className="w-10 h-10 text-brand" />
      </motion.div>
      <div className="space-y-2 max-w-sm">
        <h2 className="text-xl font-display font-semibold text-white">
          Your co-founder is ready to build
        </h2>
        <p className="text-sm text-white/50 leading-relaxed">
          Start the build to watch your AI co-founder work through each phase in
          real time.
        </p>
      </div>
      <Link
        href={`/projects/${projectId}/build`}
        className="inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-brand hover:bg-brand/90 text-white font-semibold shadow-glow transition-all duration-200 hover:scale-105 active:scale-95"
      >
        <Rocket className="w-5 h-5" />
        Start Build
      </Link>
    </motion.div>
  );
}

// ──────────────────────────────────────────────────────────────────────────────
// Build complete CTAs
// ──────────────────────────────────────────────────────────────────────────────

function BuildCompleteCtas({
  previewUrl,
  projectId,
}: {
  previewUrl: string | null;
  projectId: string;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: 0.2 }}
      className="flex flex-wrap items-center gap-3 px-4 py-3 border-t border-white/5"
    >
      {previewUrl && (
        <a
          href={previewUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-brand hover:bg-brand/90 text-white text-sm font-medium transition-colors shadow-glow"
        >
          View your app
        </a>
      )}
      <Link
        href={`/projects/${projectId}/deploy?iterate=true`}
        className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg border border-white/20 text-white/70 text-sm font-medium hover:bg-white/5 hover:text-white transition-colors"
      >
        Start new milestone
      </Link>
    </motion.div>
  );
}

// ──────────────────────────────────────────────────────────────────────────────
// Escalation attention banner
// ──────────────────────────────────────────────────────────────────────────────

function EscalationAttentionBanner({
  pendingCount,
  onDismiss,
}: {
  pendingCount: number;
  onDismiss: () => void;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, height: 0 }}
      animate={{ opacity: 1, height: "auto" }}
      exit={{ opacity: 0, height: 0 }}
      transition={{ duration: 0.25 }}
      className="overflow-hidden shrink-0"
    >
      <div className="flex items-center justify-between gap-2 px-4 py-2.5 bg-amber-500/10 border-b border-amber-500/20">
        <p className="text-sm text-amber-300 font-medium">
          Your co-founder needs your input on{" "}
          <span className="font-bold">{pendingCount}</span>{" "}
          {pendingCount === 1 ? "item" : "items"}
        </p>
        <button
          type="button"
          onClick={onDismiss}
          className="p-1 rounded text-amber-400/60 hover:text-amber-300 transition-colors"
          aria-label="Dismiss attention banner"
        >
          <X className="w-4 h-4" />
        </button>
      </div>
    </motion.div>
  );
}

// ──────────────────────────────────────────────────────────────────────────────
// AutonomousBuildView — top-level composition
// ──────────────────────────────────────────────────────────────────────────────

/**
 * AutonomousBuildView — the single source of truth for all autonomous build state.
 *
 * This is the ONLY component that calls the domain hooks directly. All child
 * components receive data via props. A single SSE connection is established
 * here by merging all handler sets from each domain hook.
 *
 * Layout (desktop):
 *   [Sidebar 280px] | [Feed flex-1] | [Preview 50% — optional]
 *
 * Mobile (< md):
 *   Sidebar renders as compact strip at top (handled by GsdPhaseSidebar).
 *   Feed takes full width. Preview hidden.
 */
export function AutonomousBuildView({
  jobId,
  projectId,
  projectName,
  getToken,
}: AutonomousBuildViewProps) {
  // ── Domain hooks ─────────────────────────────────────────────────────────────

  const {
    phases,
    activePhaseId,
    filterPhaseId: phaseFilterId,
    setFilterPhaseId: setPhaseFilterId,
    eventHandlers: phaseEventHandlers,
  } = useAgentPhases(jobId, getToken);

  const {
    state,
    elapsedMs,
    wakeAt,
    budgetPct,
    pendingEscalationCount,
    currentPhaseName,
    eventHandlers: stateEventHandlers,
  } = useAgentState(jobId, getToken);

  const {
    entries,
    isTyping,
    shouldAutoScroll,
    onUserScroll,
    jumpToLatest,
    setFilterPhaseId: setFeedFilterPhaseId,
    eventHandlers: feedEventHandlers,
  } = useAgentActivityFeed(jobId, getToken);

  const {
    escalations,
    pendingCount,
    resolve,
    eventHandlers: escalationEventHandlers,
  } = useAgentEscalations(jobId, getToken);

  // ── Single SSE connection — merged handlers ───────────────────────────────

  const { isConnected } = useAgentEvents(jobId, getToken, {
    ...phaseEventHandlers,
    ...stateEventHandlers,
    ...feedEventHandlers,
    ...escalationEventHandlers,
  });

  // ── Preview toggle ─────────────────────────────────────────────────────────

  const [showPreview, setShowPreview] = useState(false);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [previewRefreshKey, setPreviewRefreshKey] = useState(0);

  // Auto-refresh preview when agent deploys or updates sandbox
  const incrementPreviewRefresh = useCallback(() => {
    setPreviewRefreshKey((k) => k + 1);
  }, []);

  // Fetch preview URL from job status when preview is toggled on or build completes
  useEffect(() => {
    if (!showPreview && state !== "completed") return;
    if (!jobId) return;

    let cancelled = false;
    async function fetchPreviewUrl() {
      try {
        const res = await apiFetch(`/api/jobs/${jobId}/status`, getToken);
        if (!res.ok || cancelled) return;
        const data = (await res.json()) as { preview_url?: string | null };
        if (!cancelled && data.preview_url) {
          setPreviewUrl(data.preview_url);
        }
      } catch {
        // Silently fail — preview URL will remain null
      }
    }
    fetchPreviewUrl();
    return () => {
      cancelled = true;
    };
  }, [showPreview, state, jobId, getToken]);

  // ── Phase-to-feed wiring ──────────────────────────────────────────────────

  // Sync filter between sidebar selection and feed filtering (shared state)
  const handlePhaseClick = useCallback(
    (phaseId: string | null) => {
      setPhaseFilterId(phaseId);
      setFeedFilterPhaseId(phaseId);
    },
    [setPhaseFilterId, setFeedFilterPhaseId],
  );

  // ── Overall progress ──────────────────────────────────────────────────────

  const phasesTotal = phases.length;
  const phasesCompleted = phases.filter((p) => p.status === "completed").length;
  const overallProgress =
    phasesTotal > 0 ? Math.round((phasesCompleted / phasesTotal) * 100) : 0;

  // ── Confetti on build complete ─────────────────────────────────────────────

  const confettiFiredRef = useRef(false);
  const prevStateRef = useRef(state);

  useEffect(() => {
    if (
      state === "completed" &&
      prevStateRef.current !== "completed" &&
      !confettiFiredRef.current
    ) {
      confettiFiredRef.current = true;
      confetti({
        particleCount: 120,
        spread: 80,
        origin: { y: 0.6 },
        colors: ["#7c3aed", "#2563eb", "#10b981", "#f59e0b", "#ef4444"],
      });
    }
    prevStateRef.current = state;
  }, [state]);

  // ── Escalation attention banner ───────────────────────────────────────────

  // Show banner on page load if there are pending escalations
  const initialPendingLoadedRef = useRef(false);
  const [showAttentionBanner, setShowAttentionBanner] = useState(false);

  useEffect(() => {
    if (!initialPendingLoadedRef.current && pendingCount > 0) {
      initialPendingLoadedRef.current = true;
      setShowAttentionBanner(true);
    }
  }, [pendingCount]);

  // ── Browser push notifications on first escalation ───────────────────────

  const notificationFiredRef = useRef(false);

  // Listen for waiting_for_input events via state change
  useEffect(() => {
    if (
      state === "waiting_for_input" &&
      !notificationFiredRef.current &&
      pendingEscalationCount > 0
    ) {
      notificationFiredRef.current = true;

      if (!("Notification" in window)) return;

      const firstEscalation = escalations.find((e) => e.status === "pending");
      const body = firstEscalation?.plain_english_problem ?? undefined;

      if (Notification.permission === "granted") {
        new Notification("Your co-founder needs your help", { body });
      } else if (Notification.permission === "default") {
        Notification.requestPermission().then((permission) => {
          if (permission === "granted") {
            new Notification("Your co-founder needs your help", { body });
          }
        });
      }
    }
  }, [state, pendingEscalationCount, escalations]);

  // ── Wake now / Pause after phase handlers ─────────────────────────────────

  const handleWakeNow = useCallback(async () => {
    if (!jobId) return;
    try {
      await apiFetch(`/api/jobs/${jobId}/wake`, getToken, { method: "POST" });
    } catch {
      // Non-fatal — wake_event.set() via Redis may handle it
    }
  }, [jobId, getToken]);

  const handlePauseAfterPhase = useCallback(async () => {
    if (!jobId) return;
    try {
      await apiFetch(`/api/jobs/${jobId}/pause`, getToken, { method: "POST" });
    } catch {
      // Non-fatal — backend will check pause flag before next phase
    }
  }, [jobId, getToken]);

  // ── Resolved escalation → refresh preview (if sandbox was updated) ────────

  const handleResolveEscalation = useCallback(
    async (escalationId: string, decision: string, guidance?: string) => {
      await resolve(escalationId, decision, guidance);
      // Increment preview refresh key in case the resolution triggers a deploy
      incrementPreviewRefresh();
    },
    [resolve, incrementPreviewRefresh],
  );

  // ── Preview rebuild/iterate callbacks ─────────────────────────────────────

  function handlePreviewRebuild() {
    window.location.href = `/projects/${projectId}/deploy`;
  }

  function handlePreviewIterate() {
    window.location.href = `/projects/${projectId}/deploy?iterate=true`;
  }

  // ── Filter phase name (for feed filter bar) ───────────────────────────────

  const filterPhaseName =
    phaseFilterId != null
      ? (phases.find((p) => p.phase_id === phaseFilterId)?.phase_name ?? phaseFilterId)
      : undefined;

  // ── Has any activity ──────────────────────────────────────────────────────

  const hasActivity = entries.length > 0 || phases.length > 0 || isTyping;

  // ── Connection indicator (subtle top border) ──────────────────────────────

  void isConnected; // used implicitly via border class below

  // ─────────────────────────────────────────────────────────────────────────────
  // Render
  // ─────────────────────────────────────────────────────────────────────────────

  if (!hasActivity && state === "idle") {
    return (
      <div className="flex h-full items-center justify-center">
        <EmptyState projectId={projectId} />
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* Mobile sidebar strip + feed column */}
      <div className="flex flex-col flex-1 md:flex-row overflow-hidden">

        {/* Sidebar (desktop: fixed-width; mobile: handled by GsdPhaseSidebar) */}
        <GsdPhaseSidebar
          phases={phases}
          activePhaseId={activePhaseId}
          selectedPhaseId={phaseFilterId}
          onPhaseClick={handlePhaseClick}
          overallProgress={overallProgress}
        />

        {/* Main content area */}
        <div className="flex-1 flex flex-col overflow-hidden min-w-0">

          {/* Header bar */}
          <div className="flex items-center justify-between gap-3 px-4 py-2.5 border-b border-white/10 bg-black/30 shrink-0">
            {/* Breadcrumb */}
            <nav className="flex items-center gap-1.5 text-xs text-white/40 min-w-0">
              <Link
                href="/projects"
                className="hover:text-white/70 transition-colors shrink-0"
              >
                Projects
              </Link>
              <span className="text-white/20">/</span>
              <Link
                href={`/projects/${projectId}`}
                className="hover:text-white/70 transition-colors truncate max-w-[120px]"
              >
                {projectName}
              </Link>
              <span className="text-white/20">/</span>
              <span className="text-white/60 shrink-0">Build</span>
            </nav>

            {/* Preview toggle */}
            <button
              type="button"
              onClick={() => setShowPreview((v) => !v)}
              className="hidden md:inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-white/10 text-xs text-white/50 hover:text-white/80 hover:bg-white/5 transition-colors shrink-0"
              title={showPreview ? "Hide preview" : "Show preview"}
            >
              {showPreview ? (
                <>
                  <EyeOff className="w-3.5 h-3.5" />
                  Hide preview
                </>
              ) : (
                <>
                  <Eye className="w-3.5 h-3.5" />
                  Preview
                </>
              )}
            </button>
          </div>

          {/* Escalation attention banner */}
          <AnimatePresence>
            {showAttentionBanner && pendingCount > 0 && (
              <EscalationAttentionBanner
                key="attention-banner"
                pendingCount={pendingCount}
                onDismiss={() => setShowAttentionBanner(false)}
              />
            )}
          </AnimatePresence>

          {/* Activity feed */}
          <div className="flex-1 overflow-hidden">
            <AgentActivityFeed
              entries={entries}
              escalations={escalations}
              isTyping={isTyping}
              shouldAutoScroll={shouldAutoScroll}
              onUserScroll={onUserScroll}
              onJumpToLatest={jumpToLatest}
              onResolveEscalation={handleResolveEscalation}
              filterPhaseId={phaseFilterId}
              filterPhaseName={filterPhaseName}
              onClearFilter={() => handlePhaseClick(null)}
            />
          </div>

          {/* Build complete CTAs */}
          <AnimatePresence>
            {state === "completed" && (
              <BuildCompleteCtas
                key="complete-ctas"
                previewUrl={previewUrl}
                projectId={projectId}
              />
            )}
          </AnimatePresence>
        </div>

        {/* Preview pane — desktop only, third column */}
        <AnimatePresence>
          {showPreview && previewUrl && (
            <motion.div
              key="preview-pane"
              initial={{ opacity: 0, width: 0 }}
              animate={{ opacity: 1, width: "50%" }}
              exit={{ opacity: 0, width: 0 }}
              transition={{ duration: 0.3, ease: "easeInOut" }}
              className="hidden md:flex flex-col border-l border-white/10 overflow-hidden"
              style={{ minWidth: 0 }}
            >
              <PreviewPane
                key={previewRefreshKey}
                previewUrl={previewUrl}
                sandboxExpiresAt={null}
                sandboxPaused={false}
                jobId={jobId}
                projectId={projectId}
                getToken={getToken}
                onRebuild={handlePreviewRebuild}
                onIterate={handlePreviewIterate}
                className="h-full"
              />
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Agent state badge — floating, fixed bottom-right */}
      <AgentStateBadge
        state={state}
        elapsedMs={elapsedMs}
        wakeAt={wakeAt}
        budgetPct={budgetPct}
        pendingEscalationCount={pendingEscalationCount}
        currentPhaseName={currentPhaseName}
        phasesCompleted={phasesCompleted}
        phasesTotal={phasesTotal}
        onWakeNow={handleWakeNow}
        onPauseAfterPhase={handlePauseAfterPhase}
      />
    </div>
  );
}
