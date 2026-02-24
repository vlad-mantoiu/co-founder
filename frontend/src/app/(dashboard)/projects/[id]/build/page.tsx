"use client";

import { useState, useEffect } from "react";
import { useParams, useSearchParams, useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import {
  Loader2,
  X,
  Rocket,
  Clock,
  Shield,
  Target,
  CheckCircle2,
  XCircle,
  ArrowRight,
  AlertCircle,
} from "lucide-react";
import Link from "next/link";
import { useAuth } from "@clerk/nextjs";
import { useBuildProgress } from "@/hooks/useBuildProgress";
import { useBuildLogs } from "@/hooks/useBuildLogs";
import { BuildProgressBar } from "@/components/build/BuildProgressBar";
import { BuildLogPanel } from "@/components/build/BuildLogPanel";
import { AutoFixBanner } from "@/components/build/AutoFixBanner";
import { BuildSummary } from "@/components/build/BuildSummary";
import { BuildFailureCard } from "@/components/build/BuildFailureCard";
import { PreviewPane } from "@/components/build/PreviewPane";
import { GlassCard } from "@/components/ui/glass-card";
import { apiFetch } from "@/lib/api";

// ──────────────────────────────────────────────────────────────────────────────
// Types for the selected execution plan
// ──────────────────────────────────────────────────────────────────────────────

interface ExecutionOption {
  id: string;
  name: string;
  is_recommended: boolean;
  time_to_ship: string;
  engineering_cost: string;
  risk_level: "low" | "medium" | "high";
  scope_coverage: number;
  pros: string[];
  cons: string[];
  technical_approach: string;
  tradeoffs: string[];
  engineering_impact: string;
  cost_note: string;
}

// ──────────────────────────────────────────────────────────────────────────────
// Pre-build view — shows selected plan details + "Start Build" CTA
// ──────────────────────────────────────────────────────────────────────────────

function PreBuildView({
  projectId,
  getToken,
}: {
  projectId: string;
  getToken: () => Promise<string | null>;
}) {
  const router = useRouter();
  const [plan, setPlan] = useState<ExecutionOption | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [starting, setStarting] = useState(false);
  const [comingSoon, setComingSoon] = useState(false);

  useEffect(() => {
    async function fetchSelectedPlan() {
      try {
        const res = await apiFetch(
          `/api/plans/${projectId}/selected`,
          getToken,
        );
        if (!res.ok) {
          setError("No execution plan selected yet.");
          return;
        }
        const data = await res.json();
        setPlan(data.selected_option);
      } catch {
        setError("Failed to load your selected plan.");
      } finally {
        setLoading(false);
      }
    }
    fetchSelectedPlan();
  }, [projectId, getToken]);

  async function handleStartBuild() {
    if (!plan) return;
    setStarting(true);
    try {
      const res = await apiFetch(`/api/generation/start`, getToken, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          project_id: projectId,
          goal: plan.technical_approach || plan.name,
        }),
      });
      if (res.status === 501) {
        // Autonomous agent not yet ready — show non-blocking "coming soon" banner
        setComingSoon(true);
        setStarting(false);
        return;
      }
      if (!res.ok) {
        const body = await res.json().catch(() => null);
        setError(body?.detail ?? "Failed to start build.");
        setStarting(false);
        return;
      }
      const data = await res.json();
      router.push(`/projects/${projectId}/build?job_id=${data.job_id}`);
    } catch {
      setError("Failed to start build. Please try again.");
      setStarting(false);
    }
  }

  const riskColor = {
    low: "text-emerald-400",
    medium: "text-amber-400",
    high: "text-red-400",
  };

  const riskBg = {
    low: "bg-emerald-400/10 border-emerald-400/20",
    medium: "bg-amber-400/10 border-amber-400/20",
    high: "bg-red-400/10 border-red-400/20",
  };

  if (loading) {
    return (
      <div className="min-h-[60vh] flex items-center justify-center">
        <Loader2 className="w-6 h-6 text-brand animate-spin" />
      </div>
    );
  }

  if (error && !plan) {
    return (
      <div className="min-h-[60vh] flex items-center justify-center">
        <div className="text-center space-y-3">
          <AlertCircle className="w-8 h-8 text-amber-400 mx-auto" />
          <p className="text-white/60 text-sm">{error}</p>
          <Link
            href={`/projects/${projectId}/understanding`}
            className="inline-flex items-center gap-1.5 text-brand hover:text-brand/80 text-sm"
          >
            Go to Decision Gate
            <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>
      </div>
    );
  }

  if (!plan) return null;

  return (
    <div className="min-h-[60vh] flex flex-col items-center justify-center py-12">
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.35 }}
        className="w-full max-w-2xl mx-auto px-4 space-y-6"
      >
        {/* Header */}
        <div className="text-center space-y-2">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-brand/10 border border-brand/20 mb-2">
            <Rocket className="w-7 h-7 text-brand" />
          </div>
          <h1 className="text-2xl font-display font-bold text-white">
            Ready to Build
          </h1>
          <p className="text-sm text-white/50 max-w-md mx-auto">
            Review your selected execution path below, then launch the build.
          </p>
        </div>

        {/* Selected plan card */}
        <GlassCard className="space-y-5">
          {/* Plan name + badge */}
          <div className="flex items-start justify-between gap-3">
            <div>
              <h2 className="text-lg font-semibold text-white">{plan.name}</h2>
              {plan.is_recommended && (
                <span className="inline-block mt-1 text-[10px] font-bold uppercase tracking-wider text-brand bg-brand/10 border border-brand/20 px-2 py-0.5 rounded-full">
                  Recommended
                </span>
              )}
            </div>
            <div
              className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg border text-xs font-medium ${riskBg[plan.risk_level]} ${riskColor[plan.risk_level]}`}
            >
              <Shield className="w-3.5 h-3.5" />
              {plan.risk_level.charAt(0).toUpperCase() +
                plan.risk_level.slice(1)}{" "}
              Risk
            </div>
          </div>

          {/* Key metrics row */}
          <div className="grid grid-cols-3 gap-3">
            <div className="bg-white/[0.03] border border-white/[0.06] rounded-xl p-3 text-center">
              <Clock className="w-4 h-4 text-white/40 mx-auto mb-1" />
              <p className="text-xs text-white/40">Timeline</p>
              <p className="text-sm font-medium text-white mt-0.5">
                {plan.time_to_ship}
              </p>
            </div>
            <div className="bg-white/[0.03] border border-white/[0.06] rounded-xl p-3 text-center">
              <Target className="w-4 h-4 text-white/40 mx-auto mb-1" />
              <p className="text-xs text-white/40">Scope</p>
              <p className="text-sm font-medium text-white mt-0.5">
                {plan.scope_coverage}%
              </p>
            </div>
            <div className="bg-white/[0.03] border border-white/[0.06] rounded-xl p-3 text-center">
              <Shield className="w-4 h-4 text-white/40 mx-auto mb-1" />
              <p className="text-xs text-white/40">Cost</p>
              <p className="text-sm font-medium text-white mt-0.5">
                {plan.engineering_cost}
              </p>
            </div>
          </div>

          {/* Technical approach */}
          {plan.technical_approach && (
            <div>
              <p className="text-xs font-medium text-white/40 uppercase tracking-wider mb-1.5">
                Technical Approach
              </p>
              <p className="text-sm text-white/70 leading-relaxed">
                {plan.technical_approach}
              </p>
            </div>
          )}

          {/* Pros & Cons */}
          {(plan.pros.length > 0 || plan.cons.length > 0) && (
            <div className="grid grid-cols-2 gap-4">
              {plan.pros.length > 0 && (
                <div>
                  <p className="text-xs font-medium text-emerald-400/70 uppercase tracking-wider mb-2">
                    Pros
                  </p>
                  <ul className="space-y-1.5">
                    {plan.pros.map((pro, i) => (
                      <li
                        key={i}
                        className="flex items-start gap-1.5 text-sm text-white/60"
                      >
                        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400/60 mt-0.5 flex-shrink-0" />
                        {pro}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              {plan.cons.length > 0 && (
                <div>
                  <p className="text-xs font-medium text-red-400/70 uppercase tracking-wider mb-2">
                    Cons
                  </p>
                  <ul className="space-y-1.5">
                    {plan.cons.map((con, i) => (
                      <li
                        key={i}
                        className="flex items-start gap-1.5 text-sm text-white/60"
                      >
                        <XCircle className="w-3.5 h-3.5 text-red-400/60 mt-0.5 flex-shrink-0" />
                        {con}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
        </GlassCard>

        {/* Error banner */}
        {error && (
          <div className="px-4 py-3 bg-red-500/10 border border-red-500/20 rounded-xl text-sm text-red-400">
            {error}
          </div>
        )}

        {/* Coming soon banner — shown when backend returns 501 (autonomous agent in progress) */}
        {comingSoon && (
          <div className="rounded-lg border border-blue-200 bg-blue-50 p-4 text-center dark:border-blue-800 dark:bg-blue-950">
            <p className="text-sm font-medium text-blue-800 dark:text-blue-200">
              Your AI Co-Founder is being built
            </p>
            <p className="mt-1 text-xs text-blue-600 dark:text-blue-400">
              We&apos;re upgrading your co-founder with autonomous capabilities. This feature will be available soon.
            </p>
          </div>
        )}

        {/* Start Build CTA */}
        <button
          onClick={handleStartBuild}
          disabled={starting}
          className="w-full py-3.5 px-6 bg-brand hover:bg-brand/90 disabled:opacity-50 disabled:cursor-not-allowed text-white font-semibold rounded-xl transition-all duration-200 shadow-glow flex items-center justify-center gap-2.5"
        >
          {starting ? (
            <>
              <Loader2 className="w-5 h-5 animate-spin" />
              Starting build...
            </>
          ) : (
            <>
              <Rocket className="w-5 h-5" />
              Start Build
            </>
          )}
        </button>

        {/* Back link */}
        <div className="text-center">
          <Link
            href={`/projects/${projectId}/understanding`}
            className="text-sm text-white/40 hover:text-white/60 transition-colors"
          >
            Back to decision gate
          </Link>
        </div>
      </motion.div>
    </div>
  );
}

// ──────────────────────────────────────────────────────────────────────────────
// Project-scoped Build page — orchestrates building → success/failure states
// ──────────────────────────────────────────────────────────────────────────────

export default function BuildPage() {
  const params = useParams<{ id: string }>();
  const searchParams = useSearchParams();
  const { getToken } = useAuth();

  const projectId = params.id;
  // job_id comes from URL query param: /projects/{id}/build?job_id=...
  const jobId = searchParams.get("job_id");

  const {
    status,
    label,
    previewUrl,
    buildVersion,
    error,
    debugId,
    stageIndex,
    totalStages,
    isTerminal,
    connectionFailed,
    sandboxExpiresAt,
    sandboxPaused,
  } = useBuildProgress(jobId, getToken);

  // SSE log streaming — called unconditionally so autoFixAttempt detection works
  // even when the log panel is collapsed (which it is by default)
  const {
    lines: logLines,
    isConnected: logConnected,
    hasEarlierLines,
    autoFixAttempt,
    loadEarlier,
  } = useBuildLogs(jobId, getToken);

  const [cancelling, setCancelling] = useState(false);

  // ────────────────────────────────────────────────────────────────────────────
  // Cancel handler
  // ────────────────────────────────────────────────────────────────────────────

  async function handleCancel() {
    if (!jobId) return;
    setCancelling(true);
    try {
      await apiFetch(`/api/generation/${jobId}/cancel`, getToken, {
        method: "POST",
      });
    } catch {
      // Non-fatal — build state will update via SSE or user can navigate away
    } finally {
      setCancelling(false);
    }
  }

  // ────────────────────────────────────────────────────────────────────────────
  // Retry handler — navigates back without job_id so user can start fresh
  // ────────────────────────────────────────────────────────────────────────────

  function handleRetry() {
    // Navigate back to the project dashboard where they can trigger a new build
    window.location.href = `/projects/${projectId}/deploy`;
  }

  // ────────────────────────────────────────────────────────────────────────────
  // PreviewPane callbacks — rebuild or iterate from expired state
  // ────────────────────────────────────────────────────────────────────────────

  function handleRebuild() {
    // Navigate to deploy page to trigger a fresh build
    window.location.href = `/projects/${projectId}/deploy`;
  }

  function handleIterate() {
    // Navigate to conversation/iterate flow
    window.location.href = `/projects/${projectId}/deploy?iterate=true`;
  }

  const isBuilding = !isTerminal && status !== "failed";
  const isSuccess = status === "ready";
  const isFailure = status === "failed";

  // When auto-fix is active, rewind the visual stage bar to "code" (index 3 in STAGE_ORDER).
  // The debugger returns to the coder which maps to the "Writing code" stage.
  const effectiveStageIndex =
    autoFixAttempt !== null && isBuilding ? 3 : stageIndex;

  // ────────────────────────────────────────────────────────────────────────────
  // No job ID — show selected plan + "Start Build" CTA
  // ────────────────────────────────────────────────────────────────────────────

  if (!jobId) {
    return <PreBuildView projectId={projectId} getToken={getToken} />;
  }

  return (
    <div className="min-h-[70vh] flex flex-col items-center justify-center py-12">
      {/* Cancel button — top right, only while building */}
      {isBuilding && (
        <div className="fixed top-20 right-6 z-40">
          <AlertDialog>
            <AlertDialogTrigger asChild>
              <button
                disabled={cancelling}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white/5 border border-white/10 text-sm text-white/50 hover:text-white/80 hover:bg-white/8 transition-colors disabled:opacity-40"
              >
                <X className="w-4 h-4" />
                {cancelling ? "Cancelling..." : "Cancel build"}
              </button>
            </AlertDialogTrigger>
            <AlertDialogContent className="bg-obsidian-light border border-white/10">
              <AlertDialogHeader>
                <AlertDialogTitle className="text-white">
                  Cancel this build?
                </AlertDialogTitle>
                <AlertDialogDescription className="text-white/60">
                  Are you sure you want to cancel this build? Progress will be
                  lost and you&apos;ll need to start a new build.
                </AlertDialogDescription>
              </AlertDialogHeader>
              <AlertDialogFooter>
                <AlertDialogCancel className="bg-white/5 border border-white/10 text-white hover:bg-white/10">
                  Keep building
                </AlertDialogCancel>
                <AlertDialogAction
                  onClick={handleCancel}
                  className="bg-red-500/80 hover:bg-red-500 text-white border-0"
                >
                  Yes, cancel
                </AlertDialogAction>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>
        </div>
      )}

      <AnimatePresence mode="wait">
        {/* Building state — narrow container */}
        {isBuilding && (
          <motion.div
            key="building"
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -12 }}
            transition={{ duration: 0.35 }}
            className="w-full max-w-xl mx-auto px-4"
          >
            <div className="glass rounded-2xl p-8 space-y-8">
              {/* Header */}
              <div className="text-center space-y-1">
                <h1 className="text-xl font-display font-semibold text-white">
                  Building your MVP
                </h1>
                <p className="text-sm text-white/50">
                  Sit tight — we&apos;re writing and testing your code.
                </p>
              </div>

              {/* Reconnecting banner — shown after 3 consecutive poll failures */}
              {connectionFailed && (
                <div className="mb-4 px-4 py-3 bg-yellow-500/10 border border-yellow-500/20 rounded-xl flex items-center gap-2">
                  <Loader2 className="h-4 w-4 text-yellow-400 animate-spin" />
                  <span className="text-sm text-yellow-400">
                    Reconnecting to build server...
                  </span>
                </div>
              )}

              {/* Auto-fix banner — above the stage bar when debugger is retrying */}
              <AnimatePresence>
                {autoFixAttempt !== null && (
                  <AutoFixBanner attempt={autoFixAttempt} />
                )}
              </AnimatePresence>

              {/* Progress bar — stage rewound to "Writing code" during auto-fix */}
              <BuildProgressBar
                stageIndex={effectiveStageIndex}
                totalStages={totalStages}
                label={label}
                status={status}
                autoFixAttempt={autoFixAttempt}
              />

              {/* Log panel — collapsed by default, below the progress bar */}
              <BuildLogPanel
                lines={logLines}
                isConnected={logConnected}
                hasEarlierLines={hasEarlierLines}
                onLoadEarlier={loadEarlier}
              />
            </div>
          </motion.div>
        )}

        {/* Success state with preview — wide container to give iframe room */}
        {isSuccess && previewUrl && (
          <motion.div
            key="success"
            initial={{ opacity: 0, scale: 0.96 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.4 }}
            className="w-full max-w-5xl mx-auto px-4 space-y-6"
          >
            <BuildSummary
              buildVersion={buildVersion ?? "build v0.1"}
              previewUrl={previewUrl}
              projectId={projectId}
            />
            <div className="w-full">
              <PreviewPane
                previewUrl={previewUrl}
                sandboxExpiresAt={sandboxExpiresAt}
                sandboxPaused={sandboxPaused}
                jobId={jobId}
                projectId={projectId}
                getToken={getToken}
                onRebuild={handleRebuild}
                onIterate={handleIterate}
              />
            </div>
          </motion.div>
        )}

        {/* Success but no preview URL yet (edge case) */}
        {isSuccess && !previewUrl && (
          <motion.div
            key="success-no-preview"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="w-full max-w-xl mx-auto px-4"
          >
            <div className="glass rounded-2xl p-8 text-center space-y-4">
              <p className="text-white font-semibold">Build complete!</p>
              <p className="text-white/50 text-sm">
                Preview URL is being prepared...
              </p>
              <a
                href={`/projects/${projectId}/deploy`}
                className="inline-block text-brand hover:text-brand-light text-sm underline"
              >
                Back to deploy
              </a>
            </div>
          </motion.div>
        )}

        {/* Failure state — narrow container */}
        {isFailure && (
          <motion.div
            key="failure"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.35 }}
            className="w-full max-w-xl mx-auto px-4"
          >
            <BuildFailureCard
              errorMessage={error ?? "An unexpected error occurred."}
              debugId={debugId ?? jobId ?? "unknown"}
              onRetry={handleRetry}
            />
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
