"use client";

import { MotionConfig } from "framer-motion";
import { Navbar } from "@/components/marketing/navbar";
import { Footer } from "@/components/marketing/footer";
import { RouteProgressBar } from "@/components/marketing/loading/route-progress-bar";

export default function MarketingLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="font-display min-h-screen bg-obsidian text-white">
      <Navbar />
      <MotionConfig reducedMotion="user">
        <RouteProgressBar />
        <main>{children}</main>
      </MotionConfig>
      <Footer />
    </div>
  );
}
