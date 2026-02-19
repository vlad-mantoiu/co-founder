export type StageId =
  | "strategic-analysis"
  | "architecture-design"
  | "validation-testing"
  | "issue-resolution"
  | "quality-assurance"
  | "deployment-delivery";

export type StageStatus = "queued" | "active" | "complete";

export interface StageState {
  id: StageId;
  label: string;
  status: StageStatus;
  logs: LogLine[];
  summary?: string;
  durationMs?: number;
  metrics?: Record<string, string | number>;
}

export interface LogLine {
  id: string;
  text: string;
  timestamp: number;
}

export interface Entity {
  text: string;
  type: "technology" | "feature" | "integration" | "platform" | "concept";
}

export type FlowPhase = "idle" | "parsing" | "analysis" | "complete";

export interface AnalysisState {
  phase: FlowPhase;
  idea: string;
  entities: Entity[];
  stages: StageState[];
  activeStageIndex: number;
  progress: number;
  sessionId: string | null;
  latencyMs: number;
  finalOutput: string | null;
  error: string | null;
}

export interface SSEEvent {
  session_id: string;
  node: string;
  message: string;
}

export const STAGE_MAP: Record<string, StageId> = {
  architect: "strategic-analysis",
  coder: "architecture-design",
  executor: "validation-testing",
  debugger: "issue-resolution",
  reviewer: "quality-assurance",
  git_manager: "deployment-delivery",
};

export const ORDERED_STAGES: { id: StageId; label: string }[] = [
  { id: "strategic-analysis", label: "Strategic Analysis" },
  { id: "architecture-design", label: "Architecture & Design" },
  { id: "validation-testing", label: "Validation & Testing" },
  { id: "issue-resolution", label: "Issue Resolution" },
  { id: "quality-assurance", label: "Quality Assurance" },
  { id: "deployment-delivery", label: "Deployment & Delivery" },
];

export function createInitialStages(): StageState[] {
  return ORDERED_STAGES.map(({ id, label }) => ({
    id,
    label,
    status: "queued" as StageStatus,
    logs: [],
  }));
}
