"use client";

import { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import { useAuth } from "@clerk/nextjs";
import {
  MessageSquare,
  GitBranch,
  Hammer,
  Rocket,
  Clock,
  ArrowRight,
  CheckCircle2,
} from "lucide-react";
import Link from "next/link";
import { apiFetch } from "@/lib/api";
import { GlassCard } from "@/components/ui/glass-card";

interface Project {
  id: string;
  name: string;
  description: string;
  github_repo: string | null;
  status: string;
  created_at: string;
  has_pending_gate: boolean;
  has_understanding_session: boolean;
  has_brief: boolean;
  has_execution_plan: boolean;
}

const stages = [
  {
    key: "understanding",
    label: "Understanding",
    description: "Deep-dive interview to understand your idea",
    icon: MessageSquare,
    href: (id: string) => `/projects/${id}/understanding`,
  },
  {
    key: "strategy",
    label: "Strategy",
    description: "Architecture decisions and execution plan",
    icon: GitBranch,
    href: (id: string) => `/projects/${id}/strategy`,
  },
  {
    key: "build",
    label: "Build",
    description: "AI builds your project end-to-end",
    icon: Hammer,
    href: (id: string) => `/projects/${id}/build`,
  },
  {
    key: "deploy",
    label: "Deploy",
    description: "Ship to production",
    icon: Rocket,
    href: (id: string) => `/projects/${id}/deploy`,
  },
];

function getActiveStage(project: Project): string {
  if (project.has_execution_plan) return "build";
  if (project.has_brief || project.has_pending_gate) return "strategy";
  return "understanding";
}

export default function ProjectOverviewPage() {
  const params = useParams<{ id: string }>();
  const { getToken } = useAuth();
  const router = useRouter();
  const [project, setProject] = useState<Project | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchProject() {
      try {
        const res = await apiFetch(`/api/projects/${params.id}`, getToken);
        if (res.ok) {
          setProject(await res.json());
        }
      } catch {
        // API may not be running
      } finally {
        setLoading(false);
      }
    }
    fetchProject();
  }, [params.id, getToken]);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[50vh]">
        <div className="w-8 h-8 border-2 border-brand border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (!project) {
    return (
      <div className="text-center py-20">
        <p className="text-muted-foreground">Project not found.</p>
      </div>
    );
  }

  const activeStage = getActiveStage(project);

  return (
    <div className="space-y-8 max-w-3xl mx-auto">
      {/* Header */}
      <div>
        <h1 className="font-display text-3xl font-bold text-white">
          {project.name}
        </h1>
        {project.description && (
          <p className="text-muted-foreground mt-2">{project.description}</p>
        )}
        <p className="text-xs text-muted-foreground mt-2">
          <Clock className="w-3 h-3 inline mr-1" />
          Created {new Date(project.created_at).toLocaleDateString()}
        </p>
      </div>

      {/* Journey stages */}
      <div className="space-y-3">
        <h2 className="font-display text-lg font-semibold text-white">
          Project Journey
        </h2>
        <div className="space-y-2">
          {stages.map((stage, i) => {
            const Icon = stage.icon;
            const isActive = stage.key === activeStage;
            const stageIndex = stages.findIndex((s) => s.key === activeStage);
            const isComplete = i < stageIndex;
            const isLocked = i > stageIndex;

            return (
              <Link key={stage.key} href={stage.href(params.id)}>
                <GlassCard
                  variant={isActive ? "strong" : "default"}
                  className={`flex items-center gap-4 transition-all ${
                    isActive
                      ? "ring-1 ring-brand/40"
                      : isLocked
                        ? "opacity-50"
                        : "hover:ring-1 hover:ring-white/10"
                  }`}
                >
                  <div
                    className={`w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0 ${
                      isComplete
                        ? "bg-neon-green/10"
                        : isActive
                          ? "bg-brand/10"
                          : "bg-white/5"
                    }`}
                  >
                    {isComplete ? (
                      <CheckCircle2 className="w-5 h-5 text-neon-green" />
                    ) : (
                      <Icon
                        className={`w-5 h-5 ${isActive ? "text-brand" : "text-muted-foreground"}`}
                      />
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p
                      className={`font-medium ${isActive ? "text-white" : "text-muted-foreground"}`}
                    >
                      {stage.label}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {stage.description}
                    </p>
                  </div>
                  {isActive && (
                    <ArrowRight className="w-4 h-4 text-brand flex-shrink-0" />
                  )}
                </GlassCard>
              </Link>
            );
          })}
        </div>
      </div>

      {/* CTA */}
      <button
        onClick={() =>
          router.push(
            stages.find((s) => s.key === activeStage)!.href(params.id)
          )
        }
        className="w-full py-3 rounded-xl bg-brand text-white font-medium hover:bg-brand-dark transition-colors shadow-glow flex items-center justify-center gap-2"
      >
        Continue to {stages.find((s) => s.key === activeStage)!.label}
        <ArrowRight className="w-4 h-4" />
      </button>
    </div>
  );
}
