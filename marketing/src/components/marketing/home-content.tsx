"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import {
  ArrowRight,
  Brain,
  Shield,
  MessageSquare,
  Moon,
  Check,
  X as XIcon,
  Lock,
  Eye,
  Server,
  Zap,
} from "lucide-react";
import { FadeIn, StaggerContainer, StaggerItem } from "./fade-in";
import HowItWorksSection from "./how-it-works-section";

export default function HomeContent() {
  return (
    <>
      <HeroSection />
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

/* ─── Hero ─── */

const terminalLines = [
  { text: "$ cofound build --idea \"SaaS MVP\"", color: "text-white" },
  { text: "> Analyzing requirements...", color: "text-white/50" },
  { text: "> Designing system architecture...", color: "text-white/50" },
  { text: "> Implementing authentication module...", color: "text-white/50" },
  { text: "> Writing API endpoints (12 routes)...", color: "text-white/50" },
  { text: "> Creating React components...", color: "text-white/50" },
  { text: "> Running tests... 47/47 passed", color: "text-neon-green" },
  { text: "> Deploying to production...", color: "text-white/50" },
  { text: "\u2713 Your MVP is live.", color: "text-neon-green font-semibold" },
];

function HeroSection() {
  return (
    <section className="relative pt-32 pb-20 lg:pt-40 lg:pb-32 overflow-hidden">
      {/* Background glows */}
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[800px] h-[600px] bg-brand/8 rounded-full blur-[120px] pointer-events-none" />
      <div className="absolute top-40 right-0 w-[400px] h-[400px] bg-neon-cyan/5 rounded-full blur-[100px] pointer-events-none" />

      <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid lg:grid-cols-2 gap-12 lg:gap-16 items-center">
          {/* Left column */}
          <div>
            <div className="hero-fade">
              <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full glass text-sm text-white/60 mb-8">
                <span className="w-2 h-2 rounded-full bg-neon-green animate-pulse" />
                Now in public beta
              </div>

              <h1 className="text-4xl sm:text-5xl lg:text-6xl xl:text-7xl font-bold tracking-tight leading-[1.08]">
                Ship Faster Without Giving Away{" "}
                <span className="bg-gradient-to-r from-brand to-brand-light bg-clip-text text-transparent">
                  Founder Equity
                </span>
              </h1>
            </div>

            <div className="hero-fade-delayed">
              <p className="mt-6 text-lg sm:text-xl text-white/50 leading-relaxed max-w-xl">
                Co-Founder.ai is your AI technical co-founder. It turns product
                requirements into architecture, production code, tested pull
                requests, and deployment-ready changes you approve.
              </p>
              <p className="mt-4 text-sm sm:text-base text-white/40 leading-relaxed max-w-xl">
                Quick answer: you get senior-level technical execution without
                giving up equity or managing an outsourced dev shop.
              </p>

              <div className="mt-10 flex flex-col sm:flex-row gap-4">
                <a
                  href="https://cofounder.getinsourced.ai/onboarding"
                  className="inline-flex items-center justify-center px-8 py-4 bg-brand text-white font-semibold rounded-xl hover:bg-brand-dark transition-all duration-200 shadow-glow hover:shadow-glow-lg text-lg"
                >
                  Start Building with Co-Founder.ai
                </a>
                <Link
                  href="/cofounder/how-it-works"
                  className="inline-flex items-center justify-center gap-2 px-8 py-4 glass text-white font-medium rounded-xl hover:bg-white/5 transition-all duration-200 text-lg"
                >
                  See How It Works
                  <ArrowRight className="h-5 w-5" />
                </Link>
              </div>

              {/* Social proof */}
              <div className="mt-12 flex items-center gap-4">
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
            </div>
          </div>

          {/* Right column: terminal mockup */}
          <div className="hero-fade-delayed relative">
            <div className="glass rounded-2xl overflow-hidden shadow-glow-lg">
              {/* Terminal header */}
              <div className="flex items-center gap-2 px-4 py-3 border-b border-white/5">
                <div className="w-3 h-3 rounded-full bg-red-500/70" />
                <div className="w-3 h-3 rounded-full bg-yellow-500/70" />
                <div className="w-3 h-3 rounded-full bg-green-500/70" />
                <span className="ml-2 text-xs text-white/30 font-mono">
                  co-founder.ai
                </span>
              </div>
              {/* Terminal body */}
              <div className="p-5 font-mono text-sm leading-relaxed space-y-1">
                {terminalLines.map((line, i) => (
                  <motion.div
                    key={i}
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: 0.6 + i * 0.15, duration: 0.3 }}
                    className={line.color}
                  >
                    {line.text}
                  </motion.div>
                ))}
                <motion.span
                  initial={{ opacity: 0 }}
                  animate={{ opacity: [0, 1, 0] }}
                  transition={{
                    delay: 2.2,
                    duration: 1,
                    repeat: Infinity,
                  }}
                  className="inline-block w-2.5 h-5 bg-neon-green/80 ml-0.5 mt-1"
                />
              </div>
            </div>
            {/* Decorative glow behind terminal */}
            <div className="absolute -inset-4 bg-brand/5 rounded-3xl blur-2xl -z-10" />
          </div>
        </div>
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
    { label: "Typical Monthly Cost", agency: "$15k - $40k", self: "Your time", ai: "$299" },
    { label: "Typical Time to Ship", agency: "6-12 weeks", self: "6-18 months", ai: "Days" },
    { label: "Team Availability", agency: "Business hours", self: "Your schedule", ai: "24/7" },
    { label: "Code Ownership", agency: "Depends", self: "Yours", ai: "100% yours" },
    { label: "Execution Level", agency: "Variable", self: "Beginner", ai: "Senior-level" },
    { label: "Scaling Effort", agency: "Re-negotiate", self: "Bottleneck", ai: "Instantly" },
  ],
};

function ComparisonSection() {
  return (
    <section className="py-24 lg:py-32">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <FadeIn className="text-center mb-16">
          <h2 className="text-3xl sm:text-4xl lg:text-5xl font-bold tracking-tight">
            Which path gets your product live with the least risk?
          </h2>
          <p className="mt-4 text-lg text-white/40 max-w-2xl mx-auto">
            Quick answer: Co-Founder.ai combines founder control with autonomous
            execution, without agency retainers or equity negotiations.
          </p>
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
            What do you get from an AI technical co-founder?
          </h2>
          <p className="mt-4 text-lg text-white/40 max-w-2xl mx-auto">
            You get persistent product context, controlled code execution, and
            faster shipping without hiring a full dev team.
          </p>
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
            What changes after founders switch to Co-Founder.ai?
          </h2>
          <p className="mt-4 text-lg text-white/40 max-w-2xl mx-auto">
            They spend less time coordinating engineering work and more time on
            customer validation and growth.
          </p>
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
            How does Co-Founder.ai protect your code and IP?
          </h2>
          <p className="mt-4 text-lg text-white/40 max-w-2xl mx-auto">
            Security is built into delivery with encrypted data paths, isolated
            execution, and exportable ownership by default.
          </p>
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

/* ─── CTA ─── */

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
                Ready to turn requirements into shipped code?
              </h2>
              <p className="mt-4 text-lg text-white/45 max-w-xl mx-auto">
                Work with Co-Founder.ai to generate, review, and deploy
                production-ready changes faster.
              </p>
              <div className="mt-10 flex flex-col sm:flex-row gap-4 justify-center">
                <a
                  href="https://cofounder.getinsourced.ai/onboarding"
                  className="inline-flex items-center justify-center px-8 py-4 bg-brand text-white font-semibold rounded-xl hover:bg-brand-dark transition-all duration-200 shadow-glow hover:shadow-glow-lg text-lg"
                >
                  Start Building with Co-Founder.ai
                </a>
                <Link
                  href="/pricing"
                  className="inline-flex items-center justify-center gap-2 px-8 py-4 glass text-white font-medium rounded-xl hover:bg-white/5 transition-all duration-200 text-lg"
                >
                  Compare Plans
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
