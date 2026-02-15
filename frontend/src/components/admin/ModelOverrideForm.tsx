"use client";

import { useState } from "react";

const AVAILABLE_MODELS = [
  { id: "claude-sonnet-4-20250514", label: "Sonnet" },
  { id: "claude-opus-4-20250514", label: "Opus" },
];

const ROLES = ["architect", "coder", "debugger", "reviewer"] as const;

interface Props {
  currentOverrides: Record<string, string> | null;
  onSave: (overrides: Record<string, string> | null) => void;
  saving?: boolean;
}

export function ModelOverrideForm({ currentOverrides, onSave, saving }: Props) {
  const [overrides, setOverrides] = useState<Record<string, string>>(
    currentOverrides ?? {},
  );
  const [enabled, setEnabled] = useState(currentOverrides !== null);

  const handleChange = (role: string, model: string) => {
    setOverrides((prev) => ({ ...prev, [role]: model }));
  };

  const handleSubmit = () => {
    if (!enabled) {
      onSave(null);
    } else {
      onSave(overrides);
    }
  };

  return (
    <div className="space-y-4 rounded-xl border border-white/5 bg-white/[0.02] p-5">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-medium text-white">Model Overrides</h3>
        <label className="flex items-center gap-2 text-xs text-muted-foreground">
          <input
            type="checkbox"
            checked={enabled}
            onChange={(e) => setEnabled(e.target.checked)}
            className="rounded"
          />
          Enable overrides
        </label>
      </div>

      {enabled && (
        <div className="grid grid-cols-2 gap-3">
          {ROLES.map((role) => (
            <label key={role} className="space-y-1">
              <span className="text-xs text-muted-foreground capitalize">
                {role}
              </span>
              <select
                value={overrides[role] || ""}
                onChange={(e) => handleChange(role, e.target.value)}
                className="w-full rounded-lg bg-white/5 border border-white/10 px-3 py-1.5 text-sm text-white"
              >
                <option value="">Use plan default</option>
                {AVAILABLE_MODELS.map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.label}
                  </option>
                ))}
              </select>
            </label>
          ))}
        </div>
      )}

      <button
        onClick={handleSubmit}
        disabled={saving}
        className="px-3 py-1.5 rounded-lg bg-brand text-white text-sm font-medium disabled:opacity-50"
      >
        {saving ? "Saving..." : "Save Overrides"}
      </button>
    </div>
  );
}
