"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams } from "next/navigation";
import { useAuth } from "@clerk/nextjs";
import {
  fetchUser,
  updateUser,
  fetchUserUsage,
  type UserDetail,
  type UserUsageBreakdown,
} from "@/lib/admin-api";
import { ModelOverrideForm } from "@/components/admin/ModelOverrideForm";
import { ArrowLeft } from "lucide-react";
import Link from "next/link";

export default function AdminUserDetailPage() {
  const params = useParams<{ userId: string }>();
  const { getToken } = useAuth();
  const [user, setUser] = useState<UserDetail | null>(null);
  const [usage, setUsage] = useState<UserUsageBreakdown[]>([]);
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    try {
      const [u, usg] = await Promise.all([
        fetchUser(params.userId, getToken),
        fetchUserUsage(params.userId, getToken, "today"),
      ]);
      setUser(u);
      setUsage(usg);
    } catch {
      // Non-fatal
    }
  }, [params.userId, getToken]);

  useEffect(() => {
    load();
  }, [load]);

  const handleToggleAdmin = async () => {
    if (!user) return;
    setSaving(true);
    try {
      const updated = await updateUser(
        user.clerk_user_id,
        { is_admin: !user.is_admin },
        getToken,
      );
      setUser(updated);
    } finally {
      setSaving(false);
    }
  };

  const handleToggleSuspend = async () => {
    if (!user) return;
    setSaving(true);
    try {
      const updated = await updateUser(
        user.clerk_user_id,
        { is_suspended: !user.is_suspended },
        getToken,
      );
      setUser(updated);
    } finally {
      setSaving(false);
    }
  };

  const handleSaveOverrides = async (
    overrides: Record<string, string> | null,
  ) => {
    if (!user) return;
    setSaving(true);
    try {
      const updated = await updateUser(
        user.clerk_user_id,
        { override_models: overrides },
        getToken,
      );
      setUser(updated);
    } finally {
      setSaving(false);
    }
  };

  if (!user) {
    return (
      <div className="text-muted-foreground text-sm animate-pulse">
        Loading user...
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-3xl">
      <div className="flex items-center gap-3">
        <Link
          href="/admin/users"
          className="p-1.5 rounded-lg hover:bg-white/5 text-muted-foreground hover:text-white"
        >
          <ArrowLeft className="w-4 h-4" />
        </Link>
        <h1 className="text-2xl font-display font-semibold text-white">
          User Detail
        </h1>
      </div>

      {/* Info card */}
      <div className="rounded-xl border border-white/5 bg-white/[0.02] p-5 space-y-3">
        <div className="flex items-center justify-between">
          <span className="font-mono text-xs text-muted-foreground">
            {user.clerk_user_id}
          </span>
          <div className="flex gap-2">
            <button
              onClick={handleToggleAdmin}
              disabled={saving}
              className="px-3 py-1 rounded-lg bg-white/5 text-xs font-medium text-muted-foreground hover:text-white disabled:opacity-50"
            >
              {user.is_admin ? "Revoke Admin" : "Grant Admin"}
            </button>
            <button
              onClick={handleToggleSuspend}
              disabled={saving}
              className={`px-3 py-1 rounded-lg text-xs font-medium disabled:opacity-50 ${
                user.is_suspended
                  ? "bg-green-500/10 text-green-400"
                  : "bg-red-500/10 text-red-400"
              }`}
            >
              {user.is_suspended ? "Unsuspend" : "Suspend"}
            </button>
          </div>
        </div>
        <div className="grid grid-cols-3 gap-4 text-sm">
          <div>
            <span className="text-xs text-muted-foreground">Plan</span>
            <p className="text-white font-medium">{user.plan_tier.name}</p>
          </div>
          <div>
            <span className="text-xs text-muted-foreground">Tokens Today</span>
            <p className="text-white font-medium">
              {user.daily_tokens_used.toLocaleString()}
            </p>
          </div>
          <div>
            <span className="text-xs text-muted-foreground">Joined</span>
            <p className="text-white font-medium">
              {new Date(user.created_at).toLocaleDateString()}
            </p>
          </div>
        </div>
      </div>

      {/* Model overrides */}
      <ModelOverrideForm
        currentOverrides={user.override_models}
        onSave={handleSaveOverrides}
        saving={saving}
      />

      {/* Usage breakdown */}
      <div className="rounded-xl border border-white/5 bg-white/[0.02] p-5">
        <h3 className="text-sm font-medium text-white mb-3">
          Usage Today
        </h3>
        {usage.length === 0 ? (
          <p className="text-xs text-muted-foreground">No usage recorded today.</p>
        ) : (
          <div className="space-y-2">
            {usage.map((row, i) => (
              <div
                key={i}
                className="flex items-center justify-between text-xs"
              >
                <div className="flex gap-2">
                  <span className="text-muted-foreground capitalize">
                    {row.role}
                  </span>
                  <span className="text-white/50">
                    {row.model_used.replace("claude-", "").replace("-20250514", "")}
                  </span>
                </div>
                <div className="flex gap-4 text-muted-foreground">
                  <span>{row.total_tokens.toLocaleString()} tokens</span>
                  <span>{row.request_count} requests</span>
                  <span>
                    ${(row.total_cost_microdollars / 1_000_000).toFixed(4)}
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
