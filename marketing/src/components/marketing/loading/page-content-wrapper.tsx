"use client";

import { useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";

interface PageContentWrapperProps {
  children: React.ReactNode;
  skeleton: React.ReactNode;
}

export function PageContentWrapper({ children, skeleton }: PageContentWrapperProps) {
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const id = requestAnimationFrame(() => setIsLoading(false));
    return () => cancelAnimationFrame(id);
  }, []);

  return (
    <AnimatePresence mode="wait">
      {isLoading ? (
        <motion.div
          key="skeleton"
          exit={{ opacity: 0 }}
          transition={{ duration: 0.15 }}
        >
          {skeleton}
        </motion.div>
      ) : (
        <motion.div
          key="content"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.3 }}
        >
          {children}
        </motion.div>
      )}
    </AnimatePresence>
  );
}
