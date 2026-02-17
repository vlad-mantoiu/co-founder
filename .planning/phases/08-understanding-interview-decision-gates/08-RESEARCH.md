# Phase 8: Understanding Interview & Decision Gates - Research

**Researched:** 2026-02-17
**Domain:** Adaptive LLM interviews, decision gate workflows, execution plan generation, state machine integration, comparison UI patterns
**Confidence:** HIGH

## Summary

Phase 8 extends Phase 4's onboarding with a deeper understanding interview that produces a Rationalised Idea Brief (investor-quality), then introduces Decision Gate 1 (Proceed/Narrow/Pivot/Park) as a critical stage-transition pattern. After proceeding, founders choose from 2-3 execution plan options before build begins. The phase combines conversational AI patterns (adaptive questioning, back-navigation with regeneration), state machine decision points (conditional routing based on gate resolution), and comparison table UX (analytical build path selection).

The architecture builds on established patterns: LangGraph conditional edges for decision routing, Anthropic Structured Outputs for reliable brief/option generation, PostgreSQL JSONB for idea brief versioning, and shadcn/ui Collapsible + Card for expandable sections. Decision gates block stage advancement (409 if not resolved), track decisions in a dedicated table, and support Narrow/Pivot actions that update the brief. The Deep Research button stubs with 402 (payment required) for beta gating.

**Primary recommendation:** Extend Phase 4's OnboardingSession with adaptive question regeneration on back-navigation. Create DecisionGate model for gate lifecycle (pending → decided/expired). Use LangGraph conditional edges to route based on gate decisions. Implement comparison table UI with shadcn data tables for execution plan selection. Store Idea Brief as versioned JSONB in Artifact model. Use full-screen modal (shadcn Dialog in fullscreen mode) for Decision Gate 1 ceremony.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### Interview Flow
- One question at a time — single question focus, founder answers, next question appears
- Adaptive questioning — LLM picks the next question based on what was answered (feels like a real co-founder conversation)
- Back-navigation with re-adaptation — founder can edit any previous answer, subsequent questions regenerate based on the change
- Skeleton shimmer for loading between questions — consistent with Phase 4 patterns

#### Idea Brief Display
- Card summary + expand layout — key fields as summary cards, click to expand full sections (scannable at a glance, detail on demand)
- Both inline editing and re-interview — inline edit for small tweaks + "Re-interview" button for major changes
- Investor-facing tone — professional, structured, could be shared with investors (problem/solution/market framing)
- Per-section confidence indicators — each section shows strength based on input quality (e.g., "Strong" for detailed answers, "Needs depth" for thin ones)

#### Decision Gate UX
- Full-screen modal — blocks everything, this is a critical decision moment deserving full attention and ceremony
- Rich cards per option — each of Proceed/Narrow/Pivot/Park as a card with: description, what happens next, pros/cons, and "why you might choose this" blurb
- Narrow/Pivot action: edit prompt — show a text field ("Describe how you want to narrow/pivot"), then LLM updates brief from that input
- Park action: archive with note — project moves to "Parked" section, founder adds optional note about why, can revisit anytime

#### Build Path Selection
- Comparison table layout — feature-by-feature comparison grid with rows for time, cost, risk, scope (data-dense, analytical)
- Recommended option: badge + border — "Recommended" badge with brand-colored border (clear but not pushy)
- Full breakdown per option — time to ship, engineering cost estimate, risk level, scope coverage, pros/cons, and technical approach summary
- Select or regenerate — pick one option, or hit "Generate different options" for a fresh set (prevents analysis paralysis while allowing flexibility)

### Claude's Discretion
- Exact animation timing for question transitions
- Section ordering within the Idea Brief
- Specific wording of confidence level labels
- Visual design of the comparison table cells

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope

</user_constraints>

## Standard Stack

### Core Backend
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| langgraph | 0.2.0+ | State machine with conditional edges | Already installed, decision routing patterns |
| anthropic | 0.40.0+ | Structured Outputs for brief generation | Already installed, guaranteed JSON schema compliance |
| SQLAlchemy | 2.0.0+ | Async ORM with JSONB versioning | Already installed, Artifact model exists |
| Pydantic | 2.10.0+ | Schema validation for brief/options | Already installed, type-safe validation |

### Core Frontend
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| React 19 | 19.x | Component framework | Already installed |
| Next.js 15 | 15.0.0+ | App Router, server actions | Already installed |
| shadcn/ui | Latest | Dialog, Card, Collapsible components | Already installed, Radix primitives |
| Framer Motion | 12.34.0 | Modal animations, skeleton shimmer | Already installed |
| Tailwind CSS | 4.0.0+ | Utility-first styling | Already installed |

### Supporting Libraries
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| react-loading-skeleton | 3.5.0+ | Skeleton shimmer components | Question loading states (already in Phase 4) |
| @radix-ui/react-collapsible | Via shadcn | Expandable card sections | Idea Brief section expansion |
| @radix-ui/react-dialog | Via shadcn | Full-screen modal | Decision Gate 1 ceremony |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| LangGraph conditional edges | Manual if/else routing | Conditional edges provide explicit graph structure, better debugging |
| DecisionGate model | Project.metadata JSONB | Dedicated table enables gate history queries, audit trail |
| shadcn Dialog | Custom modal | Dialog provides accessibility, focus management, escape handling |
| JSONB brief versioning | Separate brief_versions table | JSONB simpler for small version history, relational better for >10 versions |

**Installation:**
```bash
# Backend (no new dependencies needed)
cd backend
pip install -e ".[dev]"  # All dependencies already in pyproject.toml

# Frontend (no new dependencies needed)
cd frontend
npm install  # shadcn components already configured
```

## Architecture Patterns

### Recommended Project Structure

```
backend/app/
├── api/routes/
│   ├── onboarding.py           # EXTEND: Add re-interview, adaptive regeneration
│   ├── decision_gates.py       # NEW: POST /create, POST /resolve, GET /status
│   └── execution_plans.py      # NEW: POST /generate, POST /select
├── agent/
│   ├── runner.py               # EXTEND: Add generate_idea_brief(), generate_execution_options()
│   ├── runner_real.py          # EXTEND: Implement with Anthropic Structured Outputs
│   └── runner_fake.py          # EXTEND: Add scenario data for gates/plans
├── db/models/
│   ├── decision_gate.py        # EXISTING: Extend with gate_context JSONB
│   ├── onboarding_session.py   # EXTEND: Add regeneration tracking
│   └── artifact.py             # EXISTING: Use for Idea Brief storage
├── domain/
│   └── gates.py                # EXISTING: Extend with Narrow/Pivot logic
└── schemas/
    ├── decision_gates.py       # NEW: Pydantic models for gate API
    └── execution_plans.py      # NEW: Pydantic models for build options

frontend/src/
├── app/(dashboard)/
│   ├── understanding/
│   │   └── page.tsx            # NEW: Understanding interview page
│   └── project/[id]/
│       └── brief/page.tsx      # NEW: Idea Brief display page
├── components/understanding/
│   ├── AdaptiveInterview.tsx   # NEW: Extended from Phase 4 with regeneration
│   ├── IdeaBriefCard.tsx       # NEW: Expandable summary cards
│   ├── ConfidenceIndicator.tsx # NEW: Section strength badges
│   └── ReInterviewButton.tsx   # NEW: Trigger major regeneration
├── components/decision-gates/
│   ├── DecisionGateModal.tsx   # NEW: Full-screen modal for gate
│   ├── GateOptionCard.tsx      # NEW: Rich card per decision option
│   └── NarrowPivotForm.tsx     # NEW: Text field for scope changes
└── components/execution-plans/
    ├── PlanComparisonTable.tsx # NEW: Feature-by-feature grid
    └── PlanOptionCard.tsx      # NEW: Detailed option breakdown
```

### Pattern 1: Adaptive Question Regeneration on Edit

**What:** When user edits a previous answer, selectively regenerate subsequent questions if they become redundant

**When to use:** Multi-step conversational flows where context matters and questions adapt

**Example:**
```python
# Source: LangGraph conversation memory patterns + Phase 4 research
from app.agent.runner import Runner
from app.db.models.onboarding_session import OnboardingSession
from sqlalchemy.orm.attributes import flag_modified

async def handle_answer_edit(
    session_id: str,
    question_id: str,
    new_answer: str,
    runner: Runner
) -> OnboardingSession:
    """Edit answer and selectively regenerate subsequent questions."""
    async with get_session_factory()() as db:
        session = await db.get(OnboardingSession, session_id)

        # Update answer
        session.answers[question_id] = new_answer
        flag_modified(session, "answers")

        # Find question index
        question_index = next(
            (i for i, q in enumerate(session.questions) if q["id"] == question_id),
            None
        )

        if question_index is None:
            return session

        # Check if subsequent questions are now redundant
        subsequent_questions = session.questions[question_index + 1:]

        # Ask LLM: do these questions need regeneration?
        should_regenerate = await runner.check_question_redundancy(
            idea=session.idea_text,
            answered_questions=session.questions[:question_index + 1],
            answers=session.answers,
            remaining_questions=subsequent_questions
        )

        if should_regenerate["needs_regeneration"]:
            # Regenerate only redundant questions, preserve non-redundant ones
            new_questions = await runner.regenerate_questions(
                idea=session.idea_text,
                answers=session.answers,
                preserve_indices=should_regenerate["preserve_indices"]
            )

            # Update questions list
            session.questions = (
                session.questions[:question_index + 1] +
                new_questions
            )
            flag_modified(session, "questions")

        await db.commit()
        await db.refresh(session)
        return session
```

**Why selective regeneration:**
- Preserves user progress (doesn't discard all subsequent answers)
- Feels intelligent (LLM adapts, doesn't blindly reset)
- Reduces frustration (editing doesn't lose work)

### Pattern 2: Decision Gate State Machine Integration

**What:** LangGraph conditional edges route based on decision gate status

**When to use:** When stage transitions require explicit human decision, not automatic advancement

**Example:**
```python
# Source: LangGraph conditional edges docs + existing gates.py
from langgraph.graph import StateGraph, END
from app.domain.gates import GateDecision, resolve_gate
from app.db.models.decision_gate import DecisionGate

def create_stage_advancement_graph():
    """State machine for stage advancement with decision gates."""
    graph = StateGraph()

    # Nodes
    graph.add_node("check_exit_criteria", check_stage_exit_criteria)
    graph.add_node("create_gate", create_decision_gate)
    graph.add_node("wait_for_decision", wait_for_gate_decision)
    graph.add_node("resolve_proceed", resolve_proceed_decision)
    graph.add_node("resolve_narrow", resolve_narrow_decision)
    graph.add_node("resolve_pivot", resolve_pivot_decision)
    graph.add_node("resolve_park", resolve_park_decision)

    # Entry point
    graph.set_entry_point("check_exit_criteria")

    # Conditional routing based on exit criteria
    graph.add_conditional_edges(
        "check_exit_criteria",
        route_exit_criteria,
        {
            "criteria_met": "create_gate",
            "criteria_not_met": END,
        }
    )

    # Always wait for decision after gate created
    graph.add_edge("create_gate", "wait_for_decision")

    # Conditional routing based on gate decision
    graph.add_conditional_edges(
        "wait_for_decision",
        route_gate_decision,
        {
            "proceed": "resolve_proceed",
            "narrow": "resolve_narrow",
            "pivot": "resolve_pivot",
            "park": "resolve_park",
            "pending": "wait_for_decision",  # Loop until decided
        }
    )

    # Terminal nodes
    graph.add_edge("resolve_proceed", END)
    graph.add_edge("resolve_narrow", END)
    graph.add_edge("resolve_pivot", END)
    graph.add_edge("resolve_park", END)

    return graph.compile()

def route_gate_decision(state: dict) -> str:
    """Route based on current decision gate status."""
    gate = state["current_gate"]

    if gate.status == "pending":
        return "pending"

    # Map decision to node name
    return gate.decision  # "proceed", "narrow", "pivot", or "park"

async def resolve_proceed_decision(state: dict) -> dict:
    """Advance to next stage."""
    gate = state["current_gate"]
    project = state["project"]

    resolution = resolve_gate(
        decision=GateDecision.PROCEED,
        current_stage=project.stage,
        gate_stage=gate.stage_number,
        milestone_keys=[]
    )

    # Update project stage
    project.stage = resolution.target_stage

    return {"project": project, "resolution": resolution}
```

**Why LangGraph for gates:**
- Explicit decision points visible in graph visualization
- Conditional routing prevents stage advancement without decision
- State machine naturally models gate lifecycle (pending → decided)

### Pattern 3: Idea Brief as Versioned Artifact

**What:** Store Rationalised Idea Brief in Artifact model with JSONB versioning for edits

**When to use:** When content has multiple versions (LLM-generated, inline edits, Narrow/Pivot updates)

**Example:**
```python
# Source: Existing Artifact model from Phase 6 + JSONB patterns
from app.db.models.artifact import Artifact, ArtifactType
from pydantic import BaseModel, Field

class RationalisedIdeaBrief(BaseModel):
    """Investor-quality idea brief schema."""
    # Core sections (always present)
    problem_statement: str = Field(description="Clear problem statement")
    target_user: str = Field(description="Specific target user persona")
    value_prop: str = Field(description="Value proposition and differentiation")

    # Context sections
    market_context: str = Field(description="Market landscape and opportunity")
    key_constraints: list[str] = Field(description="Primary constraints (time/money/skills)")

    # Strategic sections (tier-dependent in Phase 4, always present here)
    differentiation: str = Field(description="Competitive differentiation")
    monetization_hypothesis: str = Field(description="Revenue model hypothesis")
    assumptions: list[str] = Field(description="Key assumptions to validate")
    risks: list[str] = Field(description="Identified risks and mitigations")
    smallest_viable_experiment: str = Field(description="MVE recommendation")

    # Metadata
    confidence_scores: dict[str, str] = Field(
        description="Section confidence: 'strong' | 'moderate' | 'needs_depth'"
    )
    generated_at: str = Field(description="ISO timestamp")

async def create_idea_brief_artifact(
    project_id: str,
    session: OnboardingSession,
    runner: Runner
) -> Artifact:
    """Generate Idea Brief from interview answers and store as Artifact."""
    async with get_session_factory()() as db:
        # Generate brief via LLM
        brief_data = await runner.generate_idea_brief(
            idea=session.idea_text,
            answers=session.answers,
            questions=session.questions
        )

        # Create Artifact
        artifact = Artifact(
            project_id=project_id,
            artifact_type=ArtifactType.IDEA_BRIEF,
            name="Rationalised Idea Brief",
            description="Investor-quality brief from understanding interview",
            content=brief_data.model_dump(),  # JSONB storage
            version=1,
            generation_status="completed",
        )

        db.add(artifact)
        await db.commit()
        await db.refresh(artifact)

        return artifact

async def update_brief_inline_edit(
    artifact_id: str,
    section_name: str,
    new_content: str
) -> Artifact:
    """Update brief section via inline edit (creates new version)."""
    async with get_session_factory()() as db:
        artifact = await db.get(Artifact, artifact_id)

        # Clone current content
        updated_content = artifact.content.copy()
        updated_content[section_name] = new_content
        updated_content["confidence_scores"][section_name] = "manually_edited"

        # Create new version
        artifact.content = updated_content
        artifact.version += 1
        flag_modified(artifact, "content")

        await db.commit()
        await db.refresh(artifact)

        return artifact
```

**Why Artifact model for brief:**
- Reuses existing versioning infrastructure (Phase 6)
- Supports inline edits + full regeneration
- Queryable via Artifact API (no new routes needed)
- Integrates with Strategy Graph and Timeline

### Pattern 4: Full-Screen Modal for Decision Ceremony

**What:** shadcn Dialog in fullscreen mode with rich option cards for critical decision

**When to use:** High-stakes moments requiring full attention and deliberate choice

**Example:**
```tsx
// Source: shadcn Dialog + modal UX research (2026 best practices)
"use client";

import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Card, CardHeader, CardContent, CardFooter } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { useState } from "react";

interface DecisionGateModalProps {
  isOpen: boolean;
  onClose: () => void;
  gateId: string;
  projectId: string;
}

const GATE_OPTIONS = [
  {
    value: "proceed",
    title: "Proceed to Build",
    description: "We're ready to start building this idea",
    whatHappens: "You'll choose an execution plan and move to implementation",
    pros: ["Clear direction", "Momentum maintained", "Validated approach"],
    cons: ["Commitment to current scope", "Resource allocation locked"],
    whyChoose: "Choose this when the brief feels solid and you're ready to ship.",
  },
  {
    value: "narrow",
    title: "Narrow the Scope",
    description: "The idea is too broad — let's focus on a smaller piece",
    whatHappens: "You'll describe how to narrow, then we'll update the brief",
    pros: ["Faster to ship", "Lower risk", "Learn quicker"],
    cons: ["Smaller initial market", "May miss opportunities"],
    whyChoose: "Choose this when the scope feels too ambitious for your constraints.",
  },
  {
    value: "pivot",
    title: "Pivot Direction",
    description: "The core idea needs to change significantly",
    whatHappens: "You'll describe the pivot, then we'll regenerate the brief",
    pros: ["Course correction", "New opportunities", "Better fit"],
    cons: ["Loses existing work", "Resets timeline"],
    whyChoose: "Choose this when you've learned something that changes the fundamentals.",
  },
  {
    value: "park",
    title: "Park This Idea",
    description: "Not the right time for this idea — archive it for later",
    whatHappens: "Project moves to 'Parked' section, no further action",
    pros: ["Frees up capacity", "No wasted effort", "Can revisit anytime"],
    cons: ["Momentum lost", "No progress"],
    whyChoose: "Choose this when timing, resources, or market aren't aligned.",
  },
];

export function DecisionGateModal({ isOpen, onClose, gateId, projectId }: DecisionGateModalProps) {
  const [selectedOption, setSelectedOption] = useState<string | null>(null);
  const [narrowPivotText, setNarrowPivotText] = useState("");
  const [parkNote, setParkNote] = useState("");

  const handleDecision = async () => {
    if (!selectedOption) return;

    const payload: any = {
      decision: selectedOption,
    };

    if (selectedOption === "narrow" || selectedOption === "pivot") {
      payload.action_text = narrowPivotText;
    } else if (selectedOption === "park") {
      payload.park_note = parkNote;
    }

    await fetch(`/api/decision-gates/${gateId}/resolve`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    onClose();
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-6xl h-screen max-h-screen p-0 gap-0">
        {/* Header */}
        <DialogHeader className="p-8 pb-6 border-b">
          <DialogTitle className="text-3xl font-display">
            Decision Gate 1: Direction
          </DialogTitle>
          <p className="text-muted-foreground mt-2">
            This is a critical decision point. Review your Idea Brief, then choose your path forward.
          </p>
        </DialogHeader>

        {/* Options Grid */}
        <div className="flex-1 overflow-y-auto p-8">
          <div className="grid grid-cols-2 gap-6">
            {GATE_OPTIONS.map((option) => (
              <Card
                key={option.value}
                className={`cursor-pointer transition-all ${
                  selectedOption === option.value
                    ? "ring-2 ring-brand shadow-glow"
                    : "hover:ring-1 hover:ring-white/20"
                }`}
                onClick={() => setSelectedOption(option.value)}
              >
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <h3 className="font-display text-xl">{option.title}</h3>
                    {selectedOption === option.value && (
                      <Badge variant="default">Selected</Badge>
                    )}
                  </div>
                  <p className="text-sm text-muted-foreground mt-1">
                    {option.description}
                  </p>
                </CardHeader>

                <CardContent className="space-y-4">
                  <div>
                    <p className="text-sm font-semibold">What happens next:</p>
                    <p className="text-sm text-muted-foreground mt-1">
                      {option.whatHappens}
                    </p>
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <p className="text-sm font-semibold text-green-400">Pros</p>
                      <ul className="text-xs text-muted-foreground mt-1 space-y-1">
                        {option.pros.map((pro, i) => (
                          <li key={i}>• {pro}</li>
                        ))}
                      </ul>
                    </div>
                    <div>
                      <p className="text-sm font-semibold text-red-400">Cons</p>
                      <ul className="text-xs text-muted-foreground mt-1 space-y-1">
                        {option.cons.map((con, i) => (
                          <li key={i}>• {con}</li>
                        ))}
                      </ul>
                    </div>
                  </div>

                  <div className="pt-2 border-t">
                    <p className="text-xs text-muted-foreground italic">
                      {option.whyChoose}
                    </p>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>

          {/* Conditional input fields */}
          {(selectedOption === "narrow" || selectedOption === "pivot") && (
            <div className="mt-6 p-6 glass-strong rounded-lg">
              <label className="block text-sm font-semibold mb-2">
                {selectedOption === "narrow" ? "How should we narrow?" : "What's the pivot?"}
              </label>
              <Textarea
                value={narrowPivotText}
                onChange={(e) => setNarrowPivotText(e.target.value)}
                placeholder={
                  selectedOption === "narrow"
                    ? "E.g., Focus only on small businesses instead of all companies..."
                    : "E.g., Instead of a marketplace, build a SaaS tool for..."
                }
                rows={4}
                className="w-full"
              />
            </div>
          )}

          {selectedOption === "park" && (
            <div className="mt-6 p-6 glass-strong rounded-lg">
              <label className="block text-sm font-semibold mb-2">
                Why are you parking this? (optional)
              </label>
              <Textarea
                value={parkNote}
                onChange={(e) => setParkNote(e.target.value)}
                placeholder="E.g., Need to validate market first, timing not right, resource constraints..."
                rows={3}
                className="w-full"
              />
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-8 pt-6 border-t flex items-center justify-between">
          <Button variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button
            onClick={handleDecision}
            disabled={!selectedOption}
            className="min-w-[200px]"
          >
            Confirm Decision
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
```

**Why full-screen modal:**
- Commands full attention (high-stakes decision deserves ceremony)
- Blocks everything (founder must engage, can't accidentally dismiss)
- Rich cards communicate options clearly (pros/cons, what happens next)
- Escape/cancel available (user always has exit, but intentional)

### Pattern 5: Comparison Table for Build Path Selection

**What:** Feature-by-feature grid comparing execution plan options (time, cost, risk, scope)

**When to use:** When founder needs analytical comparison to make informed build decision

**Example:**
```tsx
// Source: shadcn data tables + comparison UI research
"use client";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardContent } from "@/components/ui/card";

interface ExecutionOption {
  id: string;
  name: string;
  is_recommended: boolean;
  time_to_ship: string;
  engineering_cost: string;
  risk_level: "low" | "medium" | "high";
  scope_coverage: number; // 0-100%
  pros: string[];
  cons: string[];
  technical_approach: string;
}

interface PlanComparisonTableProps {
  options: ExecutionOption[];
  onSelect: (optionId: string) => void;
  onRegenerate: () => void;
}

export function PlanComparisonTable({ options, onSelect, onRegenerate }: PlanComparisonTableProps) {
  const COMPARISON_ROWS = [
    { key: "time_to_ship", label: "Time to Ship" },
    { key: "engineering_cost", label: "Engineering Cost" },
    { key: "risk_level", label: "Risk Level" },
    { key: "scope_coverage", label: "Scope Coverage" },
  ];

  const getRiskBadgeVariant = (level: string) => {
    switch (level) {
      case "low": return "success";
      case "medium": return "warning";
      case "high": return "destructive";
      default: return "secondary";
    }
  };

  return (
    <div className="space-y-6">
      {/* Comparison Grid */}
      <div className="overflow-x-auto">
        <table className="w-full border-collapse">
          <thead>
            <tr className="border-b">
              <th className="text-left p-4 font-semibold">Feature</th>
              {options.map((option) => (
                <th key={option.id} className="text-center p-4">
                  <div className="space-y-2">
                    <div className="font-display text-lg">{option.name}</div>
                    {option.is_recommended && (
                      <Badge variant="default" className="bg-brand">
                        Recommended
                      </Badge>
                    )}
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {COMPARISON_ROWS.map((row) => (
              <tr key={row.key} className="border-b">
                <td className="p-4 font-medium text-sm">{row.label}</td>
                {options.map((option) => (
                  <td key={option.id} className="p-4 text-center">
                    {row.key === "risk_level" ? (
                      <Badge variant={getRiskBadgeVariant(option[row.key])}>
                        {option[row.key].toUpperCase()}
                      </Badge>
                    ) : row.key === "scope_coverage" ? (
                      <div className="flex flex-col items-center gap-1">
                        <span className="text-sm">{option[row.key]}%</span>
                        <div className="w-full h-2 bg-white/10 rounded-full overflow-hidden">
                          <div
                            className="h-full bg-brand"
                            style={{ width: `${option[row.key]}%` }}
                          />
                        </div>
                      </div>
                    ) : (
                      <span className="text-sm">{option[row.key]}</span>
                    )}
                  </td>
                ))}
              </tr>
            </tbody>
          </table>
        </div>

        {/* Detailed Option Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-8">
          {options.map((option) => (
            <Card
              key={option.id}
              className={option.is_recommended ? "ring-2 ring-brand" : ""}
            >
              <CardHeader>
                <h3 className="font-display text-xl">{option.name}</h3>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <p className="text-sm font-semibold">Technical Approach</p>
                  <p className="text-xs text-muted-foreground mt-1">
                    {option.technical_approach}
                  </p>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <p className="text-sm font-semibold text-green-400">Pros</p>
                    <ul className="text-xs text-muted-foreground mt-1 space-y-1">
                      {option.pros.map((pro, i) => (
                        <li key={i}>• {pro}</li>
                      ))}
                    </ul>
                  </div>
                  <div>
                    <p className="text-sm font-semibold text-red-400">Cons</p>
                    <ul className="text-xs text-muted-foreground mt-1 space-y-1">
                      {option.cons.map((con, i) => (
                        <li key={i}>• {con}</li>
                      ))}
                    </ul>
                  </div>
                </div>

                <Button
                  className="w-full"
                  variant={option.is_recommended ? "default" : "outline"}
                  onClick={() => onSelect(option.id)}
                >
                  Select This Plan
                </Button>
              </CardContent>
            </Card>
          ))}
        </div>

        {/* Regenerate Option */}
        <div className="mt-6 text-center">
          <Button variant="ghost" onClick={onRegenerate}>
            Generate Different Options
          </Button>
        </div>
      </div>
    </div>
  );
}
```

**Why comparison table:**
- Data-dense (founder sees all tradeoffs at once)
- Analytical (side-by-side comparison supports informed choice)
- Recommended option clear but not pushy (badge + border, not pre-selected)
- Regenerate available (prevents analysis paralysis, allows exploration)

### Pattern 6: Expandable Card Layout for Idea Brief

**What:** shadcn Card + Collapsible for scannable summary with detail-on-demand

**When to use:** When content has natural sections and founder needs quick scan + deep dive

**Example:**
```tsx
// Source: shadcn Collapsible + Card patterns (2026 best practices)
"use client";

import { Card, CardHeader, CardContent } from "@/components/ui/card";
import { Collapsible, CollapsibleTrigger, CollapsibleContent } from "@/components/ui/collapsible";
import { Badge } from "@/components/ui/badge";
import { ChevronDown, Edit, CheckCircle, AlertCircle } from "lucide-react";
import { useState } from "react";

interface BriefSection {
  key: string;
  title: string;
  summary: string;
  fullContent: string;
  confidence: "strong" | "moderate" | "needs_depth";
}

interface IdeaBriefCardProps {
  section: BriefSection;
  onEdit: (sectionKey: string, newContent: string) => void;
}

const CONFIDENCE_CONFIG = {
  strong: { icon: CheckCircle, color: "text-green-400", label: "Strong" },
  moderate: { icon: AlertCircle, color: "text-yellow-400", label: "Needs refinement" },
  needs_depth: { icon: AlertCircle, color: "text-red-400", label: "Needs depth" },
};

export function IdeaBriefCard({ section, onEdit }: IdeaBriefCardProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [editedContent, setEditedContent] = useState(section.fullContent);

  const ConfidenceIcon = CONFIDENCE_CONFIG[section.confidence].icon;

  const handleSave = () => {
    onEdit(section.key, editedContent);
    setIsEditing(false);
  };

  return (
    <Card>
      <Collapsible open={isOpen} onOpenChange={setIsOpen}>
        <CardHeader className="pb-4">
          <div className="flex items-start justify-between">
            <div className="flex-1">
              <CollapsibleTrigger className="flex items-center gap-2 w-full text-left group">
                <ChevronDown
                  className={`w-5 h-5 transition-transform ${
                    isOpen ? "rotate-180" : ""
                  }`}
                />
                <h3 className="font-display text-lg group-hover:text-brand transition-colors">
                  {section.title}
                </h3>
              </CollapsibleTrigger>

              <p className="text-sm text-muted-foreground mt-2 ml-7">
                {section.summary}
              </p>
            </div>

            <div className="flex items-center gap-2">
              <ConfidenceIcon
                className={`w-4 h-4 ${CONFIDENCE_CONFIG[section.confidence].color}`}
              />
              <Badge variant="secondary" className="text-xs">
                {CONFIDENCE_CONFIG[section.confidence].label}
              </Badge>
            </div>
          </div>
        </CardHeader>

        <CollapsibleContent>
          <CardContent className="pt-0">
            <div className="ml-7 space-y-4">
              {isEditing ? (
                <div className="space-y-2">
                  <textarea
                    value={editedContent}
                    onChange={(e) => setEditedContent(e.target.value)}
                    className="w-full h-32 px-4 py-3 bg-white/5 border border-white/10 rounded-lg text-white resize-none"
                  />
                  <div className="flex gap-2">
                    <button
                      onClick={handleSave}
                      className="px-4 py-2 bg-brand text-white rounded-lg text-sm"
                    >
                      Save
                    </button>
                    <button
                      onClick={() => {
                        setIsEditing(false);
                        setEditedContent(section.fullContent);
                      }}
                      className="px-4 py-2 bg-white/5 text-white rounded-lg text-sm"
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              ) : (
                <>
                  <p className="text-sm text-muted-foreground whitespace-pre-wrap">
                    {section.fullContent}
                  </p>
                  <button
                    onClick={() => setIsEditing(true)}
                    className="flex items-center gap-2 text-sm text-gray-400 hover:text-white transition-colors"
                  >
                    <Edit className="w-4 h-4" />
                    Edit inline
                  </button>
                </>
              )}
            </div>
          </CardContent>
        </CollapsibleContent>
      </Collapsible>
    </Card>
  );
}
```

**Why expandable cards:**
- Scannable at a glance (summary + confidence visible)
- Detail on demand (expand for full content)
- Inline editing without context loss (edit right in place)
- Confidence indicators guide focus (founder knows which sections need work)

### Anti-Patterns to Avoid

- **Automatic stage advancement:** Gates must be explicitly resolved (Proceed decision), never auto-advance even if all exit criteria met
- **Regenerating all questions on edit:** Selectively check redundancy, preserve non-redundant questions
- **Hiding decision context:** Decision Gate modal must show current brief state, not just options
- **Pre-selecting recommended plan:** Recommend with badge/border, but don't pre-select (founder must actively choose)
- **Blocking inline edits during LLM regeneration:** Allow edits anytime, queue regeneration requests
- **Missing 409 for ungated operations:** Return 409 Conflict if trying to generate plans before gate resolved

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Decision gate routing | Manual if/else chains in controller | LangGraph conditional edges | Explicit graph structure, visual debugging, easier to extend with new gate types |
| Full-screen modal | Custom overlay + focus trap | shadcn Dialog with fullscreen class | Accessibility (focus management, escape handling, screen reader support) handled |
| Expandable sections | Custom accordion with useState | shadcn Collapsible (Radix primitive) | Keyboard navigation, ARIA attributes, smooth animations built-in |
| Comparison table | Hand-rolled HTML table | shadcn data table patterns | Responsive, accessible, consistent with existing UI |
| Brief versioning | Custom version history table | Artifact model JSONB versioning (Phase 6) | Reuses existing infrastructure, integrates with Strategy Graph |
| Confidence scoring | Manual rules ("if answer length < 50 chars, low confidence") | LLM-based assessment per section | Nuanced evaluation (considers quality, not just length), adapts to context |

**Key insight:** LangGraph conditional edges make decision gates explicit in the graph structure. Previously, routing logic lived in scattered if/else blocks. Now it's a first-class graph concept with visualization and testing support.

## Common Pitfalls

### Pitfall 1: Question Regeneration Loses All Progress

**What goes wrong:** User edits answer to Q2, all answers Q3-Q7 are discarded

**Why it happens:** Naive regeneration assumes all subsequent questions are invalid

**How to avoid:**
```python
# BAD: Discard all subsequent answers
async def handle_edit(session_id, question_id, new_answer):
    session = await get_session(session_id)
    q_index = find_index(session.questions, question_id)

    # Discard ALL answers after edit
    session.answers = {k: v for k, v in session.answers.items()
                      if find_index(session.questions, k) <= q_index}

    # Regenerate all subsequent questions
    new_questions = await generate_questions(session.idea, session.answers)
    session.questions = session.questions[:q_index+1] + new_questions

# GOOD: Selective regeneration with LLM redundancy check
async def handle_edit(session_id, question_id, new_answer):
    session = await get_session(session_id)
    session.answers[question_id] = new_answer

    # Ask LLM which subsequent questions are now redundant
    redundancy_check = await runner.check_question_redundancy(
        answered_so_far=session.answers,
        remaining_questions=session.questions[q_index+1:]
    )

    if redundancy_check["needs_change"]:
        # Only regenerate specific questions, preserve others
        await regenerate_specific(session, redundancy_check["indices"])
    else:
        # No regeneration needed
        pass
```

**Warning signs:**
- High abandonment after first edit
- Users complain "editing lost my progress"
- Support tickets about disappeared answers

### Pitfall 2: Missing 409 for Ungated Operations

**What goes wrong:** Founder tries to generate execution plans before resolving Decision Gate 1, gets 500 error

**Why it happens:** No explicit check for gate resolution before plan generation

**How to avoid:**
```python
# BAD: Assume gate is resolved
@router.post("/execution-plans/generate")
async def generate_plans(project_id: str, user: ClerkUser = Depends(require_auth)):
    project = await get_project(project_id)

    # Generate plans without checking gate
    options = await runner.generate_execution_options(project)
    return options

# GOOD: Explicit gate check with 409 response
@router.post("/execution-plans/generate")
async def generate_plans(project_id: str, user: ClerkUser = Depends(require_auth)):
    project = await get_project(project_id)

    # Check for unresolved Decision Gate 1
    gate = await get_current_gate(project_id, gate_type="stage_advance")

    if gate and gate.status == "pending":
        raise HTTPException(
            status_code=409,
            detail="Decision Gate 1 must be resolved before generating execution plans. Visit /decision-gates to make your decision."
        )

    if gate and gate.decision != "proceed":
        raise HTTPException(
            status_code=409,
            detail=f"Cannot generate plans: gate resolved as '{gate.decision}'. Only 'proceed' allows plan generation."
        )

    options = await runner.generate_execution_options(project)
    return options
```

**Warning signs:**
- 500 errors in logs for plan generation
- Frontend shows generic error instead of "resolve gate first"
- No clear path for founder to unblock themselves

### Pitfall 3: Confidence Indicators Don't Update After Edits

**What goes wrong:** Founder edits "Problem Statement" section, confidence still shows "Needs depth"

**Why it happens:** Confidence scores stored statically, not recalculated on edit

**How to avoid:**
```python
# BAD: Store confidence once, never update
async def create_idea_brief(session):
    brief = await runner.generate_idea_brief(session.answers)
    # Confidence set once
    brief["confidence_scores"] = calculate_confidence(session.answers)
    return brief

# GOOD: Recalculate confidence on inline edit
async def update_brief_section(artifact_id, section_key, new_content):
    artifact = await get_artifact(artifact_id)

    # Update content
    artifact.content[section_key] = new_content

    # Recalculate confidence for edited section
    # LLM evaluates: "Is this content deep enough? Clear enough?"
    new_confidence = await runner.assess_section_confidence(
        section_key=section_key,
        content=new_content
    )

    artifact.content["confidence_scores"][section_key] = new_confidence
    flag_modified(artifact, "content")

    await commit()
```

**Warning signs:**
- Confidence indicators stale after edits
- No visual feedback that edit improved section quality
- Founder unsure if edits helped

### Pitfall 4: Decision Gate Modal Doesn't Show Brief Context

**What goes wrong:** Modal shows Proceed/Narrow/Pivot/Park options, but founder can't see the brief to decide

**Why it happens:** Modal designed in isolation, doesn't surface relevant context

**How to avoid:**
```tsx
// BAD: Modal only shows decision options
<DecisionGateModal
  options={GATE_OPTIONS}
  onDecide={handleDecision}
/>

// GOOD: Modal shows brief summary + options
<DecisionGateModal
  brief={ideaBrief}  // Current brief visible
  options={GATE_OPTIONS}
  onDecide={handleDecision}
>
  {/* Brief summary in modal header */}
  <div className="mb-6 p-4 bg-white/5 rounded-lg">
    <h4 className="text-sm font-semibold mb-2">Your Current Brief</h4>
    <div className="text-xs text-muted-foreground space-y-1">
      <p><strong>Problem:</strong> {brief.problem_statement.slice(0, 100)}...</p>
      <p><strong>Target:</strong> {brief.target_user.slice(0, 100)}...</p>
      <p><strong>Value:</strong> {brief.value_prop.slice(0, 100)}...</p>
    </div>
    <a href={`/project/${projectId}/brief`} className="text-xs text-brand mt-2 inline-block">
      View full brief →
    </a>
  </div>
</DecisionGateModal>
```

**Warning signs:**
- Founders ask "how do I see the brief?"
- Decision made without context (then regretted)
- Support tickets about "what am I deciding on?"

### Pitfall 5: Comparison Table Overload

**What goes wrong:** Table has 15 rows (features, risks, costs, timelines, tech stack, testing, etc.), founder overwhelmed

**Why it happens:** Trying to show "everything" in one table

**How to avoid:**
```tsx
// BAD: 15-row comparison table
const COMPARISON_ROWS = [
  "time_to_ship", "engineering_cost", "risk_level", "scope_coverage",
  "tech_stack", "testing_approach", "deployment", "monitoring",
  "team_size", "skill_requirements", "maintenance_burden",
  "scalability", "security", "compliance", "migration_path"
];

// GOOD: 4 critical rows in table + details in cards
const COMPARISON_ROWS = [
  { key: "time_to_ship", label: "Time to Ship" },
  { key: "engineering_cost", label: "Engineering Cost" },
  { key: "risk_level", label: "Risk Level" },
  { key: "scope_coverage", label: "Scope Coverage" },
];

// Other details (tech stack, testing, etc.) in expandable option cards below
```

**Warning signs:**
- Horizontal scroll on desktop
- Founder skips table, just picks first option
- No clear "winner" emerges from comparison

### Pitfall 6: Narrow/Pivot Text Field Too Small

**What goes wrong:** Founder writes 3 paragraphs about pivot direction, text field only shows 1 line

**Why it happens:** Text input used instead of textarea

**How to avoid:**
```tsx
// BAD: Single-line input for complex edits
<input
  type="text"
  placeholder="Describe how to narrow..."
  value={narrowText}
  onChange={e => setNarrowText(e.target.value)}
/>

// GOOD: Multi-line textarea with guidance
<div className="space-y-2">
  <label className="text-sm font-semibold">
    How should we narrow the scope?
  </label>
  <p className="text-xs text-muted-foreground">
    Be specific: What are we cutting? What are we keeping?
  </p>
  <Textarea
    value={narrowText}
    onChange={e => setNarrowText(e.target.value)}
    placeholder="E.g., Focus only on small businesses (10-50 employees) instead of all companies. Cut the mobile app for now, web-only MVP."
    rows={6}
    className="w-full"
  />
  <p className="text-xs text-gray-500">
    The more detail you provide, the better we can update your brief.
  </p>
</div>
```

**Warning signs:**
- Vague narrow/pivot descriptions ("make it smaller")
- LLM can't generate meaningful updates
- Founder frustrated by poor regeneration quality

## Code Examples

Verified patterns from official sources:

### LangGraph Conditional Edge for Gate Routing

```python
# Source: https://docs.langchain.com/oss/python/langgraph/graph-api
from langgraph.graph import StateGraph, END

def route_decision_gate(state: dict) -> str:
    """Route based on decision gate status and decision."""
    gate = state.get("current_gate")

    if not gate or gate["status"] != "decided":
        return "wait"

    # Map decision to next node
    decision_map = {
        "proceed": "generate_execution_plans",
        "narrow": "update_brief_narrow",
        "pivot": "update_brief_pivot",
        "park": "archive_project",
    }

    return decision_map.get(gate["decision"], "wait")

# Build graph
graph = StateGraph()
graph.add_node("check_gate", check_decision_gate_exists)
graph.add_node("wait", wait_for_gate_decision)
graph.add_node("generate_execution_plans", generate_plans_node)
graph.add_node("update_brief_narrow", narrow_brief_node)
graph.add_node("update_brief_pivot", pivot_brief_node)
graph.add_node("archive_project", park_project_node)

# Conditional routing
graph.add_conditional_edges(
    "check_gate",
    route_decision_gate,
    {
        "wait": "wait",
        "generate_execution_plans": "generate_execution_plans",
        "update_brief_narrow": "update_brief_narrow",
        "update_brief_pivot": "update_brief_pivot",
        "archive_project": "archive_project",
    }
)

graph.set_entry_point("check_gate")
```

### Anthropic Structured Output for Execution Options

```python
# Source: https://platform.claude.com/docs/en/build-with-claude/structured-outputs
from anthropic import Anthropic
from pydantic import BaseModel, Field

class ExecutionOption(BaseModel):
    """Single execution plan option."""
    id: str
    name: str
    is_recommended: bool
    time_to_ship: str = Field(description="E.g., '6-8 weeks'")
    engineering_cost: str = Field(description="E.g., 'Medium (2-3 engineers)'")
    risk_level: str = Field(description="'low' | 'medium' | 'high'")
    scope_coverage: int = Field(ge=0, le=100, description="% of brief scope covered")
    pros: list[str] = Field(min_length=2, max_length=5)
    cons: list[str] = Field(min_length=2, max_length=5)
    technical_approach: str = Field(description="1-2 sentence summary")

class ExecutionPlanOptions(BaseModel):
    """2-3 execution plan options with recommendation."""
    options: list[ExecutionOption] = Field(min_length=2, max_length=3)
    recommended_id: str

async def generate_execution_options(brief: dict) -> ExecutionPlanOptions:
    """Generate 2-3 execution plan options from idea brief."""
    client = Anthropic(api_key=settings.anthropic_api_key)

    prompt = f"""Based on this Idea Brief, generate 2-3 execution plan options.

Brief:
- Problem: {brief["problem_statement"]}
- Target User: {brief["target_user"]}
- Value Prop: {brief["value_prop"]}
- Constraints: {", ".join(brief["key_constraints"])}

Generate options that trade off:
1. Speed vs completeness (fast MVP vs full vision)
2. Risk vs innovation (proven tech vs cutting-edge)
3. Scope vs quality (breadth vs depth)

Make one option "recommended" based on constraints and risks.

For each option:
- Name it clearly (e.g., "Fast MVP", "Full-Featured Launch", "Hybrid Approach")
- Estimate time_to_ship realistically (weeks/months)
- Assess engineering_cost (Small/Medium/Large with team size)
- Evaluate risk_level (low/medium/high)
- Calculate scope_coverage (% of brief scope delivered)
- List 2-5 pros and cons
- Summarize technical_approach in 1-2 sentences
"""

    response = client.messages.create(
        model="claude-opus-4-20250514",
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
        response_format={
            "type": "json_schema",
            "json_schema": ExecutionPlanOptions.model_json_schema()
        }
    )

    data = json.loads(response.content[0].text)
    return ExecutionPlanOptions.model_validate(data)
```

### shadcn Dialog Fullscreen Modal

```tsx
// Source: https://ui.shadcn.com/docs/components/radix/dialog
"use client";

import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";

export function FullScreenGateModal({ isOpen, onClose, children }) {
  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-7xl h-screen max-h-screen p-0 gap-0">
        <DialogHeader className="p-8 pb-6 border-b">
          <DialogTitle className="text-3xl font-display">
            Critical Decision Point
          </DialogTitle>
        </DialogHeader>

        <div className="flex-1 overflow-y-auto">
          {children}
        </div>
      </DialogContent>
    </Dialog>
  );
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Manual if/else routing | LangGraph conditional edges | 2024-2025 (LangGraph maturity) | Explicit graph structure, visual debugging, easier testing |
| Static forms | Adaptive LLM-driven questions | 2024-2025 (conversational AI) | Fewer redundant questions, higher completion rates |
| Automatic stage advancement | Decision gates with manual resolution | Product decision (Phase 2) | Founder control, prevents accidental progression |
| Single execution plan | 2-3 options with tradeoff comparison | Product pattern (informed choice) | Reduces regret, founder owns decision |
| Hidden tier-gated features | Visible with upgrade prompts | Phase 4 pattern | Higher upgrade conversion, feature awareness |

**Deprecated/outdated:**
- **Automatic progression after exit criteria:** Gates require explicit Proceed decision (even if all criteria met)
- **Pre-selecting recommended option:** Show recommendation clearly (badge + border), but require active selection
- **Blocking gate without context:** Modal must show brief summary so founder can make informed decision

## Open Questions

1. **Question Redundancy Check: LLM Call or Heuristic?**
   - What we know: Editing Q2 answer may make Q3 redundant
   - What's unclear: LLM call for every edit (slow, costly) vs heuristic rules (fast, less accurate)?
   - Recommendation: Start with heuristic (keyword overlap, topic similarity) + manual override ("Skip this question" button). Add LLM redundancy check in Phase 9+ if heuristics miss cases. Measure: false positive rate (good questions skipped) vs false negative rate (redundant questions shown).

2. **Confidence Scoring: Section-Level or Field-Level?**
   - What we know: Idea Brief has 9 sections, each with confidence indicator
   - What's unclear: Score entire "Problem Statement" section, or individual fields within it?
   - Recommendation: Section-level for MVP (simpler UI). Each section gets one badge: "Strong" / "Moderate" / "Needs depth". Field-level granularity can come later if founders ask "which part of this section needs work?"

3. **Deep Research Button: Stub with 402 or Hide Completely?**
   - What we know: Phase 8 stubs Deep Research with 402 (payment required)
   - What's unclear: Show button but return 402, or hide button entirely for non-eligible tiers?
   - Recommendation: Show button, return 402 with "Available in CTO tier" message. Visibility drives awareness (upgrade funnel), 402 is semantically correct (resource exists but requires payment).

4. **Execution Plan Regeneration: Full Regenerate or Adjust?**
   - What we know: "Generate different options" button lets founder regenerate plans
   - What's unclear: Full regeneration (3 new options), or "adjust" (tweak current options based on feedback)?
   - Recommendation: Full regeneration for MVP (simpler to implement, clearer UX). Add "Why didn't you like these?" feedback field before regenerating, pass to LLM for context. Prevents infinite regeneration loop.

## Sources

### Primary (HIGH confidence)

- [LangGraph Graph API Documentation](https://docs.langchain.com/oss/python/langgraph/graph-api) — Conditional edges, routing patterns
- [LangGraph Memory Overview](https://docs.langchain.com/oss/python/langgraph/memory) — State management, checkpoints
- [Anthropic Structured Outputs](https://platform.claude.com/docs/en/build-with-claude/structured-outputs) — Guaranteed JSON schema compliance
- [shadcn/ui Dialog Component](https://ui.shadcn.com/docs/components/radix/dialog) — Full-screen modal patterns
- [shadcn/ui Collapsible Component](https://ui.shadcn.com/docs/components/radix/collapsible) — Expandable sections
- [shadcn/ui Card Component](https://ui.shadcn.com/docs/components/radix/card) — Card styling
- Existing codebase:
  - `backend/app/db/models/decision_gate.py` — Gate model with JSONB context
  - `backend/app/domain/gates.py` — Gate resolution logic
  - `backend/app/db/models/artifact.py` — JSONB versioning pattern
  - `backend/app/services/onboarding_service.py` — Adaptive question patterns (Phase 4)

### Secondary (MEDIUM confidence)

- [LangGraph Conditional Edges Router Pattern Guide](https://langchain-tutorials.github.io/langgraph-conditional-edges-router-pattern-guide/) — Router implementation examples
- [Modal UX Design Best Practices 2026](https://userpilot.com/blog/modal-ux-design/) — Full-screen modal usage, when to use
- [Mastering Modal UX](https://www.eleken.co/blog-posts/modal-ux) — Decision modal patterns, exit options
- [Shadcn UI Best Practices for 2026](https://medium.com/write-a-catalyst/shadcn-ui-best-practices-for-2026-444efd204f44) — Component composition, accessibility
- [shadcn Card Collapsible Pattern](https://www.shadcn.io/patterns/collapsible-card-1) — Expandable card implementation
- [React Hook Form Multi-Step Tutorial](https://www.buildwithmatija.com/blog/master-multi-step-forms-build-a-dynamic-react-form-in-6-simple-steps) — Back navigation with state preservation

### Tertiary (LOW confidence - requires verification)

- [LangGraph Adaptive RAG](https://langchain-ai.github.io/langgraph/tutorials/rag/langgraph_adaptive_rag_local/) — Adaptive routing patterns
- [Building Multi-Step Forms in React](https://makerkit.dev/blog/tutorials/multi-step-forms-reactjs) — Form state management
- [Comparison Table UI Examples](https://www.patterns.dev/react/table-patterns/) — Data table patterns

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — All libraries already installed, LangGraph conditional edges verified in official docs
- Architecture: HIGH — Patterns verified in existing codebase (gates.py, Artifact model, onboarding_service.py) + LangGraph/shadcn official docs
- Pitfalls: MEDIUM-HIGH — Regeneration issues derived from Phase 4 research, 409 enforcement from REST best practices, modal context from UX research

**Research date:** 2026-02-17
**Valid until:** 2026-03-17 (30 days — LangGraph patterns stable, shadcn/ui actively maintained)

---

## Sources

- [Memory overview - LangChain](https://docs.langchain.com/oss/python/langgraph/memory)
- [LangGraph Explained (2026 Edition)](https://medium.com/@dewasheesh.rana/langgraph-explained-2026-edition-ea8f725abff3)
- [Building Multi-Step Forms with React](https://makerkit.dev/blog/tutorials/multi-step-forms-reactjs)
- [React Hook Form Multi-Step Tutorial](https://www.buildwithmatija.com/blog/master-multi-step-forms-build-a-dynamic-react-form-in-6-simple-steps)
- [Framer Blog: Shimmer Effect Techniques](https://www.framer.com/blog/shimmer-effect/)
- [Improve React UX with skeleton UIs](https://blog.logrocket.com/improve-react-ux-skeleton-ui/)
- [Mastering the Stage-Gate Process](https://cerri.com/mastering-the-stage-gate-process-a-comprehensive-guide-from-a-to-z/)
- [State Machine Design Pattern](https://www.linkedin.com/pulse/state-machine-design-pattern-concepts-examples-python-sajad-rahimi)
- [shadcn UI: Complete Guide (2026)](https://designrevision.com/blog/shadcn-ui-guide)
- [Shadcn UI Best Practices for 2026](https://medium.com/write-a-catalyst/shadcn-ui-best-practices-for-2026-444efd204f44)
- [LangGraph Conditional Edges Router Pattern Guide](https://langchain-tutorials.github.io/langgraph-conditional-edges-router-pattern-guide/)
- [Modal UX design: Patterns, examples, and best practices](https://blog.logrocket.com/ux-design/modal-ux-design-patterns-examples-best-practices/)
- [shadcn/ui Card Collapsible](https://www.shadcn.io/patterns/collapsible-card-1)
- [LangGraph Graph API overview](https://docs.langchain.com/oss/python/langgraph/graph-api)
