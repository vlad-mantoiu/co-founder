"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@clerk/nextjs";
import { fetchGlobalUsage, fetchUsers, type UsageAggregate } from "@/lib/admin-api";
import { Users, Zap, DollarSign, Activity } from "lucide-react";

export default function AdminOverviewPage() {
  const { getToken } = useAuth();
  const [usage, setUsage] = useState<UsageAggregate | null>(null);
  const [userCount, setUserCount] = useState(0);

  useEffect(() => {
    (async () => {
      try {
        const [u, users] = await Promise.all([
          fetchGlobalUsage(getToken, "today"),
          fetchUsers(getToken, { per_page: 1 }),
        ]);
        setUsage(u);
        setUserCount(users.length > 0 ? users.length : 0);
      } catch {
        // Silently handle — admin panel just shows stale/empty data
      }
    })();
  }, [getToken]);

  const cards = [
    {
      label: "Users",
      value: userCount,
      icon: Users,
      color: "text-blue-400",
    },
    {
      label: "Requests Today",
      value: usage?.total_requests ?? 0,
      icon: Activity,
      color: "text-green-400",
    },
    {
      label: "Tokens Today",
      value: formatNumber(usage?.total_tokens ?? 0),
      icon: Zap,
      color: "text-yellow-400",
    },
    {
      label: "Cost Today",
      value: `$${((usage?.total_cost_microdollars ?? 0) / 1_000_000).toFixed(2)}`,
      icon: DollarSign,
      color: "text-brand",
    },
  ];

  return (
    <div className="space-y-8">
      <h1 className="text-2xl font-display font-semibold text-white">
        Admin Overview
      </h1>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {cards.map((c) => (
          <div
            key={c.label}
            className="rounded-xl border border-white/5 bg-white/[0.02] p-5"
          >
            <div className="flex items-center justify-between mb-3">
              <span className="text-sm text-muted-foreground">{c.label}</span>
              <c.icon className={`w-4 h-4 ${c.color}`} />
            </div>
            <p className="text-2xl font-semibold text-white">{c.value}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

function formatNumber(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return String(n);
}
