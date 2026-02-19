"use client";

import { useSearchParams } from "next/navigation";
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

  // Assign layers based on dependency depth
  const layers = new Map<string, number>();

  function getLayer(id: string): number {
    if (layers.has(id)) return layers.get(id)!;
    const deps = depMap.get(id) ?? [];
    const layer =
      deps.length === 0 ? 0 : Math.max(...deps.map(getLayer)) + 1;
    layers.set(id, layer);
    return layer;
  }

  for (const step of steps) getLayer(step.id);

  // Group by layer for row positioning
  const layerGroups = new Map<number, PlanStep[]>();
  for (const step of steps) {
    const l = layers.get(step.id) ?? 0;
    if (!layerGroups.has(l)) layerGroups.set(l, []);
    layerGroups.get(l)!.push(step);
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

// Demo data when no session is provided
const DEMO_STEPS: PlanStep[] = [
  {
    id: "1",
    title: "Requirements Analysis",
    description: "Gather and analyze project requirements",
    agent: "architect",
    status: "completed",
  },
  {
    id: "2",
    title: "System Architecture",
    description: "Design overall system architecture",
    agent: "architect",
    status: "completed",
    depends_on: ["1"],
  },
  {
    id: "3",
    title: "API Design",
    description: "Define API endpoints and contracts",
    agent: "coder",
    status: "active",
    depends_on: ["2"],
  },
  {
    id: "4",
    title: "Database Schema",
    description: "Design database models and migrations",
    agent: "coder",
    status: "active",
    depends_on: ["2"],
  },
  {
    id: "5",
    title: "Frontend Components",
    description: "Build UI component library",
    agent: "coder",
    status: "queued",
    depends_on: ["3"],
  },
  {
    id: "6",
    title: "Testing Suite",
    description: "Write comprehensive test coverage",
    agent: "executor",
    status: "queued",
    depends_on: ["3", "4"],
  },
  {
    id: "7",
    title: "Deployment Pipeline",
    description: "Configure CI/CD and infrastructure",
    agent: "git_manager",
    status: "queued",
    depends_on: ["5", "6"],
  },
];

export default function ArchitecturePage() {
  const searchParams = useSearchParams();
  const sessionId = searchParams.get("session");
  const { getToken } = useAuth();
  const [nodes, setNodes] = useState<GraphNodeData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [nodeLogs] = useState<Record<string, LogLine[]>>({});

  useEffect(() => {
    if (!sessionId) {
      // Demo mode
      setNodes(layoutNodes(DEMO_STEPS));
      setLoading(false);
      return;
    }

    let cancelled = false;

    async function fetchSession() {
      try {
        const res = await apiFetch(
          `/api/agent/sessions/${sessionId}`,
          getToken,
        );
        if (!res.ok) throw new Error(`Failed to fetch session: ${res.status}`);
        const data: SessionData = await res.json();
        if (cancelled) return;

        if (data.plan && data.plan.length > 0) {
          setNodes(layoutNodes(data.plan));
        } else {
          setNodes(layoutNodes(DEMO_STEPS));
        }
      } catch (err) {
        if (cancelled) return;
        setError((err as Error).message);
        setNodes(layoutNodes(DEMO_STEPS));
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

  if (error && nodes.length === 0) {
    return (
      <div className="flex h-[calc(100vh-7rem)] flex-col items-center justify-center gap-3">
        <Network className="h-10 w-10 text-white/20" />
        <p className="text-sm text-white/50">{error}</p>
      </div>
    );
  }

  return (
    <div className="h-[calc(100vh-7rem)] rounded-2xl overflow-hidden glass-strong">
      <GraphCanvas nodes={nodes} nodeLogs={nodeLogs} />
    </div>
  );
}
