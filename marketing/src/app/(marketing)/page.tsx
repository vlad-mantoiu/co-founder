import type { Metadata } from 'next'
import { sharedOG, SITE_URL } from '@/lib/seo'
import InsourcedHomeContent from "@/components/marketing/insourced-home-content";

export const metadata: Metadata = {
  alternates: { canonical: `${SITE_URL}/` },
  openGraph: {
    ...sharedOG,
    title: 'GetInsourced — AI Co-Founder',
    description: 'AI technical co-founder that plans architecture, writes code, runs tests, and ships software for non-technical founders.',
    url: `${SITE_URL}/`,
  },
}

export default function HomePage() {
  return <InsourcedHomeContent />;
}
