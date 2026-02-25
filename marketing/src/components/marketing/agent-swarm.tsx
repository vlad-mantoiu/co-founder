"use client";

import { useRef, useLayoutEffect, useState, useCallback } from "react";
import {
  Network,
  Landmark,
  Terminal,
  Bug,
  ClipboardCheck,
  Puzzle,
} from "lucide-react";

interface Point {
  x: number;
  y: number;
}

const AGENTS = [
  { id: "architect", label: "Architect", icon: Landmark, color: "text-sky-400" },
  { id: "developer", label: "Developer", icon: Terminal, color: "text-emerald-400" },
  { id: "tester", label: "Tester", icon: Bug, color: "text-purple-400" },
  { id: "reviewer", label: "Reviewer", icon: ClipboardCheck, color: "text-orange-400" },
  { id: "integration", label: "Integration", icon: Puzzle, color: "text-pink-400" },
] as const;

/** Returns the center of `el` relative to `container`. */
function centerOf(el: HTMLElement, container: HTMLElement): Point {
  const eR = el.getBoundingClientRect();
  const cR = container.getBoundingClientRect();
  return {
    x: eR.left - cR.left + eR.width / 2,
    y: eR.top - cR.top + eR.height / 2,
  };
}

export function AgentSwarm() {
  const containerRef = useRef<HTMLDivElement>(null);
  const coreRef = useRef<HTMLDivElement>(null);
  const nodeRefs = useRef<Record<string, HTMLDivElement | null>>({});

  const [lines, setLines] = useState<{ from: Point; to: Point; id: string }[]>(
    [],
  );

  const measure = useCallback(() => {
    const container = containerRef.current;
    const core = coreRef.current;
    if (!container || !core) return;

    const coreCenter = centerOf(core, container);
    const next: typeof lines = [];

    for (const agent of AGENTS) {
      const el = nodeRefs.current[agent.id];
      if (!el) continue;
      next.push({
        id: agent.id,
        from: coreCenter,
        to: centerOf(el, container),
      });
    }

    setLines(next);
  }, []);

  useLayoutEffect(() => {
    measure();

    const container = containerRef.current;
    if (!container) return;

    const ro = new ResizeObserver(measure);
    ro.observe(container);
    return () => ro.disconnect();
  }, [measure]);

  return (
    <div className="glass-strong rounded-2xl p-8 relative h-full">
      <h3 className="text-sm font-bold uppercase tracking-wider text-white/30 mb-6">
        Agent Swarm Cluster
      </h3>

      <div ref={containerRef} className="relative w-full h-[320px]">
        {/* Dynamic connection lines */}
        <svg className="absolute inset-0 w-full h-full pointer-events-none z-0">
          {lines.map((l) => (
            <line
              key={l.id}
              x1={l.from.x}
              y1={l.from.y}
              x2={l.to.x}
              y2={l.to.y}
              stroke="#6467f2"
              strokeWidth="1.5"
              opacity="0.3"
            />
          ))}
        </svg>

        {/* Central node */}
        <div
          ref={coreRef}
          className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 z-10 flex flex-col items-center gap-2"
        >
          <div className="w-20 h-20 rounded-full bg-brand/10 border border-brand/50 flex items-center justify-center shadow-glow">
            <Network className="h-10 w-10 text-brand" />
          </div>
          <span className="text-xs font-bold text-white uppercase tracking-wider">
            Core
          </span>
        </div>

        {/* Satellite nodes */}
        {AGENTS.map((a) => (
          <div
            key={a.id}
            ref={(el) => { nodeRefs.current[a.id] = el; }}
            className={`absolute flex flex-col items-center gap-1 ${positionClass(a.id)}`}
          >
            <div className="w-12 h-12 rounded-full bg-obsidian-light border border-white/10 flex items-center justify-center">
              <a.icon className={`h-5 w-5 ${a.color}`} />
            </div>
            <span className="text-[10px] text-white/40">{a.label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

/** Tailwind position classes for each satellite — pentagon layout. */
function positionClass(id: string): string {
  switch (id) {
    case "architect":
      return "top-0 left-1/2 -translate-x-1/2";
    case "developer":
      return "top-[12%] right-[5%]";
    case "tester":
      return "bottom-[8%] right-[5%]";
    case "reviewer":
      return "bottom-[8%] left-[5%]";
    case "integration":
      return "top-[12%] left-[5%]";
    default:
      return "";
  }
}
