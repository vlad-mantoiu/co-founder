"use client";

import Link from "next/link";
import {
  ArrowRight,
  Check,
  Sparkles,
  Users,
  TrendingUp,
  Bot,
} from "lucide-react";
import { FadeIn, StaggerContainer, StaggerItem } from "./fade-in";

export default function InsourcedHomeContent() {
  return (
    <>
      <InsourcedHero />
      <FlagshipProduct />
      <ProductSuiteRoadmap />
      <BottomCTA />
    </>
  );
}

/* ─── Insourced Hero ─── */

function InsourcedHero() {
  return (
    <section
      id="hero"
      className="relative pt-32 pb-24 lg:pt-44 lg:pb-36 overflow-hidden"
    >
      {/* Background */}
      <div className="absolute inset-0 bg-grid opacity-40" />
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[900px] h-[700px] bg-brand/10 rounded-full blur-[150px] pointer-events-none" />
      <div className="absolute top-60 right-0 w-[500px] h-[500px] bg-neon-cyan/5 rounded-full blur-[120px] pointer-events-none" />

      <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
        <div className="hero-fade">
          {/* Pill badge */}
          <div className="inline-flex items-center gap-2 px-5 py-2 rounded-full glass-card-strong text-sm text-white/80 mb-10">
            <span className="w-2 h-2 rounded-full bg-neon-green animate-pulse" />
            FLAGSHIP LIVE: CO-FOUNDER.AI
          </div>

          <h1 className="text-5xl sm:text-6xl lg:text-7xl xl:text-8xl font-bold tracking-tight leading-[1.05]">
            Insourced AI for Founders
            <br />
            Who Need to <span className="glow-text">Ship Faster.</span>
          </h1>
        </div>

        <div className="hero-fade-delayed">
          <p className="mt-8 text-lg sm:text-xl lg:text-2xl text-white/50 leading-relaxed max-w-3xl mx-auto">
            Start with Co-Founder.ai, your AI technical co-founder. It plans
            architecture, writes code, runs tests, and prepares deployments so
            you can focus on customers and growth.
          </p>
          <p className="mt-4 text-sm sm:text-base text-white/40 leading-relaxed max-w-2xl mx-auto">
            Quick answer: Insourced AI gives founders autonomous agents that
            replace outsourced execution and keep product decisions in-house.
          </p>

          <div className="mt-12 flex flex-col sm:flex-row gap-4 justify-center">
            <Link
              href="/waitlist"
              className="inline-flex items-center justify-center px-10 py-4.5 bg-brand text-white font-semibold rounded-xl hover:bg-brand-dark transition-all duration-200 shadow-glow hover:shadow-glow-lg text-lg"
            >
              Join the Waitlist
            </Link>
            <a
              href="#suite"
              className="inline-flex items-center justify-center gap-2 px-10 py-4.5 glass text-white font-medium rounded-xl hover:bg-white/5 transition-all duration-200 text-lg"
            >
              See the Agent Roadmap
              <ArrowRight className="h-5 w-5" />
            </a>
          </div>

          {/* Social proof */}
          <div className="mt-16 flex items-center justify-center gap-4">
            <div className="flex -space-x-3">
              {["S", "M", "A", "J", "R"].map((letter, i) => (
                <div
                  key={i}
                  className="w-9 h-9 rounded-full border-2 border-obsidian flex items-center justify-center text-xs font-bold"
                  style={{
                    background: `linear-gradient(135deg, hsl(${239 + i * 20}, 60%, ${55 + i * 5}%), hsl(${239 + i * 20}, 60%, ${35 + i * 5}%))`,
                  }}
                >
                  {letter}
                </div>
              ))}
            </div>
            <p className="text-sm text-white/40">
              Advanced frameworks used by{" "}
              <span className="text-white/70 font-medium">thousands</span>{" "}
              already
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}

/* ─── Flagship Product Card ─── */

function FlagshipProduct() {
  return (
    <section className="py-20 lg:py-28">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <FadeIn>
          <div className="glass-card-strong rounded-3xl p-8 sm:p-12 lg:p-16 transition-all duration-500">
            <div className="grid lg:grid-cols-2 gap-12 lg:gap-16 items-center">
              {/* Left: product info */}
              <div>
                <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-brand/10 border border-brand/20 text-xs font-semibold text-brand mb-6">
                  <Sparkles className="h-3.5 w-3.5" />
                  FLAGSHIP PRODUCT
                </div>

                <h2 className="text-3xl sm:text-4xl lg:text-5xl font-bold tracking-tight mb-4">
                  Co-Founder<span className="text-brand">.ai</span>
                </h2>

                <p className="text-lg text-white/50 leading-relaxed mb-8">
                  For non-technical founders, Co-Founder.ai is an AI technical
                  co-founder that architects, codes, tests, and prepares
                  deployment-ready changes in your workflow.
                </p>

                {/* Badge chips */}
                <div className="flex flex-wrap gap-3 mb-10">
                  {[
                    { label: "24/7", desc: "Always On" },
                    { label: "Full Stack", desc: "End to End" },
                    { label: "Zero Equity", desc: "You Own It All" },
                  ].map((badge) => (
                    <div
                      key={badge.label}
                      className="glass rounded-xl px-4 py-2.5 flex items-center gap-2"
                    >
                      <Check className="h-4 w-4 text-neon-green" />
                      <span className="text-sm font-semibold text-white">
                        {badge.label}
                      </span>
                      <span className="text-xs text-white/40">
                        {badge.desc}
                      </span>
                    </div>
                  ))}
                </div>

                <div className="flex items-center gap-4">
                  <Link
                    href="/waitlist"
                    className="inline-flex items-center gap-2 px-8 py-4 bg-brand text-white font-semibold rounded-xl hover:bg-brand-dark transition-all duration-200 shadow-glow hover:shadow-glow-lg text-lg"
                  >
                    Join the Waitlist
                    <ArrowRight className="h-5 w-5" />
                  </Link>
                  <Link href="/cofounder" className="text-sm text-brand hover:text-brand-light transition-colors">
                    Learn more →
                  </Link>
                </div>
              </div>

              {/* Right: chat UI mockup */}
              <div className="relative">
                <div className="glass rounded-2xl overflow-hidden shadow-glow-lg">
                  {/* Chat header */}
                  <div className="flex items-center gap-3 px-5 py-4 border-b border-white/5">
                    <div className="w-8 h-8 rounded-lg bg-brand/20 flex items-center justify-center">
                      <Bot className="h-4 w-4 text-brand" />
                    </div>
                    <div>
                      <p className="text-sm font-semibold">Co-Founder.ai</p>
                      <p className="text-xs text-neon-green">Active</p>
                    </div>
                  </div>
                  {/* Chat body */}
                  <div className="p-5 space-y-4">
                    <div className="flex justify-end">
                      <div className="bg-brand/20 rounded-2xl rounded-tr-sm px-4 py-2.5 max-w-[80%]">
                        <p className="text-sm text-white/90">
                          Build me a SaaS with user auth, billing, and a dashboard
                        </p>
                      </div>
                    </div>
                    <div className="flex justify-start">
                      <div className="glass rounded-2xl rounded-tl-sm px-4 py-2.5 max-w-[85%]">
                        <p className="text-sm text-white/70">
                          On it. I will architect the system with Next.js + FastAPI,
                          set up Stripe billing, and build a real-time dashboard.
                          Starting now.
                        </p>
                      </div>
                    </div>
                    <div className="flex justify-start">
                      <div className="glass rounded-2xl rounded-tl-sm px-4 py-2.5 max-w-[85%]">
                        <div className="flex items-center gap-2 text-sm">
                          <span className="w-2 h-2 rounded-full bg-neon-green animate-pulse" />
                          <span className="text-neon-green font-medium">
                            47/47 tests passed
                          </span>
                          <span className="text-white/40">
                            — PR ready for review
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
                {/* Decorative glow */}
                <div className="absolute -inset-4 bg-brand/5 rounded-3xl blur-2xl -z-10" />
              </div>
            </div>
          </div>
        </FadeIn>
      </div>
    </section>
  );
}

/* ─── Product Suite Roadmap ─── */

const suiteProducts = [
  {
    name: "Interview",
    tagline: "Talent Acquisition",
    description:
      "AI-driven candidate interviews and evaluations to help founders hire faster with less manual screening.",
    status: "Coming Q3",
    statusColor: "text-white/40",
    icon: Users,
    gradient: "from-neon-cyan/10 to-brand/5",
    borderColor: "border-neon-cyan/20",
  },
  {
    name: "Swarm",
    tagline: "Agentic Engineering",
    description:
      "Multi-agent development squads that handle complex codebases in parallel so product work keeps moving.",
    status: "In Beta",
    statusColor: "text-neon-green",
    icon: Bot,
    gradient: "from-brand/15 to-neon-green/5",
    borderColor: "border-brand/30",
    highlighted: true,
  },
  {
    name: "Fund",
    tagline: "Financial Ops",
    description:
      "Autonomous financial modeling and investor reporting to keep runway decisions current and clear.",
    status: "Coming Q4",
    statusColor: "text-white/40",
    icon: TrendingUp,
    gradient: "from-neon-pink/10 to-brand/5",
    borderColor: "border-neon-pink/20",
  },
];

function ProductSuiteRoadmap() {
  return (
    <section id="suite" className="py-20 lg:py-28 border-t border-white/5">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <FadeIn className="text-center mb-16">
          <p className="text-sm uppercase tracking-widest text-brand font-medium mb-4">
            The Insourced Suite
          </p>
          <h2 className="text-3xl sm:text-4xl lg:text-5xl font-bold tracking-tight">
            Which startup roles can Insourced AI replace first?
          </h2>
          <p className="mt-4 text-lg text-white/40 max-w-2xl mx-auto">
            Start with engineering execution, then extend into hiring and
            finance workflows as each agent delivers production outcomes.
          </p>
        </FadeIn>

        <StaggerContainer
          className="grid md:grid-cols-3 gap-6 lg:gap-8"
          stagger={0.12}
        >
          {suiteProducts.map((product) => (
            <StaggerItem key={product.name}>
              <div
                className={`relative rounded-2xl p-6 lg:p-8 h-full bg-gradient-to-b ${product.gradient} border ${product.borderColor} hover:translate-y-[-4px] transition-all duration-300 group`}
              >
                {product.highlighted && (
                  <div className="absolute -top-3 left-1/2 -translate-x-1/2 px-3 py-1 bg-brand rounded-full text-xs font-semibold text-white">
                    Active
                  </div>
                )}

                <div className="flex items-center justify-between mb-6">
                  <div className="h-12 w-12 rounded-xl bg-white/5 border border-white/10 flex items-center justify-center group-hover:bg-white/10 transition-colors">
                    <product.icon className="h-6 w-6 text-brand" />
                  </div>
                  <span
                    className={`text-xs font-semibold uppercase tracking-wider ${product.statusColor}`}
                  >
                    {product.highlighted && (
                      <span className="inline-block w-1.5 h-1.5 rounded-full bg-neon-green mr-1.5 animate-pulse" />
                    )}
                    {product.status}
                  </span>
                </div>

                <h3 className="text-xl font-bold mb-1">{product.name}</h3>
                <p className="text-sm text-brand/80 font-medium mb-3">
                  {product.tagline}
                </p>
                <p className="text-sm text-white/40 leading-relaxed">
                  {product.description}
                </p>
              </div>
            </StaggerItem>
          ))}
        </StaggerContainer>
      </div>
    </section>
  );
}

/* ─── Bottom CTA ─── */

function BottomCTA() {
  return (
    <section className="py-20 lg:py-28">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <FadeIn>
          <div className="relative rounded-3xl overflow-hidden p-10 sm:p-16 lg:p-20 text-center">
            <div className="absolute inset-0 bg-gradient-to-br from-brand/15 via-brand/5 to-transparent" />
            <div className="absolute inset-0 glass" />
            <div className="absolute inset-0 bg-grid opacity-20" />
            <div className="relative">
              <h2 className="text-3xl sm:text-4xl lg:text-5xl font-bold tracking-tight">
                Need an AI technical co-founder that ships?
              </h2>
              <p className="mt-4 text-lg text-white/45 max-w-xl mx-auto">
                Start with Co-Founder.ai to move from product requirements to
                reviewed, deployable code.
              </p>
              <div className="mt-10">
                <Link
                  href="/waitlist"
                  className="inline-flex items-center justify-center px-10 py-4 bg-brand text-white font-semibold rounded-xl hover:bg-brand-dark transition-all duration-200 shadow-glow hover:shadow-glow-lg text-lg"
                >
                  Join the Waitlist
                </Link>
              </div>
            </div>
          </div>
        </FadeIn>
      </div>
    </section>
  );
}
