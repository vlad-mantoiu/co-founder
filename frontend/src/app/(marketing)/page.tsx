import type { Metadata } from "next";
import { headers } from "next/headers";
import { auth } from "@clerk/nextjs/server";
import { redirect } from "next/navigation";
import HomeContent from "@/components/marketing/home-content";
import InsourcedHomeContent from "@/components/marketing/insourced-home-content";

export const dynamic = "force-dynamic";

const INSOURCED_HOSTS = ["www.getinsourced.ai", "getinsourced.ai"];

function isInsourcedHost(host: string): boolean {
  const hostname = host.split(":")[0];
  return INSOURCED_HOSTS.includes(hostname);
}

export async function generateMetadata(): Promise<Metadata> {
  const headersList = await headers();
  const host = headersList.get("host") ?? "";

  if (isInsourcedHost(host)) {
    return {
      title: "Insourced AI | Autonomous AI Agents for Non-Technical Founders",
      description:
        "Stop outsourcing your vision. Scale with a suite of autonomous AI agents that architect, code, hire, and manage — so you keep 100% of your equity.",
    };
  }

  return {
    title: "Co-Founder.ai | Your AI Technical Co-Founder",
    description:
      "Stop giving away 50% equity. Your AI technical co-founder architects, codes, tests, and deploys your product. 24/7 autonomous development for a fraction of what you would pay a dev shop.",
  };
}

export default async function HomePage() {
  const { userId } = await auth();
  if (userId) redirect("/dashboard");

  const headersList = await headers();
  const host = headersList.get("host") ?? "";

  if (isInsourcedHost(host)) {
    return <InsourcedHomeContent />;
  }

  return <HomeContent />;
}
