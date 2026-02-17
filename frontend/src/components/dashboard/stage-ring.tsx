"use client";

interface StageRingProps {
  currentStage: number;
  progressPercent: number;
}

const STAGES = ["Thesis", "Validated", "MVP Built", "Feedback", "Scale"];

export function StageRing({ currentStage, progressPercent }: StageRingProps) {
  const radius = 80;
  const circumference = 2 * Math.PI * radius;
  const gapLength = 8;
  const usableCircumference = circumference - gapLength * 5;
  const segmentLength = usableCircumference / 5;

  return (
    <div className="relative w-48 h-48 flex items-center justify-center">
      {/* SVG ring with 5 segments */}
      <svg
        className="absolute inset-0 -rotate-90"
        width="192"
        height="192"
        viewBox="0 0 192 192"
      >
        {STAGES.map((_, idx) => {
          const startOffset = idx * (segmentLength + gapLength);

          // Determine segment color based on stage position
          let strokeColor: string;
          if (idx < currentStage) {
            // Completed stages: brand color at 50% opacity
            strokeColor = "rgba(59, 130, 246, 0.5)"; // blue-500 at 50%
          } else if (idx === currentStage) {
            // Current stage: full brand color
            strokeColor = "rgb(59, 130, 246)"; // blue-500
          } else {
            // Future stages: white at 10% opacity
            strokeColor = "rgba(255, 255, 255, 0.1)";
          }

          return (
            <circle
              key={idx}
              cx="96"
              cy="96"
              r={radius}
              fill="none"
              stroke={strokeColor}
              strokeWidth="12"
              strokeDasharray={`${segmentLength} ${circumference - segmentLength}`}
              strokeDashoffset={-startOffset}
              strokeLinecap="round"
            />
          );
        })}
      </svg>

      {/* Center text */}
      <div className="flex flex-col items-center justify-center text-center z-10">
        <div className="text-4xl font-bold text-white">
          {progressPercent}%
        </div>
        <div className="text-sm text-white/60 mt-1">
          {STAGES[currentStage] || "Unknown"}
        </div>
      </div>
    </div>
  );
}
