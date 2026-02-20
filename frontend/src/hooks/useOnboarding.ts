"use client";

import { useState, useCallback } from "react";
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
  project_id?: string | null;
  current_question_index: number;
  total_questions: number;
  created_at: string;
}

export interface ProjectSummary {
  id: string;
  name: string;
  status: string;
  created_at: string;
}

export interface ProjectLimitError {
  code: "project_limit_reached";
  message: string;
  active_count: number;
  max_projects: number;
  upgrade_url: string;
  projects_url: string;
  active_projects: ProjectSummary[];
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
  projectLimitError: ProjectLimitError | null;
  isLoading: boolean;
  inProgressSessions: OnboardingSessionInfo[];
  completedWithoutProjectSessions: OnboardingSessionInfo[];
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
  projectLimitError: null,
  isLoading: false,
  inProgressSessions: [],
  completedWithoutProjectSessions: [],
};

/**
 * Custom hook managing the full onboarding session lifecycle.
 *
 * State machine: idea_input → expanding (optional) → questioning → finalizing → viewing_snapshot
 */
export function useOnboarding() {
  const { getToken } = useAuth();
  const [state, setState] = useState<OnboardingState>(INITIAL_STATE);

  const isProjectLimitError = (detail: unknown): detail is ProjectLimitError => {
    if (!detail || typeof detail !== "object") return false;
    const candidate = detail as Partial<ProjectLimitError>;
    return (
      candidate.code === "project_limit_reached" &&
      typeof candidate.message === "string" &&
      typeof candidate.active_count === "number" &&
      typeof candidate.max_projects === "number"
    );
  };

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
          projectLimitError: null,
        }));
        return;
      }

      setState((s) => ({
        ...s,
        phase: "loading_question",
        isLoading: true,
        idea: trimmed,
        error: null,
        projectLimitError: null,
      }));

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
          projectLimitError: null,
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
    setState((s) => ({ ...s, phase: "loading_question", isLoading: true, error: null, projectLimitError: null }));

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
        projectLimitError: null,
        isLoading: false,
      }));
    }
  }, [getToken, state.idea]);

  /**
   * Finalize session and generate ThesisSnapshot.
   */
  const finalize = useCallback(async () => {
    if (!state.sessionId) return;

    setState((s) => ({ ...s, phase: "finalizing", isLoading: true, error: null, projectLimitError: null }));

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
        projectLimitError: null,
        isLoading: false,
      }));
    }
  }, [getToken, state.sessionId]);

  /**
   * Submit answer to current question.
   */
  const submitAnswer = useCallback(
    async (questionId: string, answer: string) => {
      if (!state.sessionId) return;

      setState((s) => ({ ...s, isLoading: true, error: null, projectLimitError: null }));

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
          projectLimitError: null,
          isLoading: false,
        }));
      }
    },
    [getToken, state.sessionId, state.totalQuestions, finalize],
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
            projectLimitError: null,
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
      setState((s) => ({ ...s, isLoading: true, error: null, projectLimitError: null }));

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
          projectLimitError: null,
          isLoading: false,
          inProgressSessions: [],
          completedWithoutProjectSessions: [],
        });
      } catch (err) {
        setState((s) => ({
          ...s,
          phase: "error",
          error: (err as Error).message,
          projectLimitError: null,
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
        setState((s) => ({
          ...s,
          phase: "idea_input",
          projectLimitError: null,
          inProgressSessions: [],
          completedWithoutProjectSessions: [],
          isLoading: false,
        }));
        return;
      }

      const sessions: OnboardingSessionInfo[] = await response.json();
      const inProgressSessions = sessions.filter((s) => s.status === "in_progress");
      const completedWithoutProjectSessions = sessions.filter(
        (s) => s.status === "completed" && !s.project_id,
      );

      if (inProgressSessions.length > 0 || completedWithoutProjectSessions.length > 0) {
        setState((s) => ({
          ...s,
          phase: "idle",
          inProgressSessions,
          completedWithoutProjectSessions,
          isLoading: false,
        }));
      } else {
        setState((s) => ({
          ...s,
          phase: "idea_input",
          projectLimitError: null,
          inProgressSessions: [],
          completedWithoutProjectSessions: [],
          isLoading: false,
        }));
      }
    } catch {
      // On error, just go to idea_input
      setState((s) => ({
        ...s,
        phase: "idea_input",
        projectLimitError: null,
        inProgressSessions: [],
        completedWithoutProjectSessions: [],
        isLoading: false,
      }));
    }
  }, [getToken]);

  /**
   * Start fresh onboarding (skip active sessions).
   */
  const startFresh = useCallback(() => {
    setState((s) => ({
      ...s,
      phase: "idea_input",
      error: null,
      projectLimitError: null,
      inProgressSessions: [],
      completedWithoutProjectSessions: [],
    }));
  }, []);

  /**
   * Create project from completed onboarding session.
   */
  const createProject = useCallback(async () => {
    if (!state.sessionId) return;

    setState((s) => ({ ...s, isLoading: true, error: null, projectLimitError: null }));

    try {
      const response = await apiFetch(`/api/onboarding/${state.sessionId}/create-project`, getToken, {
        method: "POST",
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        const detail = errorData?.detail;

        // Handle project limit error (403)
        if (response.status === 403 && isProjectLimitError(detail)) {
          setState((s) => ({
            ...s,
            phase: "error",
            error: detail.message,
            projectLimitError: detail,
            isLoading: false,
          }));
          return;
        }

        const detailMessage =
          typeof detail === "string"
            ? detail
            : typeof detail === "object" &&
                detail !== null &&
                "message" in detail &&
                typeof (detail as { message?: unknown }).message === "string"
              ? (detail as { message: string }).message
              : `API error: ${response.status}`;
        throw new Error(detailMessage);
      }

      const data = await response.json();

      // Trigger teaser artifact generation (non-blocking for 409/accepted states).
      try {
        const generateResponse = await apiFetch("/api/artifacts/generate", getToken, {
          method: "POST",
          body: JSON.stringify({ project_id: data.project_id }),
        });
        if (!generateResponse.ok && generateResponse.status !== 409) {
          // Teaser page can still poll and recover even if generation call fails.
          console.warn("Failed to trigger artifact generation", generateResponse.status);
        }
      } catch {
        // Non-fatal: teaser page can still render and allow manual subscribe flow.
      }

      setState((s) => ({ ...s, isLoading: false }));

      const sessionQuery = state.sessionId
        ? `?sessionId=${encodeURIComponent(state.sessionId)}`
        : "";
      window.location.href = `/projects/${data.project_id}/teaser${sessionQuery}`;
    } catch (err) {
      setState((s) => ({
        ...s,
        phase: "error",
        error: (err as Error).message,
        projectLimitError: null,
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
