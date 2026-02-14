import { currentUser } from "@clerk/nextjs/server";
import Link from "next/link";

export const dynamic = "force-dynamic";

export default async function DashboardPage() {
  const user = await currentUser();

  return (
    <div>
      <h1 className="text-3xl font-bold mb-2">
        Welcome back, {user?.firstName || "Builder"}
      </h1>
      <p className="text-muted-foreground mb-8">
        Your AI co-founder is ready to help you build.
      </p>

      <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
        <ActionCard
          title="Start Building"
          description="Chat with your co-founder to start a new feature or fix a bug."
          href="/chat"
          action="Open Chat"
        />
        <ActionCard
          title="View Projects"
          description="Manage your connected repositories and see project status."
          href="/projects"
          action="View Projects"
        />
        <ActionCard
          title="Recent Activity"
          description="See what your co-founder has been working on."
          href="/activity"
          action="View Activity"
        />
      </div>

      <section className="mt-12">
        <h2 className="text-xl font-semibold mb-4">Quick Stats</h2>
        <div className="grid md:grid-cols-4 gap-4">
          <StatCard label="PRs Created" value="0" />
          <StatCard label="Commits" value="0" />
          <StatCard label="Tasks Completed" value="0" />
          <StatCard label="Hours Saved" value="0" />
        </div>
      </section>
    </div>
  );
}

function ActionCard({
  title,
  description,
  href,
  action,
}: {
  title: string;
  description: string;
  href: string;
  action: string;
}) {
  return (
    <div className="p-6 rounded-lg border border-border bg-card">
      <h3 className="font-semibold mb-2">{title}</h3>
      <p className="text-sm text-muted-foreground mb-4">{description}</p>
      <Link
        href={href}
        className="text-sm font-medium text-primary hover:underline"
      >
        {action} &rarr;
      </Link>
    </div>
  );
}

function StatCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="p-4 rounded-lg border border-border bg-card">
      <div className="text-2xl font-bold">{value}</div>
      <div className="text-sm text-muted-foreground">{label}</div>
    </div>
  );
}
