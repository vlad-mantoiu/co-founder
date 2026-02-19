"use client";

import { ZoomIn, ZoomOut, Maximize, GitBranch } from "lucide-react";

interface GraphToolbarProps {
  onZoomIn: () => void;
  onZoomOut: () => void;
  onRecenter: () => void;
  logicPaths: boolean;
  onToggleLogicPaths: () => void;
}

export function GraphToolbar({
  onZoomIn,
  onZoomOut,
  onRecenter,
  logicPaths,
  onToggleLogicPaths,
}: GraphToolbarProps) {
  return (
    <div className="absolute left-4 top-4 z-10 flex flex-col gap-1 glass rounded-xl p-1.5">
      <ToolbarButton icon={ZoomIn} label="Zoom In" onClick={onZoomIn} />
      <ToolbarButton icon={ZoomOut} label="Zoom Out" onClick={onZoomOut} />
      <ToolbarButton icon={Maximize} label="Recenter" onClick={onRecenter} />
      <div className="my-1 h-px bg-white/10" />
      <ToolbarButton
        icon={GitBranch}
        label="Logic Paths"
        onClick={onToggleLogicPaths}
        active={logicPaths}
      />
    </div>
  );
}

function ToolbarButton({
  icon: Icon,
  label,
  onClick,
  active,
}: {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  onClick: () => void;
  active?: boolean;
}) {
  return (
    <button
      onClick={onClick}
      title={label}
      className={`flex h-8 w-8 items-center justify-center rounded-lg transition-colors ${
        active
          ? "bg-brand/20 text-brand"
          : "text-white/50 hover:bg-white/5 hover:text-white"
      }`}
    >
      <Icon className="h-4 w-4" />
    </button>
  );
}
