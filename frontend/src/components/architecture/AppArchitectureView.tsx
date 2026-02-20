"use client";

import { useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import {
  Monitor,
  Server,
  Database,
  Shield,
  HardDrive,
  Box,
  ChevronDown,
  ChevronUp,
  DollarSign,
  Lightbulb,
  ArrowRight,
} from "lucide-react";

export interface ArchitectureComponent {
  name: string;
  type: "frontend" | "backend" | "database" | "auth" | "storage" | "other";
  description: string;
  tech_recommendation: string;
  alternatives: string[];
  detail_level: "simplified" | "expanded";
}

export interface ArchitectureConnection {
  from_component: string;
  to_component: string;
  protocol: string;
  description: string;
}

export interface CostBreakdown {
  component: string;
  cost: string;
  note: string;
}

export interface CostEstimate {
  startup_monthly: string;
  scale_monthly: string;
  breakdown: CostBreakdown[];
}

export interface AppArchitectureViewProps {
  components: ArchitectureComponent[];
  connections: ArchitectureConnection[];
  costEstimate: CostEstimate;
  integrationRecommendations: string[];
}

const TYPE_CONFIG: Record<
  ArchitectureComponent["type"],
  { icon: React.ElementType; bg: string; iconColor: string; label: string }
> = {
  frontend: {
    icon: Monitor,
    bg: "bg-emerald-500/10",
    iconColor: "text-emerald-400",
    label: "Frontend",
  },
  backend: {
    icon: Server,
    bg: "bg-blue-500/10",
    iconColor: "text-blue-400",
    label: "Backend",
  },
  database: {
    icon: Database,
    bg: "bg-violet-500/10",
    iconColor: "text-violet-400",
    label: "Database",
  },
  auth: {
    icon: Shield,
    bg: "bg-amber-500/10",
    iconColor: "text-amber-400",
    label: "Auth",
  },
  storage: {
    icon: HardDrive,
    bg: "bg-sky-500/10",
    iconColor: "text-sky-400",
    label: "Storage",
  },
  other: {
    icon: Box,
    bg: "bg-white/10",
    iconColor: "text-white/60",
    label: "Other",
  },
};

function ComponentCard({ component }: { component: ArchitectureComponent }) {
  const [expanded, setExpanded] = useState(false);
  const config = TYPE_CONFIG[component.type];
  const Icon = config.icon;

  return (
    <div className="flex flex-col rounded-xl border border-white/[0.06] bg-white/[0.02] p-5 hover:border-white/[0.10] transition-colors">
      {/* Header */}
      <div className="flex items-start gap-3 mb-3">
        <div className={`flex-shrink-0 rounded-lg p-2 ${config.bg}`}>
          <Icon className={`h-5 w-5 ${config.iconColor}`} />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-sm font-semibold text-white">{component.name}</span>
            <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${config.bg} ${config.iconColor}`}>
              {config.label}
            </span>
          </div>
          <p className="mt-1 text-sm text-white/60 leading-relaxed">{component.description}</p>
        </div>
      </div>

      {/* Tech recommendation badge */}
      <div className="mb-3">
        <span className="inline-flex items-center gap-1.5 rounded-md bg-brand/10 px-3 py-1.5 text-sm font-medium text-brand border border-brand/20">
          {component.tech_recommendation}
        </span>
      </div>

      {/* Expand/collapse toggle */}
      <button
        onClick={() => setExpanded((v) => !v)}
        className="mt-auto flex items-center gap-1.5 text-xs text-white/40 hover:text-white/70 transition-colors self-start pt-1"
      >
        {expanded ? (
          <>
            <ChevronUp className="h-3.5 w-3.5" />
            Hide detail
          </>
        ) : (
          <>
            <ChevronDown className="h-3.5 w-3.5" />
            Show technical detail
          </>
        )}
      </button>

      {/* Expanded content */}
      <AnimatePresence>
        {expanded && (
          <motion.div
            key="expanded"
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2, ease: "easeInOut" }}
            className="overflow-hidden"
          >
            <div className="pt-4 space-y-3 border-t border-white/[0.06] mt-3">
              {component.alternatives.length > 0 && (
                <div>
                  <p className="text-xs font-semibold text-white/50 uppercase tracking-wider mb-2">
                    Alternatives
                  </p>
                  <div className="flex flex-wrap gap-1.5">
                    {component.alternatives.map((alt) => (
                      <span
                        key={alt}
                        className="text-xs px-2.5 py-1 rounded-full bg-white/[0.04] border border-white/[0.08] text-white/60"
                      >
                        {alt}
                      </span>
                    ))}
                  </div>
                </div>
              )}
              <div>
                <p className="text-xs font-semibold text-white/50 uppercase tracking-wider mb-1.5">
                  Technical notes
                </p>
                <p className="text-xs text-white/50 leading-relaxed">{component.description}</p>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

function CostEstimateSection({ costEstimate }: { costEstimate: CostEstimate }) {
  const [showBreakdown, setShowBreakdown] = useState(false);

  return (
    <div className="rounded-xl border border-white/[0.06] bg-white/[0.02] p-6">
      <div className="flex items-center gap-2 mb-4">
        <DollarSign className="h-5 w-5 text-emerald-400" />
        <h3 className="text-base font-semibold text-white">Cost Estimates</h3>
      </div>

      <div className="flex flex-wrap gap-6 mb-4">
        <div>
          <p className="text-xs text-white/40 mb-1">To start</p>
          <p className="text-2xl font-bold text-emerald-400">{costEstimate.startup_monthly}</p>
          <p className="text-xs text-white/40 mt-0.5">per month</p>
        </div>
        <div>
          <p className="text-xs text-white/40 mb-1">At 1,000 users</p>
          <p className="text-2xl font-bold text-amber-400">{costEstimate.scale_monthly}</p>
          <p className="text-xs text-white/40 mt-0.5">per month</p>
        </div>
      </div>

      {costEstimate.breakdown.length > 0 && (
        <>
          <button
            onClick={() => setShowBreakdown((v) => !v)}
            className="flex items-center gap-1.5 text-xs text-white/40 hover:text-white/70 transition-colors mb-3"
          >
            {showBreakdown ? (
              <>
                <ChevronUp className="h-3.5 w-3.5" />
                Hide breakdown
              </>
            ) : (
              <>
                <ChevronDown className="h-3.5 w-3.5" />
                Show cost breakdown
              </>
            )}
          </button>

          <AnimatePresence>
            {showBreakdown && (
              <motion.div
                key="breakdown"
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: "auto", opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                transition={{ duration: 0.2, ease: "easeInOut" }}
                className="overflow-hidden"
              >
                <div className="rounded-lg border border-white/[0.06] overflow-hidden">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-white/[0.06] bg-white/[0.02]">
                        <th className="text-left px-4 py-2.5 text-xs font-semibold text-white/40 uppercase tracking-wider">
                          Component
                        </th>
                        <th className="text-right px-4 py-2.5 text-xs font-semibold text-white/40 uppercase tracking-wider">
                          Cost
                        </th>
                        <th className="text-left px-4 py-2.5 text-xs font-semibold text-white/40 uppercase tracking-wider hidden sm:table-cell">
                          Note
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      {costEstimate.breakdown.map((item, i) => (
                        <tr
                          key={i}
                          className="border-b border-white/[0.04] last:border-0 hover:bg-white/[0.02] transition-colors"
                        >
                          <td className="px-4 py-2.5 text-white/70">{item.component}</td>
                          <td className="px-4 py-2.5 text-right font-mono text-white/80">{item.cost}</td>
                          <td className="px-4 py-2.5 text-white/40 text-xs hidden sm:table-cell">{item.note}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </>
      )}
    </div>
  );
}

export function AppArchitectureView({
  components,
  connections,
  costEstimate,
  integrationRecommendations,
}: AppArchitectureViewProps) {
  return (
    <div className="space-y-8 p-6">
      {/* Component diagram section */}
      <section>
        <h2 className="text-sm font-semibold text-white/40 uppercase tracking-wider mb-4">
          Your Tech Stack
        </h2>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {components.map((component) => (
            <ComponentCard key={component.name} component={component} />
          ))}
        </div>
      </section>

      {/* Connections section */}
      {connections.length > 0 && (
        <section>
          <h2 className="text-sm font-semibold text-white/40 uppercase tracking-wider mb-4">
            How Components Connect
          </h2>
          <div className="rounded-xl border border-white/[0.06] bg-white/[0.02] divide-y divide-white/[0.04]">
            {connections.map((conn, i) => (
              <div key={i} className="flex items-start gap-3 px-5 py-4">
                <div className="flex items-center gap-2 flex-1 min-w-0">
                  <span className="text-sm font-medium text-white/80 truncate">{conn.from_component}</span>
                  <ArrowRight className="h-4 w-4 text-white/30 flex-shrink-0" />
                  <span className="text-sm font-medium text-white/80 truncate">{conn.to_component}</span>
                  <span className="ml-1 text-xs px-2 py-0.5 rounded-full bg-white/[0.04] border border-white/[0.08] text-white/40 flex-shrink-0">
                    {conn.protocol}
                  </span>
                </div>
                <p className="text-sm text-white/40 hidden md:block flex-shrink-0 max-w-[40%] truncate">
                  {conn.description}
                </p>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Cost estimates section */}
      <section>
        <h2 className="text-sm font-semibold text-white/40 uppercase tracking-wider mb-4">
          Infrastructure Costs
        </h2>
        <CostEstimateSection costEstimate={costEstimate} />
      </section>

      {/* Integration recommendations */}
      {integrationRecommendations.length > 0 && (
        <section>
          <h2 className="text-sm font-semibold text-white/40 uppercase tracking-wider mb-4">
            Recommended Integrations
          </h2>
          <div className="rounded-xl border border-white/[0.06] bg-white/[0.02] divide-y divide-white/[0.04]">
            {integrationRecommendations.map((rec, i) => (
              <div key={i} className="flex items-start gap-3 px-5 py-4">
                <Lightbulb className="h-4 w-4 text-amber-400 flex-shrink-0 mt-0.5" />
                <p className="text-sm text-white/70">{rec}</p>
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
