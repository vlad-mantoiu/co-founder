"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { Terminal, Menu, X } from "lucide-react";
import { cn } from "@/lib/utils";

const insourcedLinks = [
  { href: "/#hero", label: "Vision" },
  { href: "/#suite", label: "Suite" },
  { href: "/pricing", label: "Pricing" },
  { href: "/about", label: "About" },
];

const cofounderLinks = [
  { href: "/cofounder/#features", label: "Features" },
  { href: "/cofounder/how-it-works", label: "How It Works" },
  { href: "/pricing", label: "Pricing" },
  { href: "/about", label: "About" },
];

export function Navbar() {
  const [scrolled, setScrolled] = useState(false);
  const [open, setOpen] = useState(false);
  const pathname = usePathname();

  const isInsourced = pathname === "/";
  const isCofounder = !isInsourced;

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 20);
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  useEffect(() => {
    setOpen(false);
  }, [pathname]);

  const navLinks = isInsourced ? insourcedLinks : cofounderLinks;

  const brandName = isInsourced ? (
    <>getinsourced<span className="text-brand">.ai</span></>
  ) : (
    <>Co-Founder<span className="text-brand">.ai</span></>
  );

  const logoHref = isInsourced ? "/" : "/cofounder";

  const isActive = (href: string) => {
    if (isInsourced && href.startsWith("/#")) return pathname === "/";
    if (isCofounder && href.startsWith("/cofounder/#")) return pathname.startsWith("/cofounder");
    return pathname === href;
  };

  return (
    <header
      className={cn(
        "fixed top-0 inset-x-0 z-50 transition-all duration-300",
        scrolled ? "glass-strong py-3" : "py-5"
      )}
    >
      <nav className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex items-center justify-between">
        <div className="flex flex-col items-start">
          <Link href={logoHref} className="flex items-center gap-2.5 group">
            <div className="h-8 w-8 rounded-lg bg-brand/10 border border-brand/20 flex items-center justify-center group-hover:bg-brand/20 transition-colors">
              <Terminal className="h-4 w-4 text-brand" />
            </div>
            <span className="text-lg font-bold text-white tracking-tight">
              {brandName}
            </span>
          </Link>
          {isCofounder && (
            <Link
              href="/"
              className="ml-10 text-xs text-white/30 hover:text-white/60 transition-colors"
            >
              by Insourced AI
            </Link>
          )}
        </div>

        <div className="hidden md:flex items-center gap-8">
          {navLinks.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className={cn(
                "text-sm font-medium transition-colors duration-200",
                isActive(link.href)
                  ? "text-white"
                  : "text-white/50 hover:text-white"
              )}
            >
              {link.label}
            </Link>
          ))}
        </div>

        <div className="hidden md:flex items-center gap-3">
          <a
            href="https://cofounder.getinsourced.ai/signin"
            className="px-4 py-2 text-sm font-medium text-white/70 hover:text-white transition-colors"
          >
            Sign In
          </a>
          <a
            href="https://cofounder.getinsourced.ai/onboarding"
            className="px-5 py-2.5 bg-brand text-white text-sm font-semibold rounded-xl hover:bg-brand-dark transition-all duration-200 shadow-glow hover:shadow-glow-lg"
          >
            Start with Co-Founder.ai
          </a>
        </div>

        <button
          onClick={() => setOpen(!open)}
          className="md:hidden p-2 text-white/70 hover:text-white transition-colors"
          aria-label={open ? "Close menu" : "Open menu"}
        >
          {open ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
        </button>
      </nav>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.2 }}
            className="md:hidden border-t border-white/5 overflow-hidden"
          >
            <div className="glass-strong px-4 py-6 flex flex-col gap-1">
              {navLinks.map((link) => (
                <Link
                  key={link.href}
                  href={link.href}
                  className={cn(
                    "text-sm font-medium py-3 px-3 rounded-lg transition-colors",
                    isActive(link.href)
                      ? "text-white bg-white/5"
                      : "text-white/60 hover:text-white hover:bg-white/5"
                  )}
                >
                  {link.label}
                </Link>
              ))}
              <hr className="border-white/10 my-2" />
              <a
                href="https://cofounder.getinsourced.ai/signin"
                className="text-sm font-medium text-white/60 hover:text-white py-3 px-3 rounded-lg"
              >
                Sign In
              </a>
              <a
                href="https://cofounder.getinsourced.ai/onboarding"
                className="mt-2 text-center px-5 py-3 bg-brand text-white text-sm font-semibold rounded-xl hover:bg-brand-dark transition-colors"
              >
                Start with Co-Founder.ai
              </a>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </header>
  );
}
