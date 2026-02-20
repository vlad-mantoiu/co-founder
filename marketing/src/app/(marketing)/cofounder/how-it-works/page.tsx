import type { Metadata } from "next";
import HowItWorksSection from "@/components/marketing/how-it-works-section";

export const metadata: Metadata = {
  title: "How It Works | Co-Founder.ai",
  description:
    "Learn how Co-Founder.ai takes you from idea to deployment: define goals, generate architecture and code, review tested changes, and ship.",
};

export default function HowItWorksPage() {
  return (
    <div className="pt-20">
      <HowItWorksSection />
    </div>
  );
}
