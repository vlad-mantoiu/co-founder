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

  useEffect(() => {
    let cancelled = false;

    async function fetchSession() {
      if (!sessionId) {
        setNodes([]);
        setLoading(false);
        return;
      }

      try {
        const res = await apiFetch(`/api/agent/sessions/${sessionId}`, getToken);
        if (!res.ok) throw new Error(`Failed to fetch session: ${res.status}`);
        const data: SessionData = await res.json();
        if (cancelled) return;
        setNodes(data.plan && data.plan.length > 0 ? layoutNodes(data.plan) : []);
      } catch (err) {
        if (cancelled) return;
        setError((err as Error).message);
        setNodes([]);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    fetchSession();
    return () => {
      cancelled = true;
    };
  }, [sessionId, getToken]);

  if (loading) {
    return (
      <div className="flex h-[calc(100vh-7rem)] items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-brand" />
      </div>
    );
  }

  if (!sessionId) {
    return (
      <div className="flex h-[calc(100vh-7rem)] flex-col items-center justify-center gap-4 text-center">
        <Network className="h-10 w-10 text-white/20" />
        <div className="space-y-1">
          <p className="text-base text-white/70">No architecture session selected</p>
          <p className="text-sm text-white/40">
            Open architecture from a project build flow when a session is available.
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
