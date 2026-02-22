"use client";

import { useState, useCallback } from "react";
import { Play, Loader2, AlertCircle } from "lucide-react";
import { apiFetch } from "@/lib/api";
import { useRouter } from "next/navigation";

type ResumeState = "idle" | "resuming" | "success" | "failed";

interface ResumeButtonProps {
  jobId: string;
  projectId: string;
  getToken: () => Promise<string | null>;
}

export function ResumeButton({ jobId, projectId, getToken }: ResumeButtonProps) {
  const [state, setState] = useState<ResumeState>("idle");
  const router = useRouter();

  const handleResume = useCallback(async () => {
    setState("resuming");
    try {
      const res = await apiFetch(`/api/generation/${jobId}/resume`, getToken, { method: "POST" });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setState("success");
      router.push(`/projects/${projectId}/build?job_id=${jobId}`);
    } catch {
      setState("failed");
    }
  }, [jobId, projectId, getToken, router]);

  if (state === "resuming") {
    return (
      <button disabled className="flex items-center gap-1.5 text-xs text-white/50 cursor-wait">
        <Loader2 className="w-3.5 h-3.5 animate-spin" />
        Resuming...
      </button>
    );
  }

  if (state === "failed") {
    return (
      <span className="flex items-center gap-1.5 text-xs text-red-400/80">
        <AlertCircle className="w-3.5 h-3.5" />
        Resume failed
      </span>
    );
  }

  if (state === "success") {
    return (
      <span className="flex items-center gap-1.5 text-xs text-emerald-400/80">
        Redirecting...
      </span>
    );
  }

  return (
    <button
      onClick={handleResume}
      className="flex items-center gap-1.5 text-xs text-white/60 hover:text-white/90 transition-colors"
    >
      <Play className="w-3.5 h-3.5" />
      Resume preview
    </button>
  );
}
