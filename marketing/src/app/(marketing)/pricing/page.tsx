import type { Metadata } from "next";
import { sharedOG, SITE_URL } from '@/lib/seo'
import PricingContent from "@/components/marketing/pricing-content";

export const metadata: Metadata = {
  title: 'Pricing',
  description: 'Simple, transparent pricing for Co-Founder.ai. Start free, upgrade as your product grows. No per-seat fees. Cancel anytime.',
  alternates: { canonical: `${SITE_URL}/pricing/` },
  openGraph: {
    ...sharedOG,
    title: 'Pricing | GetInsourced',
    description: 'Simple, transparent pricing for Co-Founder.ai. Start free, upgrade as your product grows. No per-seat fees. Cancel anytime.',
    url: `${SITE_URL}/pricing/`,
  },
}

export default function PricingPage() {
  return <PricingContent />;
}
