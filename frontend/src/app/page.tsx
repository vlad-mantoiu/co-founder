import Link from "next/link";
import { auth } from "@clerk/nextjs/server";
import { redirect } from "next/navigation";

// Force dynamic rendering to avoid build-time Clerk validation
export const dynamic = "force-dynamic";

export default async function LandingPage() {
  const { userId } = await auth();

  if (userId) {
    redirect("/dashboard");
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-background to-muted">
      <header className="container mx-auto px-4 py-6 flex justify-between items-center">
        <div className="text-2xl font-bold">AI Co-Founder</div>
        <nav className="flex gap-4">
          <Link
            href="/sign-in"
            className="px-4 py-2 text-sm font-medium hover:text-primary/80"
          >
            Sign In
          </Link>
          <Link
            href="/sign-up"
            className="px-4 py-2 text-sm font-medium bg-primary text-primary-foreground rounded-md hover:bg-primary/90"
          >
            Get Started
          </Link>
        </nav>
      </header>

      <main className="container mx-auto px-4 py-20">
        <div className="max-w-3xl mx-auto text-center">
          <h1 className="text-5xl font-bold tracking-tight mb-6">
            Your AI Technical Co-Founder
          </h1>
          <p className="text-xl text-muted-foreground mb-8">
            Stop struggling with the technical side. Let AI handle architecture,
            coding, testing, and deployment while you focus on your vision.
          </p>
          <div className="flex gap-4 justify-center">
            <Link
              href="/sign-up"
              className="px-6 py-3 text-lg font-medium bg-primary text-primary-foreground rounded-md hover:bg-primary/90"
            >
              Start Building
            </Link>
            <Link
              href="#features"
              className="px-6 py-3 text-lg font-medium border border-border rounded-md hover:bg-accent"
            >
              Learn More
            </Link>
          </div>
        </div>

        <section id="features" className="mt-32 grid md:grid-cols-3 gap-8">
          <FeatureCard
            title="Plan & Architect"
            description="Describe your idea in plain English. AI breaks it down into executable steps and creates a technical plan."
          />
          <FeatureCard
            title="Code & Test"
            description="Watch as your co-founder writes production-ready code, complete with tests and error handling."
          />
          <FeatureCard
            title="Deploy & Iterate"
            description="Push to GitHub, open PRs, and deploy automatically. Your co-founder handles the DevOps."
          />
        </section>
      </main>
    </div>
  );
}

function FeatureCard({ title, description }: { title: string; description: string }) {
  return (
    <div className="p-6 rounded-lg border border-border bg-card">
      <h3 className="text-lg font-semibold mb-2">{title}</h3>
      <p className="text-muted-foreground">{description}</p>
    </div>
  );
}
