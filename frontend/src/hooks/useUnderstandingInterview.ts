"use client";

import { useState, useCallback } from "react";
import { useAuth } from "@clerk/nextjs";
import { apiFetch } from "@/lib/api";
import { toast } from "sonner";

/**
 * Understanding interview phase state machine.
 */
type UnderstandingPhase =
  | "idle"
  | "starting"
  | "questioning"
  | "loading_next"
  | "editing_answer"
  | "finalizing"
  | "viewing_brief"
  | "re_interviewing"
  | "error";

/**
 * TypeScript interfaces matching backend Pydantic schemas.
 */
export interface UnderstandingQuestion {
  id: string;
  text: string;
  input_type: "text" | "textarea" | "multiple_choice";
  required: boolean;
  options?: string[];
  follow_up_hint?: string;
}

export interface RationalisedIdeaBrief {
  schema_version: number;
  problem_statement: string;
  target_user: string;
  value_prop: string;
  differentiation: string;
  monetization_hypothesis: string;
  market_context: string;
  key_constraints: string[];
  assumptions: string[];
  risks: string[];
  smallest_viable_experiment: string;
  confidence_scores: Record<string, string>;
  generated_at: string;
}

interface UnderstandingState {
  phase: UnderstandingPhase;
  sessionId: string | null;
  currentQuestion: UnderstandingQuestion | null;
  questionNumber: number;
  totalQuestions: number;
  answeredQuestions: { question: UnderstandingQuestion; answer: string }[];
  brief: RationalisedIdeaBrief | null;
  artifactId: string | null;
  briefVersion: number;
  error: string | null;
  debugId?: string;
}

const INITIAL_STATE: UnderstandingState = {
  phase: "idle",
  sessionId: null,
  currentQuestion: null,
  questionNumber: 0,
  totalQuestions: 0,
  answeredQuestions: [],
  brief: null,
  artifactId: null,
  briefVersion: 0,
  error: null,
};

/**
 * Custom hook managing the understanding interview lifecycle.
 *
 * State machine: idle → starting → questioning → loading_next → ... → finalizing → viewing_brief
 * Supports back-navigation, answer editing, and brief section editing.
 */
export function useUnderstandingInterview() {
  const { getToken } = useAuth();
  const [state, setState] = useState<UnderstandingState>(INITIAL_STATE);

  /**
   * Start understanding interview from completed onboarding session.
   */
  const startInterview = useCallback(
    async (onboardingSessionId: string) => {
      setState((s) => ({ ...s, phase: "starting", error: null }));

      try {
        const response = await apiFetch("/api/understanding/start", getToken, {
          method: "POST",
          body: JSON.stringify({ session_id: onboardingSessionId }),
        });

        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.detail || `API error: ${response.status}`);
        }

        const data = await response.json();
        setState((s) => ({
          ...s,
          phase: "questioning",
          sessionId: data.understanding_session_id,
          currentQuestion: data.question,
          questionNumber: data.question_number,
          totalQuestions: data.total_questions,
          answeredQuestions: [],
        }));
      } catch (err) {
        setState((s) => ({
          ...s,
          phase: "error",
          error: (err as Error).message,
        }));
      }
    },
    [getToken],
  );

  /**
   * Submit answer to current question.
   */
  const submitAnswer = useCallback(
    async (questionId: string, answer: string) => {
      if (!state.sessionId) return;

      setState((s) => ({ ...s, phase: "loading_next", error: null }));

      try {
        const response = await apiFetch(
          `/api/understanding/${state.sessionId}/answer`,
          getToken,
          {
            method: "POST",
            body: JSON.stringify({ question_id: questionId, answer }),
          },
        );

        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.detail || `API error: ${response.status}`);
        }

        const data = await response.json();

        // Store answered question
        const newAnsweredQuestions = [
          ...state.answeredQuestions,
          { question: state.currentQuestion!, answer },
        ];

        // Check if interview is complete
        if (data.is_complete) {
          // Auto-finalize
          setState((s) => ({
            ...s,
            answeredQuestions: newAnsweredQuestions,
            phase: "finalizing",
          }));

          // Brief shimmer delay
          await new Promise((r) => setTimeout(r, 500));
          await finalize();
        } else {
          // Show next question
          setState((s) => ({
            ...s,
            answeredQuestions: newAnsweredQuestions,
            currentQuestion: data.next_question,
            questionNumber: data.question_number,
            totalQuestions: data.total_questions,
            phase: "questioning",
          }));
        }
      } catch (err) {
        setState((s) => ({
          ...s,
          phase: "error",
          error: (err as Error).message,
        }));
      }
    },
    [getToken, state.sessionId, state.currentQuestion, state.answeredQuestions],
  );

  /**
   * Edit a previous answer (triggers re-adaptation if needed).
   */
  const editAnswer = useCallback(
    async (questionId: string, newAnswer: string) => {
      if (!state.sessionId) return;

      setState((s) => ({ ...s, phase: "loading_next", error: null }));

      try {
        const response = await apiFetch(
          `/api/understanding/${state.sessionId}/answer`,
          getToken,
          {
            method: "PATCH",
            body: JSON.stringify({ question_id: questionId, new_answer: newAnswer }),
          },
        );

        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.detail || `API error: ${response.status}`);
        }

        const data = await response.json();

        // Update answered questions with new answer
        const updatedAnsweredQuestions = state.answeredQuestions.map((qa) =>
          qa.question.id === questionId ? { ...qa, answer: newAnswer } : qa,
        );

        // If questions were regenerated, rebuild question list
        if (data.regenerated) {
          setState((s) => ({
            ...s,
            answeredQuestions: updatedAnsweredQuestions,
            currentQuestion: data.updated_questions[data.current_question_number - 1] || null,
            questionNumber: data.current_question_number,
            totalQuestions: data.total_questions,
            phase: "questioning",
          }));
        } else {
          setState((s) => ({
            ...s,
            answeredQuestions: updatedAnsweredQuestions,
            phase: "questioning",
          }));
        }
      } catch (err) {
        setState((s) => ({
          ...s,
          phase: "error",
          error: (err as Error).message,
        }));
      }
    },
    [getToken, state.sessionId, state.answeredQuestions],
  );

  /**
   * Navigate back to a previous question for editing.
   */
  const navigateBack = useCallback(
    (questionIndex: number) => {
      const targetQuestion = state.answeredQuestions[questionIndex];
      if (!targetQuestion) return;

      setState((s) => ({
        ...s,
        phase: "editing_answer",
        currentQuestion: targetQuestion.question,
        questionNumber: questionIndex + 1,
      }));
    },
    [state.answeredQuestions],
  );

  /**
   * Finalize interview and generate Rationalised Idea Brief.
   */
  const finalize = useCallback(async () => {
    if (!state.sessionId) return;

    setState((s) => ({ ...s, phase: "finalizing", error: null }));

    try {
      const response = await apiFetch(
        `/api/understanding/${state.sessionId}/finalize`,
        getToken,
        {
          method: "POST",
        },
      );

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || `API error: ${response.status}`);
      }

      const data = await response.json();
      setState((s) => ({
        ...s,
        phase: "viewing_brief",
        brief: data.brief,
        artifactId: data.artifact_id,
        briefVersion: data.version,
      }));
    } catch (err) {
      setState((s) => ({
        ...s,
        phase: "error",
        error: (err as Error).message,
      }));
    }
  }, [getToken, state.sessionId]);

  /**
   * Edit a section in the Rationalised Idea Brief.
   * Takes projectId as first arg (backend expects project_id, not artifactId).
   */
  const editBriefSection = useCallback(
    async (projectId: string, sectionKey: string, newContent: string) => {
      if (!projectId) return;

      // Optimistic update — keep user's text visible even on failure
      setState((s) => ({
        ...s,
        brief: s.brief
          ? {
              ...s.brief,
              [sectionKey]: newContent,
            }
          : null,
      }));

      try {
        const response = await apiFetch(
          `/api/understanding/${projectId}/brief`,
          getToken,
          {
            method: "PATCH",
            body: JSON.stringify({ section_key: sectionKey, new_content: newContent }),
          },
        );

        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.detail || `API error: ${response.status}`);
        }

        const data = await response.json();

        // Update confidence score
        setState((s) => ({
          ...s,
          brief: s.brief
            ? {
                ...s.brief,
                confidence_scores: {
                  ...s.brief.confidence_scores,
                  [sectionKey]: data.new_confidence,
                },
              }
            : null,
          briefVersion: data.version,
        }));

        toast.success("Section updated");
      } catch (err) {
        // Do NOT revert state — keep user's text visible (locked decision)
        setState((s) => ({
          ...s,
          error: (err as Error).message,
        }));
        toast.error("Failed to save section. Tap to retry.", {
          action: {
            label: "Retry",
            onClick: () => editBriefSection(projectId, sectionKey, newContent),
          },
        });
      }
    },
    [getToken],
  );

  /**
   * Re-interview: Reset session for major changes.
   */
  const reInterview = useCallback(async () => {
    if (!state.sessionId) return;

    setState((s) => ({ ...s, phase: "re_interviewing", error: null }));

    try {
      const response = await apiFetch(
        `/api/understanding/${state.sessionId}/re-interview`,
        getToken,
        {
          method: "POST",
        },
      );

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || `API error: ${response.status}`);
      }

      const data = await response.json();
      setState((s) => ({
        ...s,
        phase: "questioning",
        currentQuestion: data.question,
        questionNumber: data.question_number,
        totalQuestions: data.total_questions,
        answeredQuestions: [],
      }));
    } catch (err) {
      setState((s) => ({
        ...s,
        phase: "error",
        error: (err as Error).message,
      }));
    }
  }, [getToken, state.sessionId]);

  /**
   * Resume existing session.
   */
  const resumeSession = useCallback(
    async (sessionId: string) => {
      setState((s) => ({ ...s, phase: "starting", error: null }));

      try {
        const response = await apiFetch(`/api/understanding/${sessionId}`, getToken, {
          method: "GET",
        });

        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.detail || `API error: ${response.status}`);
        }

        const data = await response.json();

        // Determine phase based on session state
        let phase: UnderstandingPhase = "questioning";
        if (data.brief) {
          phase = "viewing_brief";
        }

        setState({
          phase,
          sessionId: data.id,
          currentQuestion: data.current_question || null,
          questionNumber: data.current_question_index || 0,
          totalQuestions: data.total_questions || 0,
          answeredQuestions: data.answered_questions || [],
          brief: data.brief || null,
          artifactId: data.artifact_id || null,
          briefVersion: data.version || 0,
          error: null,
        });
      } catch (err) {
        setState((s) => ({
          ...s,
          phase: "error",
          error: (err as Error).message,
        }));
      }
    },
    [getToken],
  );

  /**
   * Reset to initial state.
   */
  const reset = useCallback(() => {
    setState(INITIAL_STATE);
  }, []);

  return {
    state,
    startInterview,
    submitAnswer,
    editAnswer,
    navigateBack,
    finalize,
    editBriefSection,
    reInterview,
    resumeSession,
    reset,
  };
}
