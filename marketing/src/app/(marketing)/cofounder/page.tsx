import type { Metadata } from "next";
import { sharedOG, SITE_URL } from '@/lib/seo'
import HomeContent from "@/components/marketing/home-content";
import { cofounderFaqs } from "@/lib/faq-data";
import { PageContentWrapper } from "@/components/marketing/loading/page-content-wrapper";
import { HeroSkeleton } from "@/components/marketing/loading/skeleton-templates";

export const metadata: Metadata = {
  title: 'Co-Founder.ai',
  description: 'Co-Founder.ai: the AI that replaces your technical co-founder. Architecture, code, tests, and deployment — no equity required.',
  alternates: { canonical: `${SITE_URL}/cofounder/` },
  openGraph: {
    ...sharedOG,
    title: 'Co-Founder.ai | GetInsourced',
    description: 'Co-Founder.ai: the AI that replaces your technical co-founder. Architecture, code, tests, and deployment — no equity required.',
    url: `${SITE_URL}/cofounder/`,
  },
}

export default function CofounderPage() {
  return (
    <>
      {/* JSON-LD must stay in server component layer for static export */}
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{
          __html: JSON.stringify({
            '@context': 'https://schema.org',
            '@type': 'SoftwareApplication',
            name: 'Co-Founder.ai',
            url: 'https://cofounder.getinsourced.ai',
            applicationCategory: 'BusinessApplication',
            operatingSystem: 'Web',
            offers: {
              '@type': 'Offer',
              price: '0',
              priceCurrency: 'USD',
              description: 'Free tier available',
            },
            description: 'AI technical co-founder that plans architecture, writes code, runs tests, and prepares deployments for non-technical founders.',
            publisher: {
              '@type': 'Organization',
              name: 'GetInsourced',
              url: 'https://getinsourced.ai',
            },
          }),
        }}
      />
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{
          __html: JSON.stringify({
            '@context': 'https://schema.org',
            '@type': 'FAQPage',
            mainEntity: cofounderFaqs.map(faq => ({
              '@type': 'Question',
              name: faq.question,
              acceptedAnswer: {
                '@type': 'Answer',
                text: faq.answer,
              },
            })),
          }),
        }}
      />
      <PageContentWrapper skeleton={<HeroSkeleton />}>
        <HomeContent />
      </PageContentWrapper>
    </>
  )
}
