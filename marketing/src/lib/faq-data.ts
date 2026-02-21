/**
 * Shared FAQ data for /cofounder and /pricing pages.
 * Used by both:
 *   - home-content.tsx (visible FAQ accordion, client component)
 *   - cofounder/page.tsx (FAQPage JSON-LD, server component)
 *   - pricing-content.tsx (visible FAQ accordion, client component)
 *   - pricing/page.tsx (FAQPage JSON-LD, server component)
 *
 * Kept as a plain module (no "use client") so server components can import it directly.
 */

export const pricingFaqs: { q: string; a: string }[] = [
  {
    q: "What's included in every Co-Founder.ai plan?",
    a: "All plans include an AI technical co-founder that analyzes your requirements, designs architecture, writes production code, runs tests, and prepares deployment-ready changes. You also get GitHub integration, sandbox execution, and 100% code ownership. Higher tiers add priority speed, Deep Memory, Nightly Janitor (automated maintenance), and dedicated support.",
  },
  {
    q: "How is Co-Founder.ai different from hiring a developer or agency?",
    a: "A developer costs $15k–$40k/month with 6–12 week timelines. A CTO takes 15–25% equity. Co-Founder.ai gives you the same senior-level execution starting at $99/month — available 24/7, retaining full context between sessions, and starting immediately. No recruiting, no contracts, no equity negotiation.",
  },
  {
    q: "Which plan is right for me?",
    a: "The Bootstrapper ($99/month) is for solo founders validating an early-stage product — one active project, standard build speed. Autonomous Partner ($299/month) is for founders who need faster execution across multiple projects with Deep Memory and automated maintenance. CTO Scale ($999/month) is for teams running multi-agent workflows with enterprise needs and dedicated support.",
  },
  {
    q: "Can I cancel anytime?",
    a: "Yes. No long-term contracts. Cancel anytime and keep access through your current billing period. Export all code and data before you leave — your code is always 100% yours.",
  },
  {
    q: "Who owns the code Co-Founder.ai generates?",
    a: "You do. Everything built by Co-Founder.ai belongs to you — code, assets, architecture, all of it. We never claim ownership. Your intellectual property is never used to train models.",
  },
]

export const cofounderFaqs: { question: string; answer: string }[] = [
  {
    question: "What does Co-Founder.ai actually do?",
    answer:
      "Co-Founder.ai is your AI technical co-founder — it thinks through product decisions WITH you, then executes. That means generating system architecture, writing production code, running tests, and preparing deployment-ready changes. It's not a no-code builder where you're still doing the building. Think of it as having a senior engineer on call 24/7, without the equity negotiation or 6-week agency ramp-up. You describe what you want; it translates that into technical decisions and working code.",
  },
  {
    question: "Do I need technical skills to use it?",
    answer:
      "No. You communicate in plain language — describe what you want your product to do, and Co-Founder.ai handles the technical translation. It designs the architecture, chooses the right tools, writes the code, and explains every decision in founder-friendly terms. You review and approve changes at each step. If you can describe your product idea, you can work with Co-Founder.ai.",
  },
  {
    question: "Is my idea safe with Co-Founder.ai?",
    answer:
      "Yes. All data is encrypted in transit (TLS 1.3) and at rest (AES-256). Your code and business logic are never used to train models — your IP stays yours. We run on SOC2-compliant infrastructure, and you can export everything at any time. Your idea doesn't leave your control.",
  },
  {
    question: "How is this different from hiring a developer or agency?",
    answer:
      "Hiring a CTO means equity negotiations and months of recruiting. An agency means $15k–$40k/month retainers, 6-week timelines, and handoff risk when the engagement ends. Co-Founder.ai costs $99–$999/month, starts immediately, is available 24/7, never loses context between sessions, and you own 100% of the output. It's senior-level execution without the overhead of a hiring process or a retainer contract.",
  },
  {
    question: "How long does it take to go from idea to MVP?",
    answer:
      "Minutes for strategy, days for working code. The moment you describe your idea, Co-Founder.ai analyzes requirements, designs the architecture, and starts building. You stay in control by reviewing and approving at every step — no waiting for sprint planning or stand-ups. Most founders have a working prototype within a week of starting.",
  },
];
