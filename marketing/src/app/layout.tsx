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
    default: "Insourced AI | Autonomous AI Agents for Non-Technical Founders",
    template: "%s | Insourced AI",
  },
  description:
    "Stop outsourcing your vision. Scale with a suite of autonomous AI agents that architect, code, hire, and manage — so you keep 100% of your equity.",
  openGraph: {
    title: "Insourced AI | Autonomous AI Agents for Non-Technical Founders",
    description:
      "A suite of autonomous AI agents replacing the roles startups can't afford to fill.",
    siteName: "Insourced AI",
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "Insourced AI | Autonomous AI Agents for Non-Technical Founders",
    description:
      "A suite of autonomous AI agents replacing the roles startups can't afford to fill.",
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
      <body
        className={`${GeistSans.variable} ${GeistMono.variable} ${spaceGrotesk.variable} antialiased`}
      >
        {children}
      </body>
    </html>
  );
}
