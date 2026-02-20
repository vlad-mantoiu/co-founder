"use client";

import { useState, useEffect, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import { useAuth } from "@clerk/nextjs";
import { KanbanBoard } from "@/components/timeline/KanbanBoard";
import { TimelineSearch, SearchParams } from "@/components/timeline/TimelineSearch";
import { MvpTimeline } from "@/components/timeline/MvpTimeline";
import { NodeDetailModal, NodeDetail } from "@/components/strategy-graph/NodeDetailModal";
import { TimelineItem } from "@/components/timeline/types";
import { apiFetch } from "@/lib/api";

interface MvpTimelineContent {
  milestones: Array<{
    week: number;
    title: string;
    deliverables: string[];
    duration_weeks: number;
    description: string;
  }>;
  long_term_roadmap: Array<{
    phase: string;
    title: string;
    description: string;
    estimated_weeks: number;
  }>;
  total_mvp_weeks: number;
  adapted_for: string;
}

function buildQueryString(projectId: string, params: SearchParams): string {
  const parts: string[] = [];
  if (params.query) parts.push(`query=${encodeURIComponent(params.query)}`);
  if (params.typeFilter) parts.push(`type_filter=${encodeURIComponent(params.typeFilter)}`);
  if (params.dateFrom) parts.push(`date_from=${encodeURIComponent(params.dateFrom)}`);
  if (params.dateTo) parts.push(`date_to=${encodeURIComponent(params.dateTo)}`);
  const qs = parts.length > 0 ? `?${parts.join("&")}` : "";
  return `/api/timeline/${projectId}${qs}`;
}

function TimelineSkeleton() {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
      {Array.from({ length: 4 }).map((_, i) => (
        <div key={i} className="bg-white/[0.02] rounded-xl p-3 animate-pulse">
          <div className="h-4 bg-white/5 rounded w-20 mb-3" />
          {Array.from({ length: 3 }).map((_, j) => (
            <div key={j} className="h-16 bg-white/5 rounded-lg mb-2" />
          ))}
        </div>
      ))}
    </div>
  );
}

/**
 * Project-scoped Timeline page.
 *
 * Dual-mode: shows MVP milestones from artifact when available, with Kanban
 * board below. Falls back to Kanban-only when no mvp_timeline artifact exists.
 *
 * Reads projectId from URL path segment (params.id).
 * View-in-graph links navigate to /projects/{id}/strategy?highlight={nodeId}.
 */
export default function ProjectTimelinePage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const { getToken } = useAuth();

  // projectId from URL path segment — always present
  const projectId = params.id;

  const [items, setItems] = useState<TimelineItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searchState, setSearchState] = useState<SearchParams>({
    query: "",
    typeFilter: null,
    dateFrom: null,
    dateTo: null,
  });
  const [enrichedDetail, setEnrichedDetail] = useState<NodeDetail | null>(null);
  // Holds mvp_timeline artifact content when available (null = Kanban-only mode)
  const [mvpTimelineData, setMvpTimelineData] = useState<MvpTimelineContent | null>(null);

  const fetchTimeline = useCallback(
    async (params: SearchParams) => {
      setLoading(true);
      setError(null);
      try {
        // FIRST: try to fetch the mvp_timeline artifact
        const artifactRes = await apiFetch(`/api/artifacts/project/${projectId}`, getToken);
        if (artifactRes.ok) {
          const artifacts = await artifactRes.json();
          const timelineArtifact = artifacts.find(
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            (a: any) => a.artifact_type === "mvp_timeline" && a.generation_status === "idle" && a.current_content
          );
          if (timelineArtifact) {
            setMvpTimelineData(timelineArtifact.current_content as MvpTimelineContent);
          } else {
            setMvpTimelineData(null);
          }
        }

        // ALWAYS fetch Kanban board items too (shown below MVP milestones or as fallback)
        const url = buildQueryString(projectId, params);
        const res = await apiFetch(url, getToken);
        if (!res.ok) {
          throw new Error(`Failed to load timeline (${res.status})`);
        }
        const data = await res.json();
        setItems(data.items ?? []);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load timeline");
      } finally {
        setLoading(false);
      }
    },
    [projectId, getToken],
  );

  useEffect(() => {
    fetchTimeline(searchState);
  }, [fetchTimeline, searchState]);

  const handleSearch = useCallback((params: SearchParams) => {
    setSearchState(params);
  }, []);

  const handleCardClick = useCallback(async (item: TimelineItem) => {
    const base: NodeDetail = {
      id: item.graph_node_id ?? item.id,
      title: item.title,
      type: item.type,
      status: item.kanban_status,
      created_at: item.timestamp,
      why: item.summary,
      impact_summary: "",
      tradeoffs: [],
      alternatives: [],
    };

    if (item.type === "decision" && item.graph_node_id && projectId) {
      try {
        const res = await apiFetch(
          `/api/graph/${projectId}/nodes/${item.graph_node_id}`,
          getToken
        );
        if (res.ok) {
          const detail = await res.json();
          base.impact_summary = detail.impact_summary ?? "";
          base.tradeoffs = detail.tradeoffs ?? [];
          base.alternatives = detail.alternatives ?? [];
          base.created_at = detail.created_at ?? item.timestamp;
        }
      } catch {
        // Non-fatal fallback
      }
    }

    setEnrichedDetail(base);
  }, [projectId, getToken]);

  const handleCloseModal = useCallback(() => {
    setEnrichedDetail(null);
  }, []);

  const handleViewInGraph = useCallback(
    (nodeId: string) => {
      setEnrichedDetail(null);
      // Use project-scoped strategy URL
      router.push(`/projects/${projectId}/strategy?highlight=${nodeId}`);
    },
    [router, projectId],
  );

  return (
    <div className="p-6">
      {/* Page header */}
      <div className="mb-6">
        <h1 className="text-2xl font-display font-semibold text-white">Timeline</h1>
        <p className="text-sm text-muted-foreground mt-1">
          {mvpTimelineData
            ? "Your personalized MVP launch plan"
            : "Track project events and milestones"}
        </p>
      </div>

      {/* MVP milestones from artifact — shown when available */}
      {mvpTimelineData && !loading && (
        <div className="mb-10">
          <MvpTimeline
            milestones={mvpTimelineData.milestones ?? []}
            longTermRoadmap={mvpTimelineData.long_term_roadmap ?? []}
            totalMvpWeeks={mvpTimelineData.total_mvp_weeks ?? 0}
            adaptedFor={mvpTimelineData.adapted_for ?? ""}
          />
        </div>
      )}

      {/* Kanban board — always shown (as primary content or below MVP milestones) */}
      {mvpTimelineData && !loading && items.length > 0 && (
        <div className="mb-4">
          <h2 className="text-base font-semibold text-white/60 mb-4">Project Events</h2>
        </div>
      )}

      {/* Search bar */}
      <div className="mb-5">
        <TimelineSearch onSearch={handleSearch} />
      </div>

      {/* Board content */}
      {loading ? (
        <TimelineSkeleton />
      ) : error ? (
        <div className="flex flex-col items-center justify-center h-[40vh] text-center">
          <p className="text-red-400 text-sm mb-3">{error}</p>
          <button
            onClick={() => fetchTimeline(searchState)}
            className="px-4 py-2 rounded-lg bg-white/5 hover:bg-white/10 text-sm text-white/70 transition-colors"
          >
            Retry
          </button>
        </div>
      ) : items.length === 0 &&
        (searchState.query ||
          searchState.typeFilter ||
          searchState.dateFrom ||
          searchState.dateTo) ? (
        <div className="flex flex-col items-center justify-center h-[40vh] text-center">
          <p className="text-white/40 text-sm mb-2">No matching items found</p>
          <p className="text-white/30 text-xs">Try clearing filters to see all timeline items</p>
        </div>
      ) : (
        <KanbanBoard items={items} onCardClick={handleCardClick} />
      )}

      {/* Node detail modal */}
      <NodeDetailModal
        node={enrichedDetail}
        onClose={handleCloseModal}
        showGraphLink={true}
        onViewInGraph={handleViewInGraph}
      />
    </div>
  );
}
