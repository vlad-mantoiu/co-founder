"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@clerk/nextjs";
import Link from "next/link";
import {
  CreditCard,
  ExternalLink,
  Loader2,
  ArrowRight,
  CheckCircle2,
  AlertTriangle,
  Zap,
} from "lucide-react";
import { GlassCard } from "@/components/ui/glass-card";
import { apiFetch } from "@/lib/api";

interface BillingStatus {
  plan_slug: string;
  plan_name: string;
  stripe_subscription_status: string | null;
  has_subscription: boolean;
}

interface UsageData {
  tokens_used_today: number;
  tokens_limit: number;
  plan_slug: string;
  plan_name: string;
  reset_at: string;
}

const STATUS_STYLES: Record<string, { label: string; className: string; icon: typeof CheckCircle2 }> = {
  active: { label: "Active", className: "bg-neon-green/10 text-neon-green", icon: CheckCircle2 },
  trialing: { label: "Trial", className: "bg-blue-500/10 text-blue-400", icon: CheckCircle2 },
  past_due: { label: "Past Due", className: "bg-amber-500/10 text-amber-400", icon: AlertTriangle },
  canceled: { label: "Canceled", className: "bg-red-500/10 text-red-400", icon: AlertTriangle },
};

function formatTokens(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(0)}K`;
  return String(n);
}

function UsageMeter({ usage }: { usage: UsageData }) {
  if (usage.tokens_limit === -1) {
    return (
      <div className="space-y-2">
        <div className="flex items-center justify-between text-sm">
          <span className="text-muted-foreground">Token Usage Today</span>
          <span className="text-neon-green font-semibold">Unlimited</span>
        </div>
        <div className="h-2 rounded-full bg-white/10">
          <div className="h-2 rounded-full bg-neon-green w-0" />
        </div>
        <p className="text-xs text-muted-foreground">
          {formatTokens(usage.tokens_used_today)} tokens used &mdash; no limit on your plan
        </p>
      </div>
    );
  }

  const pct = Math.min(100, (usage.tokens_used_today / usage.tokens_limit) * 100);
  const barColor =
    pct >= 90 ? "bg-red-500" : pct >= 70 ? "bg-amber-500" : "bg-neon-green";
  const textColor =
    pct >= 90 ? "text-red-400" : pct >= 70 ? "text-amber-400" : "text-neon-green";

  const resetTime = new Date(usage.reset_at).toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
    timeZoneName: "short",
  });

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between text-sm">
        <span className="text-muted-foreground">Token Usage Today</span>
        <span className={`font-semibold ${textColor}`}>
          {formatTokens(usage.tokens_used_today)} / {formatTokens(usage.tokens_limit)}
        </span>
      </div>
      <div className="h-2 rounded-full bg-white/10 overflow-hidden">
        <div
          className={`h-2 rounded-full transition-all duration-500 ${barColor}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <p className="text-xs text-muted-foreground">
        Resets at midnight UTC ({resetTime})
      </p>
    </div>
  );
}

export default function BillingPage() {
  const { getToken } = useAuth();
  const [status, setStatus] = useState<BillingStatus | null>(null);
  const [usage, setUsage] = useState<UsageData | null>(null);
  const [loading, setLoading] = useState(true);
  const [portalLoading, setPortalLoading] = useState(false);

  useEffect(() => {
    async function fetchData() {
      try {
        const [statusRes, usageRes] = await Promise.all([
          apiFetch("/api/billing/status", getToken),
          apiFetch("/api/billing/usage", getToken),
        ]);
        if (statusRes.ok) setStatus(await statusRes.json());
        if (usageRes.ok) setUsage(await usageRes.json());
      } catch {
        // API may not be available
      } finally {
        setLoading(false);
      }
    }
    fetchData();
  }, [getToken]);

  async function handleManageSubscription() {
    setPortalLoading(true);
    try {
      const res = await apiFetch("/api/billing/portal", getToken, {
        method: "POST",
      });
      const data = await res.json();
      if (data.portal_url) {
        window.location.href = data.portal_url;
      }
    } catch {
      // Portal creation failed
    } finally {
      setPortalLoading(false);
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-8 h-8 border-2 border-brand border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  const subStatus = status?.stripe_subscription_status;
  const statusStyle = subStatus ? STATUS_STYLES[subStatus] : null;
  const StatusIcon = statusStyle?.icon;

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="space-y-2">
        <h1 className="font-display text-3xl sm:text-4xl font-bold text-white">
          Billing
        </h1>
        <p className="text-muted-foreground text-lg">
          Manage your subscription and billing details
        </p>
      </div>

      {/* Usage meter — primary visual for subscribed users */}
      {status?.has_subscription && usage && (
        <GlassCard variant="strong">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-9 h-9 rounded-lg bg-brand/10 flex items-center justify-center">
              <Zap className="w-4 h-4 text-brand" />
            </div>
            <h2 className="text-base font-semibold text-white">AI Token Usage</h2>
          </div>
          <UsageMeter usage={usage} />
        </GlassCard>
      )}

      {/* Current plan card */}
      <GlassCard variant="strong">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-xl bg-brand/10 flex items-center justify-center">
              <CreditCard className="w-6 h-6 text-brand" />
            </div>
            <div>
              <div className="flex items-center gap-3">
                <h2 className="text-xl font-bold text-white">
                  {status?.plan_name || "Bootstrapper"}
                </h2>
                {statusStyle && StatusIcon && (
                  <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-semibold rounded-full ${statusStyle.className}`}>
                    <StatusIcon className="w-3 h-3" />
                    {statusStyle.label}
                  </span>
                )}
              </div>
              <p className="text-sm text-muted-foreground mt-0.5">
                {status?.has_subscription
                  ? "Your subscription is managed through Stripe"
                  : "Upgrade to start building with AI"}
              </p>
            </div>
          </div>

          {status?.has_subscription ? (
            <button
              onClick={handleManageSubscription}
              disabled={portalLoading}
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl glass hover:bg-white/5 text-white text-sm font-medium transition-colors self-start"
            >
              {portalLoading ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <ExternalLink className="w-4 h-4" />
              )}
              Manage Subscription
            </button>
          ) : (
            <Link
              href="/pricing"
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-brand text-white text-sm font-medium hover:bg-brand-dark transition-colors shadow-glow self-start"
            >
              Upgrade Plan <ArrowRight className="w-4 h-4" />
            </Link>
          )}
        </div>
      </GlassCard>

      {/* Info cards for subscribed users */}
      {status?.has_subscription && (
        <div className="grid sm:grid-cols-2 gap-4">
          <GlassCard>
            <h3 className="font-semibold text-white mb-1">Update Payment Method</h3>
            <p className="text-sm text-muted-foreground mb-4">
              Change your credit card or billing details through the Stripe portal.
            </p>
            <button
              onClick={handleManageSubscription}
              className="text-sm text-brand hover:text-brand-light transition-colors font-medium"
            >
              Open billing portal
            </button>
          </GlassCard>
          <GlassCard>
            <h3 className="font-semibold text-white mb-1">View Invoices</h3>
            <p className="text-sm text-muted-foreground mb-4">
              Download past invoices and receipts from the Stripe portal.
            </p>
            <button
              onClick={handleManageSubscription}
              className="text-sm text-brand hover:text-brand-light transition-colors font-medium"
            >
              View invoice history
            </button>
          </GlassCard>
        </div>
      )}

      {/* Upgrade-focused layout for unsubscribed founders */}
      {!status?.has_subscription && (
        <GlassCard>
          <div className="text-center py-8">
            <div className="w-16 h-16 rounded-2xl bg-brand/10 flex items-center justify-center mx-auto mb-4">
              <Zap className="w-8 h-8 text-brand" />
            </div>
            <h3 className="font-display font-bold text-white text-2xl mb-2">
              Build faster with AI
            </h3>
            <p className="text-muted-foreground mb-2 max-w-md mx-auto">
              Get your technical co-founder for <span className="text-white font-semibold">$99/mo</span>.
              Full LLM access, unlimited projects, and priority support.
            </p>
            <ul className="text-sm text-muted-foreground mb-6 space-y-1">
              <li className="flex items-center justify-center gap-2">
                <CheckCircle2 className="w-3.5 h-3.5 text-neon-green" />
                500K tokens/day to start &mdash; Partner plan unlocks more
              </li>
              <li className="flex items-center justify-center gap-2">
                <CheckCircle2 className="w-3.5 h-3.5 text-neon-green" />
                Stripe-secured billing, cancel any time
              </li>
              <li className="flex items-center justify-center gap-2">
                <CheckCircle2 className="w-3.5 h-3.5 text-neon-green" />
                From idea to running MVP in under 10 minutes
              </li>
            </ul>
            <Link
              href="/pricing"
              className="inline-flex items-center gap-2 px-8 py-3 rounded-xl bg-brand text-white font-semibold hover:bg-brand-dark transition-colors shadow-glow"
            >
              View Plans &amp; Pricing <ArrowRight className="w-4 h-4" />
            </Link>
          </div>
        </GlassCard>
      )}
    </div>
  );
}
