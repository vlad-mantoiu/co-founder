import { BrandNav } from "@/components/ui/brand-nav";
import { FloatingChat } from "@/components/chat/FloatingChat";

// Dashboard pages are "use client" components that use useSearchParams() —
// force-dynamic prevents Next.js from attempting static prerendering of these pages.
export const dynamic = "force-dynamic";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="min-h-screen bg-obsidian bg-grid">
      <BrandNav />
      <main className="pt-16">
        <div className="max-w-6xl mx-auto px-4 sm:px-6 py-8">{children}</div>
      </main>
      <FloatingChat />
    </div>
  );
}
