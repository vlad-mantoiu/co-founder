"use client";

import { useState, useEffect, useRef } from "react";
import { useDashboard, ArtifactSummary } from "@/hooks/useDashboard";
import { StageRing } from "@/components/dashboard/stage-ring";
import { ActionHero } from "@/components/dashboard/action-hero";
import { ArtifactCard } from "@/components/dashboard/artifact-card";
import { RiskFlags } from "@/components/dashboard/risk-flags";
import { SlideOver } from "@/components/ui/slide-over";
import { ArtifactPanel } from "@/components/dashboard/artifact-panel";
import { toast } from "sonner";

interface CompanyDashboardPageProps {
  params: {
    projectId: string;
  };
}

export default function CompanyDashboardPage({
  params,
}: CompanyDashboardPageProps) {
  const { projectId } = params;
  const { data, loading, error, changedFields, refetch } = useDashboard(projectId);
  const [selectedArtifactId, setSelectedArtifactId] = useState<string | null>(null);

  // Track previous artifacts for toast notifications
  const previousArtifactsRef = useRef<ArtifactSummary[]>([]);

  // Toast notifications for polling changes
  useEffect(() => {
    if (!data) return;

    // Check for artifact status changes
    if (changedFields.has("artifacts")) {
      const prevArtifacts = previousArtifactsRef.current;
      const currentArtifacts = data.artifacts;

      currentArtifacts.forEach((artifact) => {
        const prevArtifact = prevArtifacts.find((a) => a.id === artifact.id);

        if (prevArtifact) {
          // Check for generation completion
          if (prevArtifact.generation_status === "generating" && artifact.generation_status === "idle") {
            toast.success("Artifact generation completed");
          }

          // Check for generation failure
          if (artifact.generation_status === "failed" && prevArtifact.generation_status !== "failed") {
            toast.error("Artifact generation failed");
          }
        }
      });
    }

    // Check for progress changes
    if (changedFields.has("progress")) {
      toast.success(`Progress updated: ${data.mvp_completion_percent}%`);
    }

    // Update previous artifacts ref
    previousArtifactsRef.current = data.artifacts;
  }, [data, changedFields]);

  // Loading state (first load, no data yet)
  if (loading && !data) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-950 via-blue-950 to-slate-950 p-8">
        <div className="max-w-7xl mx-auto space-y-8">
          {/* Hero row skeleton */}
          <div className="flex gap-8 items-center">
            {/* Stage ring skeleton */}
            <div className="w-48 h-48 bg-white/5 rounded-full animate-pulse" />

            {/* Action hero skeleton */}
            <div className="flex-1 bg-white/5 border border-white/10 rounded-xl p-6 space-y-4 animate-pulse">
              <div className="h-4 bg-white/10 rounded w-24" />
              <div className="h-6 bg-white/10 rounded w-3/4" />
              <div className="h-4 bg-white/10 rounded w-1/2" />
            </div>
          </div>

          {/* Artifacts grid skeleton */}
          <div>
            <div className="h-6 bg-white/10 rounded w-32 mb-4 animate-pulse" />
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {[1, 2, 3].map((i) => (
                <div
                  key={i}
                  className="p-6 bg-white/5 border border-white/10 rounded-xl space-y-3 animate-pulse"
                >
                  <div className="h-6 bg-white/10 rounded w-3/4" />
                  <div className="h-4 bg-white/10 rounded w-1/2" />
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-950 via-blue-950 to-slate-950 p-8 flex items-center justify-center">
        <div className="text-center space-y-4">
          <p className="text-red-400 text-lg">Something went wrong. Please try again.</p>
          <button
            onClick={() => refetch()}
            className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  // No data (shouldn't happen after loading, but safety check)
  if (!data) {
    return null;
  }

  const hasArtifacts = data.artifacts.length > 0;
  const artifactsChanged = changedFields.has("artifacts");

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-blue-950 to-slate-950 p-8">
      <div className="max-w-7xl mx-auto space-y-8">
        {/* Hero row: Stage ring + Action hero side-by-side */}
        <div className="flex gap-8 items-center">
          <StageRing
            currentStage={data.stage}
            progressPercent={data.mvp_completion_percent}
          />
          <ActionHero
            suggestedFocus={data.suggested_focus}
            pendingDecisions={data.pending_decisions}
            nextMilestone={data.next_milestone}
          />
        </div>

        {/* Risk flags (only when present) */}
        <RiskFlags risks={data.risk_flags} />

        {/* Artifacts section */}
        <div>
          <h2 className="text-xl font-semibold text-white mb-4">
            Your Documents
          </h2>

          {/* Empty state */}
          {!hasArtifacts && (
            <div className="text-center py-12 text-white/50">
              <p>No documents generated yet.</p>
              <p className="text-sm mt-2">
                Start by generating your project artifacts.
              </p>
            </div>
          )}

          {/* Artifacts grid */}
          {hasArtifacts && (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {data.artifacts.map((artifact) => (
                <ArtifactCard
                  key={artifact.id}
                  artifact={artifact}
                  isChanged={artifactsChanged}
                  onClick={() => setSelectedArtifactId(artifact.id)}
                />
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Slide-over panel for artifact drill-down */}
      {selectedArtifactId && (
        <SlideOver
          key={selectedArtifactId}
          open={selectedArtifactId !== null}
          onClose={() => setSelectedArtifactId(null)}
          title={
            data.artifacts.find((a) => a.id === selectedArtifactId)?.artifact_type
              .split("_")
              .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
              .join(" ") || "Artifact"
          }
        >
          <ArtifactPanel
            artifactId={selectedArtifactId}
            projectId={projectId}
            onClose={() => setSelectedArtifactId(null)}
          />
        </SlideOver>
      )}
    </div>
  );
}
