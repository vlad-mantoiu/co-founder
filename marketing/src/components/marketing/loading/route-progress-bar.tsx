"use client";

import { useEffect, useRef, useState } from "react";
import { motion, useMotionValue, useSpring, useTransform } from "framer-motion";
import { usePathname } from "next/navigation";

export function RouteProgressBar() {
  const pathname = usePathname();
  const prevPath = useRef<string | null>(null);
  const [isAnimating, setIsAnimating] = useState(false);
  const progress = useMotionValue(0);
  const springProgress = useSpring(progress, { stiffness: 80, damping: 25 });
  const width = useTransform(springProgress, [0, 100], ["0%", "100%"]);

  useEffect(() => {
    if (prevPath.current !== null && prevPath.current !== pathname) {
      setIsAnimating(true);
      progress.set(0);
      requestAnimationFrame(() => progress.set(100));
      const timer = setTimeout(() => setIsAnimating(false), 700);
      prevPath.current = pathname;
      return () => clearTimeout(timer);
    }
    prevPath.current = pathname;
  }, [pathname, progress]);

  return (
    <motion.div
      className="fixed top-0 left-0 right-0 z-[9998] pointer-events-none h-[3px]"
      style={{ opacity: isAnimating ? 1 : 0, transition: "opacity 0.3s ease-out" }}
    >
      <motion.div
        className="h-full animate-progress-gradient rounded-r-full"
        style={{
          width,
          boxShadow:
            "0 0 10px rgba(100,103,242,0.7), 0 0 20px rgba(100,103,242,0.4)",
        }}
      />
    </motion.div>
  );
}
