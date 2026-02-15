"use client";

import { useState } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import { Check, Zap, Star, Building2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { FadeIn, StaggerContainer, StaggerItem } from "./fade-in";

const plans = [
  {
    name: "The Bootstrapper",
    icon: Zap,
    monthlyPrice: 99,
    annualPrice: 79,
    description: "Perfect for solo founders validating their first product.",
    popular: false,
    features: [
      "Standard build speed",
      "1 active project",
      "Community support",
      "GitHub integration",
      "Basic memory (last 5 sessions)",
      "Sandbox execution",
    ],
  },
  {
    name: "Autonomous Partner",
    icon: Star,
    monthlyPrice: 299,
    annualPrice: 239,
    description:
      "For founders ready to ship fast with a full autonomous dev loop.",
    popular: true,
    features: [
      "Priority build speed",
      "3 active projects",
      "Nightly Janitor included",
      "Deep Memory (full context)",
      "Messaging integration",
      "Priority support",
      "Custom deployment targets",
      "Automated testing suite",
    ],
  },
  {
    name: "CTO Scale",
    icon: Building2,
    monthlyPrice: 999,
    annualPrice: 799,
    description:
      "For teams that need multi-agent workflows and enterprise controls.",
    popular: false,
    features: [
      "Maximum build speed",
      "Unlimited projects",
      "Multi-agent workflows",
      "VPC deployment option",
      "Dedicated support engineer",
      "SOC2 compliance",
      "Custom integrations",
      "SLA guarantee",
      "Priority feature requests",
    ],
  },
];

const faqs = [
  {
    q: "Who owns the code?",
    a: "You do. 100%. Everything built by Co-Founder.ai belongs entirely to you. We never claim ownership of any code, assets, or intellectual property generated for your projects.",
  },
  {
    q: "Can I cancel anytime?",
    a: "Yes. There are no long-term contracts. Cancel your subscription at any time and keep full access to all code and data generated during your subscription. You can export everything before you leave.",
  },
  {
    q: "Does it work with my existing codebase?",
    a: "Absolutely. Co-Founder.ai connects to your GitHub repository and understands your existing code, conventions, and architecture. It builds on top of what you already have rather than starting from scratch.",
  },
  {
    q: "How secure is my data?",
    a: "All data is encrypted in transit (TLS 1.3) and at rest (AES-256). Your code is never used to train models. We run on SOC2-compliant infrastructure with full audit logging and support VPC deployment for enterprise plans.",
  },
];

export default function PricingContent() {
  const [annual, setAnnual] = useState(false);

  return (
    <>
      {/* Hero */}
      <section className="relative pt-32 pb-16 lg:pt-40 lg:pb-20 overflow-hidden">
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[600px] h-[400px] bg-brand/8 rounded-full blur-[120px] pointer-events-none" />
        <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <motion.div
            initial={{ opacity: 0, y: 24 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
          >
            <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold tracking-tight">
              Hire a Senior Engineer
              <br />
              <span className="text-white/40">
                for the price of your coffee habit
              </span>
            </h1>
            <p className="mt-6 text-lg text-white/50 max-w-2xl mx-auto">
              Simple, transparent pricing. No hidden fees, no surprise invoices,
              no equity negotiations. Start building today.
            </p>
          </motion.div>
        </div>
      </section>

      {/* Toggle */}
      <section className="pb-8">
        <div className="flex items-center justify-center gap-4">
          <span
            className={cn(
              "text-sm font-medium transition-colors",
              !annual ? "text-white" : "text-white/40"
            )}
          >
            Monthly
          </span>
          <button
            onClick={() => setAnnual(!annual)}
            className={cn(
              "relative w-14 h-7 rounded-full transition-colors duration-200",
              annual ? "bg-brand" : "bg-white/10"
            )}
            aria-label="Toggle annual pricing"
          >
            <span
              className={cn(
                "absolute top-0.5 left-0.5 w-6 h-6 rounded-full bg-white transition-transform duration-200",
                annual && "translate-x-7"
              )}
            />
          </button>
          <span
            className={cn(
              "text-sm font-medium transition-colors",
              annual ? "text-white" : "text-white/40"
            )}
          >
            Annual
          </span>
          {annual && (
            <span className="px-2.5 py-0.5 bg-neon-green/10 text-neon-green text-xs font-semibold rounded-full">
              Save 20%
            </span>
          )}
        </div>
      </section>

      {/* Pricing Cards */}
      <section className="pb-24 lg:pb-32">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <StaggerContainer
            className="grid md:grid-cols-3 gap-6 lg:gap-8 items-start"
            stagger={0.1}
          >
            {plans.map((plan) => (
              <StaggerItem key={plan.name}>
                <div
                  className={cn(
                    "relative rounded-2xl p-6 lg:p-8 h-full flex flex-col transition-transform duration-300 hover:translate-y-[-4px]",
                    plan.popular
                      ? "bg-gradient-to-b from-brand/15 to-brand/5 border border-brand/25 shadow-glow-lg scale-[1.02]"
                      : "glass"
                  )}
                >
                  {plan.popular && (
                    <div className="absolute -top-3 left-1/2 -translate-x-1/2 px-4 py-1 bg-brand rounded-full text-xs font-semibold text-white">
                      Most Popular
                    </div>
                  )}

                  <div className="flex items-center gap-3 mb-4">
                    <div
                      className={cn(
                        "h-10 w-10 rounded-xl flex items-center justify-center",
                        plan.popular
                          ? "bg-brand/20 border border-brand/30"
                          : "bg-white/5 border border-white/10"
                      )}
                    >
                      <plan.icon
                        className={cn(
                          "h-5 w-5",
                          plan.popular ? "text-brand-light" : "text-white/60"
                        )}
                      />
                    </div>
                    <h3 className="text-lg font-bold">{plan.name}</h3>
                  </div>

                  <div className="mb-4">
                    <span className="text-4xl lg:text-5xl font-bold">
                      ${annual ? plan.annualPrice : plan.monthlyPrice}
                    </span>
                    <span className="text-white/40 text-sm ml-1">/month</span>
                  </div>
                  <p className="text-sm text-white/40 mb-6 leading-relaxed">
                    {plan.description}
                  </p>

                  <ul className="space-y-3 mb-8 flex-1">
                    {plan.features.map((feat) => (
                      <li key={feat} className="flex items-start gap-3">
                        <Check
                          className={cn(
                            "h-4 w-4 mt-0.5 flex-shrink-0",
                            plan.popular ? "text-brand-light" : "text-white/40"
                          )}
                        />
                        <span className="text-sm text-white/60">{feat}</span>
                      </li>
                    ))}
                  </ul>

                  <Link
                    href="/sign-up"
                    className={cn(
                      "block text-center py-3.5 rounded-xl font-semibold text-sm transition-all duration-200",
                      plan.popular
                        ? "bg-brand text-white hover:bg-brand-dark shadow-glow hover:shadow-glow-lg"
                        : "glass hover:bg-white/5 text-white"
                    )}
                  >
                    Get Started
                  </Link>
                </div>
              </StaggerItem>
            ))}
          </StaggerContainer>
        </div>
      </section>

      {/* FAQ */}
      <section className="py-24 lg:py-32 border-t border-white/5">
        <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8">
          <FadeIn className="text-center mb-12">
            <h2 className="text-3xl sm:text-4xl font-bold tracking-tight">
              Frequently Asked Questions
            </h2>
          </FadeIn>

          <div className="space-y-4">
            {faqs.map((faq, i) => (
              <FadeIn key={faq.q} delay={i * 0.08}>
                <details className="group glass rounded-xl overflow-hidden">
                  <summary className="flex items-center justify-between p-5 cursor-pointer list-none text-left font-semibold hover:bg-white/[0.02] transition-colors">
                    {faq.q}
                    <span className="text-white/30 group-open:rotate-45 transition-transform duration-200 text-xl ml-4 flex-shrink-0">
                      +
                    </span>
                  </summary>
                  <div className="px-5 pb-5 text-sm text-white/50 leading-relaxed">
                    {faq.a}
                  </div>
                </details>
              </FadeIn>
            ))}
          </div>
        </div>
      </section>
    </>
  );
}
