"use client";

import { useEffect, useState } from "react";
import { useSearchParams, useRouter, useParams } from "next/navigation";
import { ArrowLeft, Loader2, CheckCircle2 } from "lucide-react";
import Link from "next/link";
import { useUnderstandingInterview } from "@/hooks/useUnderstandingInterview";
import { InterviewQuestion } from "@/components/understanding/InterviewQuestion";
import { InterviewHistory } from "@/components/understanding/InterviewHistory";
import { IdeaBriefView } from "@/components/understanding/IdeaBriefView";
import { DecisionGateModal } from "@/components/decision-gates/DecisionGateModal";
import { PlanComparisonTable } from "@/components/execution-plans/PlanComparisonTable";
import { PlanOptionCard } from "@/components/execution-plans/PlanOptionCard";
import { useDecisionGate } from "@/hooks/useDecisionGate";
import { useExecutionPlans } from "@/hooks/useExecutionPlans";

/**
 * Project-scoped Understanding Interview Page.
 *
 * Reads projectId from URL path segment (params.id) — not from searchParams.
 * onboardingSessionId still comes from searchParams.get("sessionId").
 *
 * Phase-based rendering:
 * - idle: Start button or "Complete onboarding first" message
 * - starting/loading_next: Skeleton shimmer
 * - questioning/editing_answer: Interview UI with history
 * - finalizing: Brief generation loading
 * - viewing_brief: IdeaBriefView with full brief + "Ready to decide?" CTA
 * - gate_open: DecisionGateModal full-screen
 * - plan_selection: PlanComparisonTable + PlanOptionCards
 * - plan_selected: Success state with dashboard link
 * - parked: Parked confirmation
 * - re_interviewing: Transition back to questioning
 * - error: Error display with debug_id
 */
export default function ProjectUnderstandingPage() {
  const params = useParams<{ id: string }>();
  const searchParams = useSearchParams();
  const router = useRouter();

  // projectId comes from URL path segment — always present
  const projectId = params.id;

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

  const {
    state: gateState,
    openGate,
    selectOption,
    resolveGate,
    closeGate,
  } = useDecisionGate();

  const {
    state: planState,
    generatePlans,
    selectPlan,
    regeneratePlans,
  } = useExecutionPlans();

  // onboarding session ID comes from query param
  const onboardingSessionId = searchParams.get("sessionId");

  // Local UI phase tracking
  const [uiPhase, setUiPhase] = useState<
    "interview" | "gate_open" | "plan_selection" | "plan_selected" | "parked"
  >("interview");

  useEffect(() => {
    // Auto-start interview if onboarding session ID provided
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

  // Handle decision gate opening
  const handleOpenGate = async () => {
    if (!projectId) return;
    setUiPhase("gate_open");
    await openGate(projectId);
  };

  // Handle gate resolution
  const handleGateResolve = async (actionText?: string, parkNote?: string) => {
    await resolveGate(actionText, parkNote);

    // Wait for resolution
    setTimeout(() => {
      const decision = gateState.selectedOption;

      if (decision === "proceed") {
        // Proceed: Generate execution plans
        setUiPhase("plan_selection");
        generatePlans(projectId);
      } else if (decision === "narrow" || decision === "pivot") {
        // Narrow/Pivot: Regenerate brief (stub for now - return to brief view)
        setUiPhase("interview");
        // Brief regeneration would happen in backend
      } else if (decision === "park") {
        // Park: Show parked confirmation
        setUiPhase("parked");
      }
    }, 600);
  };

  // Handle plan selection
  const handlePlanSelect = async (optionId: string) => {
    await selectPlan(projectId, optionId);
    setUiPhase("plan_selected");
  };

  // Handle plan regeneration
  const handlePlanRegenerate = async () => {
    await regeneratePlans(projectId, "Generate different options");
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
        {/* IDLE without session: Guard — show message with link to onboarding */}
        {state.phase === "idle" && !onboardingSessionId && (
          <div className="max-w-2xl w-full text-center space-y-6">
            <h1 className="text-4xl font-display font-bold text-white">
              Understanding Interview
            </h1>
            <p className="text-lg text-muted-foreground">
              Complete onboarding first to start the understanding interview for this project.
            </p>
            <Link
              href="/onboarding"
              className="inline-flex items-center gap-2 px-6 py-3 bg-brand hover:bg-brand/90 text-white font-semibold rounded-xl transition-colors shadow-glow"
            >
              Go to Onboarding
            </Link>
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

        {/* VIEWING_BRIEF: Full brief display + Ready to decide CTA */}
        {state.phase === "viewing_brief" && state.brief && uiPhase === "interview" && (
          <div className="w-full">
            <IdeaBriefView
              brief={state.brief}
              onEditSection={editBriefSection}
              onReInterview={reInterview}
              onProceedToDecision={handleOpenGate}
              artifactId={state.artifactId || ""}
              version={state.briefVersion}
              projectId={projectId}
            />
          </div>
        )}

        {/* GATE_OPEN: DecisionGateModal full-screen */}
        {uiPhase === "gate_open" && (
          <DecisionGateModal
            isOpen={gateState.isOpen}
            onClose={() => {
              closeGate();
              setUiPhase("interview");
            }}
            gateId={gateState.gateId}
            projectId={projectId}
            briefSummary={
              state.brief
                ? {
                    problem_statement: state.brief.problem_statement,
                    target_user: state.brief.target_user,
                    value_prop: state.brief.value_prop,
                  }
                : undefined
            }
            options={gateState.options}
            selectedOption={gateState.selectedOption}
            onSelectOption={selectOption}
            onResolve={handleGateResolve}
            isResolving={gateState.isResolving}
            error={gateState.error}
          />
        )}

        {/* PLAN_SELECTION: Execution plan comparison */}
        {uiPhase === "plan_selection" && (
          <div className="max-w-6xl mx-auto px-6 py-12 space-y-8">
            <div className="space-y-3">
              <h2 className="text-3xl font-display font-bold text-white">
                Choose Your Execution Path
              </h2>
              <p className="text-muted-foreground">
                We&apos;ve generated three execution options. Review the comparison and select
                the path that best fits your goals.
              </p>
            </div>

            {/* Comparison Table */}
            <PlanComparisonTable
              options={planState.options}
              onSelect={handlePlanSelect}
              onRegenerate={handlePlanRegenerate}
              isGenerating={planState.isGenerating}
            />

            {/* Detailed option cards */}
            {!planState.isGenerating && planState.options.length > 0 && (
              <div className="space-y-4 pt-8 border-t border-white/10">
                <h3 className="text-xl font-display font-semibold text-white">
                  Detailed Breakdown
                </h3>
                <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
                  {planState.options.map((option) => (
                    <PlanOptionCard
                      key={option.id}
                      option={option}
                      isRecommended={option.is_recommended}
                      onSelect={() => handlePlanSelect(option.id)}
                    />
                  ))}
                </div>
              </div>
            )}

            {planState.error && (
              <div className="p-4 rounded-lg bg-red-500/10 border border-red-500/20">
                <p className="text-sm text-red-400">{planState.error}</p>
              </div>
            )}
          </div>
        )}

        {/* PLAN_SELECTED: Success state */}
        {uiPhase === "plan_selected" && (
          <div className="max-w-2xl w-full text-center space-y-6">
            <CheckCircle2 className="h-16 w-16 text-brand mx-auto" />
            <div className="space-y-2">
              <h2 className="text-3xl font-display font-bold text-white">
                Execution Plan Selected
              </h2>
              <p className="text-muted-foreground">
                Your execution path has been saved. You can now continue to your dashboard to
                track progress.
              </p>
            </div>
            <button
              onClick={() => router.push("/dashboard")}
              className="px-6 py-3 bg-brand hover:bg-brand/90 text-white font-semibold rounded-xl transition-colors shadow-glow"
            >
              Continue to Dashboard
            </button>
          </div>
        )}

        {/* PARKED: Parked confirmation */}
        {uiPhase === "parked" && (
          <div className="max-w-2xl w-full text-center space-y-6">
            <div className="p-6 bg-white/5 border border-white/10 rounded-xl">
              <h2 className="text-2xl font-display font-semibold text-white mb-3">
                Project Parked
              </h2>
              <p className="text-muted-foreground">
                This project has been parked. You can resume it anytime from your dashboard.
              </p>
            </div>
            <button
              onClick={() => router.push("/dashboard")}
              className="px-6 py-3 bg-white/10 hover:bg-white/20 text-white font-medium rounded-xl transition-colors"
            >
              Return to Dashboard
            </button>
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
