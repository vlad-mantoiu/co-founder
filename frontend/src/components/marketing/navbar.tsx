"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { Terminal, Menu, X } from "lucide-react";
import { cn } from "@/lib/utils";

const navLinks = [
  { href: "/#features", label: "Features" },
  { href: "/#how-it-works", label: "How It Works" },
  { href: "/pricing", label: "Pricing" },
  { href: "/about", label: "About" },
];

export function Navbar() {
  const [scrolled, setScrolled] = useState(false);
  const [open, setOpen] = useState(false);
  const pathname = usePathname();

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 20);
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  useEffect(() => {
    setOpen(false);
  }, [pathname]);

  const isActive = (href: string) => {
    if (href.startsWith("/#")) return pathname === "/";
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
        <Link href="/" className="flex items-center gap-2.5 group">
          <div className="h-8 w-8 rounded-lg bg-brand/10 border border-brand/20 flex items-center justify-center group-hover:bg-brand/20 transition-colors">
            <Terminal className="h-4 w-4 text-brand" />
          </div>
          <span className="text-lg font-bold text-white tracking-tight">
            Co-Founder<span className="text-brand">.ai</span>
          </span>
        </Link>

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
          <Link
            href="/signin"
            className="px-4 py-2 text-sm font-medium text-white/70 hover:text-white transition-colors"
          >
            Sign In
          </Link>
          <Link
            href="/sign-up"
            className="px-5 py-2.5 bg-brand text-white text-sm font-semibold rounded-xl hover:bg-brand-dark transition-all duration-200 shadow-glow hover:shadow-glow-lg"
          >
            Start Building
          </Link>
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
              <Link
                href="/signin"
                className="text-sm font-medium text-white/60 hover:text-white py-3 px-3 rounded-lg"
              >
                Sign In
              </Link>
              <Link
                href="/sign-up"
                className="mt-2 text-center px-5 py-3 bg-brand text-white text-sm font-semibold rounded-xl hover:bg-brand-dark transition-colors"
              >
                Start Building
              </Link>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </header>
  );
}
