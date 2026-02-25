import type { Metadata } from "next";
import { WaitlistContent } from "@/components/marketing/waitlist-content";

export const metadata: Metadata = {
  title: "Join the Inner Circle — Co-Founder.ai Global Waitlist",
  description:
    "Be among the first 200 founders to get 50% off. Join the Co-Founder.ai waitlist and lead the launch.",
  openGraph: {
    title: "Join the Inner Circle — Co-Founder.ai Global Waitlist",
    description:
      "Be among the first 200 founders to get 50% off. Join the Co-Founder.ai waitlist.",
  },
};

export default function WaitlistPage() {
  return <WaitlistContent />;
}
