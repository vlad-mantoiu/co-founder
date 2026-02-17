export interface TimelineItem {
  id: string;
  project_id: string;
  timestamp: string;
  type: "decision" | "milestone" | "artifact";
  title: string;
  summary: string;
  kanban_status: "backlog" | "planned" | "in_progress" | "done";
  graph_node_id: string | null;
  build_version: string | null;
  decision_id: string | null;
  debug_id: string | null;
}
