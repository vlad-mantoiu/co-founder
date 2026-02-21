import type { Metadata } from "next";
import { GeistSans } from "geist/font/sans";
import { GeistMono } from "geist/font/mono";
import { Space_Grotesk } from "next/font/google";
import { SITE_URL } from "@/lib/seo";
import { SplashScreen } from "@/components/marketing/loading/splash-screen";
import "./globals.css";

const spaceGrotesk = Space_Grotesk({
  subsets: ["latin"],
  variable: "--font-space-grotesk",
  weight: ["300", "400", "500", "600", "700"],
  display: "block",
});

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: {
    default: "GetInsourced — AI Co-Founder",
    template: "%s | GetInsourced",
  },
  description:
    "AI technical co-founder that plans architecture, writes code, runs tests, and ships software for non-technical founders.",
  openGraph: {
    siteName: "GetInsourced",
    type: "website",
    locale: "en_US",
  },
  twitter: {
    card: "summary_large_image",
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
              name: "GetInsourced",
              url: "https://getinsourced.ai",
              logo: "https://getinsourced.ai/logo.png",
              description:
                "GetInsourced helps non-technical founders ship software faster with AI agents and an AI technical co-founder.",
            }),
          }}
        />
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{
            __html: JSON.stringify({
              "@context": "https://schema.org",
              "@type": "WebSite",
              name: "GetInsourced",
              url: "https://getinsourced.ai",
              description:
                "AI Technical Co-Founder and Autonomous Agents for Founders",
            }),
          }}
        />
        <script
          dangerouslySetInnerHTML={{
            __html: `(function(){try{if(sessionStorage.getItem('gi-splash')){document.documentElement.setAttribute('data-no-splash','')}}catch(e){}})();`,
          }}
        />
      </head>
      <body
        className={`${GeistSans.variable} ${GeistMono.variable} ${spaceGrotesk.variable} antialiased`}
      >
        <SplashScreen />
        {children}
      </body>
    </html>
  );
}
