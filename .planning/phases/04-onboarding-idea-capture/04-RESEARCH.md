# Phase 4: Onboarding & Idea Capture - Research

**Researched:** 2026-02-16
**Domain:** LLM-driven conversational onboarding, dynamic question generation, structured output, tier-dependent features, session resumption
**Confidence:** HIGH

## Summary

Phase 4 implements a dynamic LLM-tailored onboarding flow where founders describe their startup idea, answer adaptive questions (5-7, one at a time), and receive a tier-dependent Thesis Snapshot. The phase leverages Anthropic's Structured Outputs (November 2025) for guaranteed JSON schema compliance, React conversational form patterns for engaging UX, and PostgreSQL JSONB for flexible session state storage.

The architecture follows established patterns: Claude's `with_structured_output()` for reliable question/brief generation, PostgreSQL JSONB for resumable sessions (no expiration), tier-gated sections in the Thesis Snapshot (Bootstrapper gets core fields, Partner adds business fields, CTO gets full strategic analysis), and inline editing with canonical state management (edits override LLM output).

**Primary recommendation:** Use Anthropic Structured Outputs with Pydantic models for question generation and Thesis Snapshot creation. Store onboarding sessions as JSONB in a new `onboarding_sessions` table with `clerk_user_id` for isolation. Implement one-question-at-a-time conversational UI with skeleton shimmer loading states. Use tier-based content filtering for Thesis Snapshot sections. Support multiple concurrent sessions per tier (Bootstrapper: 1, Partner: 3, CTO: unlimited).

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### Idea entry experience
- One-liner + smart expand: founder types a short pitch, if < 10 words prompt for more detail, otherwise go straight to question generation
- Placeholder copy uses inclusive "we" language (e.g., "What are we building?")
- Dedicated onboarding page — full-screen focused flow, no sidebar or dashboard chrome
- Clean, minimal, single-purpose page

#### Question flow & interaction
- One question at a time, conversational feel
- LLM adapts questions based on previous answers — if a prior answer already covers what a question would ask, rethink/skip that question to avoid redundancy
- Previous Q&A pairs remain visible above (scroll back), founder can click to edit any previous answer
- Editing a previous answer may trigger question regeneration for subsequent questions
- Mixed input formats per question: LLM decides whether each question gets free text, multiple choice, or short text based on question type
- Skeleton shimmer loading state while LLM generates next question

#### Thesis Snapshot output
- Hybrid presentation: card summary at top for quick scan, expandable to full document view for detail
- Both inline editing and full regeneration: founder can edit sections directly OR go back to re-answer questions
- Inline edits become the canonical version
- Tier-dependent sections:
  - Bootstrapper (core): Problem, Target User, Value Prop, Key Constraint
  - Partner (+ business): adds Differentiation, Monetization Hypothesis
  - CTO (full strategic): adds Assumptions, Risks, Smallest Viable Experiment

#### Resumption & progress
- Choice screen on return: "Welcome back! Continue where you left off, or start fresh?"
- Progress bar visible during onboarding (visual bar filling up as they answer)
- Sessions never expire — founder can return weeks later and continue
- Multiple concurrent onboarding sessions are tier-dependent:
  - Bootstrapper: 1 active session
  - Partner: 3 active sessions
  - CTO: unlimited active sessions

### Claude's Discretion
- Tone of the Thesis Snapshot (Claude picks best tone for non-technical founders)
- Exact progress bar behavior given variable question count (5-7 questions)
- Question regeneration strategy when previous answers are edited
- Smart expand threshold tuning (currently < 10 words)

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope

</user_constraints>

## Standard Stack

### Core Backend
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| anthropic | 0.40.0+ | Claude API with Structured Outputs | Already installed, native structured output support (Nov 2025), guaranteed JSON schema compliance |
| langchain-anthropic | 0.3.0+ | ChatAnthropic wrapper | Already installed, integrates with usage tracking |
| Pydantic | 2.10.0+ | Schema definition for structured outputs | Already installed, type-safe validation, direct integration with Anthropic SDK |
| SQLAlchemy | 2.0.0+ | Async ORM for PostgreSQL | Already installed, JSONB support for flexible session storage |

### Core Frontend
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| React 19 | 19.x | Component framework | Already installed, modern hooks (useState, useEffect) |
| Next.js 15 | 15.0.0+ | App Router, server actions | Already installed, force-dynamic for real-time data |
| Tailwind CSS | 4.0.0+ | Utility-first styling | Already installed, rapid UI development |
| Framer Motion | 12.34.0 | Animations for skeleton shimmer | Already installed, smooth transitions |

### Supporting Libraries
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| react-loading-skeleton | 3.5.0+ (NEW) | Skeleton shimmer components | Loading states during LLM question generation |
| contentEditable (native) | Browser API | Inline editing | Thesis Snapshot section editing |
| clsx + tailwind-merge | 2.1.0+ (installed) | Conditional classes | Dynamic UI state (loading, editing, expanded) |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Anthropic Structured Outputs | LangChain PydanticOutputParser | Structured Outputs guarantees zero JSON parsing errors, PydanticOutputParser requires retry logic |
| JSONB session storage | Redis ephemeral storage | JSONB persists forever (sessions never expire requirement), Redis has TTL |
| Dedicated onboarding table | Project.metadata JSONB | Separate table allows multiple concurrent sessions, cleaner schema |
| contentEditable native API | React rich text library (Draft.js, Slate) | contentEditable is lightweight for simple inline editing, libraries add complexity |

**Installation:**
```bash
# Backend (no new dependencies needed)
cd backend
pip install -e ".[dev]"  # All dependencies already in pyproject.toml

# Frontend (add react-loading-skeleton)
cd frontend
npm install react-loading-skeleton
```

## Architecture Patterns

### Recommended Project Structure

```
backend/app/
├── api/routes/
│   └── onboarding.py           # NEW: POST /start, POST /answer, GET /resume, POST /finalize
├── agent/
│   ├── runner.py               # EXTEND: Add generate_questions(), generate_thesis_snapshot()
│   ├── runner_real.py          # EXTEND: Implement new methods with Anthropic Structured Outputs
│   └── runner_fake.py          # EXTEND: Add scenario data for onboarding flows
├── db/models/
│   ├── onboarding_session.py   # NEW: OnboardingSession table
│   └── user_settings.py        # EXISTING: Already has tier FK for feature gating
└── schemas/
    └── onboarding.py           # NEW: Pydantic models for API contracts

frontend/src/
├── app/(dashboard)/
│   └── onboarding/
│       └── page.tsx            # NEW: Dedicated onboarding page (full-screen)
├── components/onboarding/
│   ├── IdeaInput.tsx           # NEW: Initial idea entry with smart expand
│   ├── ConversationalQuestion.tsx  # NEW: One-question-at-a-time UI
│   ├── QuestionHistory.tsx     # NEW: Scrollable previous Q&A with edit
│   ├── ThesisSnapshot.tsx      # NEW: Hybrid card + document view
│   └── ProgressBar.tsx         # NEW: Visual progress indicator
└── hooks/
    └── useOnboarding.ts        # NEW: Session state management
```

### Pattern 1: Anthropic Structured Outputs with Pydantic

**What:** Guaranteed JSON schema compliance for LLM outputs using Pydantic models

**When to use:** Any LLM call requiring structured data (question generation, Thesis Snapshot creation)

**Example:**
```python
# Source: Anthropic Structured Outputs docs (Nov 2025)
from anthropic import Anthropic
from pydantic import BaseModel, Field

class OnboardingQuestion(BaseModel):
    """Single adaptive question for founder."""
    id: str = Field(description="Unique question identifier (q1, q2, etc.)")
    text: str = Field(description="Question text in conversational tone")
    input_type: str = Field(description="Input type: 'text' | 'textarea' | 'multiple_choice'")
    required: bool = Field(description="Whether answer is required")
    options: list[str] | None = Field(default=None, description="Multiple choice options if applicable")
    follow_up_hint: str | None = Field(default=None, description="Optional hint for elaboration")

class QuestionSet(BaseModel):
    """Set of 5-7 adaptive questions."""
    questions: list[OnboardingQuestion] = Field(min_length=5, max_length=7)
    total_count: int = Field(description="Total questions in set")

async def generate_questions(idea: str, previous_answers: dict) -> QuestionSet:
    """Generate adaptive questions based on idea and prior answers."""
    client = Anthropic(api_key=settings.anthropic_api_key)

    prompt = f"""You are a co-founder helping a founder refine their startup idea.

Idea: {idea}

Previous answers: {previous_answers}

Generate 5-7 adaptive questions that:
1. Build on what you already know (don't ask what they've answered)
2. Cover: target user, problem, value prop, key constraint, differentiation (if not covered)
3. Use "we" language (e.g., "Who are we building this for?")
4. Feel conversational, not like a form

For each question, decide the best input type:
- 'text' for short answers (1-2 sentences)
- 'textarea' for detailed explanations
- 'multiple_choice' for categorical choices (provide 3-5 options)
"""

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}],
        # CRITICAL: Structured output guarantee
        response_format={
            "type": "json_schema",
            "json_schema": QuestionSet.model_json_schema()
        }
    )

    # Parse guaranteed-valid JSON
    data = json.loads(response.content[0].text)
    return QuestionSet.model_validate(data)
```

**Why this works:**
- Zero JSON parsing errors (Anthropic guarantees schema compliance)
- Pydantic validation ensures type safety and business rules
- No retry logic needed for malformed outputs
- Direct integration with existing usage tracking (ChatAnthropic wrapper)

### Pattern 2: JSONB Session Storage for Resumption

**What:** Store flexible onboarding state in PostgreSQL JSONB column for infinite resumption

**When to use:** When sessions have variable structure and must persist indefinitely

**Example:**
```python
# Source: PostgreSQL JSONB patterns + existing project patterns
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON, Boolean
from sqlalchemy.dialects.postgresql import UUID
import uuid

class OnboardingSession(Base):
    __tablename__ = "onboarding_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    clerk_user_id = Column(String(255), nullable=False, index=True)

    # Journey tracking
    status = Column(String(20), nullable=False, default="in_progress")  # in_progress, completed, abandoned
    current_question_index = Column(Integer, nullable=False, default=0)
    total_questions = Column(Integer, nullable=False)

    # Content
    idea_text = Column(Text, nullable=False)
    questions = Column(JSON, nullable=False)  # QuestionSet as JSONB
    answers = Column(JSON, nullable=False, default=dict)  # {question_id: answer_text}
    thesis_snapshot = Column(JSON, nullable=True)  # Generated brief

    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Tier enforcement (checked at creation time)
    # No FK to avoid complexity, tier limits enforced in business logic

# Resumption pattern
async def get_or_create_session(user_id: str, idea: str) -> OnboardingSession:
    """Get in-progress session or create new one."""
    factory = get_session_factory()

    async with factory() as session:
        # Check for existing in-progress session
        result = await session.execute(
            select(OnboardingSession)
            .where(
                OnboardingSession.clerk_user_id == user_id,
                OnboardingSession.status == "in_progress"
            )
            .order_by(OnboardingSession.created_at.desc())
        )
        existing = result.scalar_one_or_none()

        if existing:
            # Resume existing session
            return existing

        # Create new session
        questions = await generate_questions(idea, {})
        new_session = OnboardingSession(
            clerk_user_id=user_id,
            idea_text=idea,
            questions=questions.model_dump(),
            total_questions=questions.total_count,
            answers={},
        )
        session.add(new_session)
        await session.commit()
        await session.refresh(new_session)
        return new_session
```

**Why JSONB:**
- Sessions never expire (stored forever)
- Variable structure (questions adapt based on answers)
- Fast query by `clerk_user_id` with GIN index
- No schema migrations for question format changes

### Pattern 3: Tier-Based Content Filtering

**What:** Generate full Thesis Snapshot, filter visible sections based on user's plan tier

**When to use:** When output structure is fixed but visibility is tier-dependent

**Example:**
```python
# Source: Existing llm_config.py pattern + research
from pydantic import BaseModel, Field

class ThesisSnapshot(BaseModel):
    """Complete thesis with tier-dependent visibility."""
    # Core (Bootstrapper tier)
    problem: str = Field(description="Problem statement")
    target_user: str = Field(description="Target user persona")
    value_prop: str = Field(description="Value proposition")
    key_constraint: str = Field(description="Primary constraint (time/money/skills)")

    # Business (Partner tier+)
    differentiation: str | None = Field(default=None, description="Competitive differentiation")
    monetization_hypothesis: str | None = Field(default=None, description="Revenue model hypothesis")

    # Strategic (CTO tier)
    assumptions: list[str] | None = Field(default=None, description="Key assumptions to validate")
    risks: list[str] | None = Field(default=None, description="Identified risks")
    smallest_viable_experiment: str | None = Field(default=None, description="MVE recommendation")

async def generate_thesis_snapshot(
    session: OnboardingSession,
    user_settings: UserSettings
) -> ThesisSnapshot:
    """Generate full snapshot, return tier-filtered view."""
    # Generate FULL snapshot (all fields)
    client = Anthropic(api_key=settings.anthropic_api_key)

    prompt = f"""Analyze this startup idea and answers to create a Thesis Snapshot.

Idea: {session.idea_text}

Q&A:
{format_answers(session.questions, session.answers)}

Generate:
1. Problem statement (1-2 sentences)
2. Target user persona (specific, not generic)
3. Value proposition (clear differentiation)
4. Key constraint (time/money/skills - identify which matters most)
5. Differentiation (vs alternatives/status quo)
6. Monetization hypothesis (revenue model)
7. Assumptions (3-5 key assumptions to validate)
8. Risks (3-5 major risks)
9. Smallest Viable Experiment (what to build first to learn fastest)

Tone: Clear, actionable, non-technical. Written for a non-technical founder.
"""

    response = client.messages.create(
        model="claude-opus-4-20250514",  # Use Opus for strategic thinking
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
        response_format={
            "type": "json_schema",
            "json_schema": ThesisSnapshot.model_json_schema()
        }
    )

    data = json.loads(response.content[0].text)
    full_snapshot = ThesisSnapshot.model_validate(data)

    # Filter by tier
    tier_slug = user_settings.plan_tier.slug

    if tier_slug == "bootstrapper":
        # Core fields only
        return ThesisSnapshot(
            problem=full_snapshot.problem,
            target_user=full_snapshot.target_user,
            value_prop=full_snapshot.value_prop,
            key_constraint=full_snapshot.key_constraint,
            # Null out tier-gated fields
            differentiation=None,
            monetization_hypothesis=None,
            assumptions=None,
            risks=None,
            smallest_viable_experiment=None,
        )
    elif tier_slug == "partner":
        # Core + business fields
        return ThesisSnapshot(
            problem=full_snapshot.problem,
            target_user=full_snapshot.target_user,
            value_prop=full_snapshot.value_prop,
            key_constraint=full_snapshot.key_constraint,
            differentiation=full_snapshot.differentiation,
            monetization_hypothesis=full_snapshot.monetization_hypothesis,
            # Strategic fields still gated
            assumptions=None,
            risks=None,
            smallest_viable_experiment=None,
        )
    else:  # cto_scale
        # All fields visible
        return full_snapshot
```

**Why generate all, filter after:**
- LLM sees full context (better quality)
- Upsell opportunity (show "Upgrade to see Risks section")
- Easier to test (single generation path)
- Future tier changes don't require regeneration

### Pattern 4: Conversational One-Question-at-a-Time UI

**What:** React component that displays one question, scrolls to show history, allows editing previous answers

**When to use:** Guided flows where context matters and editing should be seamless

**Example:**
```tsx
// Source: Research on conversational forms + React patterns
"use client";

import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import Skeleton from "react-loading-skeleton";
import "react-loading-skeleton/dist/skeleton.css";

interface Question {
  id: string;
  text: string;
  input_type: "text" | "textarea" | "multiple_choice";
  required: boolean;
  options?: string[];
  follow_up_hint?: string;
}

interface ConversationalQuestionProps {
  question: Question;
  currentAnswer: string;
  onAnswer: (questionId: string, answer: string) => void;
  isLoading: boolean;
}

export function ConversationalQuestion({
  question,
  currentAnswer,
  onAnswer,
  isLoading,
}: ConversationalQuestionProps) {
  const [value, setValue] = useState(currentAnswer);

  // Show skeleton while next question loads
  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton height={30} width="80%" />
        <Skeleton height={100} />
      </div>
    );
  }

  return (
    <AnimatePresence mode="wait">
      <motion.div
        key={question.id}
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -20 }}
        transition={{ duration: 0.3 }}
        className="space-y-4"
      >
        {/* Question text with "we" language */}
        <h2 className="text-2xl font-medium text-white">
          {question.text}
        </h2>

        {question.follow_up_hint && (
          <p className="text-sm text-gray-400">{question.follow_up_hint}</p>
        )}

        {/* Dynamic input based on question type */}
        {question.input_type === "textarea" ? (
          <textarea
            value={value}
            onChange={(e) => setValue(e.target.value)}
            onBlur={() => onAnswer(question.id, value)}
            placeholder="Tell us more..."
            className="w-full h-32 px-4 py-3 bg-white/5 border border-white/10 rounded-lg text-white placeholder:text-gray-500 focus:outline-none focus:border-white/30"
            autoFocus
          />
        ) : question.input_type === "multiple_choice" ? (
          <div className="space-y-2">
            {question.options?.map((option) => (
              <button
                key={option}
                onClick={() => {
                  setValue(option);
                  onAnswer(question.id, option);
                }}
                className={`w-full px-4 py-3 text-left rounded-lg border transition-colors ${
                  value === option
                    ? "bg-white/10 border-white/30 text-white"
                    : "bg-white/5 border-white/10 text-gray-300 hover:bg-white/10"
                }`}
              >
                {option}
              </button>
            ))}
          </div>
        ) : (
          <input
            type="text"
            value={value}
            onChange={(e) => setValue(e.target.value)}
            onBlur={() => onAnswer(question.id, value)}
            placeholder="Your answer..."
            className="w-full px-4 py-3 bg-white/5 border border-white/10 rounded-lg text-white placeholder:text-gray-500 focus:outline-none focus:border-white/30"
            autoFocus
          />
        )}
      </motion.div>
    </AnimatePresence>
  );
}
```

**Why one-at-a-time:**
- Reduces cognitive load (founder focuses on single question)
- Conversational feel (like talking to co-founder, not filling form)
- Skeleton shimmer manages expectations during LLM thinking time
- Framer Motion provides smooth transitions between questions

### Pattern 5: Inline Editing with Canonical State

**What:** contentEditable for inline text editing, edits become source of truth

**When to use:** When users need quick edits without losing context or triggering full regeneration

**Example:**
```tsx
// Source: Research on inline editing + React patterns
"use client";

import { useState, useRef, useEffect } from "react";

interface EditableSectionProps {
  title: string;
  content: string;
  onSave: (newContent: string) => void;
}

export function EditableSection({ title, content, onSave }: EditableSectionProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [localContent, setLocalContent] = useState(content);
  const contentRef = useRef<HTMLDivElement>(null);

  // Update local state when prop changes (e.g., regeneration)
  useEffect(() => {
    setLocalContent(content);
  }, [content]);

  const handleBlur = () => {
    setIsEditing(false);
    const newContent = contentRef.current?.innerText || localContent;
    if (newContent !== content) {
      onSave(newContent);  // Persist edit as canonical version
    }
  };

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold text-white">{title}</h3>
        {!isEditing && (
          <button
            onClick={() => setIsEditing(true)}
            className="text-sm text-gray-400 hover:text-white transition-colors"
          >
            Edit
          </button>
        )}
      </div>

      <div
        ref={contentRef}
        contentEditable={isEditing}
        suppressContentEditableWarning
        onBlur={handleBlur}
        className={`p-4 rounded-lg border transition-colors ${
          isEditing
            ? "bg-white/10 border-white/30 outline-none"
            : "bg-white/5 border-white/10"
        }`}
        dangerouslySetInnerHTML={{ __html: localContent }}
      />

      {isEditing && (
        <p className="text-xs text-gray-500">
          Click outside to save changes
        </p>
      )}
    </div>
  );
}
```

**Why contentEditable over rich text library:**
- Lightweight (no library needed)
- Fast inline editing for simple text
- Preserves formatting (line breaks, basic HTML)
- Edits are canonical (no "draft" state complexity)

### Anti-Patterns to Avoid

- **Static question list:** LLM should adapt questions based on previous answers, not follow rigid script
- **Expired sessions:** Requirement is "sessions never expire" — don't add TTL to JSONB or Redis keys
- **Storing only Bootstrapper fields:** Generate full Thesis Snapshot, filter on read (enables upsell + future tier changes)
- **Full page reload on edit:** Use inline editing with local state, only persist on blur
- **Blocking UI during LLM calls:** Always show skeleton shimmer during question generation, never blank screen
- **403 for tier-gated sections:** Show section title with "Upgrade to unlock" message, not HTTP error

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Structured LLM output | Custom JSON parsing + retry logic | Anthropic Structured Outputs + Pydantic | Guaranteed schema compliance, zero parsing errors, handles edge cases (nested objects, enums, field validation) |
| Session storage | Redis with TTL or custom session service | PostgreSQL JSONB with no expiration | Sessions never expire (requirement), JSONB handles variable structure, PostgreSQL already in stack |
| Loading skeletons | Custom shimmer CSS animations | react-loading-skeleton | Handles SSR, matches layout automatically, maintains during re-renders |
| Progress calculation | Manual tracking of completed questions | Derived from `current_question_index / total_questions` | Single source of truth, no desync between state and UI |
| Tier enforcement | Multiple database queries or complex logic | Single query with plan_tier FK + in-memory filtering | Leverages existing user_settings.plan_tier relationship, fast |

**Key insight:** Structured Outputs (Nov 2025) eliminates entire class of LLM reliability problems. Previously, handling malformed JSON required retry loops, fallback parsing, and error recovery. Now it's guaranteed correct, first try.

## Common Pitfalls

### Pitfall 1: Question Regeneration Cascade

**What goes wrong:** User edits answer to Q2, triggering regeneration of Q3-Q7, losing all subsequent answers

**Why it happens:** Naive approach regenerates ALL questions after edited one, discarding state

**How to avoid:**
```python
# BAD: Regenerate everything after edit
async def handle_answer_edit(session_id: str, question_id: str, new_answer: str):
    session = await get_session(session_id)
    # Clear ALL answers after this one
    session.answers = {k: v for k, v in session.answers.items() if k <= question_id}
    # Regenerate ALL subsequent questions
    new_questions = await generate_questions(session.idea_text, session.answers)
    session.questions = new_questions  # ← Loses Q4-Q7 if user edited Q2

# GOOD: Selective regeneration with answer preservation
async def handle_answer_edit(session_id: str, question_id: str, new_answer: str):
    session = await get_session(session_id)
    session.answers[question_id] = new_answer

    # Check if edit makes subsequent questions redundant
    # E.g., if Q3 asks about target user and edit now covers it
    redundant = await check_redundancy(session.questions, session.answers)

    if redundant:
        # Only regenerate specific redundant questions, preserve others
        await regenerate_specific_questions(session, redundant_indices=redundant)
    else:
        # No regeneration needed, preserve all progress
        pass

    await session.commit()
```

**Warning signs:**
- Users complain about losing progress
- "I edited my answer and all my work disappeared"
- High abandonment rate after first edit

### Pitfall 2: Tier Limit Race Condition

**What goes wrong:** Bootstrapper creates 2 concurrent sessions by clicking "start" twice quickly

**Why it happens:** Tier limit check (max 1 session) happens before insert, allowing race

**How to avoid:**
```python
# BAD: Check-then-insert (race condition)
async def create_session(user_id: str, idea: str):
    count = await session.execute(
        select(func.count(OnboardingSession.id))
        .where(OnboardingSession.clerk_user_id == user_id, OnboardingSession.status == "in_progress")
    )
    if count.scalar() >= tier.max_onboarding_sessions:
        raise HTTPException(403, "Session limit reached")

    # Another request can insert here before this one commits
    new_session = OnboardingSession(...)
    session.add(new_session)

# GOOD: Database constraint + conflict handling
# In migration:
# CREATE UNIQUE INDEX idx_active_sessions_per_user
#   ON onboarding_sessions(clerk_user_id, status)
#   WHERE status = 'in_progress';

async def create_session(user_id: str, idea: str):
    user_settings = await get_or_create_user_settings(user_id)
    tier = user_settings.plan_tier

    # Count existing (for error message)
    count_result = await session.execute(
        select(func.count(OnboardingSession.id))
        .where(OnboardingSession.clerk_user_id == user_id, OnboardingSession.status == "in_progress")
    )
    count = count_result.scalar()

    if count >= tier.max_onboarding_sessions:
        raise HTTPException(
            403,
            f"Active session limit reached ({count}/{tier.max_onboarding_sessions}). Complete or abandon existing sessions."
        )

    try:
        new_session = OnboardingSession(...)
        session.add(new_session)
        await session.commit()
    except IntegrityError:
        # Race condition: another request created session simultaneously
        raise HTTPException(403, "Session limit reached")
```

**Warning signs:**
- Bootstrapper users with 2+ in_progress sessions
- IntegrityError in logs without handling
- Tier limits not enforced consistently

### Pitfall 3: Progress Bar Jumps with Variable Questions

**What goes wrong:** Progress bar shows 40% (2/5 complete), then jumps to 33% when LLM adds 6th question

**Why it happens:** Question count changes mid-session based on adaptive logic

**How to avoid:**
```python
# BAD: Calculate progress from dynamic question count
progress = (current_index / len(questions)) * 100  # ← Jumps when questions added

# GOOD: Fix question count at session start
class OnboardingSession(Base):
    total_questions = Column(Integer, nullable=False)  # Set once, never changes
    current_question_index = Column(Integer, nullable=False, default=0)

# Progress always based on initial total
progress = (session.current_question_index / session.total_questions) * 100  # ← Stable
```

**Alternative (if questions truly adapt):**
```python
# Show "About X% complete" with fuzzy ranges
if current_index < 2:
    progress_label = "Just getting started"
elif current_index < 4:
    progress_label = "About halfway there"
else:
    progress_label = "Almost done"
```

**Warning signs:**
- Progress bar moves backward
- "100% complete" but questions remain
- User confusion about how much is left

### Pitfall 4: Inline Edit Conflicts with contentEditable

**What goes wrong:** React tries to update DOM while user is typing, cursor jumps or content resets

**Why it happens:** React's virtual DOM conflicts with contentEditable's direct DOM manipulation

**How to avoid:**
```tsx
// BAD: Re-render contentEditable on every state update
<div contentEditable={true}>
  {content}  {/* ← React updates this, cursor jumps */}
</div>

// GOOD: Suppress React updates during editing
const [isEditing, setIsEditing] = useState(false);
const contentRef = useRef<HTMLDivElement>(null);

useEffect(() => {
  // Only update content when NOT editing
  if (!isEditing && contentRef.current) {
    contentRef.current.innerText = content;
  }
}, [content, isEditing]);

<div
  ref={contentRef}
  contentEditable={isEditing}
  suppressContentEditableWarning  // ← Critical for React 19
  onFocus={() => setIsEditing(true)}
  onBlur={() => {
    setIsEditing(false);
    onSave(contentRef.current?.innerText || "");
  }}
/>
```

**Warning signs:**
- Cursor jumps to start/end while typing
- Typed characters disappear
- "Warning: A component is changing an uncontrolled input to be controlled"

### Pitfall 5: Smart Expand Threshold Too Aggressive

**What goes wrong:** User types "Food delivery app", < 10 words triggers "Please elaborate", but idea is clear

**Why it happens:** Word count threshold doesn't account for clarity/completeness

**How to avoid:**
```python
# BAD: Hardcode word threshold
if len(idea.split()) < 10:
    return {"error": "Please elaborate", "min_words": 10}

# GOOD: LLM-based clarity check
async def validate_idea_clarity(idea: str) -> tuple[bool, str | None]:
    """Check if idea is clear enough to generate questions."""
    client = Anthropic(api_key=settings.anthropic_api_key)

    prompt = f"""Is this startup idea clear enough to ask targeted questions?

Idea: "{idea}"

Respond with JSON:
{{"clear": true/false, "reason": "why" or null}}

An idea is clear if it conveys:
- What product/service (doesn't need to be detailed)
- Who it's for (even if vague like "consumers" or "businesses")

Examples:
- "Food delivery app" → CLEAR (product + implied target)
- "An app" → UNCLEAR (no indication of what it does)
- "Help small businesses" → CLEAR (target + problem)
"""

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=128,
        messages=[{"role": "user", "content": prompt}]
    )

    data = json.loads(response.content[0].text)
    return data["clear"], data.get("reason")
```

**Warning signs:**
- Users frustrated by "elaborate" prompt for clear ideas
- Support tickets about "why can't I proceed?"
- High abandonment at idea entry step

### Pitfall 6: Missing Tier Upgrade Messaging

**What goes wrong:** Bootstrapper sees "Risks: (empty)" with no indication why

**Why it happens:** UI doesn't communicate that section is tier-gated

**How to avoid:**
```tsx
// BAD: Hide tier-gated sections completely
{tier !== "bootstrapper" && <RisksSection content={snapshot.risks} />}

// GOOD: Show locked sections with upgrade message
<div className="space-y-6">
  {/* Core sections visible to all */}
  <Section title="Problem" content={snapshot.problem} />
  <Section title="Target User" content={snapshot.target_user} />

  {/* Tier-gated with upgrade hint */}
  {snapshot.risks ? (
    <Section title="Risks" content={snapshot.risks} />
  ) : (
    <LockedSection
      title="Risks"
      description="Identify potential risks and mitigation strategies"
      ctaText="Upgrade to CTO plan"
      ctaLink="/pricing"
    />
  )}
</div>

function LockedSection({ title, description, ctaText, ctaLink }) {
  return (
    <div className="p-6 border border-white/10 rounded-lg bg-white/5 relative">
      <div className="absolute inset-0 backdrop-blur-sm bg-black/50 rounded-lg flex items-center justify-center">
        <div className="text-center space-y-4">
          <div className="inline-flex items-center justify-center w-12 h-12 bg-white/10 rounded-full">
            <LockIcon className="w-6 h-6 text-white" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-white">{title}</h3>
            <p className="text-sm text-gray-400 mt-1">{description}</p>
          </div>
          <a
            href={ctaLink}
            className="inline-flex px-4 py-2 bg-white text-black rounded-lg hover:bg-white/90 transition-colors"
          >
            {ctaText}
          </a>
        </div>
      </div>
      {/* Blurred preview content */}
      <div className="opacity-0">
        <h3 className="text-lg font-semibold text-white">{title}</h3>
        <p className="text-gray-400 mt-2">Lorem ipsum dolor sit amet...</p>
      </div>
    </div>
  );
}
```

**Warning signs:**
- Low upgrade conversion despite tier-gated features
- Users don't know features exist
- Support tickets asking "where are the risks?"

## Code Examples

Verified patterns from official sources:

### Anthropic Structured Outputs for Question Generation

```python
# Source: https://docs.anthropic.com/en/docs/build-with-claude/structured-outputs
from anthropic import Anthropic
from pydantic import BaseModel, Field

class OnboardingQuestion(BaseModel):
    id: str
    text: str
    input_type: str  # "text" | "textarea" | "multiple_choice"
    required: bool
    options: list[str] | None = None

class QuestionSet(BaseModel):
    questions: list[OnboardingQuestion] = Field(min_length=5, max_length=7)
    total_count: int

async def generate_onboarding_questions(idea: str, previous_answers: dict) -> QuestionSet:
    """Generate adaptive questions using Anthropic Structured Outputs."""
    client = Anthropic(api_key=settings.anthropic_api_key)

    # Build context from previous answers
    context = f"Idea: {idea}\n\nPrevious answers:\n"
    for q_id, answer in previous_answers.items():
        context += f"- {q_id}: {answer}\n"

    prompt = f"""{context}

Generate 5-7 adaptive onboarding questions that:
1. Build on what you already know (skip redundant questions)
2. Cover: target user, problem, value prop, key constraint, differentiation
3. Use "we" language (collaborative co-founder tone)
4. Choose appropriate input_type for each question
5. Mark critical questions as required=true

Make questions conversational, not interrogative. Examples:
- Good: "Who are we building this for?"
- Bad: "Please describe your target user segment in detail."
"""

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}],
        response_format={
            "type": "json_schema",
            "json_schema": QuestionSet.model_json_schema()
        }
    )

    # Guaranteed valid JSON, no try/except needed
    data = json.loads(response.content[0].text)
    return QuestionSet.model_validate(data)
```

### React Conversational Form with Skeleton Loading

```tsx
// Source: https://blog.logrocket.com/handling-react-loading-states-react-loading-skeleton/
"use client";

import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import Skeleton from "react-loading-skeleton";

interface OnboardingFlowProps {
  sessionId: string;
}

export function OnboardingFlow({ sessionId }: OnboardingFlowProps) {
  const [questions, setQuestions] = useState<Question[]>([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [isLoadingNext, setIsLoadingNext] = useState(false);

  // Load questions on mount
  useEffect(() => {
    async function loadSession() {
      const res = await fetch(`/api/onboarding/${sessionId}`);
      const data = await res.json();
      setQuestions(data.questions);
      setAnswers(data.answers);
      setCurrentIndex(data.current_question_index);
    }
    loadSession();
  }, [sessionId]);

  const handleAnswer = async (questionId: string, answer: string) => {
    // Update local state
    setAnswers({ ...answers, [questionId]: answer });

    // Persist answer
    await fetch(`/api/onboarding/${sessionId}/answer`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question_id: questionId, answer }),
    });

    // Move to next question
    if (currentIndex < questions.length - 1) {
      setIsLoadingNext(true);
      // Simulate LLM processing time
      setTimeout(() => {
        setCurrentIndex(currentIndex + 1);
        setIsLoadingNext(false);
      }, 800);
    }
  };

  const currentQuestion = questions[currentIndex];

  return (
    <div className="max-w-2xl mx-auto px-4 py-8 space-y-8">
      {/* Progress bar */}
      <div className="space-y-2">
        <div className="flex justify-between text-sm text-gray-400">
          <span>Question {currentIndex + 1} of {questions.length}</span>
          <span>{Math.round((currentIndex / questions.length) * 100)}%</span>
        </div>
        <div className="h-2 bg-white/10 rounded-full overflow-hidden">
          <motion.div
            className="h-full bg-gradient-to-r from-blue-500 to-purple-500"
            initial={{ width: 0 }}
            animate={{ width: `${(currentIndex / questions.length) * 100}%` }}
            transition={{ duration: 0.5 }}
          />
        </div>
      </div>

      {/* Question history (scrollable) */}
      <div className="space-y-4 opacity-60">
        {questions.slice(0, currentIndex).map((q, i) => (
          <div key={q.id} className="p-4 bg-white/5 rounded-lg">
            <p className="text-sm text-gray-400">{q.text}</p>
            <p className="text-white mt-2">{answers[q.id]}</p>
            <button
              onClick={() => setCurrentIndex(i)}
              className="text-xs text-gray-500 hover:text-white mt-2"
            >
              Edit
            </button>
          </div>
        ))}
      </div>

      {/* Current question or skeleton */}
      {isLoadingNext ? (
        <div className="space-y-4">
          <Skeleton height={40} />
          <Skeleton height={120} />
        </div>
      ) : (
        currentQuestion && (
          <ConversationalQuestion
            question={currentQuestion}
            currentAnswer={answers[currentQuestion.id] || ""}
            onAnswer={handleAnswer}
            isLoading={false}
          />
        )
      )}
    </div>
  );
}
```

### JSONB Session Storage with Tier Enforcement

```python
# Source: Existing project patterns + PostgreSQL JSONB best practices
from sqlalchemy import select, func, and_
from sqlalchemy.dialects.postgresql import insert

async def create_onboarding_session(
    user_id: str,
    idea: str
) -> OnboardingSession:
    """Create new onboarding session, respecting tier limits."""
    user_settings = await get_or_create_user_settings(user_id)
    tier = user_settings.plan_tier

    factory = get_session_factory()
    async with factory() as session:
        # Check tier limit for concurrent active sessions
        count_result = await session.execute(
            select(func.count(OnboardingSession.id))
            .where(
                OnboardingSession.clerk_user_id == user_id,
                OnboardingSession.status == "in_progress"
            )
        )
        count = count_result.scalar()

        # Tier limits from plan_tier table
        max_sessions = tier.max_onboarding_sessions  # bootstrapper: 1, partner: 3, cto: -1 (unlimited)

        if max_sessions != -1 and count >= max_sessions:
            raise HTTPException(
                status_code=403,
                detail=f"Active session limit reached ({count}/{max_sessions}). Complete or abandon existing sessions to start a new one."
            )

        # Generate initial questions
        questions = await generate_onboarding_questions(idea, {})

        # Create session with JSONB storage
        new_session = OnboardingSession(
            clerk_user_id=user_id,
            idea_text=idea,
            questions=questions.model_dump(),  # Pydantic → JSONB
            total_questions=questions.total_count,
            answers={},
            status="in_progress",
            current_question_index=0,
        )

        session.add(new_session)
        await session.commit()
        await session.refresh(new_session)

        return new_session
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| LangChain PydanticOutputParser | Anthropic Structured Outputs | Nov 2025 | Zero JSON errors, no retry logic needed, guaranteed schema compliance |
| Static form questions | LLM-adaptive question generation | 2024-2025 (conversational AI trend) | Better UX, fewer redundant questions, higher completion rates |
| Redis session storage with TTL | PostgreSQL JSONB without expiration | Established pattern | Sessions persist forever (requirement), simpler architecture |
| Draft.js / Slate for inline editing | contentEditable native API | Modern browsers support | Lighter weight, faster, sufficient for simple text editing |
| Hard-coded progress indicators | Derived from session state | Best practice | Single source of truth, no desync bugs |

**Deprecated/outdated:**
- **LangChain PydanticOutputParser with retry logic**: Anthropic Structured Outputs eliminates need for retry/fallback
- **VCR cassettes for question generation testing**: Use RunnerFake with realistic scenario data instead
- **Session TTLs**: Requirement is "sessions never expire" — no Redis expiration keys

## Open Questions

1. **Question Regeneration Strategy When Editing**
   - What we know: Editing Q2 answer may make Q3 redundant
   - What's unclear: Full regeneration vs selective regeneration? Preserve vs discard subsequent answers?
   - Recommendation: Start with "no regeneration" on edit (preserves all progress). Add selective regeneration in Phase 5+ if user feedback demands it. Measure: do users actually edit, and how often?

2. **Thesis Snapshot Tone Selection**
   - What we know: Tone should be appropriate for non-technical founders
   - What's unclear: Formal vs conversational? First-person ("we") vs third-person?
   - Recommendation: Conversational, first-person plural ("we") to match onboarding tone. LLM can adapt: "We're building X to solve Y for Z" vs "The product addresses X by providing Y."

3. **Smart Expand LLM Call Cost**
   - What we know: Clarity check requires LLM call on every idea submission
   - What's unclear: Does this add meaningful latency/cost for a simple check?
   - Recommendation: Start with word count threshold (< 5 words = prompt, 5-9 words = LLM check, 10+ words = proceed). Measure: how many false positives (clear but rejected) vs false negatives (unclear but accepted)?

4. **Concurrent Session Limit Enforcement**
   - What we know: Tier limits (Bootstrapper: 1, Partner: 3, CTO: unlimited)
   - What's unclear: Count all in_progress sessions, or allow "start new, abandon old" flow?
   - Recommendation: Hard limit enforced by unique index. Founder must explicitly "Abandon" or "Complete" existing session to start new one. Prevents accidental limit-hitting by refreshing page.

## Sources

### Primary (HIGH confidence)

- [Anthropic Structured Outputs Documentation](https://platform.claude.com/docs/en/build-with-claude/structured-outputs) — Official structured output feature docs
- [Anthropic API Reference - JSON Schema](https://docs.anthropic.com/en/docs/control-output-format) — JSON mode configuration
- [PostgreSQL JSONB Documentation](https://www.postgresql.org/docs/current/datatype-json.html) — Official JSONB type docs
- [React contentEditable Best Practices](https://blog.logrocket.com/build-inline-editable-ui-react/) — Verified inline editing patterns
- [react-loading-skeleton npm](https://www.npmjs.com/package/react-loading-skeleton) — Official skeleton loader library
- Existing codebase:
  - `backend/app/core/llm_config.py` — Usage tracking and tier resolution patterns
  - `backend/app/db/models/user_settings.py` — Tier FK and JSONB patterns
  - `backend/app/api/routes/projects.py` — User isolation and plan limit enforcement

### Secondary (MEDIUM confidence)

- [Structured Outputs from LLM using Pydantic](https://medium.com/@speaktoharisudhan/structured-outputs-from-llm-using-pydantic-1a36e6c3aa07) — Verified Pydantic + LLM patterns
- [PostgreSQL as a JSON Database - AWS](https://aws.amazon.com/blogs/database/postgresql-as-a-json-database-advanced-patterns-and-best-practices/) — JSONB best practices
- [Conversational Forms UX](https://sureforms.com/features/conversational-form/) — One-question-at-a-time patterns
- [React Skeleton Loaders](https://blog.logrocket.com/handling-react-loading-states-react-loading-skeleton/) — Loading state best practices
- [Inline Editing Implementation](https://apiko.com/blog/inline-editing/) — contentEditable patterns

### Tertiary (LOW confidence - requires verification)

- [AI UI Patterns](https://www.patterns.dev/react/ai-ui-patterns/) — General conversational AI UX trends
- [Assistant UI React Library](https://www.saastr.com/ai-app-of-the-week-assistant-ui-the-react-library-thats-eating-the-ai-chat-interface-market/) — Modern AI chat patterns

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — Anthropic Structured Outputs verified in official docs (Nov 2025), all other libraries already installed
- Architecture: HIGH — Patterns verified in existing codebase (llm_config.py, user_settings.py, projects.py) + official Anthropic/PostgreSQL docs
- Pitfalls: MEDIUM-HIGH — Question regeneration, tier limits, and progress bar issues derived from common patterns; contentEditable conflicts verified in React docs

**Research date:** 2026-02-16
**Valid until:** 2026-03-16 (30 days — Anthropic Structured Outputs is new but stable, React patterns are mature)
