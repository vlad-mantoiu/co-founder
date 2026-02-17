"use client";

import { TimelineItem } from "./types";
import { TimelineCard } from "./TimelineCard";

interface KanbanColumnProps {
  label: string;
  color: string;
  items: TimelineItem[];
  onCardClick: (item: TimelineItem) => void;
}

export function KanbanColumn({ label, color, items, onCardClick }: KanbanColumnProps) {
  return (
    <div className={`border-t-2 ${color} bg-white/[0.02] rounded-xl p-3 flex flex-col`}>
      {/* Column header */}
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-white/80">{label}</h3>
        {items.length > 0 && (
          <span className="text-xs font-medium text-white/40 bg-white/5 px-2 py-0.5 rounded-full">
            {items.length}
          </span>
        )}
      </div>

      {/* Cards */}
      <div className="overflow-y-auto max-h-[calc(100vh-18rem)] space-y-2">
        {items.length === 0 ? (
          <div className="flex items-center justify-center h-20 border border-dashed border-white/10 rounded-lg">
            <span className="text-xs text-white/30">No items</span>
          </div>
        ) : (
          items.map((item) => (
            <TimelineCard key={item.id} item={item} onClick={() => onCardClick(item)} />
          ))
        )}
      </div>
    </div>
  );
}
