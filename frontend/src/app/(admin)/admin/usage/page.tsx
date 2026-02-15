"use client";

import { useEffect, useState, useCallback } from "react";
import { useAuth } from "@clerk/nextjs";
import { fetchGlobalUsage, type UsageAggregate } from "@/lib/admin-api";
import { Zap, DollarSign, Activity } from "lucide-react";

const PERIODS = ["today", "week", "month"] as const;

export default function AdminUsagePage() {
  const { getToken } = useAuth();
  const [period, setPeriod] = useState<"today" | "week" | "month">("today");
  const [usage, setUsage] = useState<UsageAggregate | null>(null);

  const load = useCallback(async () => {
    try {
      const data = await fetchGlobalUsage(getToken, period);
      setUsage(data);
    } catch {
      // Non-fatal
    }
  }, [getToken, period]);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-display font-semibold text-white">
          Usage Analytics
        </h1>
        <div className="flex rounded-lg bg-white/5 p-0.5">
          {PERIODS.map((p) => (
            <button
              key={p}
              onClick={() => setPeriod(p)}
              className={`px-3 py-1.5 rounded-md text-xs font-medium capitalize transition-colors ${
                period === p
                  ? "bg-brand text-white"
                  : "text-muted-foreground hover:text-white"
              }`}
            >
              {p}
            </button>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <Card
          label="Total Requests"
          value={usage?.total_requests ?? 0}
          icon={Activity}
          color="text-green-400"
        />
        <Card
          label="Total Tokens"
          value={formatNumber(usage?.total_tokens ?? 0)}
          icon={Zap}
          color="text-yellow-400"
        />
        <Card
          label="Total Cost"
          value={`$${((usage?.total_cost_microdollars ?? 0) / 1_000_000).toFixed(2)}`}
          icon={DollarSign}
          color="text-brand"
        />
      </div>
    </div>
  );
}

function Card({
  label,
  value,
  icon: Icon,
  color,
}: {
  label: string;
  value: string | number;
  icon: React.ComponentType<{ className?: string }>;
  color: string;
}) {
  return (
    <div className="rounded-xl border border-white/5 bg-white/[0.02] p-5">
      <div className="flex items-center justify-between mb-3">
        <span className="text-sm text-muted-foreground">{label}</span>
        <Icon className={`w-4 h-4 ${color}`} />
      </div>
      <p className="text-2xl font-semibold text-white">{value}</p>
    </div>
  );
}

function formatNumber(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return String(n);
}
