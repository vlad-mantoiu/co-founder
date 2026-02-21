import type { Metadata } from 'next'
import { sharedOG, SITE_URL } from '@/lib/seo'
import ContactContent from './contact-content'

export const metadata: Metadata = {
  title: 'Contact',
  description: 'Have a question about Co-Founder.ai? Reach our team at hello@getinsourced.ai. We respond within 24 hours on business days.',
  alternates: { canonical: `${SITE_URL}/contact/` },
  openGraph: {
    ...sharedOG,
    title: 'Contact | GetInsourced',
    description: 'Have a question about Co-Founder.ai? Reach our team at hello@getinsourced.ai. We respond within 24 hours on business days.',
    url: `${SITE_URL}/contact/`,
  },
}

export default function ContactPage() {
  return <ContactContent />
}
