"use client";

import { motion } from "framer-motion";
import { Wrench } from "lucide-react";

interface AutoFixBannerProps {
  attempt: number; // 1-5 — current attempt number
  maxAttempts?: number; // Default 5
}

export function AutoFixBanner({ attempt, maxAttempts = 5 }: AutoFixBannerProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: -8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -8 }}
      transition={{ duration: 0.3 }}
      className="w-full mb-4 px-4 py-3 rounded-xl bg-amber-500/10 border border-amber-500/25 flex items-center gap-3"
    >
      <Wrench className="w-4 h-4 text-amber-400 flex-shrink-0" />
      <div className="flex-1 min-w-0">
        <p className="text-sm text-amber-300 font-medium">
          We found a small issue and are fixing it automatically
        </p>
        <p className="text-xs text-amber-400/70 mt-0.5">
          Attempt {attempt} of {maxAttempts} — this is normal, sit tight
        </p>
      </div>
    </motion.div>
  );
}
