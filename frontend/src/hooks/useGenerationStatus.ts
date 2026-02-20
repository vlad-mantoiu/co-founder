"use client";
import { useState, useEffect, useRef, useCallback } from "react";
import { useAuth } from "@clerk/nextjs";
import { apiFetch } from "@/lib/api";

interface ArtifactStatus {
  status: "not_started" | "generating" | "idle" | "failed";
  has_content: boolean;
}

interface GenerationStatus {
  artifacts: Record<string, ArtifactStatus>;
  all_complete: boolean;
  any_failed: boolean;
}

export function useGenerationStatus(projectId: string | null) {
  const { getToken } = useAuth();
  const [status, setStatus] = useState<GenerationStatus | null>(null);
  const [polling, setPolling] = useState(false);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);

  const stopPolling = useCallback(() => {
    setPolling(false);
    if (intervalRef.current) clearInterval(intervalRef.current);
  }, []);

  const startPolling = useCallback(() => {
    setPolling(true);
  }, []);

  useEffect(() => {
    if (!polling || !projectId) return;

    const poll = async () => {
      try {
        const res = await apiFetch(
          `/api/artifacts/project/${projectId}/generation-status`,
          getToken,
        );
        if (res.ok) {
          const data: GenerationStatus = await res.json();
          setStatus(data);
          if (data.all_complete || data.any_failed) {
            stopPolling();
          }
        }
      } catch {
        /* non-fatal */
      }
    };

    poll(); // immediate first poll
    intervalRef.current = setInterval(poll, 2000);

    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [polling, projectId, getToken, stopPolling]);

  return { status, startPolling, stopPolling, isPolling: polling };
}
