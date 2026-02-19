import Link from "next/link";

export default function NotFound() {
  return (
    <div className="min-h-screen bg-obsidian flex items-center justify-center px-4">
      <div className="text-center space-y-4">
        <h1 className="text-4xl font-bold text-white">Page not found</h1>
        <p className="text-muted-foreground">This page doesn&apos;t exist.</p>
        <Link
          href="/dashboard"
          className="inline-block px-6 py-3 bg-brand hover:bg-brand/90 text-white font-medium rounded-xl transition-colors"
        >
          Go to dashboard
        </Link>
      </div>
    </div>
  );
}
