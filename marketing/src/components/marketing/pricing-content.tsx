"use client";

import { useState } from "react";
import Link from "next/link";
import { Check, Zap, Star, Building2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { FadeIn, StaggerContainer, StaggerItem } from "./fade-in";
import { pricingFaqs } from "@/lib/faq-data";

export { pricingFaqs };

const plans = [
  {
    name: "The Bootstrapper",
    slug: "bootstrapper",
    icon: Zap,
    monthlyPrice: 99,
    annualPrice: 79,
    description:
      "For solo founders shipping and validating an early-stage product.",
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
    slug: "partner",
    icon: Star,
    monthlyPrice: 299,
    annualPrice: 239,
    description:
      "For founders who need faster execution with a full autonomous build loop.",
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
    slug: "cto_scale",
    icon: Building2,
    monthlyPrice: 999,
    annualPrice: 799,
    description:
      "For teams running multi-agent workflows with advanced control needs.",
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

function getPricingHref(): string {
  return "/waitlist";
}

export default function PricingContent() {
  const [annual, setAnnual] = useState(false);

  return (
    <>
      {/* Hero */}
      <section className="relative pt-32 pb-16 lg:pt-40 lg:pb-20 overflow-hidden">
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[600px] h-[400px] bg-brand/8 rounded-full blur-[120px] pointer-events-none" />
        <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <div className="hero-fade">
            <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold tracking-tight">
              Pricing for Your AI Technical Co-Founder
              <br />
              <span className="text-white/40">
                Clear plans for founders at every stage
              </span>
            </h1>
          </div>
          <div className="hero-fade-delayed">
            <p className="mt-6 text-lg text-white/50 max-w-2xl mx-auto">
              Choose the execution depth you need today, from first-product
              validation to multi-agent delivery. No hidden fees or equity
              tradeoffs.
            </p>
            <p className="mt-4 text-sm sm:text-base text-white/40 max-w-2xl mx-auto">
              Quick answer: every plan includes an AI technical co-founder that
              helps you build, test, and ship code you own.
            </p>
          </div>
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
                    {annual && (
                      <div className="mt-1">
                        <span className="text-xs text-white/30">billed annually</span>
                      </div>
                    )}
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
                    href={getPricingHref()}
                    className={cn(
                      "block w-full text-center py-3.5 rounded-xl font-semibold text-sm transition-all duration-200",
                      plan.popular
                        ? "bg-brand text-white hover:bg-brand-dark shadow-glow hover:shadow-glow-lg"
                        : "glass hover:bg-white/5 text-white"
                    )}
                  >
                    Choose {plan.name}
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
            {pricingFaqs.map((faq, i) => (
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
