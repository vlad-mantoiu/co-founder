"use client";

import {
  MessageCircle,
  Code2,
  TestTube,
  Rocket,
  RefreshCw,
  Zap,
  Info,
  CheckCircle,
  Save,
  Coffee,
  Settings,
  Code,
} from "lucide-react";
import Link from "next/link";
import { FadeIn, StaggerContainer, StaggerItem } from "./fade-in";
import { AgentSwarm } from "./agent-swarm";

/* ───────── Data ───────── */

const steps = [
  {
    icon: MessageCircle,
    step: "01",
    title: "Describe",
    description:
      "Start with the outcome you want. Co-Founder.ai turns your requirements into an executable technical plan.",
  },
  {
    icon: Code2,
    step: "02",
    title: "Architect & Build",
    description:
      "Get production-ready architecture and code aligned to your stack, conventions, and product priorities.",
  },
  {
    icon: TestTube,
    step: "03",
    title: "Review & Correct",
    description:
      "Review tested changes, request revisions, and approve what ships with full visibility into each update.",
  },
  {
    icon: Rocket,
    step: "04",
    title: "Ship",
    description:
      "Deploy approved changes to your infrastructure and release under your own accounts, domain, and control.",
  },
];

const milestones = [
  {
    status: "Completed",
    statusColor: "bg-emerald-500/10 text-emerald-400",
    borderColor: "border-emerald-500",
    time: "10:42 AM",
    title: "Architectural Plan",
    description: "System architecture defined. Database schema finalized. API endpoints mapped.",
  },
  {
    status: "In Progress",
    statusColor: "bg-brand/10 text-brand",
    borderColor: "border-brand",
    time: "NOW",
    title: "Backend Implementation",
    description: "Coding auth middleware. Writing unit tests for user service.",
    pulse: true,
    bgIcon: true,
  },
  {
    status: "Queued",
    statusColor: "bg-white/5 text-white/40",
    borderColor: "border-white/20",
    time: "--:--",
    title: "Pull Request Review",
    description: "Waiting for implementation completion. Reviewer agent on standby.",
    dimmed: true,
  },
];

/* ───────── Component ───────── */

export default function HowItWorksSection() {
  return (
    <>
      {/* ─── 1. Hero ─── */}
      <section className="mx-auto max-w-7xl px-6 lg:px-8 text-center py-20">
        <FadeIn>
          <div className="inline-flex items-center gap-2 rounded-full border border-brand/20 bg-brand/5 px-3 py-1 text-xs font-medium text-brand mb-8">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-brand opacity-75" />
              <span className="relative inline-flex rounded-full h-2 w-2 bg-brand" />
            </span>
            SYSTEM ACTIVE V2.4
          </div>
        </FadeIn>

        <div className="hero-fade">
          <h1 className="text-5xl font-bold tracking-tighter text-white sm:text-7xl mb-6">
            How Structured <br />
            <span className="glow-text">Autonomy Works</span>
          </h1>
        </div>

        <div className="hero-fade-delayed">
          <p className="mx-auto max-w-2xl text-lg leading-relaxed text-white/40">
            Your AI Co-Founder is not a chatbot. It&rsquo;s a living system of
            agents operating on a continuous loop, ensuring progress never stops.
          </p>
        </div>
      </section>

      {/* ─── 2. Four-Step Process (original) ─── */}
      <section className="py-24 lg:py-32 border-t border-white/5">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <FadeIn className="text-center mb-16">
            <p className="text-sm uppercase tracking-widest text-brand font-medium mb-4">
              Process
            </p>
            <h2 className="text-3xl sm:text-4xl lg:text-5xl font-bold tracking-tight">
              How does Co-Founder.ai take you from idea to deployment?
            </h2>
            <p className="mt-4 text-lg text-white/40 max-w-2xl mx-auto">
              You define the goal, Co-Founder.ai executes the development loop,
              and you approve each production-ready release.
            </p>
          </FadeIn>

          <StaggerContainer
            className="grid sm:grid-cols-2 lg:grid-cols-4 gap-6"
            stagger={0.12}
          >
            {steps.map((s, i) => (
              <StaggerItem key={s.step}>
                <div className="relative glass rounded-2xl p-6 lg:p-8 h-full group hover:bg-white/[0.04] transition-colors duration-300">
                  {i < steps.length - 1 && (
                    <div className="hidden lg:block absolute top-1/2 -right-3 w-6 h-px bg-white/10" />
                  )}
                  <span className="text-xs font-mono text-brand/60 mb-4 block">
                    {s.step}
                  </span>
                  <div className="h-12 w-12 rounded-xl bg-brand/10 border border-brand/20 flex items-center justify-center mb-5 group-hover:bg-brand/15 transition-colors">
                    <s.icon className="h-6 w-6 text-brand" />
                  </div>
                  <h3 className="text-lg font-bold mb-2">{s.title}</h3>
                  <p className="text-sm text-white/40 leading-relaxed">
                    {s.description}
                  </p>
                </div>
              </StaggerItem>
            ))}
          </StaggerContainer>
        </div>
      </section>

      {/* ─── 3. 24/7 Engine + Agent Swarm ─── */}
      <section className="mx-auto max-w-7xl px-6 lg:px-8 py-16">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Engine Card */}
          <FadeIn direction="left">
            <div className="glass-strong rounded-2xl p-8 relative overflow-hidden group h-full">
              <div className="absolute top-0 right-0 p-6 opacity-20 group-hover:opacity-40 transition-opacity">
                <Settings className="h-24 w-24 text-brand animate-[spin_10s_linear_infinite]" />
              </div>
              <div className="relative z-10 flex flex-col h-full justify-between gap-12">
                <div>
                  <div className="h-12 w-12 rounded-xl bg-brand/20 flex items-center justify-center text-brand mb-6">
                    <RefreshCw className="h-6 w-6" />
                  </div>
                  <h2 className="text-3xl font-bold text-white mb-4">
                    The 24/7 Engine
                  </h2>
                  <p className="text-white/40 leading-relaxed">
                    Unlike standard bots, this system initiates work without
                    constant prompting. It runs 24/7, plans while you sleep, and
                    requires no hand-holding.
                  </p>
                </div>
                <div className="flex gap-4">
                  <div className="flex flex-col gap-1">
                    <span className="text-xs uppercase tracking-wider text-white/30">
                      Status
                    </span>
                    <span className="text-emerald-400 font-mono text-sm">
                      ● OPERATIONAL
                    </span>
                  </div>
                  <div className="flex flex-col gap-1 border-l border-white/10 pl-4">
                    <span className="text-xs uppercase tracking-wider text-white/30">
                      Uptime
                    </span>
                    <span className="text-white font-mono text-sm">99.9%</span>
                  </div>
                </div>
              </div>
            </div>
          </FadeIn>

          {/* Agent Swarm */}
          <FadeIn direction="right">
            <AgentSwarm />
          </FadeIn>
        </div>
      </section>

      {/* ─── 4. Token Energy System ─── */}
      <section className="mx-auto max-w-5xl px-6 lg:px-8 py-16">
        <FadeIn>
          <div className="glass-card-strong rounded-3xl p-8">
            <div className="flex flex-col md:flex-row gap-12 items-center">
              <div className="flex-1 space-y-6">
                <div className="inline-flex items-center gap-2 rounded-full bg-brand/10 px-3 py-1 text-xs font-bold text-brand">
                  <Zap className="h-3.5 w-3.5" />
                  Resource Management
                </div>
                <h2 className="text-3xl font-bold text-white">
                  Compute Energy
                </h2>
                <p className="text-white/40">
                  Each plan comes with a daily energy budget that fuels your
                  agents&rsquo; reasoning, coding, and testing cycles. The system
                  optimises every token so your team ships as much as possible
                  before the next reset.
                </p>
                <div className="grid grid-cols-2 gap-4 pt-4">
                  <div className="p-4 rounded-xl bg-obsidian border border-white/5">
                    <div className="text-2xl font-bold text-white mb-1">24/7</div>
                    <div className="text-xs text-white/30 uppercase">
                      Always Running
                    </div>
                  </div>
                  <div className="p-4 rounded-xl bg-obsidian border border-white/5">
                    <div className="text-2xl font-bold text-white mb-1">
                      ~10k
                    </div>
                    <div className="text-xs text-white/30 uppercase">
                      Lines / Day
                    </div>
                  </div>
                </div>
              </div>

              {/* Battery visual */}
              <div className="flex-1 w-full">
                <div className="bg-obsidian rounded-2xl p-6 border border-white/10 shadow-2xl">
                  <div className="flex justify-between items-end mb-4">
                    <span className="text-sm font-medium text-white/40">
                      Current Energy Level
                    </span>
                    <span className="text-2xl font-mono font-bold text-brand">
                      78%
                    </span>
                  </div>
                  <div className="h-12 w-full bg-black rounded-lg border border-white/10 p-1 relative overflow-hidden">
                    <div className="h-full w-[78%] bg-brand rounded-md energy-bar-striped relative animate-pulse shadow-glow" />
                  </div>
                  <div className="flex justify-between mt-4 text-xs font-mono text-white/20">
                    <span>0%</span>
                    <span>|</span>
                    <span>|</span>
                    <span>|</span>
                    <span>100%</span>
                  </div>
                  <div className="mt-6 flex gap-3 items-center text-xs text-white/30 bg-black/40 p-3 rounded border border-white/5">
                    <Info className="h-4 w-4 shrink-0" />
                    Resets automatically every 24 hours at 00:00 UTC.
                  </div>
                </div>
              </div>
            </div>
          </div>
        </FadeIn>
      </section>

      {/* ─── 5. Pause & Resume ─── */}
      <section className="mx-auto max-w-7xl px-6 lg:px-8 py-16">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-12 items-center">
          {/* Save-state visual */}
          <FadeIn direction="left" className="order-2 md:order-1">
            <div className="relative w-full aspect-video bg-obsidian-light rounded-xl border border-white/10 p-6 flex items-center justify-center transform -rotate-1 hover:rotate-0 transition-transform duration-500 shadow-2xl">
              <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-transparent via-brand to-transparent opacity-50" />
              <div className="w-full max-w-sm border-2 border-white/10 rounded-lg p-6 bg-obsidian flex flex-col gap-4">
                <div className="flex justify-between items-center border-b border-white/10 pb-4">
                  <span className="text-xs font-mono text-white/30">
                    SAVE_STATE_V9.2
                  </span>
                  <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
                </div>
                <div className="flex gap-4 items-center">
                  <div className="h-12 w-12 rounded bg-white/5 flex items-center justify-center">
                    <Save className="h-5 w-5 text-white/40" />
                  </div>
                  <div className="flex flex-col gap-1">
                    <div className="h-2 w-32 bg-white/10 rounded" />
                    <div className="h-2 w-20 bg-white/10 rounded" />
                  </div>
                </div>
                <div className="mt-2 text-center text-xs text-white/20 font-mono">
                  [CONTEXT PERSISTED TO SECURE STORAGE]
                </div>
              </div>
            </div>
          </FadeIn>

          {/* Copy */}
          <FadeIn direction="right" className="order-1 md:order-2 space-y-6">
            <h2 className="text-3xl font-bold text-white">
              The &lsquo;Pause &amp; Resume&rsquo; Mechanic
            </h2>
            <p className="text-white/40 text-lg">
              What happens when energy runs out? The system creates a perfect
              &ldquo;Save State&rdquo;. Your agents pause, preserve their
              context, and seamlessly resume exactly where they left off once the
              daily reset occurs.
            </p>
            <ul className="space-y-4">
              {[
                "Zero context loss between sessions.",
                "Automatic Git commits before pausing.",
                "Detailed handover report generated daily.",
              ].map((item) => (
                <li key={item} className="flex items-start gap-3">
                  <CheckCircle className="h-5 w-5 text-brand mt-0.5 shrink-0" />
                  <span className="text-white/60">{item}</span>
                </li>
              ))}
            </ul>
          </FadeIn>
        </div>
      </section>

      {/* ─── 6. Caffeinate ─── */}
      <section className="mx-auto max-w-4xl px-6 lg:px-8 py-20">
        <FadeIn>
          <div className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-obsidian-light to-black border border-amber-500/30 p-px">
            <div className="absolute -top-24 -right-24 w-64 h-64 bg-amber-500/20 rounded-full blur-[80px]" />
            <div className="relative z-10 bg-obsidian rounded-[22px] p-8 md:p-12 text-center">
              <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-br from-amber-500 to-orange-600 mb-6 shadow-lg shadow-orange-500/20">
                <Coffee className="h-8 w-8 text-white" />
              </div>
              <h2 className="text-3xl md:text-4xl font-bold text-white mb-4">
                Need Momentum?{" "}
                <span className="text-amber-500">Caffeinate.</span>
              </h2>
              <p className="text-white/40 max-w-lg mx-auto mb-8">
                Crunch time? Bypass the daily limit instantly. Use the
                &ldquo;Caffeinate&rdquo; feature to inject emergency tokens and
                keep your agents building through the night.
              </p>
              <Link
                href="/waitlist"
                className="group relative inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-amber-500 to-orange-600 px-8 py-4 text-sm font-bold text-white shadow-[0_0_30px_rgba(245,158,11,0.4)] transition-all hover:scale-105 hover:shadow-[0_0_40px_rgba(245,158,11,0.6)]"
              >
                <Zap className="h-4 w-4" />
                Purchase Caffeine Boost
                <div className="absolute inset-0 rounded-xl ring-2 ring-white/20 group-hover:ring-white/40" />
              </Link>
              <p className="mt-4 text-xs text-white/20 font-mono uppercase tracking-wider">
                Premium Feature &bull; Pay as you go
              </p>
            </div>
          </div>
        </FadeIn>
      </section>

      {/* ─── 7. Milestone Feed ─── */}
      <section className="mx-auto max-w-7xl px-6 lg:px-8 py-16 mb-20">
        <FadeIn className="text-center mb-12">
          <h2 className="text-3xl font-bold text-white mb-4">
            Milestone Feed
          </h2>
          <p className="text-white/40">
            Total transparency. Watch the work happen in real-time.
          </p>
        </FadeIn>

        <StaggerContainer
          className="grid grid-cols-1 md:grid-cols-3 gap-6"
          stagger={0.15}
        >
          {milestones.map((m) => (
            <StaggerItem key={m.title}>
              <div
                className={`bg-obsidian-light rounded-xl p-6 border-l-4 ${m.borderColor} relative overflow-hidden ${m.dimmed ? "opacity-60" : ""}`}
              >
                {m.bgIcon && (
                  <div className="absolute top-0 right-0 p-4 opacity-10">
                    <Code className="h-16 w-16" />
                  </div>
                )}
                <div className="flex justify-between items-start mb-4">
                  <span
                    className={`px-2 py-1 ${m.statusColor} text-xs font-bold rounded uppercase inline-flex items-center gap-1`}
                  >
                    {m.pulse && (
                      <span className="w-1.5 h-1.5 rounded-full bg-brand animate-pulse" />
                    )}
                    {m.status}
                  </span>
                  <span className="text-xs text-white/30 font-mono">
                    {m.time}
                  </span>
                </div>
                <h4 className="text-white font-bold mb-2">{m.title}</h4>
                <p className="text-sm text-white/40">{m.description}</p>
              </div>
            </StaggerItem>
          ))}
        </StaggerContainer>
      </section>

      {/* ─── 8. Bottom CTA ─── */}
      <section className="border-t border-white/5 py-20">
        <FadeIn className="mx-auto max-w-2xl text-center px-6">
          <h2 className="text-3xl font-bold text-white mb-6">
            Ready to scale your vision?
          </h2>
          <p className="text-white/40 max-w-xl mx-auto mb-8">
            Stop managing freelancers. Start orchestrating a tireless,
            intelligent machine.
          </p>
          <div className="flex flex-wrap justify-center gap-4">
            <Link
              href="/waitlist"
              className="h-12 px-8 rounded-xl bg-brand text-white font-bold text-sm hover:bg-brand-dark transition-colors shadow-glow inline-flex items-center"
            >
              Hire Your Team
            </Link>
            <Link
              href="/cofounder"
              className="h-12 px-8 rounded-xl border border-white/10 text-white font-bold text-sm hover:bg-white/5 transition-colors inline-flex items-center"
            >
              Learn More
            </Link>
          </div>
        </FadeIn>
      </section>
    </>
  );
}
