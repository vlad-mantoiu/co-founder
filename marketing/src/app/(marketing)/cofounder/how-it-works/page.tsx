import type { Metadata } from "next";
import HowItWorksSection from "@/components/marketing/how-it-works-section";

export const metadata: Metadata = {
  title: "How It Works | Co-Founder.ai",
  description:
    "From idea to deployed product in four steps. Describe, architect, review, and ship with your AI technical co-founder.",
};

export default function HowItWorksPage() {
  return (
    <div className="pt-20">
      <HowItWorksSection />
    </div>
  );
}
