"use client";

import { useState, useEffect, useCallback } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { useAuth } from "@clerk/nextjs";
import { KanbanBoard } from "@/components/timeline/KanbanBoard";
import { TimelineSearch, SearchParams } from "@/components/timeline/TimelineSearch";
import { NodeDetailModal, NodeDetail } from "@/components/strategy-graph/NodeDetailModal";
import { TimelineItem } from "@/components/timeline/types";
import { apiFetch } from "@/lib/api";

function buildQueryString(projectId: string, params: SearchParams): string {
  const parts: string[] = [];
  if (params.query) parts.push(`query=${encodeURIComponent(params.query)}`);
  if (params.typeFilter) parts.push(`type_filter=${encodeURIComponent(params.typeFilter)}`);
  if (params.dateFrom) parts.push(`date_from=${encodeURIComponent(params.dateFrom)}`);
  if (params.dateTo) parts.push(`date_to=${encodeURIComponent(params.dateTo)}`);
  const qs = parts.length > 0 ? `?${parts.join("&")}` : "";
  return `/api/timeline/${projectId}${qs}`;
}

function timelineItemToNodeDetail(item: TimelineItem): NodeDetail {
  return {
    id: item.id,
    title: item.title,
    type: item.type,
    status: item.kanban_status,
    created_at: item.timestamp,
    why: item.summary,
    impact_summary: "",
    tradeoffs: [],
    alternatives: [],
  };
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

export default function TimelinePage() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const { getToken } = useAuth();

  const projectId = searchParams.get("project");

  const [items, setItems] = useState<TimelineItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searchState, setSearchState] = useState<SearchParams>({
    query: "",
    typeFilter: null,
    dateFrom: null,
    dateTo: null,
  });
  const [selectedItem, setSelectedItem] = useState<TimelineItem | null>(null);

  const fetchTimeline = useCallback(
    async (params: SearchParams) => {
      if (!projectId) return;
      setLoading(true);
      setError(null);
      try {
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

  const handleCardClick = useCallback((item: TimelineItem) => {
    setSelectedItem(item);
  }, []);

  const handleCloseModal = useCallback(() => {
    setSelectedItem(null);
  }, []);

  const handleViewInGraph = useCallback(
    (nodeId: string) => {
      setSelectedItem(null);
      router.push(`/strategy?project=${projectId}&highlight=${nodeId}`);
    },
    [router, projectId],
  );

  // No project selected
  if (!projectId) {
    return (
      <div className="p-6">
        <div className="mb-6">
          <h1 className="text-2xl font-display font-semibold text-white">Timeline</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Track project events and milestones
          </p>
        </div>
        <div className="flex flex-col items-center justify-center h-[50vh] text-center">
          <div className="w-12 h-12 rounded-xl bg-white/5 flex items-center justify-center mb-4">
            <span className="text-2xl text-white/20">&#9776;</span>
          </div>
          <h3 className="text-lg font-medium text-white/60">No project selected</h3>
          <p className="text-sm text-white/30 mt-1 mb-4">
            Select a project to view its timeline
          </p>
          <button
            onClick={() => router.push("/projects")}
            className="px-4 py-2 rounded-lg bg-brand/20 text-brand hover:bg-brand/30 text-sm font-medium transition-colors"
          >
            Go to Projects
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6">
      {/* Page header */}
      <div className="mb-6">
        <h1 className="text-2xl font-display font-semibold text-white">Timeline</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Track project events and milestones
        </p>
      </div>

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
        node={selectedItem ? timelineItemToNodeDetail(selectedItem) : null}
        onClose={handleCloseModal}
        showGraphLink={true}
        onViewInGraph={handleViewInGraph}
      />
    </div>
  );
}
