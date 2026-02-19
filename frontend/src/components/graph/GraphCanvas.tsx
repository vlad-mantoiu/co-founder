"use client";

import { useState, useRef, useCallback, useEffect } from "react";
import { GraphNode, type GraphNodeData } from "./GraphNode";
import { GraphConnections } from "./GraphConnections";
import { GraphToolbar } from "./GraphToolbar";
import { GraphMinimap, type MinimapNode } from "./GraphMinimap";
import { NodeDetailPanel } from "./NodeDetailPanel";
import type { LogLine } from "@/components/chat/types";

interface GraphCanvasProps {
  nodes: GraphNodeData[];
  nodeLogs?: Record<string, LogLine[]>;
  nodeFiles?: Record<string, string[]>;
  nodeConsiderations?: Record<string, string[]>;
}

const MIN_ZOOM = 0.3;
const MAX_ZOOM = 2;
const ZOOM_STEP = 0.15;

export function GraphCanvas({
  nodes,
  nodeLogs = {},
  nodeFiles = {},
  nodeConsiderations = {},
}: GraphCanvasProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [offset, setOffset] = useState({ x: 0, y: 0 });
  const [zoom, setZoom] = useState(1);
  const [dragging, setDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
  const [logicPaths, setLogicPaths] = useState(false);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [containerSize, setContainerSize] = useState({ w: 1200, h: 800 });

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const ro = new ResizeObserver(([entry]) => {
      setContainerSize({
        w: entry.contentRect.width,
        h: entry.contentRect.height,
      });
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const handleMouseDown = useCallback(
    (e: React.MouseEvent) => {
      if (e.button !== 0) return;
      setDragging(true);
      setDragStart({ x: e.clientX - offset.x, y: e.clientY - offset.y });
    },
    [offset],
  );

  const handleMouseMove = useCallback(
    (e: React.MouseEvent) => {
      if (!dragging) return;
      setOffset({
        x: e.clientX - dragStart.x,
        y: e.clientY - dragStart.y,
      });
    },
    [dragging, dragStart],
  );

  const handleMouseUp = useCallback(() => {
    setDragging(false);
  }, []);

  const handleWheel = useCallback((e: React.WheelEvent) => {
    e.preventDefault();
    setZoom((z) => {
      const next = z - e.deltaY * 0.001;
      return Math.max(MIN_ZOOM, Math.min(MAX_ZOOM, next));
    });
  }, []);

  const zoomIn = useCallback(
    () => setZoom((z) => Math.min(MAX_ZOOM, z + ZOOM_STEP)),
    [],
  );
  const zoomOut = useCallback(
    () => setZoom((z) => Math.max(MIN_ZOOM, z - ZOOM_STEP)),
    [],
  );
  const recenter = useCallback(() => {
    setOffset({ x: 0, y: 0 });
    setZoom(1);
  }, []);

  const selectedNode = nodes.find((n) => n.id === selectedId) ?? null;

  const canvasWidth = Math.max(
    1200,
    ...nodes.map((n) => n.x + 300),
  );
  const canvasHeight = Math.max(
    800,
    ...nodes.map((n) => n.y + 200),
  );

  const minimapNodes: MinimapNode[] = nodes.map((n) => ({
    id: n.id,
    x: n.x + 112,
    y: n.y + 40,
    status: n.status,
  }));

  return (
    <div className="relative h-full w-full overflow-hidden bg-obsidian">
      {/* Grid background */}
      <div
        className="absolute inset-0"
        style={{
          backgroundImage:
            "linear-gradient(rgba(255,255,255,0.03) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.03) 1px, transparent 1px)",
          backgroundSize: "40px 40px",
          backgroundPosition: `${offset.x}px ${offset.y}px`,
        }}
      />

      {/* Pannable / zoomable area */}
      <div
        ref={containerRef}
        className="absolute inset-0"
        style={{ cursor: dragging ? "grabbing" : "grab" }}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
        onWheel={handleWheel}
      >
        <div
          style={{
            transform: `translate(${offset.x}px, ${offset.y}px) scale(${zoom})`,
            transformOrigin: "0 0",
            width: canvasWidth,
            height: canvasHeight,
            position: "relative",
          }}
        >
          <GraphConnections nodes={logicPaths ? nodes : nodes} />
          {nodes.map((node) => (
            <GraphNode
              key={node.id}
              node={node}
              selected={node.id === selectedId}
              onClick={setSelectedId}
            />
          ))}
        </div>
      </div>

      {/* Overlays */}
      <GraphToolbar
        onZoomIn={zoomIn}
        onZoomOut={zoomOut}
        onRecenter={recenter}
        logicPaths={logicPaths}
        onToggleLogicPaths={() => setLogicPaths(!logicPaths)}
      />

      <GraphMinimap
        nodes={minimapNodes}
        viewportX={offset.x}
        viewportY={offset.y}
        viewportWidth={containerSize.w}
        viewportHeight={containerSize.h}
        canvasWidth={canvasWidth}
        canvasHeight={canvasHeight}
      />

      {/* Detail panel */}
      <NodeDetailPanel
        node={selectedNode}
        logs={selectedId ? (nodeLogs[selectedId] ?? []) : []}
        files={selectedId ? (nodeFiles[selectedId] ?? []) : []}
        considerations={
          selectedId ? (nodeConsiderations[selectedId] ?? []) : []
        }
        onClose={() => setSelectedId(null)}
      />
    </div>
  );
}
