"use client";

import { useState, useCallback, useEffect } from "react";
import { useAuth } from "@clerk/nextjs";
import { apiFetch } from "@/lib/api";

/**
 * Onboarding phase state machine.
 */
type OnboardingPhase =
  | "idle"
  | "idea_input"
  | "expanding"
  | "questioning"
  | "loading_question"
  | "finalizing"
  | "viewing_snapshot"
  | "error";

/**
 * TypeScript interfaces matching backend Pydantic schemas.
 */
export interface OnboardingQuestion {
  id: string;
  text: string;
  input_type: "text" | "textarea" | "multiple_choice";
  required: boolean;
  options?: string[];
  follow_up_hint?: string;
}

export interface ThesisSnapshot {
  problem: string;
  target_user: string;
  value_prop: string;
  key_constraint: string;
  differentiation?: string | null;
  monetization_hypothesis?: string | null;
  assumptions?: string[] | null;
  risks?: string[] | null;
  smallest_viable_experiment?: string | null;
}

export interface OnboardingSessionInfo {
  id: string;
  idea_text: string;
  status: string;
  current_question_index: number;
  total_questions: number;
  created_at: string;
}

interface OnboardingState {
  phase: OnboardingPhase;
  sessionId: string | null;
  idea: string;
  questions: OnboardingQuestion[];
  answers: Record<string, string>;
  currentQuestionIndex: number;
  totalQuestions: number;
  thesisSnapshot: ThesisSnapshot | null;
  thesisEdits: Record<string, string>;
  error: string | null;
  isLoading: boolean;
  activeSessions: OnboardingSessionInfo[];
}

const INITIAL_STATE: OnboardingState = {
  phase: "idle",
  sessionId: null,
  idea: "",
  questions: [],
  answers: {},
  currentQuestionIndex: 0,
  totalQuestions: 0,
  thesisSnapshot: null,
  thesisEdits: {},
  error: null,
  isLoading: false,
  activeSessions: [],
};

/**
 * Custom hook managing the full onboarding session lifecycle.
 *
 * State machine: idea_input → expanding (optional) → questioning → finalizing → viewing_snapshot
 */
export function useOnboarding() {
  const { getToken } = useAuth();
  const [state, setState] = useState<OnboardingState>(INITIAL_STATE);

  /**
   * Submit initial idea to start onboarding session.
   */
  const submitIdea = useCallback(
    async (idea: string) => {
      const trimmed = idea.trim();
      const wordCount = trimmed.split(/\s+/).length;

      // Smart expand: if < 10 words, prompt for more context
      if (wordCount < 10) {
        setState((s) => ({
          ...s,
          phase: "expanding",
          idea: trimmed,
          error: null,
        }));
        return;
      }

      setState((s) => ({ ...s, phase: "loading_question", isLoading: true, idea: trimmed, error: null }));

      try {
        const response = await apiFetch("/api/onboarding/start", getToken, {
          method: "POST",
          body: JSON.stringify({ idea: trimmed }),
        });

        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.detail || `API error: ${response.status}`);
        }

        const data = await response.json();
        setState((s) => ({
          ...s,
          phase: "questioning",
          sessionId: data.id,
          questions: data.questions,
          answers: data.answers || {},
          currentQuestionIndex: data.current_question_index || 0,
          totalQuestions: data.total_questions,
          isLoading: false,
        }));
      } catch (err) {
        setState((s) => ({
          ...s,
          phase: "error",
          error: (err as Error).message,
          isLoading: false,
        }));
      }
    },
    [getToken],
  );

  /**
   * Continue with idea from "expanding" phase (even if < 10 words).
   */
  const continueAnyway = useCallback(async () => {
    setState((s) => ({ ...s, phase: "loading_question", isLoading: true, error: null }));

    try {
      const response = await apiFetch("/api/onboarding/start", getToken, {
        method: "POST",
        body: JSON.stringify({ idea: state.idea }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || `API error: ${response.status}`);
      }

      const data = await response.json();
      setState((s) => ({
        ...s,
        phase: "questioning",
        sessionId: data.id,
        questions: data.questions,
        answers: data.answers || {},
        currentQuestionIndex: data.current_question_index || 0,
        totalQuestions: data.total_questions,
        isLoading: false,
      }));
    } catch (err) {
      setState((s) => ({
        ...s,
        phase: "error",
        error: (err as Error).message,
        isLoading: false,
      }));
    }
  }, [getToken, state.idea]);

  /**
   * Submit answer to current question.
   */
  const submitAnswer = useCallback(
    async (questionId: string, answer: string) => {
      if (!state.sessionId) return;

      setState((s) => ({ ...s, isLoading: true, error: null }));

      try {
        const response = await apiFetch(`/api/onboarding/${state.sessionId}/answer`, getToken, {
          method: "POST",
          body: JSON.stringify({ question_id: questionId, answer }),
        });

        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.detail || `API error: ${response.status}`);
        }

        const data = await response.json();

        // Update answers and advance index
        setState((s) => ({
          ...s,
          answers: { ...s.answers, [questionId]: answer },
          currentQuestionIndex: data.current_question_index,
          isLoading: false,
        }));

        // If last question, show shimmer then auto-finalize
        if (data.current_question_index >= state.totalQuestions) {
          setState((s) => ({ ...s, phase: "finalizing", isLoading: true }));

          // Brief shimmer before finalize
          await new Promise((r) => setTimeout(r, 500));
          finalize();
        } else {
          // Show shimmer during transition
          setState((s) => ({ ...s, phase: "loading_question" }));
          await new Promise((r) => setTimeout(r, 300));
          setState((s) => ({ ...s, phase: "questioning" }));
        }
      } catch (err) {
        setState((s) => ({
          ...s,
          phase: "error",
          error: (err as Error).message,
          isLoading: false,
        }));
      }
    },
    [getToken, state.sessionId, state.totalQuestions],
  );

  /**
   * Edit a previously answered question.
   */
  const editAnswer = useCallback((questionIndex: number) => {
    setState((s) => ({
      ...s,
      phase: "questioning",
      currentQuestionIndex: questionIndex,
    }));
  }, []);

  /**
   * Finalize session and generate ThesisSnapshot.
   */
  const finalize = useCallback(async () => {
    if (!state.sessionId) return;

    setState((s) => ({ ...s, phase: "finalizing", isLoading: true, error: null }));

    try {
      const response = await apiFetch(`/api/onboarding/${state.sessionId}/finalize`, getToken, {
        method: "POST",
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || `API error: ${response.status}`);
      }

      const data = await response.json();
      setState((s) => ({
        ...s,
        phase: "viewing_snapshot",
        thesisSnapshot: data.thesis_snapshot,
        isLoading: false,
      }));
    } catch (err) {
      setState((s) => ({
        ...s,
        phase: "error",
        error: (err as Error).message,
        isLoading: false,
      }));
    }
  }, [getToken, state.sessionId]);

  /**
   * Edit a field in the thesis snapshot.
   */
  const editThesisField = useCallback(
    async (fieldName: string, newValue: string) => {
      if (!state.sessionId) return;

      // Optimistic update
      setState((s) => ({
        ...s,
        thesisEdits: { ...s.thesisEdits, [fieldName]: newValue },
        thesisSnapshot: s.thesisSnapshot
          ? { ...s.thesisSnapshot, [fieldName]: newValue }
          : null,
      }));

      try {
        const response = await apiFetch(`/api/onboarding/${state.sessionId}/thesis`, getToken, {
          method: "PATCH",
          body: JSON.stringify({ field_name: fieldName, new_value: newValue }),
        });

        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.detail || `API error: ${response.status}`);
        }
      } catch (err) {
        // Revert on error
        setState((s) => {
          const edits = { ...s.thesisEdits };
          delete edits[fieldName];
          return {
            ...s,
            thesisEdits: edits,
            error: (err as Error).message,
          };
        });
      }
    },
    [getToken, state.sessionId],
  );

  /**
   * Resume an existing session.
   */
  const resumeSession = useCallback(
    async (sessionId: string) => {
      setState((s) => ({ ...s, isLoading: true, error: null }));

      try {
        const response = await apiFetch(`/api/onboarding/${sessionId}`, getToken, {
          method: "GET",
        });

        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.detail || `API error: ${response.status}`);
        }

        const data = await response.json();

        // Determine phase based on session state
        let phase: OnboardingPhase = "questioning";
        if (data.thesis_snapshot) {
          phase = "viewing_snapshot";
        } else if (data.current_question_index >= data.total_questions) {
          phase = "finalizing";
        }

        setState({
          phase,
          sessionId: data.id,
          idea: data.idea_text,
          questions: data.questions,
          answers: data.answers,
          currentQuestionIndex: data.current_question_index,
          totalQuestions: data.total_questions,
          thesisSnapshot: data.thesis_snapshot,
          thesisEdits: {},
          error: null,
          isLoading: false,
          activeSessions: [],
        });
      } catch (err) {
        setState((s) => ({
          ...s,
          phase: "error",
          error: (err as Error).message,
          isLoading: false,
        }));
      }
    },
    [getToken],
  );

  /**
   * Fetch active sessions on mount.
   */
  const fetchActiveSessions = useCallback(async () => {
    setState((s) => ({ ...s, isLoading: true }));

    try {
      const response = await apiFetch("/api/onboarding/sessions", getToken, {
        method: "GET",
      });

      if (!response.ok) {
        // If error, just proceed to idea_input
        setState((s) => ({ ...s, phase: "idea_input", isLoading: false }));
        return;
      }

      const sessions: OnboardingSessionInfo[] = await response.json();
      const inProgressSessions = sessions.filter((s) => s.status === "in_progress");

      if (inProgressSessions.length > 0) {
        setState((s) => ({
          ...s,
          phase: "idle",
          activeSessions: inProgressSessions,
          isLoading: false,
        }));
      } else {
        setState((s) => ({ ...s, phase: "idea_input", isLoading: false }));
      }
    } catch (err) {
      // On error, just go to idea_input
      setState((s) => ({ ...s, phase: "idea_input", isLoading: false }));
    }
  }, [getToken]);

  /**
   * Start fresh onboarding (skip active sessions).
   */
  const startFresh = useCallback(() => {
    setState((s) => ({ ...s, phase: "idea_input", activeSessions: [] }));
  }, []);

  /**
   * Create project from completed onboarding session.
   */
  const createProject = useCallback(async () => {
    if (!state.sessionId) return;

    setState((s) => ({ ...s, isLoading: true, error: null }));

    try {
      const response = await apiFetch(`/api/onboarding/${state.sessionId}/create-project`, getToken, {
        method: "POST",
      });

      if (!response.ok) {
        const errorData = await response.json();

        // Handle project limit error (403)
        if (response.status === 403) {
          setState((s) => ({
            ...s,
            phase: "error",
            error: errorData.detail || "Project limit reached. Upgrade to create more projects.",
            isLoading: false,
          }));
          return;
        }

        throw new Error(errorData.detail || `API error: ${response.status}`);
      }

      const data = await response.json();

      // Success - redirect to dashboard
      setState((s) => ({ ...s, isLoading: false }));

      // Redirect to dashboard (or project page when available)
      window.location.href = "/dashboard";
    } catch (err) {
      setState((s) => ({
        ...s,
        phase: "error",
        error: (err as Error).message,
        isLoading: false,
      }));
    }
  }, [getToken, state.sessionId]);

  /**
   * Reset to initial state.
   */
  const reset = useCallback(() => {
    setState(INITIAL_STATE);
  }, []);

  return {
    state,
    submitIdea,
    continueAnyway,
    submitAnswer,
    editAnswer,
    finalize,
    editThesisField,
    resumeSession,
    createProject,
    fetchActiveSessions,
    startFresh,
    reset,
  };
}
