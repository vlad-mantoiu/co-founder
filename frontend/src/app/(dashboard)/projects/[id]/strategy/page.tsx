"use client";

import { useState, useEffect, useCallback } from "react";
import { useSearchParams, useParams } from "next/navigation";
import { useAuth } from "@clerk/nextjs";
import { GitBranch, AlertCircle, RefreshCw } from "lucide-react";
import { StrategyGraphCanvas, type GraphNode, type GraphLink } from "@/components/strategy-graph/StrategyGraphCanvas";
import { NodeDetailModal, type NodeDetail } from "@/components/strategy-graph/NodeDetailModal";
import { apiFetch } from "@/lib/api";

interface ApiEdge {
  from: string;
  to: string;
  relation: string;
}

interface GraphResponse {
  nodes: GraphNode[];
  edges: ApiEdge[];
}

interface StrategyArtifactContent {
  nodes: Array<{
    id: string;
    type: string;
    label: string;
    status: string;
    description?: string;
  }>;
  edges: Array<{
    source: string;
    target: string;
    relation: string;
  }>;
  anchor_phrases?: string[];
}

function GraphPageSkeleton() {
  return (
    <div className="w-full h-[calc(100vh-12rem)] flex items-center justify-center">
      <div className="space-y-4 w-full max-w-md px-8 text-center">
        <div className="flex justify-center gap-8 mb-8">
          <div className="w-16 h-16 rounded-full bg-violet-500/10 animate-pulse" />
          <div className="w-16 h-16 rounded-full bg-emerald-500/10 animate-pulse" />
          <div className="w-16 h-16 rounded-full bg-blue-500/10 animate-pulse" />
        </div>
        <div className="h-3 bg-white/10 rounded animate-pulse w-3/4 mx-auto" />
        <div className="h-3 bg-white/10 rounded animate-pulse w-1/2 mx-auto" />
        <p className="text-xs text-white/30 mt-4">Loading strategy graph...</p>
      </div>
    </div>
  );
}

function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center h-[60vh] text-center">
      <GitBranch className="w-12 h-12 text-white/20 mb-4" />
      <h3 className="text-lg font-medium text-white/60">No strategy data yet</h3>
      <p className="text-sm text-muted-foreground mt-1">
        Decision nodes will appear here as you make project decisions
      </p>
    </div>
  );
}

/**
 * Project-scoped Strategy Graph page.
 *
 * Dual-mode: shows artifact-based force graph (anchor + strategy nodes) when
 * a strategy_graph artifact is available, falls back to Neo4j graph otherwise.
 *
 * Reads projectId from URL path segment (params.id).
 * Reads highlight node from searchParams.get("highlight").
 */
export default function ProjectStrategyPage() {
  const params = useParams<{ id: string }>();
  const searchParams = useSearchParams();
  const { getToken } = useAuth();

  // projectId from URL path segment — always present
  const projectId = params.id;
  // highlight from query param — optional, used when navigating from timeline
  const highlightId = searchParams.get("highlight");

  const [graphData, setGraphData] = useState<{ nodes: GraphNode[]; links: GraphLink[] }>({ nodes: [], links: [] });
  const [selectedNode, setSelectedNode] = useState<NodeDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // Holds the strategy artifact content when available (null = using Neo4j fallback)
  const [artifactGraph, setArtifactGraph] = useState<StrategyArtifactContent | null>(null);

  const fetchAndOpenNode = useCallback(async (nodeId: string) => {
    try {
      const res = await apiFetch(`/api/graph/${projectId}/nodes/${nodeId}`, getToken);
      if (!res.ok) return;
      const detail = await res.json();
      setSelectedNode({
        id: detail.id,
        title: detail.title,
        type: detail.type,
        status: detail.status,
        created_at: detail.created_at,
        why: detail.why ?? "",
        impact_summary: detail.impact_summary ?? "",
        tradeoffs: detail.tradeoffs ?? [],
        alternatives: detail.alternatives ?? [],
      });
    } catch {
      // Non-fatal
    }
  }, [projectId, getToken]);

  const fetchGraph = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      // FIRST: try to fetch the strategy_graph artifact
      const artifactRes = await apiFetch(`/api/artifacts/project/${projectId}`, getToken);
      if (artifactRes.ok) {
        const artifacts = await artifactRes.json();
        const strategyArtifact = artifacts.find(
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          (a: any) => a.artifact_type === "strategy_graph" && a.generation_status === "idle" && a.current_content
        );
        if (strategyArtifact) {
          const content: StrategyArtifactContent = strategyArtifact.current_content;
          const nodes: GraphNode[] = (content.nodes || []).map((n) => ({
            id: n.id,
            type: n.type as GraphNode["type"],
            title: n.label,
            label: n.label,
            status: n.status,
            description: n.description,
          }));
          const links: GraphLink[] = (content.edges || []).map((e) => ({
            source: e.source,
            target: e.target,
            relation: e.relation,
          }));
          setArtifactGraph(content);
          setGraphData({ nodes, links });
          setLoading(false);
          return; // Skip Neo4j fetch
        }
      }

      // FALLBACK: fetch from Neo4j graph API (existing behavior)
      setArtifactGraph(null);
      const res = await apiFetch(`/api/graph/${projectId}`, getToken);
      if (!res.ok) {
        throw new Error(`Failed to load graph (${res.status})`);
      }
      const data: GraphResponse = await res.json();
      const mappedLinks: GraphLink[] = (data.edges ?? []).map((e: ApiEdge) => ({
        source: e.from,
        target: e.to,
        relation: e.relation,
      }));
      setGraphData({ nodes: data.nodes ?? [], links: mappedLinks });

      // Auto-open highlighted node if navigated from timeline
      if (highlightId && data.nodes) {
        const target = data.nodes.find((n: GraphNode) => n.id === highlightId);
        if (target) {
          fetchAndOpenNode(highlightId);
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load graph");
    } finally {
      setLoading(false);
    }
  }, [projectId, getToken, highlightId, fetchAndOpenNode]);

  useEffect(() => {
    fetchGraph();
  }, [fetchGraph]);

  const handleNodeClick = useCallback((node: GraphNode) => {
    fetchAndOpenNode(node.id);
  }, [fetchAndOpenNode]);

  const handleCloseModal = useCallback(() => {
    setSelectedNode(null);
  }, []);

  return (
    <div className="p-6">
      {/* Page header */}
      <div className="mb-6">
        <h1 className="text-2xl font-display font-semibold text-white">Strategy Graph</h1>
        <p className="text-sm text-muted-foreground mt-1">
          {artifactGraph
            ? "Your strategy — built from your answers"
            : "Decision relationships and project evolution"}
        </p>
      </div>

      {/* Anchor phrases tag list — shown when displaying artifact graph */}
      {artifactGraph && artifactGraph.anchor_phrases && artifactGraph.anchor_phrases.length > 0 && (
        <div className="flex flex-wrap gap-2 mb-4">
          {artifactGraph.anchor_phrases.map((phrase: string, i: number) => (
            <span
              key={i}
              className="text-xs px-2 py-1 rounded-full bg-amber-500/10 text-amber-400 border border-amber-500/20"
            >
              &quot;{phrase}&quot;
            </span>
          ))}
        </div>
      )}

      {/* Graph content */}
      {loading ? (
        <GraphPageSkeleton />
      ) : error ? (
        <div className="flex flex-col items-center justify-center h-[40vh] text-center">
          <AlertCircle className="w-10 h-10 text-red-400/60 mb-3" />
          <p className="text-red-400 text-sm mb-3">{error}</p>
          <button
            onClick={fetchGraph}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-white/5 hover:bg-white/10 text-sm text-white/70 transition-colors"
          >
            <RefreshCw className="w-4 h-4" />
            Retry
          </button>
        </div>
      ) : graphData.nodes.length === 0 ? (
        <EmptyState />
      ) : (
        <StrategyGraphCanvas
          nodes={graphData.nodes}
          links={graphData.links}
          onNodeClick={handleNodeClick}
        />
      )}

      {/* Node detail modal */}
      <NodeDetailModal
        node={selectedNode}
        onClose={handleCloseModal}
        showGraphLink={false}
      />
    </div>
  );
}
