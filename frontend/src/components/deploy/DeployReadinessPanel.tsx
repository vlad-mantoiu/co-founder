"use client";

import { useState, useEffect } from "react";
import { ChevronDown, ChevronRight, Copy, CheckCheck, AlertTriangle, XCircle, CheckCircle } from "lucide-react";
import { useAuth } from "@clerk/nextjs";
import { apiFetch } from "@/lib/api";
import { cn } from "@/lib/utils";

interface DeployIssue {
  id: string;
  title: string;
  status: string;
  message: string;
  fix_instruction?: string | null;
}

interface DeployReadinessData {
  project_id: string;
  overall_status: "green" | "yellow" | "red";
  ready: boolean;
  blocking_issues: DeployIssue[];
  warnings: DeployIssue[];
  deploy_paths: DeployPathOption[];
  recommended_path: string;
}

interface DeployPathOption {
  id: string;
  name: string;
  description: string;
  difficulty: string;
  cost: string;
  tradeoffs: string[];
  steps: string[];
}

interface DeployReadinessPanelProps {
  projectId: string;
  onDataLoaded?: (data: DeployReadinessData) => void;
}

const STATUS_CONFIG = {
  green: {
    label: "Ready to deploy",
    color: "bg-emerald-500",
    ring: "ring-emerald-500/30",
    text: "text-emerald-400",
    icon: CheckCircle,
    description: "All checks passed. Your project is ready to deploy.",
  },
  yellow: {
    label: "Some issues to fix",
    color: "bg-amber-500",
    ring: "ring-amber-500/30",
    text: "text-amber-400",
    icon: AlertTriangle,
    description: "Non-blocking warnings found. You can deploy but should review these.",
  },
  red: {
    label: "Not ready to deploy",
    color: "bg-red-500",
    ring: "ring-red-500/30",
    text: "text-red-400",
    icon: XCircle,
    description: "Blocking issues must be resolved before deployment.",
  },
} as const;

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);

  async function handleCopy() {
    await navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }

  return (
    <button
      onClick={handleCopy}
      className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-white/5 hover:bg-white/10 border border-white/10 text-xs text-white/60 hover:text-white transition-colors"
    >
      {copied ? (
        <CheckCheck className="w-3 h-3 text-emerald-400" />
      ) : (
        <Copy className="w-3 h-3" />
      )}
      {copied ? "Copied" : "Copy"}
    </button>
  );
}

function IssueItem({ issue }: { issue: DeployIssue }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="rounded-xl border border-white/10 bg-white/5 overflow-hidden">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-white/5 transition-colors"
      >
        <ChevronRight
          className={cn(
            "w-4 h-4 text-white/40 flex-shrink-0 transition-transform",
            expanded && "rotate-90",
          )}
        />
        <span className="text-sm text-white/80 flex-1">{issue.title}</span>
      </button>
      {expanded && (
        <div className="px-4 pb-4 space-y-3 border-t border-white/5">
          <p className="text-sm text-white/60 pt-3">{issue.message}</p>
          {issue.fix_instruction && (
            <div className="space-y-2">
              <p className="text-xs text-white/40 uppercase tracking-wide font-medium">
                Fix instruction
              </p>
              <div className="flex items-start gap-2">
                <pre className="flex-1 text-xs text-white/70 bg-black/30 border border-white/10 rounded-lg px-3 py-2 overflow-x-auto whitespace-pre-wrap font-mono">
                  {issue.fix_instruction}
                </pre>
                <CopyButton text={issue.fix_instruction} />
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export function DeployReadinessPanel({
  projectId,
  onDataLoaded,
}: DeployReadinessPanelProps) {
  const { getToken } = useAuth();
  const [data, setData] = useState<DeployReadinessData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showAll, setShowAll] = useState(false);

  useEffect(() => {
    async function fetchReadiness() {
      try {
        const res = await apiFetch(
          `/api/deploy-readiness/${projectId}`,
          getToken,
          {},
        );
        if (!res.ok) {
          throw new Error(`Failed to load deploy readiness: ${res.status}`);
        }
        const json: DeployReadinessData = await res.json();
        setData(json);
        onDataLoaded?.(json);
      } catch (err) {
        setError((err as Error).message);
      } finally {
        setLoading(false);
      }
    }
    fetchReadiness();
  }, [projectId, getToken, onDataLoaded]);

  if (loading) {
    return (
      <div className="glass-strong rounded-2xl border border-white/10 p-6 space-y-4">
        <div className="flex items-center gap-4">
          <div className="w-16 h-16 rounded-full bg-white/10 animate-pulse" />
          <div className="flex-1 space-y-2">
            <div className="h-6 w-48 bg-white/10 rounded-lg animate-pulse" />
            <div className="h-4 w-72 bg-white/10 rounded-lg animate-pulse" />
          </div>
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="glass-strong rounded-2xl border border-red-500/20 p-6">
        <p className="text-sm text-red-400">
          {error ?? "Failed to load deploy readiness."}
        </p>
      </div>
    );
  }

  const config = STATUS_CONFIG[data.overall_status];
  const StatusIcon = config.icon;

  return (
    <div className="glass-strong rounded-2xl border border-white/10 overflow-hidden">
      {/* Traffic light header */}
      <div className="px-6 py-5 flex items-center gap-5 border-b border-white/10">
        <div
          className={cn(
            "w-16 h-16 rounded-full flex-shrink-0 flex items-center justify-center",
            "ring-4 shadow-lg",
            config.color,
            config.ring,
          )}
        >
          <StatusIcon className="w-7 h-7 text-white" />
        </div>
        <div>
          <h3 className={cn("text-2xl font-bold", config.text)}>
            {config.label}
          </h3>
          <p className="text-sm text-white/50 mt-0.5">{config.description}</p>
        </div>
      </div>

      {/* Blocking issues */}
      {data.blocking_issues.length > 0 && (
        <div className="px-6 py-4 border-b border-white/10 space-y-3">
          <div className="flex items-center gap-2">
            <XCircle className="w-4 h-4 text-red-400" />
            <h4 className="text-sm font-semibold text-red-400">
              Blocking issues ({data.blocking_issues.length})
            </h4>
          </div>
          <div className="space-y-2">
            {data.blocking_issues.map((issue) => (
              <IssueItem key={issue.id} issue={issue} />
            ))}
          </div>
        </div>
      )}

      {/* Warnings */}
      {data.warnings.length > 0 && (
        <div className="px-6 py-4 border-b border-white/10 space-y-3">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-amber-400" />
            <h4 className="text-sm font-semibold text-amber-400">
              Warnings ({data.warnings.length})
            </h4>
          </div>
          <div className="space-y-2">
            {data.warnings.map((issue) => (
              <IssueItem key={issue.id} issue={issue} />
            ))}
          </div>
        </div>
      )}

      {/* Passing checks toggle */}
      {data.blocking_issues.length === 0 && data.warnings.length === 0 && (
        <div className="px-6 py-4">
          <div className="flex items-center gap-2">
            <CheckCircle className="w-4 h-4 text-emerald-400" />
            <p className="text-sm text-emerald-400">
              All checks passed
            </p>
          </div>
        </div>
      )}

      {/* Show all checks toggle (when there's a mix) */}
      {(data.blocking_issues.length > 0 || data.warnings.length > 0) && (
        <div className="px-6 py-3">
          <button
            onClick={() => setShowAll(!showAll)}
            className="flex items-center gap-1.5 text-xs text-white/40 hover:text-white/60 transition-colors"
          >
            <ChevronDown
              className={cn(
                "w-3.5 h-3.5 transition-transform",
                showAll && "rotate-180",
              )}
            />
            {showAll ? "Hide passing checks" : "Show all passing checks"}
          </button>
          {showAll && (
            <div className="mt-3 flex items-center gap-2">
              <CheckCircle className="w-4 h-4 text-emerald-400 flex-shrink-0" />
              <p className="text-sm text-white/40">
                Other checks passed successfully.
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
