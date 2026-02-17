"use client";

import { useEffect } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { ArrowLeft, Loader2 } from "lucide-react";
import Link from "next/link";
import { useUnderstandingInterview } from "@/hooks/useUnderstandingInterview";
import { InterviewQuestion } from "@/components/understanding/InterviewQuestion";
import { InterviewHistory } from "@/components/understanding/InterviewHistory";
import { IdeaBriefView } from "@/components/understanding/IdeaBriefView";

/**
 * Understanding Interview Page.
 *
 * Phase-based rendering:
 * - idle: Start button or session picker
 * - starting/loading_next: Skeleton shimmer
 * - questioning/editing_answer: Interview UI with history
 * - finalizing: Brief generation loading
 * - viewing_brief: IdeaBriefView with full brief
 * - re_interviewing: Transition back to questioning
 * - error: Error display with debug_id
 */
export default function UnderstandingPage() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const {
    state,
    startInterview,
    submitAnswer,
    editAnswer,
    navigateBack,
    editBriefSection,
    reInterview,
    resumeSession,
  } = useUnderstandingInterview();

  // Get onboarding session ID from query params
  const onboardingSessionId = searchParams.get("sessionId");

  useEffect(() => {
    // Auto-start interview if session ID provided
    if (onboardingSessionId && state.phase === "idle") {
      startInterview(onboardingSessionId);
    }
  }, [onboardingSessionId, state.phase, startInterview]);

  const handleSubmitAnswer = async (answer: string) => {
    if (state.phase === "editing_answer" && state.currentQuestion) {
      await editAnswer(state.currentQuestion.id, answer);
    } else if (state.currentQuestion) {
      await submitAnswer(state.currentQuestion.id, answer);
    }
  };

  return (
    <div className="min-h-screen flex flex-col">
      {/* Back navigation */}
      {state.phase !== "idle" && (
        <div className="p-6">
          <Link
            href="/dashboard"
            className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-white transition-colors"
          >
            <ArrowLeft className="h-4 w-4" />
            Back to Dashboard
          </Link>
        </div>
      )}

      {/* Phase-based rendering */}
      <div className="flex-1 flex items-center justify-center px-6 py-12">
        {/* IDLE: Start interface */}
        {state.phase === "idle" && !onboardingSessionId && (
          <div className="max-w-2xl w-full text-center space-y-6">
            <h1 className="text-4xl font-display font-bold text-white">
              Understanding Interview
            </h1>
            <p className="text-lg text-muted-foreground">
              Let&apos;s deepen our understanding of your idea through a guided conversation.
            </p>
            <p className="text-sm text-muted-foreground">
              No session ID provided. Please start from onboarding.
            </p>
          </div>
        )}

        {/* STARTING / LOADING_NEXT: Skeleton shimmer */}
        {(state.phase === "starting" || state.phase === "loading_next") && (
          <div className="max-w-2xl w-full space-y-6">
            <div className="space-y-4 animate-pulse">
              <div className="h-8 bg-white/10 rounded w-3/4" />
              <div className="h-6 bg-white/10 rounded w-1/2" />
              <div className="h-24 bg-white/10 rounded" />
            </div>
          </div>
        )}

        {/* QUESTIONING / EDITING_ANSWER: Interview UI */}
        {(state.phase === "questioning" || state.phase === "editing_answer") &&
          state.currentQuestion && (
            <div className="max-w-4xl w-full space-y-8">
              {/* Progress indicator */}
              <div className="text-center">
                <p className="text-sm text-muted-foreground">
                  Question {state.questionNumber} of {state.totalQuestions}
                </p>
                <div className="mt-2 h-1.5 bg-white/10 rounded-full overflow-hidden max-w-md mx-auto">
                  <div
                    className="h-full bg-brand transition-all duration-300"
                    style={{
                      width: `${(state.questionNumber / state.totalQuestions) * 100}%`,
                    }}
                  />
                </div>
              </div>

              {/* Current question */}
              <InterviewQuestion
                question={state.currentQuestion}
                onSubmit={handleSubmitAnswer}
                isLoading={false}
                initialAnswer={
                  state.answeredQuestions.find(
                    (qa) => qa.question.id === state.currentQuestion?.id,
                  )?.answer || ""
                }
              />

              {/* History of previous answers */}
              {state.answeredQuestions.length > 0 && (
                <div className="mt-8 pt-8 border-t border-white/10">
                  <InterviewHistory
                    answeredQuestions={state.answeredQuestions}
                    onEdit={navigateBack}
                    currentIndex={state.questionNumber}
                  />
                </div>
              )}
            </div>
          )}

        {/* FINALIZING: Brief generation loading */}
        {state.phase === "finalizing" && (
          <div className="max-w-2xl w-full text-center space-y-6">
            <Loader2 className="h-12 w-12 text-brand animate-spin mx-auto" />
            <div className="space-y-2">
              <h2 className="text-2xl font-display font-semibold text-white">
                Generating your Idea Brief...
              </h2>
              <p className="text-sm text-muted-foreground">
                We&apos;re synthesizing your answers into an investor-quality brief
              </p>
            </div>
          </div>
        )}

        {/* VIEWING_BRIEF: Full brief display */}
        {state.phase === "viewing_brief" && state.brief && (
          <div className="w-full">
            <IdeaBriefView
              brief={state.brief}
              onEditSection={editBriefSection}
              onReInterview={reInterview}
              artifactId={state.artifactId || ""}
              version={state.briefVersion}
            />
          </div>
        )}

        {/* RE_INTERVIEWING: Transition loading */}
        {state.phase === "re_interviewing" && (
          <div className="max-w-2xl w-full text-center space-y-6">
            <Loader2 className="h-12 w-12 text-brand animate-spin mx-auto" />
            <div className="space-y-2">
              <h2 className="text-2xl font-display font-semibold text-white">
                Resetting interview...
              </h2>
              <p className="text-sm text-muted-foreground">
                We&apos;ll start fresh with updated questions
              </p>
            </div>
          </div>
        )}

        {/* ERROR: Error display */}
        {state.phase === "error" && (
          <div className="max-w-2xl w-full text-center space-y-6">
            <div className="p-6 bg-red-500/10 border border-red-500/20 rounded-xl">
              <h2 className="text-xl font-semibold text-red-400 mb-2">Something went wrong</h2>
              <p className="text-sm text-red-300/80">{state.error}</p>
              {state.debugId && (
                <p className="text-xs text-red-300/60 mt-2">Debug ID: {state.debugId}</p>
              )}
            </div>
            <button
              onClick={() => router.push("/dashboard")}
              className="px-6 py-2.5 bg-brand hover:bg-brand/90 text-white font-medium rounded-xl transition-colors"
            >
              Return to Dashboard
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
