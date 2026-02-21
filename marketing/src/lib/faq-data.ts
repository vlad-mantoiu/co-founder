/**
 * Shared FAQ data for /cofounder page.
 * Used by both:
 *   - home-content.tsx (visible FAQ accordion, client component)
 *   - cofounder/page.tsx (FAQPage JSON-LD, server component)
 *
 * Kept as a plain module (no "use client") so server components can import it directly.
 */

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
