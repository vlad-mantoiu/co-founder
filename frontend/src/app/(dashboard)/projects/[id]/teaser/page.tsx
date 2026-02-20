"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useParams, useSearchParams } from "next/navigation";
import { useAuth } from "@clerk/nextjs";
import {
  ArrowRight,
  Calendar,
  FileText,
  ListChecks,
  Loader2,
  Lock,
  Network,
  ShieldAlert,
  type LucideIcon,
} from "lucide-react";
import { apiFetch } from "@/lib/api";
import { GlassCard } from "@/components/ui/glass-card";

const TEASER_ARTIFACT_ORDER = [
  "brief",
  "mvp_scope",
  "milestones",
  "risk_log",
  "how_it_works",
] as const;

type TeaserArtifactType = (typeof TEASER_ARTIFACT_ORDER)[number];

interface ArtifactListItem {
  id: string;
  artifact_type: string;
  generation_status: string;
  version_number: number;
}

interface ArtifactDetail {
  id: string;
  artifact_type: string;
  generation_status: string;
  version_number: number;
  current_content: Record<string, unknown>;
}

const ARTIFACT_META: Record<
  TeaserArtifactType,
  { title: string; icon: LucideIcon; description: string }
> = {
  brief: {
    title: "Brief",
    icon: FileText,
    description: "Problem, audience, and value proposition from your onboarding inputs.",
  },
  mvp_scope: {
    title: "MVP Scope",
    icon: ListChecks,
    description: "Initial feature boundaries and success criteria.",
  },
  milestones: {
    title: "Milestones",
    icon: Calendar,
    description: "Execution timeline and critical path.",
  },
  risk_log: {
    title: "Risk Log",
    icon: ShieldAlert,
    description: "Early technical, market, and execution risks.",
  },
  how_it_works: {
    title: "How It Works",
    icon: Network,
    description: "High-level architecture and user/system flow.",
  },
};

const LOCKED_FIELDS: Record<TeaserArtifactType, Array<{ key: string; label: string }>> = {
  brief: [
    { key: "market_analysis", label: "Market analysis" },
    { key: "competitive_strategy", label: "Competitive strategy" },
  ],
  mvp_scope: [
    { key: "technical_architecture", label: "Technical architecture detail" },
    { key: "scalability_plan", label: "Scalability plan" },
  ],
  milestones: [
    { key: "resource_plan", label: "Resource plan" },
    { key: "risk_mitigation_timeline", label: "Risk mitigation timeline" },
  ],
  risk_log: [
    { key: "financial_risks", label: "Financial risks" },
    { key: "strategic_risks", label: "Strategic risks" },
  ],
  how_it_works: [
    { key: "integration_points", label: "Integration points" },
    { key: "security_compliance", label: "Security and compliance" },
  ],
};

function isTeaserArtifactType(value: string): value is TeaserArtifactType {
  return TEASER_ARTIFACT_ORDER.includes(value as TeaserArtifactType);
}

function firstString(values: unknown[]): string | null {
  for (const value of values) {
    if (typeof value === "string" && value.trim()) return value.trim();
  }
  return null;
}

function summarizeArtifact(
  artifactType: TeaserArtifactType,
  content: Record<string, unknown> | null,
): string {
  if (!content) {
    return "Preview is being generated from your onboarding answers.";
  }

  if (artifactType === "brief") {
    return (
      firstString([
        content.problem_statement,
        content.value_proposition,
        content.value_prop,
        content.target_user,
      ]) || "Problem framing preview is ready."
    );
  }

  if (artifactType === "mvp_scope") {
    const features = Array.isArray(content.core_features) ? content.core_features : [];
    if (features.length > 0) {
      const firstFeature = (features[0] as Record<string, unknown>) || {};
      const featureName =
        firstString([
          firstFeature.name,
          firstFeature.title,
          firstFeature.feature,
        ]) || "your first core feature";
      return `${features.length} core feature${features.length === 1 ? "" : "s"} identified, starting with ${featureName}.`;
    }
    return "MVP boundaries and delivery scope are ready for review.";
  }

  if (artifactType === "milestones") {
    const milestones = Array.isArray(content.milestones) ? content.milestones : [];
    const duration =
      typeof content.total_duration_weeks === "number"
        ? content.total_duration_weeks
        : null;

    if (milestones.length > 0 && duration) {
      return `${milestones.length} milestone${milestones.length === 1 ? "" : "s"} planned over about ${duration} weeks.`;
    }
    if (milestones.length > 0) {
      return `${milestones.length} milestone${milestones.length === 1 ? "" : "s"} drafted for execution.`;
    }
    return "Timeline sequence is prepared from your onboarding context.";
  }

  if (artifactType === "risk_log") {
    const technical = Array.isArray(content.technical_risks) ? content.technical_risks.length : 0;
    const market = Array.isArray(content.market_risks) ? content.market_risks.length : 0;
    const execution = Array.isArray(content.execution_risks) ? content.execution_risks.length : 0;
    const total = technical + market + execution;
    if (total > 0) {
      return `${total} core risk${total === 1 ? "" : "s"} identified across technical, market, and execution categories.`;
    }
    return "Early risk surface has been generated for this project.";
  }

  return (
    firstString([content.architecture, content.data_flow]) ||
    "System architecture preview generated from your onboarding inputs."
  );
}

function lockedSectionsFor(
  artifactType: TeaserArtifactType,
  content: Record<string, unknown> | null,
): string[] {
  if (!content) return [];

  return LOCKED_FIELDS[artifactType]
    .filter(({ key }) => {
      const value = content[key];
      if (value === null || value === undefined) return true;
      if (Array.isArray(value) && value.length === 0) return true;
      if (typeof value === "string" && !value.trim()) return true;
      return false;
    })
    .map(({ label }) => label);
}

export default function ProjectTeaserPage() {
  const params = useParams<{ id: string }>();
  const searchParams = useSearchParams();
  const { getToken } = useAuth();

  const projectId = params.id;
  const sessionId = searchParams.get("sessionId");

  const [artifactsByType, setArtifactsByType] = useState<
    Partial<Record<TeaserArtifactType, ArtifactListItem>>
  >({});
  const [artifactDetailsByType, setArtifactDetailsByType] = useState<
    Partial<Record<TeaserArtifactType, ArtifactDetail>>
  >({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [checkoutLoading, setCheckoutLoading] = useState(false);

  const allSettled = useMemo(() => {
    return TEASER_ARTIFACT_ORDER.every((type) => {
      const artifact = artifactsByType[type];
      return artifact && ["idle", "failed"].includes(artifact.generation_status);
    });
  }, [artifactsByType]);

  const fetchArtifacts = useCallback(async () => {
    try {
      const listResponse = await apiFetch(`/api/artifacts/project/${projectId}`, getToken);
      if (!listResponse.ok) {
        throw new Error("Failed to fetch artifact list");
      }

      const listData = (await listResponse.json()) as ArtifactListItem[];
      const scopedArtifacts: ArtifactListItem[] = listData.filter((artifact) =>
        isTeaserArtifactType(artifact.artifact_type),
      );

      const byType: Partial<Record<TeaserArtifactType, ArtifactListItem>> = {};
      for (const artifact of scopedArtifacts) {
        const type = artifact.artifact_type as TeaserArtifactType;
        const current = byType[type];
        if (!current || artifact.version_number >= current.version_number) {
          byType[type] = artifact;
        }
      }
      setArtifactsByType(byType);

      const readyArtifacts = Object.values(byType).filter(
        (artifact): artifact is ArtifactListItem =>
          Boolean(artifact) && artifact.generation_status === "idle",
      );

      if (readyArtifacts.length > 0) {
        const detailResponses = await Promise.all(
          readyArtifacts.map(async (artifact) => {
            const detailResponse = await apiFetch(`/api/artifacts/${artifact.id}`, getToken);
            if (!detailResponse.ok) return null;
            return (await detailResponse.json()) as ArtifactDetail;
          }),
        );

        setArtifactDetailsByType((prev) => {
          const next = { ...prev };
          for (const detail of detailResponses) {
            if (!detail || !isTeaserArtifactType(detail.artifact_type)) continue;
            next[detail.artifact_type] = detail;
          }
          return next;
        });
      }

      setError(null);
    } catch {
      setError("We couldn't load your artifact previews yet. Please try again.");
    } finally {
      setLoading(false);
    }
  }, [getToken, projectId]);

  useEffect(() => {
    fetchArtifacts();
    if (allSettled) return;

    const interval = window.setInterval(fetchArtifacts, 3000);
    return () => window.clearInterval(interval);
  }, [fetchArtifacts, allSettled]);

  async function handleSubscribe() {
    setCheckoutLoading(true);
    try {
      const returnTo = sessionId
        ? `/projects/${projectId}/understanding?sessionId=${encodeURIComponent(sessionId)}`
        : `/projects/${projectId}/understanding`;

      const response = await apiFetch("/api/billing/checkout", getToken, {
        method: "POST",
        body: JSON.stringify({
          plan_slug: "bootstrapper",
          interval: "monthly",
          return_to: returnTo,
        }),
      });

      if (!response.ok) {
        throw new Error("Checkout session failed");
      }

      const data = await response.json();
      if (data.checkout_url) {
        window.location.href = data.checkout_url;
      }
    } catch {
      setError("Checkout could not be started. Please try again.");
    } finally {
      setCheckoutLoading(false);
    }
  }

  return (
    <div className="max-w-6xl mx-auto space-y-8">
      <div className="space-y-3">
        <h1 className="font-display text-3xl sm:text-4xl font-bold text-white">
          Your onboarding artifact preview
        </h1>
        <p className="text-muted-foreground max-w-3xl">
          Quick answer: your onboarding inputs already produced strategy artifacts. This is a partial preview of all 5 outputs before subscription.
        </p>
      </div>

      {error && (
        <div className="rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-300">
          {error}
        </div>
      )}

      {loading ? (
        <div className="flex items-center justify-center h-40">
          <Loader2 className="w-6 h-6 text-brand animate-spin" />
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {TEASER_ARTIFACT_ORDER.map((artifactType) => {
            const artifact = artifactsByType[artifactType];
            const detail = artifactDetailsByType[artifactType];
            const meta = ARTIFACT_META[artifactType];
            const Icon = meta.icon;

            const status = artifact?.generation_status ?? "queued";
            const summary = summarizeArtifact(artifactType, detail?.current_content ?? null);
            const lockedSections = lockedSectionsFor(
              artifactType,
              detail?.current_content ?? null,
            );

            return (
              <GlassCard key={artifactType} variant="strong" className="h-full space-y-4">
                <div className="flex items-start justify-between gap-3">
                  <div className="flex items-start gap-3">
                    <div className="w-9 h-9 rounded-lg bg-brand/10 flex items-center justify-center">
                      <Icon className="w-4 h-4 text-brand" />
                    </div>
                    <div>
                      <p className="font-semibold text-white">{meta.title}</p>
                      <p className="text-xs text-muted-foreground mt-1">{meta.description}</p>
                    </div>
                  </div>
                  <span className="text-[11px] uppercase tracking-wide text-muted-foreground">
                    {status === "idle"
                      ? "Ready"
                      : status === "generating"
                        ? "Generating"
                        : status === "failed"
                          ? "Failed"
                          : "Queued"}
                  </span>
                </div>

                <p className="text-sm text-white/85 leading-relaxed">{summary}</p>

                {status === "generating" && (
                  <div className="inline-flex items-center gap-2 text-xs text-brand">
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    Generating preview...
                  </div>
                )}

                {lockedSections.length > 0 && (
                  <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-xs text-amber-200">
                    <p className="inline-flex items-center gap-1 font-medium mb-1">
                      <Lock className="w-3 h-3" />
                      Locked depth
                    </p>
                    <p>{lockedSections.join(" | ")}</p>
                  </div>
                )}
              </GlassCard>
            );
          })}
        </div>
      )}

      <GlassCard variant="strong" className="space-y-4">
        <h2 className="font-display text-xl font-semibold text-white">
          Build with full artifact depth
        </h2>
        <p className="text-muted-foreground">
          Subscribe to unlock complete artifact detail and continue to your strategy flow.
        </p>
        <div className="flex flex-col sm:flex-row gap-3">
          <button
            onClick={handleSubscribe}
            disabled={checkoutLoading}
            className="inline-flex items-center justify-center gap-2 px-6 py-3 rounded-xl bg-brand text-white font-semibold hover:bg-brand-dark transition-colors shadow-glow"
          >
            {checkoutLoading ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <ArrowRight className="w-4 h-4" />
            )}
            Subscribe to Build
          </button>
          <Link
            href={`/projects/${projectId}`}
            className="inline-flex items-center justify-center px-6 py-3 rounded-xl border border-white/15 text-white/80 hover:text-white hover:border-white/30 transition-colors"
          >
            Continue Without Subscribing
          </Link>
        </div>
      </GlassCard>
    </div>
  );
}
