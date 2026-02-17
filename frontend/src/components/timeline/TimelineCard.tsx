"use client";

import Link from "next/link";
import { TimelineItem } from "./types";

interface TimelineCardProps {
  item: TimelineItem;
  onClick: () => void;
}

const TYPE_BADGE_STYLES: Record<TimelineItem["type"], string> = {
  decision: "bg-violet-500/20 text-violet-300 border-violet-500/30",
  milestone: "bg-emerald-500/20 text-emerald-300 border-emerald-500/30",
  artifact: "bg-blue-500/20 text-blue-300 border-blue-500/30",
};

const TYPE_LABELS: Record<TimelineItem["type"], string> = {
  decision: "Decision",
  milestone: "Milestone",
  artifact: "Artifact",
};

function formatRelativeDate(timestamp: string): string {
  const date = new Date(timestamp);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

  if (diffDays === 0) return "Today";
  if (diffDays === 1) return "Yesterday";
  if (diffDays < 7) return `${diffDays} days ago`;
  if (diffDays < 14) return "Last week";

  // For older dates, show absolute "Feb 15" style
  return date.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

export function TimelineCard({ item, onClick }: TimelineCardProps) {
  return (
    <div
      onClick={onClick}
      className="p-3 rounded-lg bg-white/[0.03] border border-white/5 cursor-pointer hover:bg-white/5 transition-colors active:scale-[0.98]"
    >
      {/* Type badge + date row */}
      <div className="flex items-center justify-between mb-2">
        <span
          className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium border ${TYPE_BADGE_STYLES[item.type]}`}
        >
          {TYPE_LABELS[item.type]}
        </span>
        <span className="text-xs text-white/40">{formatRelativeDate(item.timestamp)}</span>
      </div>

      {/* Title */}
      <p className="text-sm font-medium text-white/90 line-clamp-2 leading-snug">
        {item.title}
      </p>

      {/* View in graph link */}
      {item.graph_node_id && (
        <div className="mt-2 pt-2 border-t border-white/5">
          <Link
            href={`/strategy?project=${item.project_id}&highlight=${item.graph_node_id}`}
            onClick={(e) => e.stopPropagation()}
            className="text-xs text-brand hover:text-brand/80 transition-colors"
          >
            View in graph &rarr;
          </Link>
        </div>
      )}
    </div>
  );
}
