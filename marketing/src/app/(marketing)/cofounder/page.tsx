import type { Metadata } from "next";
import HomeContent from "@/components/marketing/home-content";

export const metadata: Metadata = {
  title: "Co-Founder.ai | Your AI Technical Co-Founder",
  description:
    "Stop giving away 50% equity. Your AI technical co-founder architects, codes, tests, and deploys your product. 24/7 autonomous development for a fraction of what you would pay a dev shop.",
};

export default function CofounderPage() {
  return <HomeContent />;
}
