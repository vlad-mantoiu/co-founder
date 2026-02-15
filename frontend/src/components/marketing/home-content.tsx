"use client";

import { useState } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import {
  ArrowRight,
  Brain,
  Shield,
  MessageSquare,
  Moon,
  Code2,
  Rocket,
  TestTube,
  MessageCircle,
  Check,
  X as XIcon,
  Lock,
  Eye,
  Server,
  Zap,
  Sparkles,
  Users,
  TrendingUp,
  Bot,
} from "lucide-react";
import { FadeIn, StaggerContainer, StaggerItem } from "./fade-in";

export default function HomeContent() {
  return (
    <>
      <InsourcedHero />
      <FlagshipProduct />
      <ProductSuiteRoadmap />
      <BottomCTA />
      <LogoTicker />
      <ComparisonSection />
      <FeatureGrid />
      <HowItWorksSection />
      <TestimonialSection />
      <SecuritySection />
      <CTASection />
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
        <motion.div
          initial={{ opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, ease: [0.22, 1, 0.36, 1] }}
        >
          {/* Pill badge */}
          <div className="inline-flex items-center gap-2 px-5 py-2 rounded-full glass-card-strong text-sm text-white/80 mb-10">
            <span className="w-2 h-2 rounded-full bg-neon-green animate-pulse" />
            FLAGSHIP LIVE: CO-FOUNDER.AI
          </div>

          <h1 className="text-5xl sm:text-6xl lg:text-7xl xl:text-8xl font-bold tracking-tight leading-[1.05]">
            The Future of Building
            <br />
            is{" "}
            <span className="glow-text">Insourced.</span>
          </h1>

          <p className="mt-8 text-lg sm:text-xl lg:text-2xl text-white/50 leading-relaxed max-w-3xl mx-auto">
            Stop outsourcing your vision. Scale with a suite of autonomous AI
            agents that architect, code, hire, and manage — so you keep
            100% of your equity.
          </p>

          <div className="mt-12 flex flex-col sm:flex-row gap-4 justify-center">
            <Link
              href="/sign-up"
              className="inline-flex items-center justify-center px-10 py-4.5 bg-brand text-white font-semibold rounded-xl hover:bg-brand-dark transition-all duration-200 shadow-glow hover:shadow-glow-lg text-lg"
            >
              Hire Your Co-Founder
            </Link>
            <a
              href="#suite"
              className="inline-flex items-center justify-center gap-2 px-10 py-4.5 glass text-white font-medium rounded-xl hover:bg-white/5 transition-all duration-200 text-lg"
            >
              View The Roadmap
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
              Trusted by{" "}
              <span className="text-white/70 font-medium">2,000+</span>{" "}
              non-technical founders
            </p>
          </div>
        </motion.div>
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
                  Your autonomous AI technical co-founder. It architects, codes,
                  tests, and deploys your product — 24/7 — for a fraction of
                  what you would pay a dev shop. No equity required.
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

                <Link
                  href="/sign-up"
                  className="inline-flex items-center gap-2 px-8 py-4 bg-brand text-white font-semibold rounded-xl hover:bg-brand-dark transition-all duration-200 shadow-glow hover:shadow-glow-lg text-lg"
                >
                  Start Building
                  <ArrowRight className="h-5 w-5" />
                </Link>
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
      "AI-powered interviewing and candidate evaluation. Screen thousands of applicants in hours, not weeks.",
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
      "Multi-agent development squads that tackle complex codebases in parallel. Your engineering team, multiplied.",
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
      "Autonomous financial modeling, investor reporting, and runway management. Your AI CFO.",
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
            One Platform. Every Role.
          </h2>
          <p className="mt-4 text-lg text-white/40 max-w-2xl mx-auto">
            A growing suite of autonomous agents replacing the roles
            startups can&apos;t afford to fill.
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

/* ─── Bottom CTA — Reclaim Your Equity ─── */

function BottomCTA() {
  const [email, setEmail] = useState("");
  const [submitted, setSubmitted] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (email.trim()) {
      setSubmitted(true);
    }
  };

  return (
    <section className="py-20 lg:py-28">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <FadeIn>
          <div className="relative rounded-3xl overflow-hidden p-10 sm:p-16 lg:p-20 text-center">
            {/* Background */}
            <div className="absolute inset-0 bg-gradient-to-br from-brand/15 via-brand/5 to-transparent" />
            <div className="absolute inset-0 glass" />
            <div className="absolute inset-0 bg-grid opacity-20" />

            <div className="relative">
              <h2 className="text-3xl sm:text-4xl lg:text-5xl font-bold tracking-tight">
                Reclaim Your{" "}
                <span className="glow-text">Equity.</span>
              </h2>
              <p className="mt-4 text-lg text-white/45 max-w-xl mx-auto">
                Join the waitlist for early access to the full Insourced suite.
                Be first in line when Interview, Swarm, and Fund go live.
              </p>

              {submitted ? (
                <motion.div
                  initial={{ opacity: 0, scale: 0.95 }}
                  animate={{ opacity: 1, scale: 1 }}
                  className="mt-10 inline-flex items-center gap-2 px-6 py-3 glass-card-strong rounded-xl"
                >
                  <Check className="h-5 w-5 text-neon-green" />
                  <span className="text-white font-medium">
                    You&apos;re on the list. We&apos;ll be in touch.
                  </span>
                </motion.div>
              ) : (
                <form
                  onSubmit={handleSubmit}
                  className="mt-10 max-w-md mx-auto"
                >
                  <div className="gradient-border flex items-center p-1">
                    <input
                      type="email"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      placeholder="you@company.com"
                      required
                      className="flex-1 bg-transparent px-5 py-3.5 text-sm text-white placeholder:text-white/30 focus:outline-none"
                    />
                    <button
                      type="submit"
                      className="px-6 py-3 bg-brand text-white text-sm font-semibold rounded-xl hover:bg-brand-dark transition-colors shrink-0"
                    >
                      Get Early Access
                    </button>
                  </div>
                </form>
              )}
            </div>
          </div>
        </FadeIn>
      </div>
    </section>
  );
}

/* ─── Logo Ticker ─── */

const integrations = [
  "React",
  "Next.js",
  "Python",
  "TypeScript",
  "AWS",
  "GitHub",
  "PostgreSQL",
  "Docker",
  "Redis",
  "Node.js",
  "Tailwind CSS",
  "Vercel",
];

function LogoTicker() {
  return (
    <section id="integrations" className="py-16 border-y border-white/5">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <p className="text-center text-sm text-white/30 mb-8 uppercase tracking-widest font-medium">
          Works with the tools you already use
        </p>
      </div>
      <div className="relative overflow-hidden">
        <div className="absolute left-0 top-0 bottom-0 w-24 bg-gradient-to-r from-obsidian to-transparent z-10" />
        <div className="absolute right-0 top-0 bottom-0 w-24 bg-gradient-to-l from-obsidian to-transparent z-10" />
        <div className="flex animate-marquee whitespace-nowrap">
          {[...integrations, ...integrations].map((name, i) => (
            <div
              key={i}
              className="mx-4 flex-shrink-0 px-6 py-2.5 glass rounded-lg text-sm text-white/40 font-medium"
            >
              {name}
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

/* ─── Comparison ─── */

const comparisonData = {
  rows: [
    { label: "Monthly Cost", agency: "$15k - $40k", self: "Your time", ai: "$299" },
    { label: "Time to Ship", agency: "6-12 weeks", self: "6-18 months", ai: "Days" },
    { label: "Availability", agency: "Business hours", self: "Your schedule", ai: "24/7" },
    { label: "Code Ownership", agency: "Depends", self: "Yours", ai: "100% yours" },
    { label: "Expertise Level", agency: "Variable", self: "Beginner", ai: "Senior-level" },
    { label: "Scales With You", agency: "Re-negotiate", self: "Bottleneck", ai: "Instantly" },
  ],
};

function ComparisonSection() {
  return (
    <section className="py-24 lg:py-32">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <FadeIn className="text-center mb-16">
          <h2 className="text-3xl sm:text-4xl lg:text-5xl font-bold tracking-tight">
            Three paths to building your startup.
            <br />
            <span className="text-white/40">Only one makes sense.</span>
          </h2>
        </FadeIn>

        <FadeIn delay={0.15}>
          <div className="grid md:grid-cols-3 gap-4 lg:gap-6">
            {/* Dev Agency */}
            <div className="glass rounded-2xl p-6 lg:p-8">
              <div className="flex items-center gap-3 mb-6">
                <div className="h-10 w-10 rounded-xl bg-red-500/10 flex items-center justify-center">
                  <XIcon className="h-5 w-5 text-red-400" />
                </div>
                <h3 className="text-lg font-bold">Dev Agency</h3>
              </div>
              <div className="space-y-4">
                {comparisonData.rows.map((row) => (
                  <div key={row.label} className="flex justify-between items-center py-2 border-b border-white/5 last:border-0">
                    <span className="text-sm text-white/40">{row.label}</span>
                    <span className="text-sm text-red-400/80 font-medium">
                      {row.agency}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            {/* Self-Taught */}
            <div className="glass rounded-2xl p-6 lg:p-8">
              <div className="flex items-center gap-3 mb-6">
                <div className="h-10 w-10 rounded-xl bg-yellow-500/10 flex items-center justify-center">
                  <XIcon className="h-5 w-5 text-yellow-400" />
                </div>
                <h3 className="text-lg font-bold">Going Self-Taught</h3>
              </div>
              <div className="space-y-4">
                {comparisonData.rows.map((row) => (
                  <div key={row.label} className="flex justify-between items-center py-2 border-b border-white/5 last:border-0">
                    <span className="text-sm text-white/40">{row.label}</span>
                    <span className="text-sm text-yellow-400/80 font-medium">
                      {row.self}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            {/* Co-Founder.ai */}
            <div className="relative rounded-2xl p-6 lg:p-8 bg-gradient-to-b from-brand/10 to-brand/5 border border-brand/20">
              <div className="absolute -top-3 left-1/2 -translate-x-1/2 px-3 py-1 bg-brand rounded-full text-xs font-semibold text-white">
                Best Value
              </div>
              <div className="flex items-center gap-3 mb-6">
                <div className="h-10 w-10 rounded-xl bg-brand/20 flex items-center justify-center">
                  <Check className="h-5 w-5 text-brand-light" />
                </div>
                <h3 className="text-lg font-bold">Co-Founder.ai</h3>
              </div>
              <div className="space-y-4">
                {comparisonData.rows.map((row) => (
                  <div key={row.label} className="flex justify-between items-center py-2 border-b border-white/5 last:border-0">
                    <span className="text-sm text-white/50">{row.label}</span>
                    <span className="text-sm text-neon-green font-semibold">
                      {row.ai}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </FadeIn>
      </div>
    </section>
  );
}

/* ─── Feature Bento Grid ─── */

const features = [
  {
    icon: Brain,
    title: "Memory Engine",
    description:
      "Retains your entire codebase context, architecture decisions, and product requirements across every session. No repeating yourself.",
    span: "md:col-span-2 lg:col-span-3",
  },
  {
    icon: Shield,
    title: "Safety Box",
    description:
      "Every code change runs in a sandboxed environment. Nothing reaches production without your explicit approval.",
    span: "md:col-span-1 lg:col-span-1",
  },
  {
    icon: MessageSquare,
    title: "Async Operations",
    description:
      "Check in from anywhere. Review progress, approve changes, and steer direction through simple messages.",
    span: "md:col-span-1 lg:col-span-1",
  },
  {
    icon: Moon,
    title: "Nightly Janitor",
    description:
      "While you sleep, your co-founder runs maintenance, updates dependencies, fixes warnings, and keeps your codebase healthy.",
    span: "md:col-span-2 lg:col-span-3",
  },
];

function FeatureGrid() {
  return (
    <section id="features" className="py-24 lg:py-32">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <FadeIn className="text-center mb-16">
          <p className="text-sm uppercase tracking-widest text-brand font-medium mb-4">
            Capabilities
          </p>
          <h2 className="text-3xl sm:text-4xl lg:text-5xl font-bold tracking-tight">
            Built for Founders Who Ship
          </h2>
        </FadeIn>

        <StaggerContainer
          className="grid md:grid-cols-2 lg:grid-cols-4 gap-4 lg:gap-5"
          stagger={0.1}
        >
          {features.map((feat) => (
            <StaggerItem
              key={feat.title}
              className={`glass rounded-2xl p-6 lg:p-8 group hover:bg-white/[0.04] transition-colors duration-300 ${feat.span}`}
            >
              <div className="h-12 w-12 rounded-xl bg-brand/10 border border-brand/20 flex items-center justify-center mb-5 group-hover:bg-brand/15 transition-colors">
                <feat.icon className="h-6 w-6 text-brand" />
              </div>
              <h3 className="text-xl font-bold mb-3">{feat.title}</h3>
              <p className="text-white/45 leading-relaxed">
                {feat.description}
              </p>
            </StaggerItem>
          ))}
        </StaggerContainer>
      </div>
    </section>
  );
}

/* ─── How It Works ─── */

const steps = [
  {
    icon: MessageCircle,
    step: "01",
    title: "Describe",
    description:
      "Tell your co-founder what you want to build. Describe features, user stories, and goals in plain English.",
  },
  {
    icon: Code2,
    step: "02",
    title: "Architect & Build",
    description:
      "AI designs the system architecture, writes production-grade code, and creates comprehensive test coverage.",
  },
  {
    icon: TestTube,
    step: "03",
    title: "Review & Correct",
    description:
      "Automated testing catches issues before they ship. You review changes and provide feedback in real time.",
  },
  {
    icon: Rocket,
    step: "04",
    title: "Ship",
    description:
      "Deploy to your infrastructure with a single click. Your app goes live on your domain, under your control.",
  },
];

function HowItWorksSection() {
  return (
    <section
      id="how-it-works"
      className="py-24 lg:py-32 border-t border-white/5"
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <FadeIn className="text-center mb-16">
          <p className="text-sm uppercase tracking-widest text-brand font-medium mb-4">
            Process
          </p>
          <h2 className="text-3xl sm:text-4xl lg:text-5xl font-bold tracking-tight">
            From Idea to Deployed Product
          </h2>
          <p className="mt-4 text-lg text-white/40 max-w-2xl mx-auto">
            A continuous loop of building, testing, and shipping. Your
            co-founder handles the entire development lifecycle.
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
  );
}

/* ─── Testimonials ─── */

const testimonials = [
  {
    quote:
      "I went from idea to paying customers in 6 weeks. My co-founder handles the technical side so I can focus entirely on growth.",
    name: "Sarah Chen",
    role: "Founder, PayFlow",
    initials: "SC",
    gradient: "from-brand to-neon-cyan",
  },
  {
    quote:
      "We evaluated dev agencies at $25k/month. Co-Founder.ai delivers the same output quality at a fraction of the cost, and it never takes PTO.",
    name: "Marcus Rivera",
    role: "CEO, Stackline",
    initials: "MR",
    gradient: "from-brand to-neon-pink",
  },
  {
    quote:
      "The memory feature is incredible. It remembers every decision we made and never loses context. Like working with a partner who never forgets.",
    name: "Aisha Patel",
    role: "Founder, TrustLoop",
    initials: "AP",
    gradient: "from-neon-green to-brand",
  },
];

function TestimonialSection() {
  return (
    <section className="py-24 lg:py-32 border-t border-white/5">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <FadeIn className="text-center mb-16">
          <p className="text-sm uppercase tracking-widest text-brand font-medium mb-4">
            Testimonials
          </p>
          <h2 className="text-3xl sm:text-4xl lg:text-5xl font-bold tracking-tight">
            Founders Are Shipping Faster
          </h2>
        </FadeIn>

        <StaggerContainer
          className="grid md:grid-cols-3 gap-6"
          stagger={0.1}
        >
          {testimonials.map((t) => (
            <StaggerItem key={t.name}>
              <div className="glass-strong rounded-2xl p-6 lg:p-8 h-full flex flex-col hover:translate-y-[-2px] transition-transform duration-300">
                <p className="text-white/70 leading-relaxed flex-1">
                  &ldquo;{t.quote}&rdquo;
                </p>
                <div className="mt-6 flex items-center gap-3">
                  <div
                    className={`w-10 h-10 rounded-full bg-gradient-to-br ${t.gradient} flex items-center justify-center text-xs font-bold text-white`}
                  >
                    {t.initials}
                  </div>
                  <div>
                    <p className="text-sm font-semibold">{t.name}</p>
                    <p className="text-xs text-white/40">{t.role}</p>
                  </div>
                </div>
              </div>
            </StaggerItem>
          ))}
        </StaggerContainer>
      </div>
    </section>
  );
}

/* ─── Security ─── */

const securityPoints = [
  {
    icon: Lock,
    title: "End-to-End Encryption",
    text: "All data in transit and at rest is encrypted with AES-256.",
  },
  {
    icon: Eye,
    title: "Never Trained On Your Code",
    text: "Your intellectual property is never used to train models. Period.",
  },
  {
    icon: Server,
    title: "SOC2 Compliant Infrastructure",
    text: "Enterprise-grade infrastructure with full audit logging.",
  },
  {
    icon: Zap,
    title: "Full Export, Anytime",
    text: "Your code, your data. Export everything with a single click.",
  },
];

function SecuritySection() {
  return (
    <section className="py-24 lg:py-32">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <FadeIn className="text-center mb-16">
          <p className="text-sm uppercase tracking-widest text-brand font-medium mb-4">
            Security
          </p>
          <h2 className="text-3xl sm:text-4xl lg:text-5xl font-bold tracking-tight">
            Your Code. Your IP.{" "}
            <span className="text-white/40">Zero Compromises.</span>
          </h2>
        </FadeIn>

        <StaggerContainer
          className="grid sm:grid-cols-2 lg:grid-cols-4 gap-5"
          stagger={0.08}
        >
          {securityPoints.map((p) => (
            <StaggerItem key={p.title}>
              <div className="glass rounded-2xl p-6 text-center h-full">
                <div className="h-12 w-12 rounded-xl bg-brand/10 border border-brand/20 flex items-center justify-center mx-auto mb-4">
                  <p.icon className="h-6 w-6 text-brand" />
                </div>
                <h3 className="font-bold mb-2">{p.title}</h3>
                <p className="text-sm text-white/40 leading-relaxed">
                  {p.text}
                </p>
              </div>
            </StaggerItem>
          ))}
        </StaggerContainer>
      </div>
    </section>
  );
}

/* ─── Final CTA ─── */

function CTASection() {
  return (
    <section className="py-24 lg:py-32 border-t border-white/5">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <FadeIn>
          <div className="relative rounded-3xl overflow-hidden p-10 sm:p-16 lg:p-20 text-center">
            {/* Background */}
            <div className="absolute inset-0 bg-gradient-to-br from-brand/15 via-brand/5 to-transparent" />
            <div className="absolute inset-0 glass" />

            <div className="relative">
              <h2 className="text-3xl sm:text-4xl lg:text-5xl font-bold tracking-tight">
                Ready to Ship Your Product?
              </h2>
              <p className="mt-4 text-lg text-white/45 max-w-xl mx-auto">
                Join 2,000+ founders who stopped waiting for a technical
                co-founder and started building.
              </p>
              <div className="mt-10 flex flex-col sm:flex-row gap-4 justify-center">
                <Link
                  href="/sign-up"
                  className="inline-flex items-center justify-center px-8 py-4 bg-brand text-white font-semibold rounded-xl hover:bg-brand-dark transition-all duration-200 shadow-glow hover:shadow-glow-lg text-lg"
                >
                  Start Building Free
                </Link>
                <Link
                  href="/pricing"
                  className="inline-flex items-center justify-center gap-2 px-8 py-4 glass text-white font-medium rounded-xl hover:bg-white/5 transition-all duration-200 text-lg"
                >
                  View Pricing
                  <ArrowRight className="h-5 w-5" />
                </Link>
              </div>
            </div>
          </div>
        </FadeIn>
      </div>
    </section>
  );
}
