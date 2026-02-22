"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { toast } from "sonner";
import { apiFetch } from "@/lib/api";

// ──────────────────────────────────────────────────────────────────────────────
// Types
// ──────────────────────────────────────────────────────────────────────────────

export type PreviewState =
  | "checking"
  | "loading"
  | "active"
  | "blocked"
  | "expired"
  | "paused"        // sandbox was beta_paused — show resume button
  | "resuming"      // resume API call in progress
  | "resume_failed" // both retry attempts failed
  | "error";

export type DeviceMode = "desktop" | "tablet" | "mobile";

export interface UsePreviewPaneReturn {
  state: PreviewState;
  deviceMode: DeviceMode;
  setDeviceMode: (mode: DeviceMode) => void;
  previewUrl: string;      // returns activePreviewUrl
  blockReason: string | null;
  timeRemaining: number | null; // seconds, null when not applicable
  markLoaded: () => void;
  onRetry: () => void;
  handleResume: () => void;                                              // NEW
  resumeErrorType: "sandbox_expired" | "sandbox_unreachable" | null;   // NEW
}

interface PreviewCheckResponse {
  embeddable: boolean;
  preview_url: string;
  reason: string | null;
}

// ──────────────────────────────────────────────────────────────────────────────
// Hook
// ──────────────────────────────────────────────────────────────────────────────

export function usePreviewPane(
  previewUrl: string,
  sandboxExpiresAt: string | null,
  sandboxPaused: boolean,   // NEW param
  jobId: string,
  getToken: () => Promise<string | null>,
): UsePreviewPaneReturn {
  const [state, setState] = useState<PreviewState>("checking");
  const [deviceMode, setDeviceMode] = useState<DeviceMode>("desktop");
  const [blockReason, setBlockReason] = useState<string | null>(null);
  const [timeRemaining, setTimeRemaining] = useState<number | null>(null);
  const [activePreviewUrl, setActivePreviewUrl] = useState(previewUrl);
  const [resumeErrorType, setResumeErrorType] = useState<"sandbox_expired" | "sandbox_unreachable" | null>(null);

  // Refs for cleanup and one-shot toast guard
  const loadingTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const expiryIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const toastShownRef = useRef(false);
  const retryCountRef = useRef(0);

  // ─── Cleanup helpers ────────────────────────────────────────────────────────

  const clearLoadingTimeout = useCallback(() => {
    if (loadingTimeoutRef.current !== null) {
      clearTimeout(loadingTimeoutRef.current);
      loadingTimeoutRef.current = null;
    }
  }, []);

  const clearExpiryInterval = useCallback(() => {
    if (expiryIntervalRef.current !== null) {
      clearInterval(expiryIntervalRef.current);
      expiryIntervalRef.current = null;
    }
  }, []);

  // ─── Expiry countdown (runs while active) ───────────────────────────────────

  const startExpiryCountdown = useCallback(() => {
    if (!sandboxExpiresAt) return;

    clearExpiryInterval();

    const tick = () => {
      const remaining = Math.floor(
        (new Date(sandboxExpiresAt).getTime() - Date.now()) / 1000,
      );

      setTimeRemaining(remaining);

      if (remaining <= 300 && !toastShownRef.current) {
        toast("Your sandbox expires in less than 5 minutes", {
          duration: 8000,
        });
        toastShownRef.current = true;
      }

      if (remaining <= 0) {
        clearExpiryInterval();
        setState("expired");
        setTimeRemaining(0);
      }
    };

    // Run immediately, then every 30 seconds
    tick();
    expiryIntervalRef.current = setInterval(tick, 30_000);
  }, [sandboxExpiresAt, clearExpiryInterval]);

  // ─── Preview-check API call ──────────────────────────────────────────────────

  const runPreviewCheck = useCallback(async () => {
    setState("checking");
    setBlockReason(null);
    clearLoadingTimeout();
    clearExpiryInterval();

    try {
      const res = await apiFetch(
        `/api/generation/${jobId}/preview-check`,
        getToken,
      );

      if (!res.ok) {
        setState("error");
        return;
      }

      const data: PreviewCheckResponse = await res.json();

      if (data.embeddable) {
        setState("loading");

        // 30-second loading timeout
        loadingTimeoutRef.current = setTimeout(() => {
          setState("error");
        }, 30_000);
      } else {
        setBlockReason(data.reason ?? null);
        setState("blocked");
      }
    } catch {
      setState("error");
    }
  }, [jobId, getToken, clearLoadingTimeout, clearExpiryInterval]);

  // ─── markLoaded — called by PreviewPane iframe.onLoad ───────────────────────

  const markLoaded = useCallback(() => {
    clearLoadingTimeout();
    setState("active");
    startExpiryCountdown();
  }, [clearLoadingTimeout, startExpiryCountdown]);

  // ─── onRetry — resets to checking ───────────────────────────────────────────

  const onRetry = useCallback(() => {
    retryCountRef.current += 1;
    runPreviewCheck();
  }, [runPreviewCheck]);

  // ─── handleResume — POST /resume with 2-attempt retry ───────────────────────

  const handleResume = useCallback(async () => {
    setState("resuming");
    setResumeErrorType(null);
    for (let attempt = 0; attempt < 2; attempt++) {
      try {
        const res = await apiFetch(`/api/generation/${jobId}/resume`, getToken, { method: "POST" });
        if (!res.ok) {
          const body = await res.json().catch(() => null);
          if (res.status === 503 && body?.detail?.error_type) {
            throw new Error(body.detail.error_type);
          }
          throw new Error(`HTTP ${res.status}`);
        }
        const data: { preview_url: string; sandbox_id: string } = await res.json();
        setActivePreviewUrl(data.preview_url);
        setState("loading");  // triggers iframe load → markLoaded → active
        return;
      } catch (err) {
        if (attempt === 0) {
          await new Promise(r => setTimeout(r, 5000));
          continue;
        }
        // Final failure — classify error
        const msg = err instanceof Error ? err.message : "";
        if (msg === "sandbox_expired") {
          setResumeErrorType("sandbox_expired");
        } else {
          setResumeErrorType("sandbox_unreachable");
        }
        setState("resume_failed");
      }
    }
  }, [jobId, getToken]);

  // ─── Mount: run preview check or go straight to paused ───────────────────────

  useEffect(() => {
    if (sandboxPaused) {
      setState("paused");
      return;
    }
    runPreviewCheck();

    return () => {
      clearLoadingTimeout();
      clearExpiryInterval();
    };
  }, [sandboxPaused, runPreviewCheck, clearLoadingTimeout, clearExpiryInterval]);

  return {
    state,
    deviceMode,
    setDeviceMode,
    previewUrl: activePreviewUrl,
    blockReason,
    timeRemaining,
    markLoaded,
    onRetry,
    handleResume,
    resumeErrorType,
  };
}
