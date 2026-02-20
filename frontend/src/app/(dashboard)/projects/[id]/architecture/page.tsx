"use client";

import Link from "next/link";
import { useSearchParams, useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { useAuth } from "@clerk/nextjs";
import { Loader2, Network } from "lucide-react";
import { apiFetch } from "@/lib/api";
import { GraphCanvas } from "@/components/graph/GraphCanvas";
import type { GraphNodeData, GraphNodeStatus } from "@/components/graph/GraphNode";
import type { LogLine } from "@/components/chat/types";
import { AppArchitectureView } from "@/components/architecture/AppArchitectureView";
import type { AppArchitectureViewProps } from "@/components/architecture/AppArchitectureView";

interface PlanStep {
  id: string;
  title: string;
  description?: string;
  agent?: string;
  status?: string;
  depends_on?: string[];
}

interface SessionData {
  session_id: string;
  plan?: PlanStep[];
}

const COL_GAP = 320;
const ROW_GAP = 140;
const START_X = 80;
const START_Y = 80;

function layoutNodes(steps: PlanStep[]): GraphNodeData[] {
  const depMap = new Map<string, string[]>();
  for (const step of steps) {
    depMap.set(step.id, step.depends_on ?? []);
  }

  const layers = new Map<string, number>();

  function getLayer(id: string): number {
    if (layers.has(id)) return layers.get(id)!;
    const deps = depMap.get(id) ?? [];
    const layer = deps.length === 0 ? 0 : Math.max(...deps.map(getLayer)) + 1;
    layers.set(id, layer);
    return layer;
  }

  for (const step of steps) getLayer(step.id);

  const layerGroups = new Map<number, PlanStep[]>();
  for (const step of steps) {
    const layer = layers.get(step.id) ?? 0;
    if (!layerGroups.has(layer)) layerGroups.set(layer, []);
    layerGroups.get(layer)!.push(step);
  }

  return steps.map((step) => {
    const layer = layers.get(step.id) ?? 0;
    const group = layerGroups.get(layer) ?? [];
    const indexInGroup = group.indexOf(step);

    const statusMap: Record<string, GraphNodeStatus> = {
      completed: "completed",
      active: "active",
      pending: "queued",
      queued: "queued",
    };

    return {
      id: step.id,
      label: step.title,
      description: step.description,
      agent: step.agent,
      status: statusMap[step.status ?? "queued"] ?? "queued",
      x: START_X + layer * COL_GAP,
      y: START_Y + indexInGroup * ROW_GAP,
      connections: step.depends_on ?? [],
    };
  });
}

export default function ProjectArchitecturePage() {
  const params = useParams<{ id: string }>();
  const searchParams = useSearchParams();
  const { getToken } = useAuth();

  const projectId = params.id;
  const sessionId = searchParams.get("session");

  const [nodes, setNodes] = useState<GraphNodeData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [nodeLogs] = useState<Record<string, LogLine[]>>({});
  const [architectureData, setArchitectureData] = useState<AppArchitectureViewProps | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function fetchData() {
      try {
        // Always fetch artifact data (shown when no ?session param)
        const artifactRes = await apiFetch(`/api/artifacts/project/${projectId}`, getToken);
        if (artifactRes.ok) {
          const artifacts = await artifactRes.json();
          const archArtifact = artifacts.find(
            (a: { artifact_type: string; generation_status: string; current_content: AppArchitectureViewProps | null }) =>
              a.artifact_type === "app_architecture" &&
              a.generation_status === "idle" &&
              a.current_content
          );
          if (archArtifact && !cancelled) {
            setArchitectureData(archArtifact.current_content);
          }
        }

        // If we have a session param, also load the session graph
        if (sessionId) {
          const res = await apiFetch(`/api/agent/sessions/${sessionId}`, getToken);
          if (!res.ok) throw new Error(`Failed to fetch session: ${res.status}`);
          const data: SessionData = await res.json();
          if (cancelled) return;
          setNodes(data.plan && data.plan.length > 0 ? layoutNodes(data.plan) : []);
        }
      } catch (err) {
        if (cancelled) return;
        setError((err as Error).message);
        setNodes([]);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    fetchData();
    return () => {
      cancelled = true;
    };
  }, [sessionId, projectId, getToken]);

  if (loading) {
    return (
      <div className="flex h-[calc(100vh-7rem)] items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-brand" />
      </div>
    );
  }

  // Session mode: ?session= param provided — show build session graph
  if (sessionId) {
    if (error && nodes.length === 0) {
      return (
        <div className="flex h-[calc(100vh-7rem)] flex-col items-center justify-center gap-4 text-center">
          <Network className="h-10 w-10 text-white/20" />
          <div className="space-y-1">
            <p className="text-base text-white/70">Could not load architecture</p>
            <p className="text-sm text-white/40">{error}</p>
          </div>
          <div className="flex items-center gap-3">
            <Link
              href={`/projects/${projectId}`}
              className="px-4 py-2 rounded-lg bg-white/5 text-white/70 hover:bg-white/10 transition-colors text-sm"
            >
              Back to Project
            </Link>
            <Link
              href={`/projects/${projectId}/build`}
              className="px-4 py-2 rounded-lg bg-brand/20 text-brand hover:bg-brand/30 transition-colors text-sm"
            >
              Go to Build
            </Link>
          </div>
        </div>
      );
    }

    if (nodes.length === 0) {
      return (
        <div className="flex h-[calc(100vh-7rem)] flex-col items-center justify-center gap-4 text-center">
          <Network className="h-10 w-10 text-white/20" />
          <div className="space-y-1">
            <p className="text-base text-white/70">No architecture data yet</p>
            <p className="text-sm text-white/40">
              Build activity has not produced a graph for this session yet.
            </p>
          </div>
          <div className="flex items-center gap-3">
            <Link
              href={`/projects/${projectId}`}
              className="px-4 py-2 rounded-lg bg-white/5 text-white/70 hover:bg-white/10 transition-colors text-sm"
            >
              Back to Project
            </Link>
            <Link
              href={`/projects/${projectId}/build`}
              className="px-4 py-2 rounded-lg bg-brand/20 text-brand hover:bg-brand/30 transition-colors text-sm"
            >
              Go to Build
            </Link>
          </div>
        </div>
      );
    }

    return (
      <div className="h-[calc(100vh-7rem)] rounded-2xl overflow-hidden glass-strong">
        <GraphCanvas nodes={nodes} nodeLogs={nodeLogs} />
      </div>
    );
  }

  // Artifact mode: show personalized tech stack from artifact
  if (architectureData) {
    return (
      <div className="max-w-5xl mx-auto">
        <div className="mb-6 px-6 pt-6">
          <h1 className="text-2xl font-semibold text-white">Your App Architecture</h1>
          <p className="text-sm text-white/50 mt-1">
            Personalized tech stack recommendations and cost estimates based on your idea.
          </p>
        </div>
        <AppArchitectureView
          components={architectureData.components}
          connections={architectureData.connections}
          costEstimate={architectureData.costEstimate}
          integrationRecommendations={architectureData.integrationRecommendations}
        />
      </div>
    );
  }

  // Empty state: no artifact and no session
  return (
    <div className="flex h-[calc(100vh-7rem)] flex-col items-center justify-center gap-4 text-center">
      <Network className="h-10 w-10 text-white/20" />
      <div className="space-y-1">
        <p className="text-base text-white/70">No architecture recommendation yet</p>
        <p className="text-sm text-white/40">
          Complete the Understanding Interview to see your personalized architecture recommendation.
        </p>
      </div>
      <div className="flex items-center gap-3">
        <Link
          href={`/projects/${projectId}`}
          className="px-4 py-2 rounded-lg bg-white/5 text-white/70 hover:bg-white/10 transition-colors text-sm"
        >
          Back to Project
        </Link>
        <Link
          href={`/projects/${projectId}/understanding`}
          className="px-4 py-2 rounded-lg bg-brand/20 text-brand hover:bg-brand/30 transition-colors text-sm"
        >
          Start Understanding Interview
        </Link>
      </div>
    </div>
  );
}
