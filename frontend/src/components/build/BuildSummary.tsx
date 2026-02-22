"use client";

import { useEffect } from "react";
import { motion } from "framer-motion";
import { CheckCircle2, ArrowRight } from "lucide-react";
import Link from "next/link";
import { cn } from "@/lib/utils";

// ──────────────────────────────────────────────────────────────────────────────
// Confetti burst — dynamic import avoids SSR crash (canvas-confetti accesses window)
// ──────────────────────────────────────────────────────────────────────────────

async function triggerConfetti() {
  const confetti = (await import("canvas-confetti")).default;
  // Main burst from bottom center
  confetti({
    particleCount: 80,
    spread: 70,
    origin: { x: 0.5, y: 0.8 },
    colors: ["#6467f2", "#8183f5", "#0df2f2", "#ffffff"],
    zIndex: 9999,
  });
  // Follow-up burst 300ms later for lingering effect
  setTimeout(() => {
    confetti({
      particleCount: 40,
      spread: 50,
      origin: { x: 0.4, y: 0.75 },
      colors: ["#6467f2", "#8183f5"],
      zIndex: 9999,
    });
  }, 300);
}

// ──────────────────────────────────────────────────────────────────────────────
// Props
// ──────────────────────────────────────────────────────────────────────────────

interface BuildSummaryProps {
  buildVersion: string;
  previewUrl: string;
  projectId?: string;
  className?: string;
}

// ──────────────────────────────────────────────────────────────────────────────
// Component — compact header above PreviewPane: confetti + headline + dashboard link
// The "Open your app" CTA is removed — BrowserChrome toolbar handles open-in-new-tab.
// Build details (fileCount, stack, features) removed to keep header slim above preview.
// ──────────────────────────────────────────────────────────────────────────────

export function BuildSummary({
  buildVersion,
  previewUrl: _previewUrl,
  projectId,
  className,
}: BuildSummaryProps) {
  // Fire confetti once on mount
  useEffect(() => {
    triggerConfetti();
  }, []);

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.97 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.4, ease: "easeOut" }}
      className={cn(
        "glass-card-strong rounded-2xl p-6 flex flex-col items-center gap-4 text-center",
        className
      )}
    >
      {/* Success icon */}
      <motion.div
        initial={{ scale: 0, rotate: -20 }}
        animate={{ scale: 1, rotate: 0 }}
        transition={{ delay: 0.15, type: "spring", stiffness: 260, damping: 18 }}
        className="w-14 h-14 rounded-full bg-brand/15 border border-brand/30 flex items-center justify-center shadow-glow"
      >
        <CheckCircle2 className="w-7 h-7 text-brand" />
      </motion.div>

      {/* Headline */}
      <div className="space-y-1">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-brand/10 border border-brand/20 mb-1">
          <span className="text-xs font-mono text-brand">{buildVersion}</span>
        </div>
        <h2 className="text-xl font-display font-semibold text-white">
          Your app is live!
        </h2>
        <p className="text-sm text-white/60">
          We built your first working preview — take a look below.
        </p>
      </div>

      {/* Secondary link — back to dashboard */}
      {projectId && (
        <Link
          href={`/company/${projectId}`}
          className="inline-flex items-center gap-1.5 text-sm text-white/40 hover:text-white/70 transition-colors"
        >
          View in Dashboard
          <ArrowRight className="w-3.5 h-3.5" />
        </Link>
      )}
    </motion.div>
  );
}
