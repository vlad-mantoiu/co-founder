import type { Metadata } from "next";
import PricingContent from "@/components/marketing/pricing-content";

export const metadata: Metadata = {
  title: "Pricing",
  description:
    "Transparent pricing for Co-Founder.ai, your AI technical co-founder. Choose a plan for early validation, faster autonomous execution, or multi-agent delivery.",
};

export default function PricingPage() {
  return <PricingContent />;
}
