"use client";

import { cn } from "@/lib/utils";

export interface MinimapNode {
  id: string;
  x: number;
  y: number;
  status: "completed" | "active" | "queued" | "inactive";
}

interface GraphMinimapProps {
  nodes: MinimapNode[];
  viewportX: number;
  viewportY: number;
  viewportWidth: number;
  viewportHeight: number;
  canvasWidth: number;
  canvasHeight: number;
}

const STATUS_COLORS: Record<MinimapNode["status"], string> = {
  completed: "bg-neon-green",
  active: "bg-brand",
  queued: "bg-white/30",
  inactive: "bg-white/10",
};

export function GraphMinimap({
  nodes,
  viewportX,
  viewportY,
  viewportWidth,
  viewportHeight,
  canvasWidth,
  canvasHeight,
}: GraphMinimapProps) {
  const scale = 0.08;
  const mapW = canvasWidth * scale;
  const mapH = canvasHeight * scale;

  return (
    <div
      className="absolute bottom-4 left-4 z-10 glass rounded-xl overflow-hidden"
      style={{ width: mapW, height: mapH }}
    >
      {/* Node dots */}
      {nodes.map((node) => (
        <div
          key={node.id}
          className={cn("absolute h-2 w-2 rounded-full", STATUS_COLORS[node.status])}
          style={{
            left: node.x * scale - 4,
            top: node.y * scale - 4,
          }}
        />
      ))}

      {/* Viewport rectangle */}
      <div
        className="absolute border border-brand/50 bg-brand/5 rounded-sm"
        style={{
          left: -viewportX * scale,
          top: -viewportY * scale,
          width: viewportWidth * scale,
          height: viewportHeight * scale,
        }}
      />
    </div>
  );
}
