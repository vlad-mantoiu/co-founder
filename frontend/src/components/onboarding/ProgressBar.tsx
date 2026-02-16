"use client";

interface ProgressBarProps {
  current: number;
  total: number;
}

/**
 * ProgressBar: Visual progress indicator for question completion.
 *
 * Shows "Question X of Y" and percentage with animated gradient fill.
 */
export function ProgressBar({ current, total }: ProgressBarProps) {
  // Integer truncation per Phase 02 pattern
  const percent = total === 0 ? 0 : Math.floor((current / total) * 100);

  return (
    <div className="space-y-2 mb-6">
      {/* Text label */}
      <div className="flex items-center justify-between text-sm">
        <span className="text-muted-foreground">
          Question {current} of {total}
        </span>
        <span className="text-muted-foreground">{percent}%</span>
      </div>

      {/* Progress bar */}
      <div className="h-2 bg-white/5 rounded-full overflow-hidden">
        <div
          className="h-full bg-gradient-to-r from-blue-500 to-purple-500 transition-all duration-500 ease-out"
          style={{ width: `${percent}%` }}
        />
      </div>
    </div>
  );
}
