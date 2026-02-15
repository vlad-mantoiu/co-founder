import type { Metadata } from "next";
import PricingContent from "@/components/marketing/pricing-content";

export const metadata: Metadata = {
  title: "Pricing",
  description:
    "Simple, transparent pricing for Co-Founder.ai. From $99/month for solo founders to enterprise plans for scaling teams. No hidden fees, no equity required.",
};

export default function PricingPage() {
  return <PricingContent />;
}
