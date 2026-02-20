"use client";

import { useState, useEffect } from "react";
import { useAuth } from "@clerk/nextjs";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { FolderOpen, ArrowRight, Plus } from "lucide-react";
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
}

const stageLabels = ["Understanding", "Strategy", "Build", "Deploy"];

function getProjectState(project: Project): ProjectState {
  if (project.status === "parked") {
    return {
      label: "Parked",
      color: "bg-yellow-500/10 text-yellow-400",
      action: "Resume Project",
      route: `/projects/${project.id}`,
      stageIndex: 0,
    };
  }

  if (project.has_execution_plan) {
    return {
      label: "Plan Selected",
      color: "bg-neon-green/10 text-neon-green",
      action: "Continue to Build",
      route: `/projects/${project.id}/build`,
      stageIndex: 2,
    };
  }

  if (project.has_pending_gate) {
    return {
      label: "Decision Pending",
      color: "bg-brand/10 text-brand",
      action: "Make Decision",
      route: `/projects/${project.id}/understanding`,
      stageIndex: 1,
    };
  }

  if (project.has_brief) {
    return {
      label: "Brief Ready",
      color: "bg-purple-500/10 text-purple-400",
      action: "Review & Decide",
      route: `/projects/${project.id}/understanding`,
      stageIndex: 1,
    };
  }

  if (project.has_understanding_session) {
    return {
      label: "Interview In Progress",
      color: "bg-white/10 text-white",
      action: "Continue Interview",
      route: `/projects/${project.id}/understanding`,
      stageIndex: 0,
    };
  }

  return {
    label: "Onboarding Complete",
    color: "bg-blue-500/10 text-blue-400",
    action: "Start Interview",
    route: `/projects/${project.id}/understanding`,
    stageIndex: 0,
  };
}

export default function ProjectsPage() {
  const { getToken } = useAuth();
  const router = useRouter();
  const [projects, setProjects] = useState<Project[]>([]);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    async function fetchProjects() {
      try {
        const res = await apiFetch("/api/projects", getToken);
        if (res.ok) {
          const data = await res.json();
          setProjects(Array.isArray(data) ? data : []);
        }
      } catch {
        // API may not be running
      } finally {
        setLoaded(true);
      }
    }
    fetchProjects();
  }, [getToken]);

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

      {/* Projects list */}
      {projects.length === 0 ? (
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
              <Link key={project.id} href={state.route}>
                <GlassCard
                  variant="strong"
                  className="group hover:ring-1 hover:ring-brand/30 transition-all cursor-pointer h-full"
                >
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

                  {/* Footer: date + next action */}
                  <div className="mt-4 flex items-center justify-between">
                    <span className="text-xs text-muted-foreground">
                      Created{" "}
                      {new Date(project.created_at).toLocaleDateString()}
                    </span>
                    <span className="inline-flex items-center gap-1 text-xs font-medium text-brand group-hover:underline">
                      {state.action}
                      <ArrowRight className="w-3.5 h-3.5" />
                    </span>
                  </div>
                </GlassCard>
              </Link>
            );
          })}
        </div>
      )}
    </div>
  );
}
