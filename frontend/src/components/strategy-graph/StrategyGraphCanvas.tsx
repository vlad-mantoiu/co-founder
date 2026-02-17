"use client";

import dynamic from "next/dynamic";
import type { GraphNode, GraphLink } from "./ForceGraphInner";
import { GraphMinimap } from "./GraphMinimap";

// Dynamic import with ssr:false for canvas-based ForceGraph2D
const ForceGraphInner = dynamic(() => import("./ForceGraphInner"), {
  ssr: false,
  loading: () => <GraphLoadingSkeleton />,
});

function GraphLoadingSkeleton() {
  return (
    <div className="w-full h-full flex items-center justify-center">
      <div className="space-y-4 w-full max-w-md px-8">
        <div className="h-4 bg-white/10 rounded animate-pulse" />
        <div className="h-4 bg-white/10 rounded animate-pulse w-3/4 mx-auto" />
        <div className="h-4 bg-white/10 rounded animate-pulse w-1/2 mx-auto" />
        <div className="flex justify-center gap-8 mt-8">
          <div className="w-16 h-16 rounded-full bg-violet-500/20 animate-pulse" />
          <div className="w-16 h-16 rounded-full bg-emerald-500/20 animate-pulse" />
          <div className="w-16 h-16 rounded-full bg-blue-500/20 animate-pulse" />
        </div>
      </div>
    </div>
  );
}

interface StrategyGraphCanvasProps {
  nodes: GraphNode[];
  links: GraphLink[];
  onNodeClick: (node: GraphNode) => void;
}

export function StrategyGraphCanvas({
  nodes,
  links,
  onNodeClick,
}: StrategyGraphCanvasProps) {
  return (
    <div className="relative w-full h-[calc(100vh-12rem)]">
      <ForceGraphInner nodes={nodes} links={links} onNodeClick={onNodeClick} />
      <GraphMinimap nodes={nodes} />
    </div>
  );
}

export type { GraphNode, GraphLink };
