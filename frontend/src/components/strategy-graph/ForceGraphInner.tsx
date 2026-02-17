"use client";

import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import ForceGraph2D from "react-force-graph-2d";
import type { ForceGraphMethods } from "react-force-graph-2d";

export interface GraphNode {
  id: string;
  type: "decision" | "milestone" | "artifact";
  title: string;
  status: string;
  x?: number;
  y?: number;
}

export interface GraphLink {
  source: string;
  target: string;
  relation: string;
}

interface ForceGraphInnerProps {
  nodes: GraphNode[];
  links: GraphLink[];
  onNodeClick: (node: GraphNode) => void;
}

const NODE_COLORS = {
  decision: "#8B5CF6", // violet
  milestone: "#10B981", // emerald
  artifact: "#3B82F6", // blue
} as const;

const HIGHLIGHT_COLOR = "#F59E0B"; // amber hover ring
const DIM_OPACITY = 0.2;
const NODE_RADIUS = 8;

function getNodeId(node: string | { id: string }): string {
  return typeof node === "object" ? node.id : node;
}

export default function ForceGraphInner({
  nodes,
  links,
  onNodeClick,
}: ForceGraphInnerProps) {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const graphRef = useRef<ForceGraphMethods<any, any>>(undefined);
  const containerRef = useRef<HTMLDivElement>(null);
  const [hoverNode, setHoverNode] = useState<GraphNode | null>(null);
  const [dimensions, setDimensions] = useState({ width: 800, height: 600 });

  // Measure container dimensions
  useEffect(() => {
    if (!containerRef.current) return;

    const observer = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const { width, height } = entry.contentRect;
        setDimensions({ width, height });
      }
    });

    observer.observe(containerRef.current);

    // Set initial dimensions
    const rect = containerRef.current.getBoundingClientRect();
    if (rect.width > 0 && rect.height > 0) {
      setDimensions({ width: rect.width, height: rect.height });
    }

    return () => observer.disconnect();
  }, []);

  // ZoomToFit on initial load
  useEffect(() => {
    if (nodes.length === 0) return;
    const timer = setTimeout(() => {
      graphRef.current?.zoomToFit(400, 40);
    }, 300);
    return () => clearTimeout(timer);
  }, [nodes.length]);

  // Build adjacency highlight sets on hover
  const { highlightNodes, highlightLinks } = useMemo(() => {
    if (!hoverNode) {
      return {
        highlightNodes: new Set<string>(),
        highlightLinks: new Set<string>(),
      };
    }

    const hnodes = new Set<string>([hoverNode.id]);
    const hlinks = new Set<string>();

    for (const link of links) {
      const srcId = getNodeId(link.source as string | { id: string });
      const tgtId = getNodeId(link.target as string | { id: string });

      if (srcId === hoverNode.id || tgtId === hoverNode.id) {
        hnodes.add(srcId);
        hnodes.add(tgtId);
        hlinks.add(`${srcId}-${tgtId}`);
      }
    }

    return { highlightNodes: hnodes, highlightLinks: hlinks };
  }, [hoverNode, links]);

  const graphData = useMemo(
    () => ({ nodes: [...nodes], links: [...links] }),
    [nodes, links],
  );

  // Custom node canvas rendering
  const nodeCanvasObject = useCallback(
    (
      node: GraphNode & { x?: number; y?: number },
      ctx: CanvasRenderingContext2D,
      globalScale: number,
    ) => {
      const x = node.x ?? 0;
      const y = node.y ?? 0;
      const isHovered = hoverNode?.id === node.id;
      const hasHover = hoverNode !== null;
      const isHighlighted = !hasHover || highlightNodes.has(node.id);
      const color = NODE_COLORS[node.type] ?? "#FFFFFF";

      // Dim non-highlighted nodes
      ctx.globalAlpha = isHighlighted ? 1.0 : DIM_OPACITY;

      // Draw node circle
      ctx.beginPath();
      ctx.arc(x, y, NODE_RADIUS, 0, 2 * Math.PI);
      ctx.fillStyle = color;
      ctx.fill();

      // Draw amber ring on hovered node
      if (isHovered) {
        ctx.beginPath();
        ctx.arc(x, y, NODE_RADIUS + 3, 0, 2 * Math.PI);
        ctx.strokeStyle = HIGHLIGHT_COLOR;
        ctx.lineWidth = 2;
        ctx.stroke();
      }

      // Draw label when zoomed in enough
      if (globalScale > 1.5) {
        const label = node.title;
        ctx.font = `${12 / globalScale}px Inter, sans-serif`;
        ctx.fillStyle = "rgba(255,255,255,0.9)";
        ctx.textAlign = "center";
        ctx.textBaseline = "top";
        ctx.fillText(label, x, y + NODE_RADIUS + 2);
      }

      // Reset alpha
      ctx.globalAlpha = 1.0;
    },
    [hoverNode, highlightNodes],
  );

  const getLinkColor = useCallback(
    (link: GraphLink) => {
      if (!hoverNode) return "rgba(255,255,255,0.1)";
      const srcId = getNodeId(link.source as string | { id: string });
      const tgtId = getNodeId(link.target as string | { id: string });
      return highlightLinks.has(`${srcId}-${tgtId}`)
        ? HIGHLIGHT_COLOR
        : "rgba(255,255,255,0.05)";
    },
    [hoverNode, highlightLinks],
  );

  const getLinkWidth = useCallback(
    (link: GraphLink) => {
      if (!hoverNode) return 1;
      const srcId = getNodeId(link.source as string | { id: string });
      const tgtId = getNodeId(link.target as string | { id: string });
      return highlightLinks.has(`${srcId}-${tgtId}`) ? 2 : 1;
    },
    [hoverNode, highlightLinks],
  );

  return (
    <div ref={containerRef} className="w-full h-full">
      <ForceGraph2D
        ref={graphRef as React.MutableRefObject<ForceGraphMethods<any, any>>}
        graphData={graphData}
        nodeCanvasObject={nodeCanvasObject}
        nodeCanvasObjectMode={() => "replace"}
        onNodeClick={(node) => onNodeClick(node as GraphNode)}
        onNodeHover={(node) => setHoverNode(node as GraphNode | null)}
        linkColor={getLinkColor as (link: object) => string}
        linkWidth={getLinkWidth as (link: object) => number}
        linkDirectionalArrowLength={4}
        linkDirectionalArrowRelPos={1}
        enableZoomInteraction={true}
        enablePanInteraction={true}
        backgroundColor="transparent"
        width={dimensions.width}
        height={dimensions.height}
      />
    </div>
  );
}
