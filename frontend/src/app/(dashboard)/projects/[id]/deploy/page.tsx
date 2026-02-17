"use client";

import { useState, useCallback } from "react";
import { useParams } from "next/navigation";
import { ChevronLeft, Square, CheckSquare2 } from "lucide-react";
import Link from "next/link";
import { DeployReadinessPanel } from "@/components/deploy/DeployReadinessPanel";
import {
  DeployPathCard,
  type DeployPathOption,
} from "@/components/deploy/DeployPathCard";
import { cn } from "@/lib/utils";

interface DeployReadinessData {
  project_id: string;
  overall_status: "green" | "yellow" | "red";
  ready: boolean;
  blocking_issues: Array<{
    id: string;
    title: string;
    status: string;
    message: string;
    fix_instruction?: string | null;
  }>;
  warnings: Array<{
    id: string;
    title: string;
    status: string;
    message: string;
    fix_instruction?: string | null;
  }>;
  deploy_paths: DeployPathOption[];
  recommended_path: string;
}

interface ChecklistItem {
  step: string;
  completed: boolean;
}

export default function DeployPage() {
  const params = useParams<{ id: string }>();
  const projectId = params.id;

  const [readinessData, setReadinessData] =
    useState<DeployReadinessData | null>(null);
  const [selectedPathId, setSelectedPathId] = useState<string | null>(null);
  const [checklist, setChecklist] = useState<ChecklistItem[]>([]);
  const [secretsChecklist, setSecretsChecklist] = useState<ChecklistItem[]>([]);

  const handleDataLoaded = useCallback((data: DeployReadinessData) => {
    setReadinessData(data);

    // Derive secrets checklist from blocking issues with env_var type
    const secretItems = data.blocking_issues
      .filter(
        (issue) =>
          issue.fix_instruction &&
          (issue.fix_instruction.toLowerCase().includes("export ") ||
            issue.fix_instruction.toLowerCase().includes("env") ||
            issue.id.startsWith("env_")),
      )
      .map((issue) => ({
        step: issue.fix_instruction ?? issue.title,
        completed: false,
      }));
    setSecretsChecklist(secretItems);
  }, []);

  function handleSelectPath(path: DeployPathOption) {
    setSelectedPathId(path.id);
    setChecklist(path.steps.map((step) => ({ step, completed: false })));
  }

  function toggleChecklistItem(index: number) {
    setChecklist((prev) =>
      prev.map((item, i) =>
        i === index ? { ...item, completed: !item.completed } : item,
      ),
    );
  }

  function toggleSecretsItem(index: number) {
    setSecretsChecklist((prev) =>
      prev.map((item, i) =>
        i === index ? { ...item, completed: !item.completed } : item,
      ),
    );
  }

  const selectedPath =
    readinessData?.deploy_paths.find((p) => p.id === selectedPathId) ?? null;
  const completedSteps = checklist.filter((i) => i.completed).length;

  return (
    <div className="space-y-8">
      {/* Back link */}
      <div className="flex items-center gap-3">
        <Link
          href={`/projects/${projectId}/build`}
          className="flex items-center gap-1.5 text-sm text-white/40 hover:text-white/70 transition-colors"
        >
          <ChevronLeft className="w-4 h-4" />
          Back to build
        </Link>
      </div>

      {/* Page header */}
      <div>
        <h1 className="text-2xl font-bold text-white">Deploy Readiness</h1>
        <p className="text-white/50 mt-1">
          Check your project&apos;s deployment readiness and follow the step-by-step guide.
        </p>
      </div>

      {/* Traffic light panel */}
      <DeployReadinessPanel
        projectId={projectId}
        onDataLoaded={handleDataLoaded}
      />

      {/* Deploy paths */}
      {readinessData && readinessData.deploy_paths.length > 0 && (
        <div className="space-y-4">
          <div>
            <h2 className="text-lg font-semibold text-white">
              Choose your deploy path
            </h2>
            <p className="text-sm text-white/40 mt-0.5">
              Select the option that best fits your project. Each path includes
              a step-by-step guide.
            </p>
          </div>

          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {readinessData.deploy_paths.map((path) => (
              <DeployPathCard
                key={path.id}
                path={path}
                recommended={path.id === readinessData.recommended_path}
                selected={path.id === selectedPathId}
                onSelect={() => handleSelectPath(path)}
              />
            ))}
          </div>
        </div>
      )}

      {/* Secrets checklist (derived from blocking env issues) */}
      {secretsChecklist.length > 0 && (
        <div className="glass-strong rounded-2xl border border-amber-500/20 p-5 space-y-4">
          <h3 className="text-base font-semibold text-amber-400">
            Required secrets &amp; env vars
          </h3>
          <div className="space-y-2">
            {secretsChecklist.map((item, i) => (
              <button
                key={i}
                onClick={() => toggleSecretsItem(i)}
                className="w-full flex items-start gap-3 px-3 py-2.5 rounded-xl hover:bg-white/5 transition-colors text-left"
              >
                {item.completed ? (
                  <CheckSquare2 className="w-4 h-4 mt-0.5 flex-shrink-0 text-emerald-400" />
                ) : (
                  <Square className="w-4 h-4 mt-0.5 flex-shrink-0 text-white/30" />
                )}
                <code className="text-xs font-mono text-white/70 leading-relaxed">
                  {item.step}
                </code>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Step-by-step guide for selected path */}
      {selectedPath && checklist.length > 0 && (
        <div className="glass-strong rounded-2xl border border-white/10 p-5 space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-base font-semibold text-white">
              Deploy guide: {selectedPath.name}
            </h3>
            <span className="text-xs text-white/40">
              {completedSteps}/{checklist.length} steps completed
            </span>
          </div>

          {/* Progress bar */}
          <div className="h-1.5 bg-white/10 rounded-full overflow-hidden">
            <div
              className={cn(
                "h-full bg-brand rounded-full transition-all duration-300",
                completedSteps === checklist.length && "bg-emerald-500",
              )}
              style={{
                width: `${checklist.length > 0 ? (completedSteps / checklist.length) * 100 : 0}%`,
              }}
            />
          </div>

          {/* Steps checklist */}
          <div className="space-y-2">
            {checklist.map((item, i) => (
              <button
                key={i}
                onClick={() => toggleChecklistItem(i)}
                className={cn(
                  "w-full flex items-start gap-3 px-4 py-3 rounded-xl border transition-all text-left",
                  item.completed
                    ? "border-emerald-500/20 bg-emerald-500/5"
                    : "border-white/10 hover:border-white/20 hover:bg-white/5",
                )}
              >
                <div
                  className={cn(
                    "flex-shrink-0 w-6 h-6 rounded-full border-2 flex items-center justify-center mt-0.5",
                    item.completed
                      ? "border-emerald-500 bg-emerald-500"
                      : "border-white/20",
                  )}
                >
                  {item.completed ? (
                    <CheckSquare2 className="w-3.5 h-3.5 text-white" />
                  ) : (
                    <span className="text-xs text-white/30 font-mono">{i + 1}</span>
                  )}
                </div>
                <span
                  className={cn(
                    "text-sm leading-relaxed",
                    item.completed ? "text-white/40 line-through" : "text-white/80",
                  )}
                >
                  {item.step}
                </span>
              </button>
            ))}
          </div>

          {completedSteps === checklist.length && (
            <div className="rounded-xl border border-emerald-500/30 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-400 text-center font-medium">
              All steps completed. Your project is deployed!
            </div>
          )}
        </div>
      )}
    </div>
  );
}
