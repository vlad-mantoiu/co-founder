"use client";

import type { GraphNodeData } from "./GraphNode";

interface GraphConnectionsProps {
  nodes: GraphNodeData[];
}

const NODE_WIDTH = 224;
const NODE_HEIGHT = 80;

export function GraphConnections({ nodes }: GraphConnectionsProps) {
  const nodeMap = new Map(nodes.map((n) => [n.id, n]));

  const edges: {
    from: GraphNodeData;
    to: GraphNodeData;
    status: "completed" | "active" | "pending";
  }[] = [];

  for (const node of nodes) {
    for (const targetId of node.connections) {
      const target = nodeMap.get(targetId);
      if (!target) continue;

      let status: "completed" | "active" | "pending" = "pending";
      if (node.status === "completed" && target.status === "completed") {
        status = "completed";
      } else if (node.status === "completed" && target.status === "active") {
        status = "active";
      }

      edges.push({ from: node, to: target, status });
    }
  }

  return (
    <svg className="pointer-events-none absolute inset-0 h-full w-full">
      {edges.map(({ from, to, status }) => {
        const x1 = from.x + NODE_WIDTH;
        const y1 = from.y + NODE_HEIGHT / 2;
        const x2 = to.x;
        const y2 = to.y + NODE_HEIGHT / 2;

        const cx1 = x1 + (x2 - x1) * 0.4;
        const cx2 = x2 - (x2 - x1) * 0.4;

        const path = `M ${x1} ${y1} C ${cx1} ${y1}, ${cx2} ${y2}, ${x2} ${y2}`;

        return (
          <path
            key={`${from.id}-${to.id}`}
            d={path}
            fill="none"
            strokeWidth={2}
            className={
              status === "completed"
                ? "stroke-white/10"
                : status === "active"
                  ? "stroke-brand"
                  : "stroke-white/10 [stroke-dasharray:6,4]"
            }
          />
        );
      })}
    </svg>
  );
}
