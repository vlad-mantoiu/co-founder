"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import { LayoutDashboard, Users, CreditCard, BarChart3 } from "lucide-react";

const links = [
  { href: "/admin", label: "Overview", icon: LayoutDashboard },
  { href: "/admin/users", label: "Users", icon: Users },
  { href: "/admin/plans", label: "Plans", icon: CreditCard },
  { href: "/admin/usage", label: "Usage", icon: BarChart3 },
] as const;

export function AdminSidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-56 shrink-0 border-r border-white/5 bg-obsidian/50 pt-4">
      <div className="px-4 pb-3 mb-2 border-b border-white/5">
        <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
          Admin
        </span>
      </div>
      <nav className="space-y-0.5 px-2">
        {links.map(({ href, label, icon: Icon }) => {
          const isActive =
            href === "/admin"
              ? pathname === "/admin"
              : pathname.startsWith(href);

          return (
            <Link
              key={href}
              href={href}
              className={cn(
                "flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm font-medium transition-colors",
                isActive
                  ? "bg-brand/15 text-brand"
                  : "text-muted-foreground hover:text-white hover:bg-white/5",
              )}
            >
              <Icon className="w-4 h-4" />
              {label}
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}
