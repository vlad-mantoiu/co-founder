import type { Metadata } from "next";
import HomeContent from "@/components/marketing/home-content";

export const metadata: Metadata = {
  title: "Co-Founder.ai | Your AI Technical Co-Founder",
  description:
    "Co-Founder.ai is an AI technical co-founder that turns product requirements into architecture, production code, tested pull requests, and deployment-ready changes.",
};

export default function CofounderPage() {
  return <HomeContent />;
}
