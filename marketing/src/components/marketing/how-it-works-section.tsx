"use client";

import {
  MessageCircle,
  Code2,
  TestTube,
  Rocket,
} from "lucide-react";
import { FadeIn, StaggerContainer, StaggerItem } from "./fade-in";

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

export default function HowItWorksSection() {
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
  );
}
