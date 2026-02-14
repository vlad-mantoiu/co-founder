import type { Metadata } from "next";
import { ClerkProvider } from "@clerk/nextjs";
import { GeistSans } from "geist/font/sans";
import { GeistMono } from "geist/font/mono";
import "./globals.css";

// Skip static prerendering for Clerk-enabled pages
export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "AI Co-Founder | Your Technical Partner",
  description: "AI-powered technical co-founder that helps you build and ship software",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <ClerkProvider>
      <html lang="en" className="dark">
        <body className={`${GeistSans.variable} ${GeistMono.variable} antialiased`}>
          {children}
        </body>
      </html>
    </ClerkProvider>
  );
}
