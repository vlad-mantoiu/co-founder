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
  | "error";

export type DeviceMode = "desktop" | "tablet" | "mobile";

export interface UsePreviewPaneReturn {
  state: PreviewState;
  deviceMode: DeviceMode;
  setDeviceMode: (mode: DeviceMode) => void;
  previewUrl: string;
  blockReason: string | null;
  timeRemaining: number | null; // seconds, null when not applicable
  markLoaded: () => void;
  onRetry: () => void;
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
  jobId: string,
  getToken: () => Promise<string | null>,
): UsePreviewPaneReturn {
  const [state, setState] = useState<PreviewState>("checking");
  const [deviceMode, setDeviceMode] = useState<DeviceMode>("desktop");
  const [blockReason, setBlockReason] = useState<string | null>(null);
  const [timeRemaining, setTimeRemaining] = useState<number | null>(null);

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

  // ─── Mount: run preview check ────────────────────────────────────────────────

  useEffect(() => {
    runPreviewCheck();

    return () => {
      clearLoadingTimeout();
      clearExpiryInterval();
    };
  }, [runPreviewCheck, clearLoadingTimeout, clearExpiryInterval]);

  return {
    state,
    deviceMode,
    setDeviceMode,
    previewUrl,
    blockReason,
    timeRemaining,
    markLoaded,
    onRetry,
  };
}
