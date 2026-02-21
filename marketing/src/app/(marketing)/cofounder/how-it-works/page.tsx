import type { Metadata } from "next";
import { sharedOG, SITE_URL } from '@/lib/seo'
import HowItWorksSection from "@/components/marketing/how-it-works-section";

export const metadata: Metadata = {
  title: 'How It Works',
  description: 'See how Co-Founder.ai turns your idea into deployed software: define goals, generate architecture, review tested code, and ship.',
  alternates: { canonical: `${SITE_URL}/cofounder/how-it-works/` },
  openGraph: {
    ...sharedOG,
    title: 'How It Works | GetInsourced',
    description: 'See how Co-Founder.ai turns your idea into deployed software: define goals, generate architecture, review tested code, and ship.',
    url: `${SITE_URL}/cofounder/how-it-works/`,
  },
}

export default function HowItWorksPage() {
  return (
    <div className="pt-20">
      <HowItWorksSection />
    </div>
  );
}
