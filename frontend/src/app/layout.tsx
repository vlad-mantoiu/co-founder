import type { Metadata } from "next";
import { ClerkProvider } from "@clerk/nextjs";
import { GeistSans } from "geist/font/sans";
import { GeistMono } from "geist/font/mono";
import { Space_Grotesk } from "next/font/google";
import "./globals.css";

export const dynamic = "force-dynamic";

const spaceGrotesk = Space_Grotesk({
  subsets: ["latin"],
  variable: "--font-space-grotesk",
  weight: ["300", "400", "500", "600", "700"],
});

export const metadata: Metadata = {
  title: {
    default: "Co-Founder.ai | Your AI Technical Co-Founder",
    template: "%s | Co-Founder.ai",
  },
  description:
    "Turn conversations into shipped products. Co-Founder.ai is an autonomous dev system that architects, codes, tests, and deploys your SaaS. No equity required.",
  openGraph: {
    title: "Co-Founder.ai | Your AI Technical Co-Founder",
    description:
      "Turn conversations into shipped products. An autonomous dev system that architects, codes, tests, and deploys your SaaS.",
    siteName: "Co-Founder.ai",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "Co-Founder.ai | Your AI Technical Co-Founder",
    description:
      "Turn conversations into shipped products. An autonomous dev system that builds your SaaS.",
  },
  robots: { index: true, follow: true },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <ClerkProvider>
      <html lang="en" className="dark">
        <body
          className={`${GeistSans.variable} ${GeistMono.variable} ${spaceGrotesk.variable} antialiased`}
        >
          {children}
        </body>
      </html>
    </ClerkProvider>
  );
}
