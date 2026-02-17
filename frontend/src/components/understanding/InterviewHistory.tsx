"use client";

import type { UnderstandingQuestion } from "@/hooks/useUnderstandingInterview";

interface InterviewHistoryProps {
  answeredQuestions: { question: UnderstandingQuestion; answer: string }[];
  onEdit: (index: number) => void;
  currentIndex: number;
}

/**
 * InterviewHistory: Scrollable previous Q&A with edit capability.
 *
 * Shows answered questions as compact cards with truncated answers.
 * Click to edit previous answers.
 */
export function InterviewHistory({
  answeredQuestions,
  onEdit,
  currentIndex,
}: InterviewHistoryProps) {
  if (answeredQuestions.length === 0) return null;

  return (
    <div className="space-y-2">
      <h4 className="text-sm font-medium text-muted-foreground mb-3">Previous answers</h4>
      <div className="space-y-2 max-h-64 overflow-y-auto pr-2">
        {answeredQuestions.map((qa, index) => {
          const isCurrent = index === currentIndex - 1;
          const truncatedAnswer =
            qa.answer.length > 80 ? qa.answer.slice(0, 80) + "..." : qa.answer;

          return (
            <button
              key={qa.question.id}
              onClick={() => onEdit(index)}
              className={`w-full text-left px-4 py-3 rounded-lg transition-colors ${
                isCurrent
                  ? "bg-brand/10 border border-brand/30"
                  : "bg-white/5 border border-white/10 hover:bg-white/10"
              }`}
            >
              <div className="space-y-1">
                <p className="text-sm font-medium text-white/90">
                  {index + 1}. {qa.question.text}
                </p>
                <p className="text-xs text-muted-foreground">{truncatedAnswer}</p>
              </div>
            </button>
          );
        })}
      </div>
      {answeredQuestions.length > 0 && (
        <div className="pt-3 border-t border-white/10">
          <p className="text-xs text-muted-foreground text-center">
            Click any answer to edit
          </p>
        </div>
      )}
    </div>
  );
}
