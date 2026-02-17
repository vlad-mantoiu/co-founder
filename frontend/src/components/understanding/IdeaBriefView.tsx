"use client";

import { RefreshCw } from "lucide-react";
import { IdeaBriefCard } from "./IdeaBriefCard";
import type { RationalisedIdeaBrief } from "@/hooks/useUnderstandingInterview";

interface IdeaBriefViewProps {
  brief: RationalisedIdeaBrief;
  onEditSection: (sectionKey: string, newContent: string) => void;
  onReInterview: () => void;
  artifactId: string;
  version: number;
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
  artifactId,
  version,
}: IdeaBriefViewProps) {
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
