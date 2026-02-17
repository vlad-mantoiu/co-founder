"use client";

import { useEffect, useRef } from "react";
import type { GraphNode } from "./ForceGraphInner";

interface GraphMinimapProps {
  nodes: GraphNode[];
}

const NODE_COLORS = {
  decision: "#8B5CF6",
  milestone: "#10B981",
  artifact: "#3B82F6",
} as const;

const MINIMAP_W = 180;
const MINIMAP_H = 120;
const DOT_RADIUS = 3;

export function GraphMinimap({ nodes }: GraphMinimapProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    // Clear canvas
    ctx.clearRect(0, 0, MINIMAP_W, MINIMAP_H);

    const nodesWithPos = nodes.filter(
      (n) => n.x !== undefined && n.y !== undefined,
    );

    if (nodesWithPos.length === 0) return;

    // Compute bounds of positioned nodes
    const xs = nodesWithPos.map((n) => n.x!);
    const ys = nodesWithPos.map((n) => n.y!);
    const minX = Math.min(...xs);
    const maxX = Math.max(...xs);
    const minY = Math.min(...ys);
    const maxY = Math.max(...ys);

    const rangeX = maxX - minX || 1;
    const rangeY = maxY - minY || 1;

    const padding = 10;
    const drawW = MINIMAP_W - padding * 2;
    const drawH = MINIMAP_H - padding * 2;

    // Draw each node as a dot
    for (const node of nodesWithPos) {
      const px = padding + ((node.x! - minX) / rangeX) * drawW;
      const py = padding + ((node.y! - minY) / rangeY) * drawH;

      ctx.beginPath();
      ctx.arc(px, py, DOT_RADIUS, 0, 2 * Math.PI);
      ctx.fillStyle = NODE_COLORS[node.type] ?? "#FFFFFF";
      ctx.globalAlpha = 0.8;
      ctx.fill();
      ctx.globalAlpha = 1.0;
    }
  }, [nodes]);

  return (
    <div className="absolute bottom-4 right-4 z-10 bg-black/60 rounded-lg border border-white/10 p-2">
      <canvas
        ref={canvasRef}
        width={MINIMAP_W}
        height={MINIMAP_H}
        style={{ display: "block" }}
      />
      <div className="flex gap-3 mt-2 px-1">
        <span className="flex items-center gap-1 text-xs text-white/50">
          <span className="w-2 h-2 rounded-full bg-violet-500 inline-block" />
          Decision
        </span>
        <span className="flex items-center gap-1 text-xs text-white/50">
          <span className="w-2 h-2 rounded-full bg-emerald-500 inline-block" />
          Milestone
        </span>
        <span className="flex items-center gap-1 text-xs text-white/50">
          <span className="w-2 h-2 rounded-full bg-blue-500 inline-block" />
          Artifact
        </span>
      </div>
    </div>
  );
}
