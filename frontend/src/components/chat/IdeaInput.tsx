"use client";

import { useState } from "react";
import { Send } from "lucide-react";

const SUGGESTIONS = [
  "Build a SaaS billing system with Stripe",
  "Create a real-time collaboration tool",
  "Design a CI/CD pipeline for microservices",
  "Build an AI-powered code review tool",
];

interface IdeaInputProps {
  onSubmit: (idea: string) => void;
}

export function IdeaInput({ onSubmit }: IdeaInputProps) {
  const [value, setValue] = useState("");

  const handleSubmit = () => {
    const trimmed = value.trim();
    if (!trimmed) return;
    onSubmit(trimmed);
    setValue("");
  };

  return (
    <div className="mx-auto w-full max-w-2xl space-y-6 py-12">
      <div className="text-center space-y-2">
        <h2 className="font-display text-2xl font-bold text-white">
          What are we building?
        </h2>
        <p className="text-sm text-white/50">
          Describe your idea and your co-founder will analyze, plan, and build
          it.
        </p>
      </div>

      <div className="relative">
        <textarea
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              handleSubmit();
            }
          }}
          placeholder="Describe what you want to build..."
          rows={4}
          className="w-full resize-none rounded-2xl border border-white/10 bg-white/5 px-5 py-4 text-sm text-white placeholder:text-white/30 focus:border-brand/50 focus:outline-none focus:ring-2 focus:ring-brand/20 transition-all"
        />
        <button
          onClick={handleSubmit}
          disabled={!value.trim()}
          className="absolute bottom-3 right-3 rounded-xl bg-brand px-4 py-2 text-sm font-medium text-white hover:bg-brand-dark disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
        >
          <Send className="h-4 w-4" />
        </button>
      </div>

      <div className="flex flex-wrap justify-center gap-2">
        {SUGGESTIONS.map((s) => (
          <button
            key={s}
            onClick={() => setValue(s)}
            className="rounded-full border border-white/10 px-3.5 py-1.5 text-xs text-white/50 hover:border-brand/30 hover:text-white/80 transition-colors"
          >
            {s}
          </button>
        ))}
      </div>
    </div>
  );
}
