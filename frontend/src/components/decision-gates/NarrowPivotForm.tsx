"use client";

interface NarrowPivotFormProps {
  type: "narrow" | "pivot";
  value: string;
  onChange: (value: string) => void;
}

/**
 * Text input form for narrow/pivot action descriptions.
 *
 * Shows guidance text and examples based on type.
 */
export function NarrowPivotForm({ type, value, onChange }: NarrowPivotFormProps) {
  const config = {
    narrow: {
      label: "How should we narrow the scope?",
      helper: "Be specific: What are we cutting? What are we keeping?",
      placeholder:
        "E.g., Focus only on small businesses (10-50 employees) instead of all companies. Cut the mobile app for now, web-only MVP.",
    },
    pivot: {
      label: "What&apos;s the pivot?",
      helper:
        "Describe the new direction. The more detail, the better we can update your brief.",
      placeholder:
        "E.g., Instead of a marketplace, build a SaaS tool for managing freelancers. Target agencies instead of individual freelancers.",
    },
  };

  const { label, helper, placeholder } = config[type];

  return (
    <div className="p-6 glass-strong rounded-2xl border border-white/5 space-y-3">
      <label className="block text-sm font-semibold text-white">
        {label}
      </label>
      <p className="text-xs text-muted-foreground">{helper}</p>
      <textarea
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        rows={6}
        className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-lg text-white text-sm placeholder:text-muted-foreground resize-none focus:outline-none focus:ring-2 focus:ring-brand focus:border-transparent"
      />
      <p className="text-xs text-gray-500">
        The more detail you provide, the better we can update your brief.
      </p>
    </div>
  );
}
