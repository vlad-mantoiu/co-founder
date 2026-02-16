"use client";

import { useState, useRef, useEffect } from "react";

interface IdeaInputProps {
  onSubmit: (idea: string) => void;
  onContinueAnyway?: () => void;
  showExpandPrompt?: boolean;
  initialIdea?: string;
  disabled?: boolean;
}

/**
 * IdeaInput component: Initial idea entry with smart expand prompt.
 *
 * Shows "What are we building?" heading and single textarea.
 * If showExpandPrompt is true, displays friendly message to elaborate.
 */
export function IdeaInput({
  onSubmit,
  onContinueAnyway,
  showExpandPrompt = false,
  initialIdea = "",
  disabled = false,
}: IdeaInputProps) {
  const [idea, setIdea] = useState(initialIdea);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    textareaRef.current?.focus();
  }, []);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!idea.trim() || disabled) return;
    onSubmit(idea);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    // Submit on Enter (but not Shift+Enter which adds newline)
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  return (
    <div className="flex flex-col items-center justify-center min-h-screen px-4">
      <div className="w-full max-w-2xl space-y-8">
        {/* Heading */}
        <div className="text-center space-y-3">
          <h1 className="text-4xl md:text-5xl font-display font-bold text-white">
            What are we building?
          </h1>
          <p className="text-lg text-muted-foreground">
            Describe your startup idea in a sentence or two
          </p>
        </div>

        {/* Input form */}
        <form onSubmit={handleSubmit} className="space-y-4">
          <textarea
            ref={textareaRef}
            value={idea}
            onChange={(e) => setIdea(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Describe your startup idea in a sentence or two..."
            disabled={disabled}
            className="w-full min-h-32 px-4 py-3 bg-white/5 border border-white/10 rounded-xl text-white placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-brand focus:border-transparent resize-none disabled:opacity-50 disabled:cursor-not-allowed"
            rows={4}
          />

          {/* Smart expand prompt */}
          {showExpandPrompt && (
            <div className="space-y-3 p-4 bg-white/5 border border-white/10 rounded-xl">
              <p className="text-sm text-muted-foreground">
                Tell us a bit more about your idea — even a couple more sentences helps us ask better questions.
              </p>
              <button
                type="button"
                onClick={onContinueAnyway}
                disabled={disabled}
                className="text-sm text-brand hover:text-brand/80 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Continue anyway →
              </button>
            </div>
          )}

          {/* Submit button */}
          {!showExpandPrompt && (
            <button
              type="submit"
              disabled={!idea.trim() || disabled}
              className="w-full px-6 py-3 bg-brand hover:bg-brand/90 text-white font-medium rounded-xl transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Let's go
            </button>
          )}
        </form>
      </div>
    </div>
  );
}
