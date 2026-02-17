"use client";

import { FileText, AlertCircle } from "lucide-react";
import { motion } from "framer-motion";
import { ArtifactSummary } from "@/hooks/useDashboard";

interface ArtifactCardProps {
  artifact: ArtifactSummary;
  onClick: () => void;
  isChanged: boolean;
}

// Map artifact types to human-readable names
const ARTIFACT_TYPE_LABELS: Record<string, string> = {
  brief: "Product Brief",
  mvp_scope: "MVP Scope",
  milestones: "Milestones",
  risk_log: "Risk Log",
  how_it_works: "How It Works",
};

export function ArtifactCard({ artifact, onClick, isChanged }: ArtifactCardProps) {
  const isGenerating = artifact.generation_status === "generating";
  const isFailed = artifact.generation_status === "failed";
  const label = ARTIFACT_TYPE_LABELS[artifact.artifact_type] || artifact.artifact_type;

  // Format updated_at timestamp
  const updatedDate = new Date(artifact.updated_at);
  const relativeTime = getRelativeTime(updatedDate);

  return (
    <motion.div
      initial={false}
      animate={
        isChanged
          ? { scale: [1, 1.02, 1] }
          : { scale: 1 }
      }
      transition={{ duration: 0.3 }}
      onClick={onClick}
      className={`
        p-6 rounded-xl bg-white/5 border transition-all cursor-pointer
        ${isChanged ? "ring-2 ring-blue-500/50" : ""}
        ${isFailed ? "border-red-500/50" : "border-white/10"}
        hover:border-blue-500/50
      `}
    >
      {/* Generating state: skeleton shimmer */}
      {isGenerating && (
        <div className="space-y-3 animate-pulse">
          <div className="h-6 bg-white/10 rounded w-3/4" />
          <div className="h-4 bg-white/10 rounded w-1/2" />
          <div className="h-4 bg-white/10 rounded w-2/3" />
        </div>
      )}

      {/* Normal/Failed state */}
      {!isGenerating && (
        <>
          <div className="flex items-start justify-between mb-3">
            <div className="flex items-center gap-3">
              {isFailed ? (
                <AlertCircle className="w-5 h-5 text-red-500 flex-shrink-0" />
              ) : (
                <FileText className="w-5 h-5 text-blue-500 flex-shrink-0" />
              )}
              <h3 className="font-medium text-white">{label}</h3>
            </div>

            {/* Edited badge */}
            {artifact.has_user_edits && (
              <span className="text-xs px-2 py-1 rounded-full bg-amber-500/10 text-amber-500 border border-amber-500/20">
                Edited
              </span>
            )}
          </div>

          <div className="flex items-center gap-4 text-sm text-white/50">
            <span>v{artifact.version_number}</span>
            <span>•</span>
            <span>{relativeTime}</span>
          </div>

          {/* Failed state: error indicator */}
          {isFailed && (
            <div className="mt-3 text-sm text-red-400">
              Generation failed. Click to retry.
            </div>
          )}
        </>
      )}
    </motion.div>
  );
}

// Helper function for relative time formatting
function getRelativeTime(date: Date): string {
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMins < 1) return "just now";
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;

  return date.toLocaleDateString();
}
