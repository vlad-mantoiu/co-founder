import type { Metadata } from "next";
import { GeistSans } from "geist/font/sans";
import { GeistMono } from "geist/font/mono";
import { Space_Grotesk } from "next/font/google";
import "./globals.css";

const spaceGrotesk = Space_Grotesk({
  subsets: ["latin"],
  variable: "--font-space-grotesk",
  weight: ["300", "400", "500", "600", "700"],
});

export const metadata: Metadata = {
  title: {
    default:
      "Insourced AI | AI Technical Co-Founder and Autonomous Agents for Founders",
    template: "%s | Insourced AI",
  },
  description:
    "Insourced AI helps non-technical founders ship software faster. Start with Co-Founder.ai to plan, build, test, and deploy with an AI technical co-founder.",
  openGraph: {
    title:
      "Insourced AI | AI Technical Co-Founder and Autonomous Agents for Founders",
    description:
      "Autonomous AI agents for founders who want faster product execution without outsourced teams.",
    siteName: "Insourced AI",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title:
      "Insourced AI | AI Technical Co-Founder and Autonomous Agents for Founders",
    description:
      "Autonomous AI agents for founders who want faster product execution without outsourced teams.",
  },
  robots: { index: true, follow: true },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <head>
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{
            __html: JSON.stringify({
              "@context": "https://schema.org",
              "@type": "Organization",
              name: "Insourced AI",
              url: "https://getinsourced.ai",
              logo: "https://getinsourced.ai/logo.png",
              description:
                "Insourced AI helps non-technical founders ship software faster with AI agents and an AI technical co-founder.",
              sameAs: [],
            }),
          }}
        />
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{
            __html: JSON.stringify({
              "@context": "https://schema.org",
              "@type": "WebSite",
              name: "Insourced AI",
              url: "https://getinsourced.ai",
              description:
                "AI Technical Co-Founder and Autonomous Agents for Founders",
            }),
          }}
        />
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{
            __html: JSON.stringify({
              "@context": "https://schema.org",
              "@type": "SoftwareApplication",
              name: "Co-Founder.ai",
              url: "https://cofounder.getinsourced.ai",
              applicationCategory: "BusinessApplication",
              operatingSystem: "Web",
              offers: {
                "@type": "Offer",
                price: "0",
                priceCurrency: "USD",
                description: "Free tier available",
              },
              description:
                "AI technical co-founder that plans architecture, writes code, runs tests, and prepares deployments for non-technical founders.",
              publisher: {
                "@type": "Organization",
                name: "Insourced AI",
                url: "https://getinsourced.ai",
              },
            }),
          }}
        />
      </head>
      <body
        className={`${GeistSans.variable} ${GeistMono.variable} ${spaceGrotesk.variable} antialiased`}
      >
        {children}
      </body>
    </html>
  );
}
