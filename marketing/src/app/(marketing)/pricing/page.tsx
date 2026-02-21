import type { Metadata } from "next";
import { sharedOG, SITE_URL } from '@/lib/seo'
import PricingContent from "@/components/marketing/pricing-content";
import { PageContentWrapper } from "@/components/marketing/loading/page-content-wrapper";
import { ListSkeleton } from "@/components/marketing/loading/skeleton-templates";
import { pricingFaqs } from "@/lib/faq-data";

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
  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{
          __html: JSON.stringify({
            '@context': 'https://schema.org',
            '@type': 'FAQPage',
            mainEntity: pricingFaqs.map(faq => ({
              '@type': 'Question',
              name: faq.q,
              acceptedAnswer: {
                '@type': 'Answer',
                text: faq.a,
              },
            })),
          }),
        }}
      />
      <PageContentWrapper skeleton={<ListSkeleton />}>
        <PricingContent />
      </PageContentWrapper>
    </>
  );
}
