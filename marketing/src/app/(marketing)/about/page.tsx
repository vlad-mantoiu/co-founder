import type { Metadata } from "next";
import { Target, Heart, Rocket, Shield, Users, Code2 } from "lucide-react";
import { FadeIn, StaggerContainer, StaggerItem } from "@/components/marketing/fade-in";

export const metadata: Metadata = {
  title: "About",
  description:
    "Co-Founder.ai was built by founders, for founders. Learn about our mission to make technical co-founders accessible to every startup.",
};

const values = [
  {
    icon: Rocket,
    title: "Ship Fast, Learn Faster",
    description:
      "We believe speed is a feature. The faster you ship, the faster you learn what your customers actually need.",
  },
  {
    icon: Heart,
    title: "Stay Honest",
    description:
      "No hype, no inflated promises. We tell you exactly what our system can and cannot do. Trust is the foundation.",
  },
  {
    icon: Shield,
    title: "Protect the Builder",
    description:
      "Your code is yours. Your data is yours. Your IP is yours. We will never compromise on this.",
  },
  {
    icon: Users,
    title: "Founders First",
    description:
      "Every feature we build starts with one question: does this help founders ship faster? If not, we skip it.",
  },
  {
    icon: Code2,
    title: "Quality Over Shortcuts",
    description:
      "We generate production-grade code with real tests, proper architecture, and maintainable patterns. No duct tape.",
  },
  {
    icon: Target,
    title: "Relentless Focus",
    description:
      "We do one thing and we do it exceptionally well: turn your vision into working, deployed software.",
  },
];

const milestones = [
  {
    year: "2024",
    title: "The Problem",
    description:
      "Our founding team watched dozens of great startup ideas die because non-technical founders could not find or afford a technical co-founder. The talent gap was real, and the solutions were broken: dev agencies charged $30k+/month, freelancers disappeared, and learning to code took years.",
  },
  {
    year: "2024",
    title: "The Breakthrough",
    description:
      "We asked a simple question: what if AI could be the technical co-founder? Not a code autocomplete tool, not a chatbot that writes snippets, but a full autonomous development system that architects, builds, tests, and deploys production software.",
  },
  {
    year: "2025",
    title: "The Product",
    description:
      "After 18 months of research and engineering, Co-Founder.ai launched in beta. An agentic system that understands your entire project, remembers every decision, runs code in sandboxes, and deploys to your infrastructure. The response from founders was immediate.",
  },
  {
    year: "2026",
    title: "The Mission",
    description:
      "Today, over 2,000 founders use Co-Founder.ai to build their products. Our mission is simple: make world-class technical execution accessible to every founder with a vision worth building.",
  },
];

export default function AboutPage() {
  return (
    <>
      {/* Hero */}
      <section className="relative pt-32 pb-20 lg:pt-40 lg:pb-28 overflow-hidden">
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[600px] h-[400px] bg-brand/8 rounded-full blur-[120px] pointer-events-none" />
        <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <FadeIn className="text-center max-w-3xl mx-auto">
            <p className="text-sm uppercase tracking-widest text-brand font-medium mb-4">
              About Us
            </p>
            <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold tracking-tight">
              Every Founder Deserves a{" "}
              <span className="bg-gradient-to-r from-brand to-brand-light bg-clip-text text-transparent">
                Technical Co-Founder
              </span>
            </h1>
            <p className="mt-6 text-lg text-white/50 leading-relaxed">
              We are building the autonomous development system that bridges the
              gap between vision and execution. No equity split required.
            </p>
          </FadeIn>
        </div>
      </section>

      {/* Story Timeline */}
      <section className="py-24 lg:py-32 border-t border-white/5">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
          <FadeIn className="text-center mb-16">
            <h2 className="text-3xl sm:text-4xl font-bold tracking-tight">
              Our Story
            </h2>
          </FadeIn>

          <div className="relative">
            {/* Vertical line */}
            <div className="absolute left-4 md:left-1/2 top-0 bottom-0 w-px bg-gradient-to-b from-transparent via-brand/30 to-transparent" />

            <div className="space-y-12">
              {milestones.map((m, i) => (
                <FadeIn
                  key={m.title}
                  delay={i * 0.1}
                  direction={i % 2 === 0 ? "left" : "right"}
                >
                  <div
                    className={`relative flex flex-col md:flex-row gap-6 ${i % 2 === 1 ? "md:flex-row-reverse" : ""}`}
                  >
                    {/* Node */}
                    <div className="absolute left-4 md:left-1/2 -translate-x-1/2 w-3 h-3 rounded-full bg-brand border-2 border-obsidian" />

                    {/* Content */}
                    <div
                      className={`ml-12 md:ml-0 md:w-1/2 ${i % 2 === 0 ? "md:pr-12 md:text-right" : "md:pl-12"}`}
                    >
                      <span className="text-xs font-mono text-brand/60">
                        {m.year}
                      </span>
                      <h3 className="text-xl font-bold mt-1 mb-2">
                        {m.title}
                      </h3>
                      <p className="text-sm text-white/45 leading-relaxed">
                        {m.description}
                      </p>
                    </div>
                  </div>
                </FadeIn>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* Values */}
      <section className="py-24 lg:py-32 border-t border-white/5">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <FadeIn className="text-center mb-16">
            <p className="text-sm uppercase tracking-widest text-brand font-medium mb-4">
              Values
            </p>
            <h2 className="text-3xl sm:text-4xl font-bold tracking-tight">
              What We Stand For
            </h2>
          </FadeIn>

          <StaggerContainer
            className="grid sm:grid-cols-2 lg:grid-cols-3 gap-6"
            stagger={0.08}
          >
            {values.map((v) => (
              <StaggerItem key={v.title}>
                <div className="glass rounded-2xl p-6 lg:p-8 h-full group hover:bg-white/[0.04] transition-colors duration-300">
                  <div className="h-12 w-12 rounded-xl bg-brand/10 border border-brand/20 flex items-center justify-center mb-5 group-hover:bg-brand/15 transition-colors">
                    <v.icon className="h-6 w-6 text-brand" />
                  </div>
                  <h3 className="text-lg font-bold mb-2">{v.title}</h3>
                  <p className="text-sm text-white/40 leading-relaxed">
                    {v.description}
                  </p>
                </div>
              </StaggerItem>
            ))}
          </StaggerContainer>
        </div>
      </section>

      {/* Metrics */}
      <section className="py-24 lg:py-32 border-t border-white/5">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <StaggerContainer
            className="grid grid-cols-2 lg:grid-cols-4 gap-6 text-center"
            stagger={0.1}
          >
            {[
              { value: "2,000+", label: "Founders building" },
              { value: "150k+", label: "Commits shipped" },
              { value: "99.9%", label: "Uptime" },
              { value: "0%", label: "Equity taken" },
            ].map((stat) => (
              <StaggerItem key={stat.label}>
                <div className="glass rounded-2xl p-6 lg:p-8">
                  <p className="text-3xl lg:text-4xl font-bold text-brand">
                    {stat.value}
                  </p>
                  <p className="mt-2 text-sm text-white/40">{stat.label}</p>
                </div>
              </StaggerItem>
            ))}
          </StaggerContainer>
        </div>
      </section>
    </>
  );
}
