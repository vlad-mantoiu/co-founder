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
    createProject,
    fetchActiveSessions,
    startFresh,
    reset,
  } = useOnboarding();

  // Check for existing sessions on mount
  useEffect(() => {
    fetchActiveSessions();
  }, [fetchActiveSessions]);

  // Welcome back screen (active sessions)
  if (state.phase === "idle" && state.activeSessions.length > 0) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen px-4 py-8">
        <div className="w-full max-w-2xl space-y-6">
          <div className="text-center space-y-3">
            <h2 className="text-3xl font-display font-bold text-white">
              Welcome Back
            </h2>
            <p className="text-muted-foreground">
              You have {state.activeSessions.length} onboarding session{state.activeSessions.length > 1 ? "s" : ""} in progress
            </p>
          </div>

          <div className="space-y-4">
            {state.activeSessions.map((session) => {
              const progress = Math.round((session.current_question_index / session.total_questions) * 100);
              const ideaPreview = session.idea_text.length > 100
                ? session.idea_text.substring(0, 100) + "..."
                : session.idea_text;
              const createdAt = new Date(session.created_at);
              const relativeTime = formatRelativeTime(createdAt);

              return (
                <div
                  key={session.id}
                  className="p-6 bg-white/5 border border-white/10 rounded-xl space-y-4"
                >
                  <div className="space-y-2">
                    <p className="text-white font-medium">{ideaPreview}</p>
                    <p className="text-sm text-muted-foreground">
                      {session.current_question_index} of {session.total_questions} questions answered • Started {relativeTime}
                    </p>
                  </div>

                  <div className="flex items-center gap-3">
                    <button
                      onClick={() => resumeSession(session.id)}
                      className="flex-1 px-4 py-2 bg-brand hover:bg-brand/90 text-white font-medium rounded-lg transition-colors"
                    >
                      Continue ({progress}%)
                    </button>
                  </div>
                </div>
              );
            })}
          </div>

          <div className="text-center">
            <button
              onClick={startFresh}
              className="px-6 py-3 text-muted-foreground hover:text-white font-medium transition-colors"
            >
              Start Fresh Session
            </button>
          </div>
        </div>
      </div>
    );
  }

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

  // Helper function for relative time formatting
  function formatRelativeTime(date: Date): string {
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return "just now";
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    return date.toLocaleDateString();
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
            onCreateProject={createProject}
            onStartFresh={reset}
            isCreatingProject={state.isLoading}
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
