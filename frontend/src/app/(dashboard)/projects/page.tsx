"use client";

import { useState, useEffect } from "react";
import { useAuth } from "@clerk/nextjs";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { FolderOpen, ArrowRight, Plus, AlertCircle } from "lucide-react";
import { apiFetch } from "@/lib/api";
import { GlassCard } from "@/components/ui/glass-card";

interface Project {
  id: string;
  name: string;
  description: string;
  github_repo: string | null;
  status: string;
  created_at: string;
  stage_number: number | null;
  has_pending_gate: boolean;
  has_understanding_session: boolean;
  has_brief: boolean;
  has_execution_plan: boolean;
}

interface ProjectState {
  label: string;
  color: string;
  action: string;
  route: string;
  stageIndex: number; // 0=understanding, 1=strategy, 2=build, 3=deploy
  actionable: boolean;
}

const stageLabels = ["Understanding", "Strategy", "Build", "Deploy"];

function getProjectState(project: Project): ProjectState {
  if (project.status === "deleted") {
    return {
      label: "Archived",
      color: "bg-zinc-500/20 text-zinc-300",
      action: "Archived",
      route: `/projects/${project.id}`,
      stageIndex: 0,
      actionable: false,
    };
  }

  if (project.status === "parked") {
    return {
      label: "Parked",
      color: "bg-yellow-500/10 text-yellow-400",
      action: "Resume Project",
      route: `/projects/${project.id}`,
      stageIndex: 0,
      actionable: true,
    };
  }

  if (project.has_execution_plan) {
    return {
      label: "Plan Selected",
      color: "bg-neon-green/10 text-neon-green",
      action: "Continue to Build",
      route: `/projects/${project.id}/build`,
      stageIndex: 2,
      actionable: true,
    };
  }

  if (project.has_pending_gate) {
    return {
      label: "Decision Pending",
      color: "bg-brand/10 text-brand",
      action: "Make Decision",
      route: `/projects/${project.id}/understanding`,
      stageIndex: 1,
      actionable: true,
    };
  }

  if (project.has_brief) {
    return {
      label: "Brief Ready",
      color: "bg-purple-500/10 text-purple-400",
      action: "Review & Decide",
      route: `/projects/${project.id}/understanding`,
      stageIndex: 1,
      actionable: true,
    };
  }

  if (project.has_understanding_session) {
    return {
      label: "Interview In Progress",
      color: "bg-white/10 text-white",
      action: "Continue Interview",
      route: `/projects/${project.id}/understanding`,
      stageIndex: 0,
      actionable: true,
    };
  }

  return {
    label: "Onboarding Complete",
    color: "bg-blue-500/10 text-blue-400",
    action: "Start Interview",
    route: `/projects/${project.id}/understanding`,
    stageIndex: 0,
    actionable: true,
  };
}

function formatStatus(status: string): string {
  if (!status) return "Unknown";
  return status.charAt(0).toUpperCase() + status.slice(1);
}

export default function ProjectsPage() {
  const { getToken, isLoaded: authLoaded } = useAuth();
  const router = useRouter();
  const [projects, setProjects] = useState<Project[]>([]);
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [deletingProjectId, setDeletingProjectId] = useState<string | null>(null);

  useEffect(() => {
    if (!authLoaded) return;

    async function fetchProjects() {
      try {
        setError(null);
        const res = await apiFetch("/api/projects", getToken);
        if (res.ok) {
          const data = await res.json();
          setProjects(Array.isArray(data) ? data : []);
        } else {
          const text = await res.text().catch(() => "");
          console.error(`[projects] fetch failed: ${res.status}`, text);
          setError(`Failed to load projects (${res.status})`);
        }
      } catch (err) {
        console.error("[projects] network error:", err);
        setError("Unable to reach the server. Please try again.");
      } finally {
        setLoaded(true);
      }
    }
    fetchProjects();
  }, [getToken, authLoaded]);

  async function handleAbandonProject(projectId: string) {
    const confirmed = window.confirm(
      "Abandon this project? You can restore flow by starting or resuming onboarding after this.",
    );
    if (!confirmed) return;

    setDeletingProjectId(projectId);
    try {
      const response = await apiFetch(`/api/projects/${projectId}`, getToken, {
        method: "DELETE",
      });
      if (!response.ok) return;

      setProjects((prev) =>
        prev.map((project) =>
          project.id === projectId ? { ...project, status: "deleted" } : project,
        ),
      );
    } finally {
      setDeletingProjectId(null);
    }
  }

  if (!loaded) {
    return (
      <div className="flex items-center justify-center min-h-[50vh]">
        <div className="w-8 h-8 border-2 border-brand border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-4">
        <div>
          <h1 className="font-display text-3xl font-bold text-white">
            Your Projects
          </h1>
          <p className="text-muted-foreground mt-1">
            Track progress and pick up where you left off
          </p>
        </div>
        <Link
          href="/onboarding"
          onClick={(e) => {
            e.preventDefault();
            router.push("/onboarding");
          }}
          className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-brand text-white text-sm font-medium hover:bg-brand-dark transition-colors shadow-glow self-start"
        >
          <Plus className="w-4 h-4" />
          New Project
        </Link>
      </div>

      {/* Error state */}
      {error && (
        <div className="rounded-xl border border-red-500/20 bg-red-500/5 p-4 text-sm text-red-400">
          {error}
        </div>
      )}

      {/* Projects list */}
      {!error && projects.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-20 text-center">
          <div className="w-16 h-16 rounded-2xl bg-brand/10 flex items-center justify-center mb-5">
            <FolderOpen className="w-8 h-8 text-brand" />
          </div>
          <h3 className="font-display text-xl font-semibold text-white mb-2">
            No projects yet
          </h3>
          <p className="text-muted-foreground mb-6 max-w-sm">
            Start your first project and your AI co-founder will guide you through the process.
          </p>
          <Link
            href="/onboarding"
            onClick={(e) => {
              e.preventDefault();
              router.push("/onboarding");
            }}
            className="inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-brand text-white font-medium hover:bg-brand-dark transition-colors shadow-glow"
          >
            <Plus className="w-5 h-5" />
            Start Your First Project
          </Link>
        </div>
      ) : (
        <div className="grid sm:grid-cols-2 gap-4">
          {projects.map((project) => {
            const state = getProjectState(project);
            return (
              <GlassCard
                key={project.id}
                variant="strong"
                className={`group hover:ring-1 hover:ring-brand/30 transition-all h-full ${project.has_pending_gate ? "ring-1 ring-amber-500/30" : ""}`}
              >
                {/* Decision Required banner */}
                {project.has_pending_gate && (
                  <Link
                    href={`/projects/${project.id}/understanding`}
                    className="flex items-center gap-2 px-4 py-2.5 -mx-6 -mt-6 mb-4 rounded-t-2xl bg-amber-500/10 border-b border-amber-500/20 text-amber-400 hover:bg-amber-500/15 transition-colors"
                  >
                    <AlertCircle className="w-4 h-4 flex-shrink-0" />
                    <span className="text-xs font-medium">Decision Required — Make your choice to continue</span>
                    <ArrowRight className="w-3.5 h-3.5 ml-auto flex-shrink-0" />
                  </Link>
                )}

                {/* Name + state badge */}
                <div className="flex items-start justify-between gap-3">
                  <h3 className="font-display font-semibold text-white group-hover:text-brand transition-colors">
                    {project.name}
                  </h3>
                  <span
                    className={`flex-shrink-0 px-2.5 py-1 text-xs rounded-full font-medium ${state.color}`}
                  >
                    {state.label}
                  </span>
                </div>

                {/* Description */}
                {project.description && (
                  <p className="text-sm text-muted-foreground mt-1.5 line-clamp-2">
                    {project.description}
                  </p>
                )}

                {/* Lifecycle status */}
                <p className="text-xs text-muted-foreground mt-2">
                  Status:{" "}
                  <span className="text-white/80">{formatStatus(project.status)}</span>
                </p>

                {/* Stage progress dots */}
                <div className="mt-4 flex items-center gap-1.5">
                  {stageLabels.map((label, i) => (
                    <div key={label} className="flex items-center gap-1.5">
                      <div
                        className={`w-2.5 h-2.5 rounded-full transition-colors ${
                          i < state.stageIndex
                            ? "bg-neon-green"
                            : i === state.stageIndex
                              ? "bg-brand"
                              : "bg-white/10"
                        }`}
                        title={label}
                      />
                      {i < stageLabels.length - 1 && (
                        <div
                          className={`w-6 h-0.5 ${
                            i < state.stageIndex
                              ? "bg-neon-green/40"
                              : "bg-white/5"
                          }`}
                        />
                      )}
                    </div>
                  ))}
                  <span className="ml-2 text-xs text-muted-foreground">
                    {stageLabels[state.stageIndex]}
                  </span>
                </div>

                {/* Footer: date + actions */}
                <div className="mt-4 flex items-center justify-between gap-3">
                  <span className="text-xs text-muted-foreground">
                    Created{" "}
                    {new Date(project.created_at).toLocaleDateString()}
                  </span>
                  <div className="flex items-center gap-2">
                    {project.status !== "deleted" && (
                      <button
                        onClick={() => handleAbandonProject(project.id)}
                        disabled={deletingProjectId === project.id}
                        className="inline-flex items-center gap-1 text-xs font-medium text-amber-400 hover:text-amber-300 transition-colors disabled:opacity-60"
                      >
                        {deletingProjectId === project.id ? "Abandoning..." : "Abandon"}
                      </button>
                    )}
                    {state.actionable ? (
                      <Link
                        href={state.route}
                        className="inline-flex items-center gap-1 text-xs font-medium text-brand hover:underline"
                      >
                        {state.action}
                        <ArrowRight className="w-3.5 h-3.5" />
                      </Link>
                    ) : (
                      <span className="text-xs text-zinc-400">{state.action}</span>
                    )}
                  </div>
                </div>
              </GlassCard>
            );
          })}
        </div>
      )}
    </div>
  );
}
