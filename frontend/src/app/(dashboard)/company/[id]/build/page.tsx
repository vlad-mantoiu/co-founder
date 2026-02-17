"use client";

import { useState } from "react";
import { useParams, useSearchParams } from "next/navigation";
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
import { X } from "lucide-react";
import { useAuth } from "@clerk/nextjs";
import { useBuildProgress } from "@/hooks/useBuildProgress";
import { BuildProgressBar } from "@/components/build/BuildProgressBar";
import { BuildSummary } from "@/components/build/BuildSummary";
import { BuildFailureCard } from "@/components/build/BuildFailureCard";
import { apiFetch } from "@/lib/api";

// ──────────────────────────────────────────────────────────────────────────────
// Build page — orchestrates building → success/failure states
// ──────────────────────────────────────────────────────────────────────────────

export default function BuildPage() {
  const params = useParams<{ id: string }>();
  const searchParams = useSearchParams();
  const { getToken } = useAuth();

  const projectId = params.id;
  // job_id comes from URL query param: /company/{id}/build?job_id=...
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
  } = useBuildProgress(jobId);

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
    window.location.href = `/company/${projectId}`;
  }

  const isBuilding = !isTerminal && status !== "failed";
  const isSuccess = status === "ready";
  const isFailure = status === "failed";

  // ────────────────────────────────────────────────────────────────────────────
  // No job ID — graceful empty state
  // ────────────────────────────────────────────────────────────────────────────

  if (!jobId) {
    return (
      <div className="min-h-[60vh] flex items-center justify-center">
        <div className="text-center space-y-2">
          <p className="text-white/40 text-sm">No active build found.</p>
          <a
            href={`/company/${projectId}`}
            className="text-brand hover:text-brand-light text-sm underline"
          >
            Back to project
          </a>
        </div>
      </div>
    );
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

      <div className="w-full max-w-xl mx-auto px-4">
        <AnimatePresence mode="wait">
          {/* Building state */}
          {isBuilding && (
            <motion.div
              key="building"
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -12 }}
              transition={{ duration: 0.35 }}
              className="glass rounded-2xl p-8 space-y-8"
            >
              {/* Header */}
              <div className="text-center space-y-1">
                <h1 className="text-xl font-display font-semibold text-white">
                  Building your MVP
                </h1>
                <p className="text-sm text-white/50">
                  Sit tight — we&apos;re writing and testing your code.
                </p>
              </div>

              {/* Progress bar */}
              <BuildProgressBar
                stageIndex={stageIndex}
                totalStages={totalStages}
                label={label}
                status={status}
              />
            </motion.div>
          )}

          {/* Success state */}
          {isSuccess && previewUrl && (
            <motion.div
              key="success"
              initial={{ opacity: 0, scale: 0.96 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.4 }}
            >
              <BuildSummary
                buildVersion={buildVersion ?? "build v0.1"}
                previewUrl={previewUrl}
                projectId={projectId}
              />
            </motion.div>
          )}

          {/* Success but no preview URL yet (edge case) */}
          {isSuccess && !previewUrl && (
            <motion.div
              key="success-no-preview"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="glass rounded-2xl p-8 text-center space-y-4"
            >
              <p className="text-white font-semibold">Build complete!</p>
              <p className="text-white/50 text-sm">
                Preview URL is being prepared...
              </p>
              <a
                href={`/company/${projectId}`}
                className="inline-block text-brand hover:text-brand-light text-sm underline"
              >
                Back to dashboard
              </a>
            </motion.div>
          )}

          {/* Failure state */}
          {isFailure && (
            <motion.div
              key="failure"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.35 }}
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
    </div>
  );
}
