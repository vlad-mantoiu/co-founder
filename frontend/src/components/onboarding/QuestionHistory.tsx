"use client";

import type { OnboardingQuestion } from "@/hooks/useOnboarding";

interface QuestionHistoryProps {
  questions: OnboardingQuestion[];
  answers: Record<string, string>;
  currentIndex: number;
  onEdit: (index: number) => void;
}

/**
 * QuestionHistory: Scrollable list of previously answered Q&A pairs.
 *
 * Shows question text, answer, and edit button.
 * Reduced opacity to de-emphasize vs current question.
 */
export function QuestionHistory({
  questions,
  answers,
  currentIndex,
  onEdit,
}: QuestionHistoryProps) {
  const previousQuestions = questions.slice(0, currentIndex);

  if (previousQuestions.length === 0) {
    return null;
  }

  return (
    <div className="space-y-4 opacity-60 mb-8">
      {previousQuestions.map((q, idx) => {
        const answer = answers[q.id];
        if (!answer) return null;

        return (
          <div
            key={q.id}
            className="p-4 bg-white/5 border border-white/10 rounded-xl space-y-2"
          >
            <div className="flex items-start justify-between gap-3">
              <div className="flex-1 space-y-1.5">
                <p className="text-sm text-muted-foreground">{q.text}</p>
                <p className="text-base text-white">{answer}</p>
              </div>
              <button
                onClick={() => onEdit(idx)}
                className="px-3 py-1.5 text-xs text-brand hover:text-brand/80 font-medium transition-colors"
              >
                Edit
              </button>
            </div>
          </div>
        );
      })}
    </div>
  );
}
