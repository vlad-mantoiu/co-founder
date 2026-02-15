import type { Metadata } from "next";
import { auth } from "@clerk/nextjs/server";
import { redirect } from "next/navigation";
import HomeContent from "@/components/marketing/home-content";

export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "Co-Founder.ai | Your AI Technical Co-Founder",
  description:
    "Turn conversations into shipped products. Co-Founder.ai is an autonomous dev system that architects, codes, tests, and deploys your SaaS. No equity required.",
};

export default async function HomePage() {
  const { userId } = await auth();
  if (userId) redirect("/dashboard");
  return <HomeContent />;
}
