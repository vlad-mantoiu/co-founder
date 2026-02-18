"use client";

import { useUser, useAuth } from "@clerk/nextjs";
import { useEffect, useState, useRef, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import Link from "next/link";
import { toast } from "sonner";
import {
  FolderPlus,
  Github,
  MessageSquare,
  ArrowRight,
  GitPullRequest,
  GitCommit,
  CheckCircle2,
  Clock,
} from "lucide-react";
import { GlassCard } from "@/components/ui/glass-card";
import { apiFetch } from "@/lib/api";

interface Project {
  id: string;
  name: string;
  description: string;
  status: string;
  github_repo: string | null;
  created_at: string;
  stage_number?: number;
  has_pending_gate?: boolean;
  has_understanding_session?: boolean;
  has_brief?: boolean;
}

/* ─── Checkout success detector (must be in Suspense — uses useSearchParams) ─── */

function CheckoutSuccessDetector() {
  const searchParams = useSearchParams();
  const hasRun = useRef(false);

  useEffect(() => {
    if (hasRun.current) return;
    const success = searchParams.get("checkout_success");
    if (success === "true") {
      hasRun.current = true;
      toast.success("Subscription activated! Welcome aboard.");
      const url = new URL(window.location.href);
      url.searchParams.delete("checkout_success");
      window.history.replaceState({}, "", url.toString());
    }
  }, [searchParams]);

  return null;
}

/* ─── Auto-checkout redirect (must be in Suspense — uses useSearchParams) ─── */

function CheckoutAutoRedirector({ getToken }: { getToken: () => Promise<string | null> }) {
  const searchParams = useSearchParams();
  const checkoutTriggered = useRef(false);

  useEffect(() => {
    const plan = searchParams.get("plan");
    const interval = searchParams.get("interval") || "monthly";

    if (!plan || checkoutTriggered.current) return;
    checkoutTriggered.current = true;

    async function triggerCheckout() {
      try {
        const res = await apiFetch("/api/billing/checkout", getToken, {
          method: "POST",
          body: JSON.stringify({ plan_slug: plan, interval }),
        });
        const data = await res.json();
        if (data.checkout_url) {
          window.location.href = data.checkout_url;
        }
      } catch {
        // Checkout failed — continue to dashboard
      }
    }
    triggerCheckout();
  }, [searchParams, getToken]);

  return null;
}

/* ─── Main page ─── */

export default function DashboardPage() {
  const { user } = useUser();
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
        // API may not be running yet — show onboarding
      } finally {
        setLoaded(true);
      }
    }
    fetchProjects();
  }, [getToken]);

  const hasProjects = projects.length > 0;
  const firstName = user?.firstName || "Builder";

  if (!loaded) {
    return (
      <>
        <Suspense fallback={null}>
          <CheckoutSuccessDetector />
          <CheckoutAutoRedirector getToken={getToken} />
        </Suspense>
        <div className="flex items-center justify-center h-64">
          <div className="w-8 h-8 border-2 border-brand border-t-transparent rounded-full animate-spin" />
        </div>
      </>
    );
  }

  // No projects yet — redirect to onboarding flow
  if (!hasProjects) {
    router.replace("/onboarding");
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-8 h-8 border-2 border-brand border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <>
      <Suspense fallback={null}>
        <CheckoutSuccessDetector />
        <CheckoutAutoRedirector getToken={getToken} />
      </Suspense>
      <ReturningUserDashboard firstName={firstName} projects={projects} />
    </>
  );
}

/* ─── Returning user dashboard ─── */

function ReturningUserDashboard({
  firstName,
  projects,
}: {
  firstName: string;
  projects: Project[];
}) {
  // Check if any projects have pending gates or understanding sessions
  const pendingGateProjects = projects.filter((p) => p.has_pending_gate);
  const understandingInProgressProjects = projects.filter(
    (p) => p.has_understanding_session && !p.has_brief
  );

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-4">
        <div className="space-y-1">
          <h1 className="font-display text-3xl font-bold text-white">
            Welcome back, <span className="text-brand">{firstName}</span>
          </h1>
          <p className="text-muted-foreground">
            Here&apos;s what&apos;s happening across your projects
          </p>
        </div>
        <Link
          href="/projects"
          className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-brand text-white text-sm font-medium hover:bg-brand-dark transition-colors shadow-glow self-start"
        >
          <FolderPlus className="w-4 h-4" /> New Project
        </Link>
      </div>

      {/* Pending Gates Banner */}
      {pendingGateProjects.length > 0 && (
        <div className="p-4 bg-brand/10 border border-brand/20 rounded-xl">
          <div className="flex items-start gap-3">
            <Clock className="w-5 h-5 text-brand mt-0.5 flex-shrink-0" />
            <div className="flex-1">
              <h3 className="font-semibold text-white mb-1">
                Decision Gate Pending
              </h3>
              <p className="text-sm text-muted-foreground">
                {pendingGateProjects.length === 1
                  ? `${pendingGateProjects[0].name} has a pending decision gate.`
                  : `${pendingGateProjects.length} projects have pending decision gates.`}{" "}
                Make your decision to continue.
              </p>
              <Link
                href={`/projects/${pendingGateProjects[0].id}/understanding`}
                className="inline-flex items-center gap-1 mt-2 text-sm text-brand hover:underline"
              >
                Go to Decision Gate <ArrowRight className="w-4 h-4" />
              </Link>
            </div>
          </div>
        </div>
      )}

      {/* Understanding Interview in Progress Banner */}
      {understandingInProgressProjects.length > 0 && (
        <div className="p-4 bg-white/5 border border-white/10 rounded-xl">
          <div className="flex items-start gap-3">
            <MessageSquare className="w-5 h-5 text-white mt-0.5 flex-shrink-0" />
            <div className="flex-1">
              <h3 className="font-semibold text-white mb-1">
                Understanding Interview in Progress
              </h3>
              <p className="text-sm text-muted-foreground">
                {understandingInProgressProjects.length === 1
                  ? `${understandingInProgressProjects[0].name} is being analyzed.`
                  : `${understandingInProgressProjects.length} projects are being analyzed.`}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Quick stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard icon={<GitPullRequest className="w-5 h-5" />} label="PRs Created" value="0" />
        <StatCard icon={<GitCommit className="w-5 h-5" />} label="Commits" value="0" />
        <StatCard icon={<CheckCircle2 className="w-5 h-5" />} label="Tasks Done" value="0" />
        <StatCard icon={<Clock className="w-5 h-5" />} label="Hours Saved" value="0" />
      </div>

      {/* Project cards */}
      <section>
        <h2 className="font-display text-xl font-semibold text-white mb-4">
          Active Projects
        </h2>
        <div className="grid sm:grid-cols-2 gap-4">
          {projects.map((project) => (
            <GlassCard key={project.id} variant="strong" className="group hover:ring-1 hover:ring-brand/30 transition-all">
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <h3 className="font-display font-semibold text-white group-hover:text-brand transition-colors">
                    {project.name}
                  </h3>
                  {project.description && (
                    <p className="text-sm text-muted-foreground mt-1 line-clamp-2">
                      {project.description}
                    </p>
                  )}
                  {/* Status badges */}
                  <div className="mt-2 flex items-center gap-2 flex-wrap">
                    {project.status === "parked" && (
                      <span className="px-2.5 py-1 text-xs rounded-full bg-yellow-500/10 text-yellow-400 font-medium">
                        Parked
                      </span>
                    )}
                    {project.has_pending_gate && (
                      <span className="px-2.5 py-1 text-xs rounded-full bg-brand/10 text-brand font-medium">
                        Pending Gate
                      </span>
                    )}
                    {project.has_understanding_session && !project.has_brief && (
                      <span className="px-2.5 py-1 text-xs rounded-full bg-white/10 text-white font-medium">
                        Understanding...
                      </span>
                    )}
                  </div>
                </div>
                <span className="flex-shrink-0 px-2.5 py-1 text-xs rounded-full bg-neon-green/10 text-neon-green font-medium">
                  {project.status !== "parked" ? project.status : "idle"}
                </span>
              </div>
              <div className="mt-4 flex items-center gap-3 text-xs text-muted-foreground">
                {project.github_repo && (
                  <span className="flex items-center gap-1">
                    <Github className="w-3.5 h-3.5" /> {project.github_repo}
                  </span>
                )}
                <span>
                  Created{" "}
                  {new Date(project.created_at).toLocaleDateString()}
                </span>
              </div>
            </GlassCard>
          ))}
        </div>
      </section>
    </div>
  );
}

function StatCard({
  icon,
  label,
  value,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
}) {
  return (
    <GlassCard variant="strong" className="flex items-center gap-4">
      <div className="w-10 h-10 rounded-xl bg-brand/10 flex items-center justify-center text-brand">
        {icon}
      </div>
      <div>
        <div className="text-2xl font-bold text-white">{value}</div>
        <div className="text-xs text-muted-foreground">{label}</div>
      </div>
    </GlassCard>
  );
}
