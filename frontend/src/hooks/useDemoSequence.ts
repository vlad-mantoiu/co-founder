"use client";

import { useState, useCallback, useRef } from "react";
import type {
  AnalysisState,
  Entity,
  LogLine,
} from "@/components/chat/types";
import { createInitialStages, ORDERED_STAGES } from "@/components/chat/types";

const ENTITY_KEYWORDS: Record<string, Entity["type"]> = {
  api: "technology",
  rest: "technology",
  graphql: "technology",
  react: "technology",
  next: "technology",
  node: "technology",
  python: "technology",
  stripe: "integration",
  auth: "feature",
  authentication: "feature",
  billing: "feature",
  dashboard: "feature",
  database: "technology",
  postgres: "technology",
  redis: "technology",
  aws: "platform",
  docker: "platform",
  kubernetes: "platform",
  ci: "concept",
  cd: "concept",
  pipeline: "concept",
  microservices: "concept",
  saas: "concept",
  real: "concept",
  time: "concept",
  collaboration: "feature",
  ai: "technology",
  code: "feature",
  review: "feature",
};

const STAGE_LOGS: string[][] = [
  [
    "Initializing strategic analysis engine...",
    "Parsing project requirements and constraints",
    "Evaluating market fit and technical feasibility",
    "Identifying core value propositions",
    "Mapping dependency graph for key features",
    "Generating strategic recommendations",
    "Prioritizing implementation roadmap",
    "Strategic analysis complete.",
  ],
  [
    "Bootstrapping architecture design module...",
    "Selecting optimal tech stack components",
    "Designing system architecture diagram",
    "Defining API contracts and data models",
    "Planning database schema and migrations",
    "Configuring service communication patterns",
    "Architecture blueprint finalized.",
  ],
  [
    "Spinning up validation environment...",
    "Generating unit test scaffolding",
    "Running static analysis checks",
    "Validating API contract compliance",
    "Executing integration test suite",
    "Performance benchmark: 120ms p99 latency",
    "All validation checks passed.",
  ],
  [
    "Scanning for potential issues...",
    "Analyzing error handling coverage",
    "Checking for security vulnerabilities",
    "Reviewing edge cases and race conditions",
    "Patching identified issues",
    "Re-running affected test cases",
    "All issues resolved successfully.",
  ],
  [
    "Initiating quality assurance review...",
    "Checking code style and conventions",
    "Reviewing documentation completeness",
    "Validating accessibility compliance",
    "Running final integration tests",
    "Code quality score: 94/100",
    "QA review passed.",
  ],
  [
    "Preparing deployment artifacts...",
    "Building production bundles",
    "Generating infrastructure-as-code templates",
    "Configuring CI/CD pipeline stages",
    "Running pre-deployment health checks",
    "Deploying to staging environment",
    "Production deployment strategy ready.",
  ],
];

function extractEntities(text: string): Entity[] {
  const words = text.toLowerCase().split(/\s+/);
  const found: Entity[] = [];
  const seen = new Set<string>();

  for (const word of words) {
    const clean = word.replace(/[^a-z]/g, "");
    if (ENTITY_KEYWORDS[clean] && !seen.has(clean)) {
      seen.add(clean);
      found.push({ text: clean, type: ENTITY_KEYWORDS[clean] });
    }
  }
  return found.slice(0, 6);
}

const INITIAL_STATE: AnalysisState = {
  phase: "idle",
  idea: "",
  entities: [],
  stages: createInitialStages(),
  activeStageIndex: -1,
  progress: 0,
  sessionId: null,
  latencyMs: 0,
  finalOutput: null,
  error: null,
};

export function useDemoSequence() {
  const [state, setState] = useState<AnalysisState>(INITIAL_STATE);
  const abortRef = useRef(false);

  const reset = useCallback(() => {
    abortRef.current = true;
    setState(INITIAL_STATE);
  }, []);

  const abort = useCallback(() => {
    abortRef.current = true;
    setState((s) => ({ ...s, phase: "idle", error: "Analysis aborted" }));
  }, []);

  const start = useCallback((idea: string) => {
    abortRef.current = false;
    const entities = extractEntities(idea);
    const sessionId = `demo-${Date.now()}`;

    setState({
      ...INITIAL_STATE,
      phase: "parsing",
      idea,
      entities,
      sessionId,
    });

    // Parsing phase: 1.5s
    setTimeout(() => {
      if (abortRef.current) return;
      setState((s) => ({
        ...s,
        phase: "analysis",
        stages: createInitialStages(),
        activeStageIndex: 0,
      }));

      // Run stages sequentially
      runStages(sessionId);
    }, 1500);

    async function runStages(sid: string) {
      const stages = createInitialStages();

      for (let si = 0; si < ORDERED_STAGES.length; si++) {
        if (abortRef.current) return;

        // Mark stage active
        stages[si].status = "active";
        const stageStart = Date.now();

        setState((s) => ({
          ...s,
          stages: [...stages],
          activeStageIndex: si,
          progress: (si / ORDERED_STAGES.length) * 100,
          latencyMs: Math.round(30 + Math.random() * 50),
        }));

        // Add log lines with delays
        const logs = STAGE_LOGS[si];
        for (let li = 0; li < logs.length; li++) {
          if (abortRef.current) return;

          await delay(300 + Math.random() * 500);
          if (abortRef.current) return;

          const line: LogLine = {
            id: `${sid}-${si}-${li}`,
            text: logs[li],
            timestamp: Date.now(),
          };

          stages[si] = {
            ...stages[si],
            logs: [...stages[si].logs, line],
          };

          setState((s) => ({
            ...s,
            stages: [...stages],
            latencyMs: Math.round(30 + Math.random() * 50),
          }));
        }

        // Complete stage
        stages[si] = {
          ...stages[si],
          status: "complete",
          summary: logs[logs.length - 1],
          durationMs: Date.now() - stageStart,
          metrics: {
            Lines: Math.round(40 + Math.random() * 200),
            Files: Math.round(3 + Math.random() * 12),
            Score: `${Math.round(85 + Math.random() * 15)}%`,
          },
        };

        setState((s) => ({
          ...s,
          stages: [...stages],
          progress: ((si + 1) / ORDERED_STAGES.length) * 100,
        }));
      }

      // Complete
      if (!abortRef.current) {
        setState((s) => ({
          ...s,
          phase: "complete",
          progress: 100,
          finalOutput: `Analysis complete for "${idea}". Your project has been fully analyzed across all six stages. The architecture is validated, tests are passing, and a deployment strategy is ready. Click "View Architecture" to see the full system diagram.`,
        }));
      }
    }
  }, []);

  return { state, start, reset, abort };
}

function delay(ms: number) {
  return new Promise((r) => setTimeout(r, ms));
}
