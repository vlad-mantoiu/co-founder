"use client";

import { useEffect } from "react";
import { useOnboarding } from "@/hooks/useOnboarding";
import { IdeaInput } from "@/components/onboarding/IdeaInput";
import { ConversationalQuestion } from "@/components/onboarding/ConversationalQuestion";
import { QuestionHistory } from "@/components/onboarding/QuestionHistory";
import { ProgressBar } from "@/components/onboarding/ProgressBar";
import { ThesisSnapshot } from "@/components/onboarding/ThesisSnapshot";

/**
 * Onboarding page: Main entry point for the onboarding flow.
 *
 * State machine routing:
 * - idle/idea_input: Show IdeaInput
 * - expanding: Show IdeaInput with expand prompt
 * - questioning/loading_question: Show questions (placeholder for Task 2)
 * - finalizing: Loading state
 * - viewing_snapshot: Show ThesisSnapshot (placeholder for Task 3)
 * - error: Show error message
 */
export default function OnboardingPage() {
  const {
    state,
    submitIdea,
    continueAnyway,
    submitAnswer,
    editAnswer,
    editThesisField,
    resumeSession,
    reset,
  } = useOnboarding();

  // Check for existing sessions on mount
  useEffect(() => {
    // TODO: Implement session check in next task
    // For now, just start fresh
  }, []);

  // Error state
  if (state.phase === "error") {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen px-4">
        <div className="w-full max-w-md space-y-6 text-center">
          <div className="space-y-3">
            <h2 className="text-2xl font-display font-bold text-white">
              Something went wrong
            </h2>
            <p className="text-muted-foreground">{state.error}</p>
          </div>
          <button
            onClick={reset}
            className="w-full px-6 py-3 bg-brand hover:bg-brand/90 text-white font-medium rounded-xl transition-colors"
          >
            Start Fresh
          </button>
        </div>
      </div>
    );
  }

  // Finalizing state
  if (state.phase === "finalizing") {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen px-4">
        <div className="w-full max-w-md space-y-6 text-center">
          <div className="space-y-3">
            <div className="animate-pulse space-y-3">
              <div className="h-8 bg-white/10 rounded w-3/4 mx-auto" />
              <div className="h-4 bg-white/10 rounded w-1/2 mx-auto" />
            </div>
            <p className="text-muted-foreground">Generating your Thesis Snapshot...</p>
          </div>
        </div>
      </div>
    );
  }

  // Viewing snapshot
  if (state.phase === "viewing_snapshot" && state.thesisSnapshot) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen px-4 py-8">
        <div className="w-full max-w-4xl">
          <ThesisSnapshot
            snapshot={state.thesisSnapshot}
            onEdit={editThesisField}
            onCreateProject={() => {
              // TODO: Wire up project creation in Plan 04-04
              console.log("Create project");
            }}
            onStartFresh={reset}
          />
        </div>
      </div>
    );
  }

  // Questioning state
  if (state.phase === "questioning" || state.phase === "loading_question") {
    const currentQuestion = state.questions[state.currentQuestionIndex];
    const isLastQuestion = state.currentQuestionIndex === state.totalQuestions - 1;

    return (
      <div className="flex flex-col items-center justify-center min-h-screen px-4 py-8">
        <div className="w-full max-w-2xl">
          <ProgressBar current={state.currentQuestionIndex + 1} total={state.totalQuestions} />

          <QuestionHistory
            questions={state.questions}
            answers={state.answers}
            currentIndex={state.currentQuestionIndex}
            onEdit={editAnswer}
          />

          {state.phase === "loading_question" ? (
            <div className="space-y-4 animate-pulse">
              <div className="h-8 bg-white/10 rounded w-3/4" />
              <div className="h-24 bg-white/10 rounded" />
            </div>
          ) : currentQuestion ? (
            <ConversationalQuestion
              question={currentQuestion}
              currentAnswer={state.answers[currentQuestion.id]}
              onSubmit={(answer) => submitAnswer(currentQuestion.id, answer)}
              isLastQuestion={isLastQuestion}
              disabled={state.isLoading}
              isLoading={false}
            />
          ) : null}
        </div>
      </div>
    );
  }

  // Idea input (idle or expanding)
  return (
    <IdeaInput
      onSubmit={submitIdea}
      onContinueAnyway={continueAnyway}
      showExpandPrompt={state.phase === "expanding"}
      initialIdea={state.idea}
      disabled={state.isLoading}
    />
  );
}
