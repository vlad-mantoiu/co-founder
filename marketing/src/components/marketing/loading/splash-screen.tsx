"use client";

import { useState, useEffect } from "react";
import { motion, AnimatePresence, MotionConfig, type Variants } from "framer-motion";

const draw: Variants = {
  hidden: { pathLength: 0, opacity: 0 },
  visible: (delay: number) => ({
    pathLength: 1,
    opacity: 1,
    transition: {
      pathLength: {
        delay,
        type: "spring" as const,
        duration: 1.0,
        bounce: 0,
      },
      opacity: { delay, duration: 0.01 },
    },
  }),
};

export function SplashScreen() {
  const [visible, setVisible] = useState(false);
  const [phase, setPhase] = useState<"drawing" | "dismissing" | "done">(
    "drawing"
  );

  useEffect(() => {
    try {
      if (sessionStorage.getItem("gi-splash")) {
        // Already shown this session — don't show again
        return;
      }
      // Mark as shown before anything renders to prevent double-show
      sessionStorage.setItem("gi-splash", "1");
    } catch (_e) {
      // sessionStorage unavailable (private browsing, etc.) — skip splash
      return;
    }

    setVisible(true);

    // After draw animation completes (~1.2s), start dismiss sequence
    const dismissTimer = setTimeout(() => {
      setPhase("dismissing");
    }, 1200);

    return () => clearTimeout(dismissTimer);
  }, []);

  if (!visible) {
    return null;
  }

  const isDismissing = phase === "dismissing";

  return (
    <MotionConfig reducedMotion="user">
      <AnimatePresence>
        <motion.div
          id="splash-overlay"
          key="splash"
          className="fixed inset-0 z-[9999] flex items-center justify-center bg-obsidian"
          animate={isDismissing ? { opacity: 0 } : { opacity: 1 }}
          transition={
            isDismissing
              ? { duration: 0.4, ease: "easeOut" }
              : { duration: 0 }
          }
          onAnimationComplete={() => {
            if (isDismissing) {
              setPhase("done");
              setVisible(false);
            }
          }}
        >
          <motion.div
            className="flex items-center justify-center"
            animate={
              isDismissing
                ? {
                    scale: 0.35,
                    x: "-38vw",
                    y: "-45vh",
                  }
                : { scale: 1, x: 0, y: 0 }
            }
            transition={
              isDismissing
                ? {
                    duration: 0.5,
                    ease: [0.4, 0, 0.2, 1],
                  }
                : { duration: 0 }
            }
          >
            <motion.svg
              width={80}
              height={56}
              viewBox="0 0 24 20"
              fill="none"
              stroke="#6467f2"
              strokeWidth={1.5}
              strokeLinecap="round"
              strokeLinejoin="round"
              initial="hidden"
              animate="visible"
            >
              {/* Terminal window frame */}
              <motion.rect
                x="2"
                y="3"
                width="20"
                height="14"
                rx="2"
                strokeDasharray="0 1"
                variants={draw}
                custom={0}
              />
              {/* Terminal prompt chevron */}
              <motion.polyline
                points="8 10 12 14"
                strokeDasharray="0 1"
                variants={draw}
                custom={0.3}
              />
              {/* Underscore cursor */}
              <motion.line
                x1="16"
                y1="14"
                x2="19"
                y2="14"
                strokeDasharray="0 1"
                variants={draw}
                custom={0.5}
              />
            </motion.svg>
          </motion.div>
        </motion.div>
      </AnimatePresence>
    </MotionConfig>
  );
}
