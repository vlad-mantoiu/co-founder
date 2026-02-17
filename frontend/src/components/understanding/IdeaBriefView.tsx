"use client";

import { useState } from "react";
import { RefreshCw, Lock, ArrowRight } from "lucide-react";
import { useAuth } from "@clerk/nextjs";
import { apiFetch } from "@/lib/api";
import { IdeaBriefCard } from "./IdeaBriefCard";
import type { RationalisedIdeaBrief } from "@/hooks/useUnderstandingInterview";

interface IdeaBriefViewProps {
  brief: RationalisedIdeaBrief;
  onEditSection: (sectionKey: string, newContent: string) => void;
  onReInterview: () => void;
  onProceedToDecision: () => void;
  artifactId: string;
  version: number;
  projectId: string;
}

/**
 * IdeaBriefView: Full Rationalised Idea Brief display.
 *
 * Renders brief as expandable cards with confidence indicators.
 * Supports inline section editing and re-interview for major changes.
 * Investor-facing tone per locked decision.
 */
export function IdeaBriefView({
  brief,
  onEditSection,
  onReInterview,
  onProceedToDecision,
  artifactId,
  version,
  projectId,
}: IdeaBriefViewProps) {
  const { getToken } = useAuth();
  const [deepResearchMessage, setDeepResearchMessage] = useState<string | null>(null);
  const [isDeepResearchLoading, setIsDeepResearchLoading] = useState(false);

  // Handle Deep Research button click (returns 402)
  const handleDeepResearch = async () => {
    setIsDeepResearchLoading(true);
    setDeepResearchMessage(null);

    try {
      const response = await apiFetch(
        `/api/plans/${projectId}/deep-research`,
        getToken,
        { method: "POST" }
      );

      if (response.status === 402) {
        const data = await response.json();
        setDeepResearchMessage(
          data.detail ||
            "Deep Research requires CTO tier. Upgrade to unlock market research, competitor analysis, and technical feasibility reports."
        );
      } else if (!response.ok) {
        setDeepResearchMessage("Failed to start Deep Research. Please try again.");
      }
    } catch {
      setDeepResearchMessage("An error occurred. Please try again.");
    } finally {
      setIsDeepResearchLoading(false);
    }
  };
  // Map brief sections to card format
  const sections = [
    {
      key: "problem_statement",
      title: "Problem Statement",
      summary: brief.problem_statement.slice(0, 100),
      fullContent: brief.problem_statement,
      confidence: brief.confidence_scores.problem_statement || "moderate",
    },
    {
      key: "target_user",
      title: "Target User",
      summary: brief.target_user.slice(0, 100),
      fullContent: brief.target_user,
      confidence: brief.confidence_scores.target_user || "moderate",
    },
    {
      key: "value_prop",
      title: "Value Proposition",
      summary: brief.value_prop.slice(0, 100),
      fullContent: brief.value_prop,
      confidence: brief.confidence_scores.value_prop || "moderate",
    },
    {
      key: "differentiation",
      title: "Differentiation",
      summary: brief.differentiation.slice(0, 100),
      fullContent: brief.differentiation,
      confidence: brief.confidence_scores.differentiation || "moderate",
    },
    {
      key: "market_context",
      title: "Market Context",
      summary: brief.market_context.slice(0, 100),
      fullContent: brief.market_context,
      confidence: brief.confidence_scores.market_context || "moderate",
    },
    {
      key: "monetization_hypothesis",
      title: "Monetization Hypothesis",
      summary: brief.monetization_hypothesis.slice(0, 100),
      fullContent: brief.monetization_hypothesis,
      confidence: brief.confidence_scores.monetization_hypothesis || "moderate",
    },
    {
      key: "key_constraints",
      title: "Key Constraints",
      summary: `${brief.key_constraints.length} constraint(s) identified`,
      fullContent: brief.key_constraints,
      confidence: brief.confidence_scores.key_constraints || "moderate",
    },
    {
      key: "assumptions",
      title: "Assumptions",
      summary: `${brief.assumptions.length} assumption(s) documented`,
      fullContent: brief.assumptions,
      confidence: brief.confidence_scores.assumptions || "moderate",
    },
    {
      key: "risks",
      title: "Risks",
      summary: `${brief.risks.length} risk(s) identified`,
      fullContent: brief.risks,
      confidence: brief.confidence_scores.risks || "moderate",
    },
    {
      key: "smallest_viable_experiment",
      title: "Smallest Viable Experiment",
      summary: brief.smallest_viable_experiment.slice(0, 100),
      fullContent: brief.smallest_viable_experiment,
      confidence: brief.confidence_scores.smallest_viable_experiment || "moderate",
    },
  ];

  return (
    <div className="max-w-4xl mx-auto px-6 py-12 space-y-8">
      {/* Header */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-3xl font-display font-bold text-white">
            Rationalised Idea Brief
          </h2>
          <div className="flex items-center gap-2">
            <span className="text-xs text-muted-foreground">v{version}</span>
          </div>
        </div>
        <p className="text-sm text-muted-foreground">
          This brief is formatted for investor communication
        </p>
      </div>

      {/* Brief sections as expandable cards */}
      <div className="space-y-3">
        {sections.map((section) => (
          <IdeaBriefCard
            key={section.key}
            section={{
              key: section.key,
              title: section.title,
              summary: section.summary,
              fullContent: section.fullContent,
              confidence: section.confidence as "strong" | "moderate" | "needs_depth",
            }}
            onEdit={onEditSection}
          />
        ))}
      </div>

      {/* Deep Research button (gated at 402) */}
      <div className="pt-6 border-t border-white/10">
        <div className="flex items-center gap-3">
          <button
            onClick={handleDeepResearch}
            disabled={isDeepResearchLoading}
            className="flex items-center gap-2 px-4 py-2.5 bg-white/5 hover:bg-white/10 text-muted-foreground font-medium rounded-xl transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Lock className="h-4 w-4" />
            Deep Research
            {isDeepResearchLoading ? (
              <span className="ml-2 h-4 w-4 border-2 border-white/20 border-t-white rounded-full animate-spin" />
            ) : (
              <span className="ml-1 px-2 py-0.5 bg-brand/20 text-brand text-xs font-semibold rounded-full">
                CTO Tier
              </span>
            )}
          </button>
        </div>
        {deepResearchMessage && (
          <div className="mt-3 p-3 bg-brand/10 border border-brand/20 rounded-lg">
            <p className="text-sm text-brand">{deepResearchMessage}</p>
          </div>
        )}
        <p className="mt-2 text-xs text-muted-foreground">
          Deep Research provides market research, competitor analysis, and technical feasibility
          reports.
        </p>
      </div>

      {/* Proceed to Decision CTA */}
      <div className="pt-6 border-t border-white/10">
        <button
          onClick={onProceedToDecision}
          className="w-full flex items-center justify-center gap-2 px-6 py-3.5 bg-brand hover:bg-brand/90 text-white font-semibold rounded-xl transition-colors shadow-glow"
        >
          Proceed to Decision Gate
          <ArrowRight className="h-5 w-5" />
        </button>
        <p className="mt-2 text-xs text-muted-foreground text-center">
          Ready to decide your next step? Review your options and choose your path forward.
        </p>
      </div>

      {/* Re-interview button */}
      <div className="pt-6 border-t border-white/10">
        <button
          onClick={onReInterview}
          className="flex items-center gap-2 px-4 py-2.5 bg-white/5 hover:bg-white/10 text-white font-medium rounded-xl transition-colors"
        >
          <RefreshCw className="h-4 w-4" />
          Re-interview for major changes
        </button>
        <p className="mt-2 text-xs text-muted-foreground">
          Use this if your idea has significantly evolved. For small tweaks, use inline editing
          above.
        </p>
      </div>
    </div>
  );
}
