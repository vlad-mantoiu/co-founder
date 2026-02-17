"use client";

import { useState, useRef, useEffect } from "react";
import { AnimatePresence, motion } from "framer-motion";
import type { UnderstandingQuestion } from "@/hooks/useUnderstandingInterview";

interface InterviewQuestionProps {
  question: UnderstandingQuestion;
  onSubmit: (answer: string) => void;
  isLoading?: boolean;
  initialAnswer?: string;
}

/**
 * InterviewQuestion: One-question-at-a-time display for understanding interview.
 *
 * Supports text, textarea, and multiple_choice input types.
 * Shows skeleton shimmer during loading state.
 * Matches Phase 4 onboarding patterns with "we" co-founder language.
 */
export function InterviewQuestion({
  question,
  onSubmit,
  isLoading = false,
  initialAnswer = "",
}: InterviewQuestionProps) {
  const [answer, setAnswer] = useState(initialAnswer);
  const inputRef = useRef<HTMLInputElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    setAnswer(initialAnswer);
  }, [initialAnswer]);

  useEffect(() => {
    // Auto-focus input on mount
    if (question.input_type === "text") {
      inputRef.current?.focus();
    } else if (question.input_type === "textarea") {
      textareaRef.current?.focus();
    }
  }, [question.id, question.input_type]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!answer.trim() || isLoading) return;
    onSubmit(answer);
    setAnswer("");
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    if (question.input_type === "text" && e.key === "Enter") {
      e.preventDefault();
      handleSubmit(e);
    } else if (question.input_type === "textarea" && e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  const handleOptionClick = (option: string) => {
    setAnswer(option);
    // Auto-submit for multiple choice
    setTimeout(() => onSubmit(option), 100);
  };

  // Loading skeleton shimmer (matches Phase 4 pattern)
  if (isLoading) {
    return (
      <div className="space-y-4 animate-pulse">
        <div className="h-8 bg-white/10 rounded w-3/4" />
        <div className="h-6 bg-white/10 rounded w-1/2" />
        <div className="h-24 bg-white/10 rounded" />
      </div>
    );
  }

  return (
    <AnimatePresence mode="wait">
      <motion.div
        key={question.id}
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -20 }}
        transition={{ duration: 0.3 }}
        className="space-y-6"
      >
        {/* Question text */}
        <div className="space-y-2">
          <h3 className="text-2xl font-display font-semibold text-white">
            {question.text}
          </h3>
          {question.follow_up_hint && (
            <p className="text-sm text-muted-foreground">{question.follow_up_hint}</p>
          )}
        </div>

        {/* Dynamic input */}
        <form onSubmit={handleSubmit} className="space-y-4">
          {question.input_type === "text" && (
            <input
              ref={inputRef}
              type="text"
              value={answer}
              onChange={(e) => setAnswer(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={isLoading}
              placeholder="Your answer..."
              className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-xl text-white placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-brand focus:border-transparent disabled:opacity-50 disabled:cursor-not-allowed"
            />
          )}

          {question.input_type === "textarea" && (
            <textarea
              ref={textareaRef}
              value={answer}
              onChange={(e) => setAnswer(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={isLoading}
              placeholder="Your answer..."
              className="w-full min-h-24 px-4 py-3 bg-white/5 border border-white/10 rounded-xl text-white placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-brand focus:border-transparent resize-none disabled:opacity-50 disabled:cursor-not-allowed"
              rows={4}
            />
          )}

          {question.input_type === "multiple_choice" && question.options && (
            <div className="space-y-2">
              {question.options.map((option, idx) => (
                <button
                  key={idx}
                  type="button"
                  onClick={() => handleOptionClick(option)}
                  disabled={isLoading}
                  className={`w-full px-4 py-3 text-left rounded-xl transition-colors disabled:opacity-50 disabled:cursor-not-allowed ${
                    answer === option
                      ? "bg-brand/20 border-2 border-brand text-white"
                      : "bg-white/5 border border-white/10 text-muted-foreground hover:bg-white/10 hover:text-white"
                  }`}
                >
                  {option}
                </button>
              ))}
            </div>
          )}

          {/* Submit button (for text/textarea only - multiple choice auto-submits) */}
          {question.input_type !== "multiple_choice" && (
            <div className="flex justify-between items-center pt-2">
              <p className="text-xs text-muted-foreground">
                {question.input_type === "textarea" ? "Cmd+Enter to submit" : "Enter to submit"}
              </p>
              <button
                type="submit"
                disabled={!answer.trim() || isLoading}
                className="px-6 py-2.5 bg-brand hover:bg-brand/90 text-white font-medium rounded-xl transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Continue
              </button>
            </div>
          )}
        </form>
      </motion.div>
    </AnimatePresence>
  );
}
