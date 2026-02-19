"use client";

import { motion } from "framer-motion";
import type { Entity } from "./types";

const TYPE_COLORS: Record<Entity["type"], string> = {
  technology: "bg-brand/20 text-brand-light border-brand/30",
  feature: "bg-neon-cyan/15 text-neon-cyan border-neon-cyan/30",
  integration: "bg-neon-pink/15 text-neon-pink border-neon-pink/30",
  platform: "bg-neon-green/15 text-neon-green border-neon-green/30",
  concept: "bg-yellow-500/15 text-yellow-400 border-yellow-500/30",
};

interface ParsingStateProps {
  idea: string;
  entities: Entity[];
}

export function ParsingState({ idea, entities }: ParsingStateProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -16 }}
      className="mx-auto w-full max-w-2xl"
    >
      <div className="glass rounded-2xl p-6 space-y-4">
        {/* Loading shimmer bar */}
        <div className="relative h-1 overflow-hidden rounded-full bg-white/5">
          <div className="absolute inset-0 animate-shimmer bg-gradient-to-r from-transparent via-brand/40 to-transparent" />
        </div>

        <p className="text-xs font-bold uppercase tracking-widest text-white/30">
          Parsing your idea
        </p>

        {/* Idea text with highlighted entities */}
        <p className="text-sm leading-relaxed text-white/80">
          {highlightEntities(idea, entities)}
        </p>

        {/* Entity type tags */}
        {entities.length > 0 && (
          <div className="flex flex-wrap gap-2 pt-2">
            {entities.map((entity, i) => (
              <motion.span
                key={`${entity.text}-${i}`}
                initial={{ opacity: 0, scale: 0.8 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: i * 0.1 }}
                className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-wider ${TYPE_COLORS[entity.type]}`}
              >
                <span className="h-1.5 w-1.5 rounded-full bg-current" />
                {entity.text}
              </motion.span>
            ))}
          </div>
        )}
      </div>
    </motion.div>
  );
}

function highlightEntities(text: string, entities: Entity[]): React.ReactNode {
  if (entities.length === 0) return text;

  const parts: React.ReactNode[] = [];
  let remaining = text;
  let keyIdx = 0;

  for (const entity of entities) {
    const idx = remaining.toLowerCase().indexOf(entity.text.toLowerCase());
    if (idx === -1) continue;

    if (idx > 0) {
      parts.push(remaining.slice(0, idx));
    }
    parts.push(
      <span
        key={keyIdx++}
        className="rounded bg-brand/20 px-1 py-0.5 text-brand-light font-medium"
      >
        {remaining.slice(idx, idx + entity.text.length)}
      </span>,
    );
    remaining = remaining.slice(idx + entity.text.length);
  }

  if (remaining) parts.push(remaining);
  return parts;
}
