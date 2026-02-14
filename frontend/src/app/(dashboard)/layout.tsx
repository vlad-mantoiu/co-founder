import { UserButton } from "@clerk/nextjs";
import Link from "next/link";

// Skip static prerendering for auth-protected pages
export const dynamic = "force-dynamic";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="min-h-screen flex">
      {/* Sidebar */}
      <aside className="w-64 border-r border-border bg-card p-4 flex flex-col">
        <div className="text-xl font-bold mb-8">AI Co-Founder</div>

        <nav className="flex-1 space-y-2">
          <NavLink href="/dashboard">Dashboard</NavLink>
          <NavLink href="/chat">Chat</NavLink>
          <NavLink href="/projects">Projects</NavLink>
        </nav>

        <div className="pt-4 border-t border-border">
          <UserButton
            appearance={{
              elements: {
                avatarBox: "w-10 h-10",
              },
            }}
          />
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 p-6">{children}</main>
    </div>
  );
}

function NavLink({ href, children }: { href: string; children: React.ReactNode }) {
  return (
    <Link
      href={href}
      className="block px-4 py-2 rounded-md text-sm font-medium text-muted-foreground hover:bg-accent hover:text-accent-foreground"
    >
      {children}
    </Link>
  );
}
