"use client";

import { useMemo } from "react";
import { TimelineItem } from "./types";
import { KanbanColumn } from "./KanbanColumn";

const COLUMNS = [
  { id: "backlog", label: "Backlog", color: "border-white/10" },
  { id: "planned", label: "Planned", color: "border-blue-500/30" },
  { id: "in_progress", label: "In Progress", color: "border-brand/30" },
  { id: "done", label: "Done", color: "border-emerald-500/30" },
] as const;

interface KanbanBoardProps {
  items: TimelineItem[];
  onCardClick: (item: TimelineItem) => void;
}

export function KanbanBoard({ items, onCardClick }: KanbanBoardProps) {
  const columnItems = useMemo(() => {
    const grouped: Record<string, TimelineItem[]> = {
      backlog: [],
      planned: [],
      in_progress: [],
      done: [],
    };

    for (const item of items) {
      const col = grouped[item.kanban_status];
      if (col) {
        col.push(item);
      }
    }

    // Sort each column: newest first
    for (const key of Object.keys(grouped)) {
      grouped[key].sort(
        (a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime(),
      );
    }

    return grouped;
  }, [items]);

  if (items.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-[50vh] text-center">
        <div className="w-12 h-12 rounded-xl bg-white/5 flex items-center justify-center mb-4">
          <span className="text-2xl text-white/20">&#9776;</span>
        </div>
        <h3 className="text-lg font-medium text-white/60">No timeline items yet</h3>
        <p className="text-sm text-white/30 mt-1">
          Events will appear here as your project progresses
        </p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 h-full">
      {COLUMNS.map((col) => (
        <KanbanColumn
          key={col.id}
          label={col.label}
          color={col.color}
          items={columnItems[col.id] ?? []}
          onCardClick={onCardClick}
        />
      ))}
    </div>
  );
}
