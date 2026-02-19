"use client";

import { useEffect, useRef } from "react";
import { motion } from "framer-motion";
import type { LogLine } from "./types";

interface TerminalOutputProps {
  lines: LogLine[];
  maxHeight?: string;
}

export function TerminalOutput({
  lines,
  maxHeight = "200px",
}: TerminalOutputProps) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = containerRef.current;
    if (el) {
      el.scrollTop = el.scrollHeight;
    }
  }, [lines.length]);

  return (
    <div
      ref={containerRef}
      className="scrollbar-thin overflow-y-auto rounded-lg bg-black/40 p-3 font-mono text-xs leading-relaxed"
      style={{ maxHeight }}
    >
      {lines.map((line, i) => {
        const isRecent = i >= lines.length - 3;
        return (
          <motion.div
            key={line.id}
            initial={{ opacity: 0, x: -8 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.2 }}
            className={
              isRecent
                ? "border-l-2 border-brand pl-2 text-white/90"
                : "pl-2 text-white/50"
            }
          >
            <span className="mr-2 text-white/20 select-none">
              {String(i + 1).padStart(2, "0")}
            </span>
            {line.text}
          </motion.div>
        );
      })}
      {lines.length > 0 && (
        <span className="inline-block w-1.5 h-3.5 bg-brand ml-2 animate-cursor-blink" />
      )}
    </div>
  );
}
