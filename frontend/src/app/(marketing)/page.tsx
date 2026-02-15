import type { Metadata } from "next";
import { auth } from "@clerk/nextjs/server";
import { redirect } from "next/navigation";
import HomeContent from "@/components/marketing/home-content";

export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "Insourced AI | Autonomous AI Agents for Non-Technical Founders",
  description:
    "Build your SaaS without coding or giving away equity. Insourced AI is a suite of autonomous AI agents — starting with Co-Founder.ai, your AI technical co-founder that architects, codes, tests, and deploys production software. The best AI coding agent and development platform for startups.",
};

export default async function HomePage() {
  const { userId } = await auth();
  if (userId) redirect("/dashboard");
  return <HomeContent />;
}
