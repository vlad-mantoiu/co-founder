"use client";

import { useState } from "react";
import { useAuth } from "@clerk/nextjs";
import { updatePlan, type PlanTier } from "@/lib/admin-api";

interface Props {
  plans: PlanTier[];
  onUpdate: () => void;
}

export function PlanEditor({ plans, onUpdate }: Props) {
  const { getToken } = useAuth();
  const [editing, setEditing] = useState<number | null>(null);
  const [saving, setSaving] = useState(false);

  const handleSave = async (plan: PlanTier, formData: FormData) => {
    setSaving(true);
    try {
      await updatePlan(
        plan.id,
        {
          name: formData.get("name") as string,
          max_projects: Number(formData.get("max_projects")),
          max_sessions_per_day: Number(formData.get("max_sessions_per_day")),
          max_tokens_per_day: Number(formData.get("max_tokens_per_day")),
        },
        getToken,
      );
      setEditing(null);
      onUpdate();
    } catch {
      // Error is non-fatal for admin UI
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-4">
      {plans.map((plan) => (
        <div
          key={plan.id}
          className="rounded-xl border border-white/5 bg-white/[0.02] p-5"
        >
          {editing === plan.id ? (
            <form
              onSubmit={(e) => {
                e.preventDefault();
                handleSave(plan, new FormData(e.currentTarget));
              }}
              className="space-y-3"
            >
              <div className="grid grid-cols-2 gap-3">
                <label className="space-y-1">
                  <span className="text-xs text-muted-foreground">Name</span>
                  <input
                    name="name"
                    defaultValue={plan.name}
                    className="w-full rounded-lg bg-white/5 border border-white/10 px-3 py-1.5 text-sm text-white"
                  />
                </label>
                <label className="space-y-1">
                  <span className="text-xs text-muted-foreground">
                    Max Projects (-1 = unlimited)
                  </span>
                  <input
                    name="max_projects"
                    type="number"
                    defaultValue={plan.max_projects}
                    className="w-full rounded-lg bg-white/5 border border-white/10 px-3 py-1.5 text-sm text-white"
                  />
                </label>
                <label className="space-y-1">
                  <span className="text-xs text-muted-foreground">
                    Sessions/Day (-1 = unlimited)
                  </span>
                  <input
                    name="max_sessions_per_day"
                    type="number"
                    defaultValue={plan.max_sessions_per_day}
                    className="w-full rounded-lg bg-white/5 border border-white/10 px-3 py-1.5 text-sm text-white"
                  />
                </label>
                <label className="space-y-1">
                  <span className="text-xs text-muted-foreground">
                    Tokens/Day (-1 = unlimited)
                  </span>
                  <input
                    name="max_tokens_per_day"
                    type="number"
                    defaultValue={plan.max_tokens_per_day}
                    className="w-full rounded-lg bg-white/5 border border-white/10 px-3 py-1.5 text-sm text-white"
                  />
                </label>
              </div>

              <div className="flex gap-2">
                <button
                  type="submit"
                  disabled={saving}
                  className="px-3 py-1.5 rounded-lg bg-brand text-white text-sm font-medium disabled:opacity-50"
                >
                  {saving ? "Saving..." : "Save"}
                </button>
                <button
                  type="button"
                  onClick={() => setEditing(null)}
                  className="px-3 py-1.5 rounded-lg bg-white/5 text-muted-foreground text-sm font-medium hover:text-white"
                >
                  Cancel
                </button>
              </div>
            </form>
          ) : (
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-white font-medium">{plan.name}</h3>
                <p className="text-xs text-muted-foreground mt-1">
                  {plan.slug} &middot; {plan.max_projects === -1 ? "Unlimited" : plan.max_projects} projects &middot;{" "}
                  {plan.max_sessions_per_day === -1 ? "Unlimited" : plan.max_sessions_per_day} sessions/day &middot;{" "}
                  {plan.max_tokens_per_day === -1 ? "Unlimited" : `${(plan.max_tokens_per_day / 1_000_000).toFixed(1)}M`} tokens/day
                </p>
                <div className="mt-2 flex flex-wrap gap-1">
                  {Object.entries(plan.default_models).map(([role, model]) => (
                    <span
                      key={role}
                      className="inline-block rounded bg-white/5 px-2 py-0.5 text-xs text-muted-foreground"
                    >
                      {role}: {model.replace("claude-", "").replace("-20250514", "")}
                    </span>
                  ))}
                </div>
              </div>
              <button
                onClick={() => setEditing(plan.id)}
                className="px-3 py-1.5 rounded-lg bg-white/5 text-sm font-medium text-muted-foreground hover:text-white"
              >
                Edit
              </button>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
