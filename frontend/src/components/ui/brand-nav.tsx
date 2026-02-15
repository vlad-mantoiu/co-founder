"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { UserButton } from "@clerk/nextjs";
import { Menu, X, Shield } from "lucide-react";
import { useState } from "react";
import { cn } from "@/lib/utils";
import { useAdmin } from "@/hooks/useAdmin";

const navLinks = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/projects", label: "Projects" },
  { href: "/chat", label: "Chat" },
  { href: "/architecture", label: "Architecture" },
] as const;

export function BrandNav() {
  const pathname = usePathname();
  const [mobileOpen, setMobileOpen] = useState(false);
  const { isAdmin } = useAdmin();

  return (
    <header className="fixed top-0 inset-x-0 z-50 h-16 glass-strong border-b border-white/5">
      <div className="max-w-7xl mx-auto h-full px-4 sm:px-6 flex items-center justify-between">
        {/* Logo */}
        <Link href="/dashboard" className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-brand flex items-center justify-center shadow-glow">
            <span className="text-white font-bold text-sm">CF</span>
          </div>
          <span className="font-display font-semibold text-lg text-white hidden sm:block">
            Co-Founder<span className="text-brand">.ai</span>
          </span>
        </Link>

        {/* Desktop nav */}
        <nav className="hidden md:flex items-center gap-1">
          {navLinks.map(({ href, label }) => {
            const isActive = pathname === href || pathname.startsWith(`${href}/`);
            return (
              <Link
                key={href}
                href={href}
                className={cn(
                  "px-4 py-2 rounded-xl text-sm font-medium transition-colors",
                  isActive
                    ? "bg-brand/15 text-brand"
                    : "text-muted-foreground hover:text-white hover:bg-white/5",
                )}
              >
                {label}
              </Link>
            );
          })}
          {isAdmin && (
            <Link
              href="/admin"
              className={cn(
                "px-4 py-2 rounded-xl text-sm font-medium transition-colors flex items-center gap-1.5",
                pathname.startsWith("/admin")
                  ? "bg-brand/15 text-brand"
                  : "text-muted-foreground hover:text-white hover:bg-white/5",
              )}
            >
              <Shield className="w-3.5 h-3.5" />
              Admin
            </Link>
          )}
        </nav>

        {/* Right side */}
        <div className="flex items-center gap-3">
          <UserButton
            appearance={{
              elements: { avatarBox: "w-8 h-8 rounded-lg" },
            }}
          />
          {/* Mobile hamburger */}
          <button
            onClick={() => setMobileOpen(!mobileOpen)}
            className="md:hidden p-2 rounded-lg text-muted-foreground hover:text-white hover:bg-white/5"
          >
            {mobileOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>
        </div>
      </div>

      {/* Mobile dropdown */}
      {mobileOpen && (
        <nav className="md:hidden glass-strong border-t border-white/5 px-4 py-3 space-y-1">
          {navLinks.map(({ href, label }) => {
            const isActive = pathname === href;
            return (
              <Link
                key={href}
                href={href}
                onClick={() => setMobileOpen(false)}
                className={cn(
                  "block px-4 py-2.5 rounded-xl text-sm font-medium transition-colors",
                  isActive
                    ? "bg-brand/15 text-brand"
                    : "text-muted-foreground hover:text-white hover:bg-white/5",
                )}
              >
                {label}
              </Link>
            );
          })}
          {isAdmin && (
            <Link
              href="/admin"
              onClick={() => setMobileOpen(false)}
              className={cn(
                "flex items-center gap-1.5 px-4 py-2.5 rounded-xl text-sm font-medium transition-colors",
                pathname.startsWith("/admin")
                  ? "bg-brand/15 text-brand"
                  : "text-muted-foreground hover:text-white hover:bg-white/5",
              )}
            >
              <Shield className="w-3.5 h-3.5" />
              Admin
            </Link>
          )}
        </nav>
      )}
    </header>
  );
}
