"use client";

import { useEffect, useState, useCallback } from "react";
import { useAuth } from "@clerk/nextjs";
import { fetchPlans, type PlanTier } from "@/lib/admin-api";
import { PlanEditor } from "@/components/admin/PlanEditor";

export default function AdminPlansPage() {
  const { getToken } = useAuth();
  const [plans, setPlans] = useState<PlanTier[]>([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await fetchPlans(getToken);
      setPlans(data);
    } catch {
      // Non-fatal
    } finally {
      setLoading(false);
    }
  }, [getToken]);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <div className="space-y-6 max-w-3xl">
      <h1 className="text-2xl font-display font-semibold text-white">
        Plan Tiers
      </h1>

      {loading ? (
        <div className="text-muted-foreground text-sm animate-pulse">
          Loading plans...
        </div>
      ) : (
        <PlanEditor plans={plans} onUpdate={load} />
      )}
    </div>
  );
}
