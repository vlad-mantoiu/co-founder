"""RunnerReal: Production implementation of the Runner protocol using direct Anthropic SDK.

Implements all Runner protocol methods with:
- Real Claude LLM calls via create_tracked_llm() (returns TrackedAnthropicClient)
- Tenacity retry on 529 OverloadedError
- Markdown fence stripping before JSON parsing
- Co-founder "we" voice in all prompts
- Silent JSON retry with stricter prompt on first parse failure
"""

import json
import time

import structlog

from app.agent.llm_helpers import _invoke_with_retry, _parse_json_response
from app.agent.state import CoFounderState
from app.core.llm_config import create_tracked_llm
from app.metrics.cloudwatch import emit_llm_latency

logger = structlog.get_logger(__name__)

COFOUNDER_SYSTEM = """You are the founder's AI co-founder — a senior technical partner invested in their success.

Your voice:
- Use "we" for shared decisions ("We should consider...", "Our biggest risk here is...")
- Use "your" for the founder's vision ("Your target customer...", "Your core insight...")
- Use "I'd suggest" for technical recommendations
- Validate first, then guide: "That's a solid instinct. One thing we should stress-test is..."
- Plain English only — no jargon. The founder should never need to Google a term.
- Never condescending. Smart, warm, direct.

{task_instructions}"""

# Tier-based interview question counts (locked decision)
QUESTION_COUNT_BY_TIER = {
    "bootstrapper": "6-8",
    "partner": "10-12",
    "cto_scale": "14-16",
}

# Tier-based brief sections (locked decision)
BRIEF_SECTIONS_BY_TIER = {
    "bootstrapper": [
        "problem_statement",
        "target_user",
        "value_prop",
        "key_constraints",
        "assumptions",
        "risks",
        "smallest_viable_experiment",
        "confidence_scores",
    ],
    "partner": [
        "problem_statement",
        "target_user",
        "value_prop",
        "differentiation",
        "monetization_hypothesis",
        "market_context",
        "key_constraints",
        "assumptions",
        "risks",
        "smallest_viable_experiment",
        "confidence_scores",
    ],
    "cto_scale": [
        "problem_statement",
        "target_user",
        "value_prop",
        "differentiation",
        "monetization_hypothesis",
        "market_context",
        "competitive_analysis",
        "scalability_notes",
        "risk_deep_dive",
        "key_constraints",
        "assumptions",
        "risks",
        "smallest_viable_experiment",
        "confidence_scores",
    ],
}

# Tier-based execution plan richness
EXEC_PLAN_DETAIL_BY_TIER = {
    "bootstrapper": "For each option, provide a brief engineering impact summary (2-3 sentences).",
    "partner": "For each option, provide detailed engineering impact analysis including team composition, coordination overhead, technical risk areas, and dependency chain. Include a cost_note with estimated budget range.",
    "cto_scale": "For each option, provide comprehensive engineering impact analysis including team composition, skill requirements, coordination overhead, technical risk areas, dependency chains, infrastructure requirements, and scaling considerations. Include detailed cost_note with budget breakdown by role. Add a 'technical_deep_dive' field with architecture recommendations.",
}

# Tier-based artifact richness
ARTIFACT_TIER_SECTIONS = {
    "bootstrapper": "Include core fields only for each artifact (no market_analysis, competitive_strategy, resource_plan, scalability_plan, financial_risks, strategic_risks, integration_points, security_compliance, risk_mitigation_timeline).",
    "partner": "Include core fields plus business-tier sections: market_analysis in brief, technical_architecture in mvp_scope, resource_plan in milestones, financial_risks in risk_log, integration_points in how_it_works.",
    "cto_scale": "Include all fields — core, business-tier, and strategic-tier sections: competitive_strategy in brief, scalability_plan in mvp_scope, risk_mitigation_timeline in milestones, strategic_risks in risk_log, security_compliance in how_it_works.",
}


class RunnerReal:
    """Production Runner implementation using direct Anthropic SDK.

    This class satisfies the Runner protocol and makes direct API calls
    via anthropic.AsyncAnthropic (no LangChain/LangGraph dependency).
    """

    def __init__(self) -> None:
        """Initialize the runner. No checkpointer needed — LangGraph removed."""
        pass

    async def run(self, state: CoFounderState) -> CoFounderState:
        """Execute a build run. Not implemented — delegates to AutonomousRunner via feature flag.

        Raises:
            NotImplementedError: Full TAOR implementation in Phase 41 via AutonomousRunner
        """
        raise NotImplementedError("RunnerReal.run() delegates to AutonomousRunner in Phase 41")

    async def step(self, state: CoFounderState, stage: str) -> CoFounderState:
        """Execute a single pipeline stage. Not implemented — LangGraph pipeline removed.

        Raises:
            NotImplementedError: Multi-node pipeline removed in Phase 40
        """
        raise NotImplementedError("RunnerReal.step() — LangGraph pipeline removed in Phase 40")

    async def generate_questions(self, context: dict) -> list[dict]:
        """Generate onboarding questions tailored to the user's idea context.

        Args:
            context: Dictionary with keys like "idea_keywords", "domain", etc.

        Returns:
            List of question dicts with keys: id, text, required

        Raises:
            RuntimeError: If LLM call fails after retries
        """
        log = logger.bind(method="generate_questions")
        user_id = context.get("user_id", "system")
        session_id = context.get("session_id", "default")
        idea_keywords = context.get("idea_keywords", "")

        client = await create_tracked_llm(user_id=user_id, role="architect", session_id=session_id)

        task_instructions = """Generate 5-7 questions that help us understand the founder's idea.

Use "we" language throughout — we're exploring this together:
- "Who are we building this for?"
- "What problem are we solving?"
- "How will we make money?"

Return ONLY a JSON array of objects:
[
  {
    "id": "q1",
    "text": "...",
    "input_type": "textarea",
    "required": true,
    "options": null,
    "follow_up_hint": null
  }
]"""

        system = COFOUNDER_SYSTEM.format(task_instructions=task_instructions)
        messages = [
            {
                "role": "user",
                "content": f"Generate onboarding questions for an idea with these keywords: {idea_keywords or 'general software product'}",
            }
        ]

        t0 = time.perf_counter()
        try:
            content = await _invoke_with_retry(client, system, messages)
            result = _parse_json_response(content)
        except json.JSONDecodeError:
            log.warning("json_parse_failed_retrying", user_id=user_id, session_id=session_id)
            strict_system = (
                "IMPORTANT: Your response MUST be valid JSON only. "
                "Do not include any explanation, markdown, or code fences. "
                "Start your response with [ .\n\n" + system
            )
            content = await _invoke_with_retry(client, strict_system, messages)
            result = _parse_json_response(content)
        await emit_llm_latency(
            method_name="generate_questions",
            duration_ms=(time.perf_counter() - t0) * 1000,
            model=client.model,
        )
        return result

    async def generate_brief(self, answers: dict) -> dict:
        """Generate a structured product brief from onboarding answers.

        Args:
            answers: Dictionary mapping question IDs to user answers

        Returns:
            Brief dict with keys: problem_statement, target_user, value_prop,
            differentiation, monetization_hypothesis, assumptions, risks,
            smallest_viable_experiment

        Raises:
            RuntimeError: If LLM call fails after retries
        """
        log = logger.bind(method="generate_brief")
        user_id = answers.get("_user_id", "system")
        session_id = answers.get("_session_id", "default")

        # Filter out internal keys
        clean_answers = {k: v for k, v in answers.items() if not k.startswith("_")}

        client = await create_tracked_llm(user_id=user_id, role="architect", session_id=session_id)

        task_instructions = """Convert the founder's onboarding answers into a structured product brief.

Use "we" voice throughout — this is our shared plan:
- "Our target user is..."
- "We're solving the problem of..."
- "Our key differentiator is..."

Return ONLY a JSON object:
{
  "problem_statement": "Clear description of the problem we're solving",
  "target_user": "Who we're building this for",
  "value_prop": "Why users will choose our solution",
  "differentiation": "What makes us unique",
  "monetization_hypothesis": "How we'll make money",
  "assumptions": ["key assumption 1", "key assumption 2"],
  "risks": ["risk 1", "risk 2"],
  "smallest_viable_experiment": "Minimal test to validate our idea"
}"""

        system = COFOUNDER_SYSTEM.format(task_instructions=task_instructions)
        messages = [{"role": "user", "content": f"Generate a product brief from these onboarding answers: {clean_answers}"}]

        t0 = time.perf_counter()
        try:
            content = await _invoke_with_retry(client, system, messages)
            result = _parse_json_response(content)
        except json.JSONDecodeError:
            log.warning("json_parse_failed_retrying", user_id=user_id, session_id=session_id)
            strict_system = (
                "IMPORTANT: Your response MUST be valid JSON only. "
                "Do not include any explanation, markdown, or code fences. "
                "Start your response with { .\n\n" + system
            )
            content = await _invoke_with_retry(client, strict_system, messages)
            result = _parse_json_response(content)
        await emit_llm_latency(
            method_name="generate_brief",
            duration_ms=(time.perf_counter() - t0) * 1000,
            model=client.model,
        )
        return result

    async def generate_understanding_questions(self, context: dict) -> list[dict]:
        """Generate adaptive understanding questions (deeper than onboarding).

        Args:
            context: Dictionary with keys like "idea_text", "onboarding_answers", "tier"

        Returns:
            List of question dicts with keys: id, text, input_type, required, options, follow_up_hint

        Raises:
            RuntimeError: If LLM call fails after retries
        """
        log = logger.bind(method="generate_understanding_questions")
        user_id = context.get("user_id", "system")
        session_id = context.get("session_id", "default")
        tier = context.get("tier", "bootstrapper")
        idea_text = context.get("idea_text", "")
        onboarding_answers = context.get("onboarding_answers", {})

        # Tier-based question count — use module-level constant
        question_count = QUESTION_COUNT_BY_TIER.get(tier, "6-8")

        client = await create_tracked_llm(user_id=user_id, role="architect", session_id=session_id)

        task_instructions = f"""Generate {question_count} understanding interview questions about the founder's idea.
These go deeper than initial onboarding — probe market validation, competitive landscape,
monetization details, risk awareness, and smallest viable experiment.

Use "we" language: "Who have we talked to...", "What's our biggest risk...", "How will we make money..."

Return ONLY a JSON array of objects:
[
  {{
    "id": "uq1",
    "text": "...",
    "input_type": "textarea",
    "required": true,
    "options": null,
    "follow_up_hint": "..."
  }}
]

End the interview with a closing question like: "I have enough to build your brief. Want to add anything else before I do?\""""

        system = COFOUNDER_SYSTEM.format(task_instructions=task_instructions)
        messages = [
            {"role": "user", "content": f"Idea: {idea_text}\n\nOnboarding answers: {onboarding_answers}"}
        ]

        t0 = time.perf_counter()
        try:
            content = await _invoke_with_retry(client, system, messages)
            result = _parse_json_response(content)
        except json.JSONDecodeError:
            log.warning("json_parse_failed_retrying", user_id=user_id, session_id=session_id, tier=tier)
            strict_system = (
                "IMPORTANT: Your response MUST be valid JSON only. "
                "Do not include any explanation, markdown, or code fences. "
                "Start your response with [ .\n\n" + system
            )
            content = await _invoke_with_retry(client, strict_system, messages)
            result = _parse_json_response(content)
        await emit_llm_latency(
            method_name="generate_understanding_questions",
            duration_ms=(time.perf_counter() - t0) * 1000,
            model=client.model,
        )
        return result

    async def generate_idea_brief(self, idea: str, questions: list[dict], answers: dict) -> dict:
        """Generate Rationalised Idea Brief from understanding interview answers.

        Args:
            idea: Original idea text
            questions: List of understanding questions
            answers: Dictionary mapping question IDs to user answers

        Returns:
            Dict matching RationalisedIdeaBrief schema with per-section confidence scores

        Raises:
            RuntimeError: If LLM call fails after retries
        """
        log = logger.bind(method="generate_idea_brief")
        user_id = answers.get("_user_id", "system")
        session_id = answers.get("_session_id", "default")
        tier = answers.get("_tier", "bootstrapper")

        # Tier-conditional sections
        sections = BRIEF_SECTIONS_BY_TIER.get(tier, BRIEF_SECTIONS_BY_TIER["bootstrapper"])
        sections_instruction = f"Include these sections in the brief: {', '.join(sections)}."

        # Build formatted Q&A pairs for the prompt
        qa_pairs = []
        for q in questions:
            qid = q.get("id", "")
            qtext = q.get("text", "")
            answer = answers.get(qid, "")
            if answer:
                qa_pairs.append(f"Q: {qtext}\nA: {answer}")
        formatted_qa = "\n\n".join(qa_pairs)

        client = await create_tracked_llm(user_id=user_id, role="architect", session_id=session_id)

        task_instructions = f"""Generate a Rationalised Idea Brief from the founder's understanding interview.

Use "we" voice throughout: "We've identified...", "Our target user is...", "The risk here is..."
Plain English — no jargon. A non-technical founder should read this without Googling anything.

{sections_instruction}

Return ONLY a JSON object with these fields:
{{
  "problem_statement": "...",
  "target_user": "...",
  "value_prop": "...",
  "differentiation": "...",
  "monetization_hypothesis": "...",
  "market_context": "...",
  "key_constraints": ["..."],
  "assumptions": ["..."],
  "risks": ["..."],
  "smallest_viable_experiment": "...",
  "confidence_scores": {{
    "problem_statement": "strong|moderate|needs_depth",
    "target_user": "strong|moderate|needs_depth",
    "value_prop": "strong|moderate|needs_depth",
    "differentiation": "strong|moderate|needs_depth",
    "monetization_hypothesis": "strong|moderate|needs_depth",
    "market_context": "strong|moderate|needs_depth",
    "key_constraints": "strong|moderate|needs_depth",
    "assumptions": "strong|moderate|needs_depth",
    "risks": "strong|moderate|needs_depth",
    "smallest_viable_experiment": "strong|moderate|needs_depth"
  }},
  "_schema_version": 1
}}

For confidence_scores, assess each section as:
- "strong": Backed by specific evidence, customer interviews, or data from the founder's answers
- "moderate": Reasonable hypothesis but not yet validated with real data
- "needs_depth": Vague or missing — the founder should revisit this section"""

        system = COFOUNDER_SYSTEM.format(task_instructions=task_instructions)
        messages = [
            {"role": "user", "content": f"Idea: {idea}\n\nUnderstanding interview answers:\n\n{formatted_qa}"}
        ]

        t0 = time.perf_counter()
        try:
            content = await _invoke_with_retry(client, system, messages)
            result = _parse_json_response(content)
        except json.JSONDecodeError:
            log.warning("json_parse_failed_retrying", user_id=user_id, session_id=session_id, tier=tier)
            strict_system = (
                "IMPORTANT: Your response MUST be valid JSON only. "
                "Do not include any explanation, markdown, or code fences. "
                "Start your response with { .\n\n" + system
            )
            content = await _invoke_with_retry(client, strict_system, messages)
            result = _parse_json_response(content)
        await emit_llm_latency(
            method_name="generate_idea_brief",
            duration_ms=(time.perf_counter() - t0) * 1000,
            model=client.model,
        )
        return result

    async def check_question_relevance(
        self, idea: str, answered: list[dict], answers: dict, remaining: list[dict]
    ) -> dict:
        """Check if remaining questions are still relevant after an answer edit.

        Args:
            idea: Original idea text
            answered: List of already-answered questions
            answers: Current answers dict
            remaining: List of remaining (unanswered) questions

        Returns:
            Dict with keys: needs_regeneration (bool), preserve_indices (list[int]),
            new_questions (optional list)

        Raises:
            RuntimeError: If LLM call fails after retries
        """
        log = logger.bind(method="check_question_relevance")
        user_id = answers.get("_user_id", "system")
        session_id = answers.get("_session_id", "default")

        # Build answered Q&A context
        answered_context = []
        for q in answered:
            qid = q.get("id", "")
            answer = answers.get(qid, "")
            answered_context.append(f"Q: {q.get('text', '')}\nA: {answer}")
        answered_str = "\n\n".join(answered_context)

        remaining_str = "\n".join(f"[{i}] {q.get('text', '')}" for i, q in enumerate(remaining))

        client = await create_tracked_llm(user_id=user_id, role="architect", session_id=session_id)

        task_instructions = """The founder has edited an answer in their understanding interview.
Review the remaining questions and determine if any are now irrelevant or if new questions are needed.

Return ONLY a JSON object:
{
  "needs_regeneration": true/false,
  "preserve_indices": [0, 2],
  "new_questions": []
}

- needs_regeneration: true if remaining questions should be regenerated
- preserve_indices: indices (0-based) of remaining questions to keep as-is
- new_questions: optional array of 1-2 new questions based on the changed answer (use same question format)"""

        system = COFOUNDER_SYSTEM.format(task_instructions=task_instructions)
        messages = [
            {
                "role": "user",
                "content": f"Idea: {idea}\n\nAnswered questions:\n{answered_str}\n\nRemaining questions:\n{remaining_str}",
            }
        ]

        t0 = time.perf_counter()
        try:
            content = await _invoke_with_retry(client, system, messages)
            result = _parse_json_response(content)
        except json.JSONDecodeError:
            log.warning("json_parse_failed_retrying", user_id=user_id, session_id=session_id)
            strict_system = (
                "IMPORTANT: Your response MUST be valid JSON only. "
                "Do not include any explanation, markdown, or code fences. "
                "Start your response with { .\n\n" + system
            )
            content = await _invoke_with_retry(client, strict_system, messages)
            result = _parse_json_response(content)
        await emit_llm_latency(
            method_name="check_question_relevance",
            duration_ms=(time.perf_counter() - t0) * 1000,
            model=client.model,
        )
        return result

    async def assess_section_confidence(self, section_key: str, content: str) -> str:
        """Assess confidence level for a brief section.

        Args:
            section_key: Section identifier (e.g., "problem_statement", "target_user")
            content: Section content to assess

        Returns:
            Confidence level: "strong" | "moderate" | "needs_depth"

        Raises:
            RuntimeError: If LLM call fails after retries
        """
        client = await create_tracked_llm(user_id="system", role="architect", session_id="assessment")

        task_instructions = """Assess the confidence level of this Idea Brief section.

Return ONLY one of: "strong", "moderate", "needs_depth"

- "strong": Specific evidence, data points, named customers, or quantified metrics
- "moderate": Reasonable hypothesis, some supporting logic, but unvalidated
- "needs_depth": Vague, generic, or missing critical detail"""

        system = COFOUNDER_SYSTEM.format(task_instructions=task_instructions)
        messages = [{"role": "user", "content": f"Section: {section_key}\n\nContent: {content}"}]

        t0 = time.perf_counter()
        text = await _invoke_with_retry(client, system, messages)
        await emit_llm_latency(
            method_name="assess_section_confidence",
            duration_ms=(time.perf_counter() - t0) * 1000,
            model=client.model,
        )
        text = text.strip().lower()
        for level in ("strong", "moderate", "needs_depth"):
            if level in text:
                return level
        return "moderate"  # safe default

    async def generate_execution_options(self, brief: dict, feedback: str | None = None) -> dict:
        """Generate 2-3 execution plan options from the Idea Brief.

        Args:
            brief: Rationalised Idea Brief artifact content
            feedback: Optional feedback on previous options (for regeneration)

        Returns:
            Dict matching ExecutionPlanOptions schema with 2-3 options

        Raises:
            RuntimeError: If LLM call fails after retries
        """
        log = logger.bind(method="generate_execution_options")
        user_id = brief.get("_user_id", "system")
        session_id = brief.get("_session_id", "default")
        # _tier is injected by service layer; fall back to _context dict for backwards compat
        tier = brief.get("_tier") or (
            brief.get("_context", {}).get("tier", "bootstrapper")
            if isinstance(brief.get("_context"), dict)
            else "bootstrapper"
        )

        # Tier-conditional engineering detail instruction
        detail_instruction = EXEC_PLAN_DETAIL_BY_TIER.get(tier, EXEC_PLAN_DETAIL_BY_TIER["bootstrapper"])

        # Clean brief for prompt (remove internal keys)
        clean_brief = {k: v for k, v in brief.items() if not k.startswith("_")}

        client = await create_tracked_llm(user_id=user_id, role="architect", session_id=session_id)

        feedback_context = ""
        if feedback:
            feedback_context = f"\n\nThe founder gave this feedback on previous options: {feedback}"

        task_instructions = f"""Generate 2-3 execution plan options based on the Rationalised Idea Brief.
Each option represents a different approach to building the MVP.

Use "we" voice: "We'll focus on...", "Our approach here is..."

For each option include:
- id (kebab-case string), name (human readable)
- is_recommended (exactly one option must be true)
- time_to_ship (e.g., "3-4 weeks"), engineering_cost (e.g., "Low (1 engineer, ~80 hours)")
- risk_level ("low", "medium", or "high"), scope_coverage (0-100 integer percent)
- pros (array of strings), cons (array of strings)
- technical_approach (string), tradeoffs (array of strings), engineering_impact (string)

Engineering detail level: {detail_instruction}

Return ONLY a JSON object:
{{
  "options": [...],
  "recommended_id": "..."
}}
{feedback_context}"""

        system = COFOUNDER_SYSTEM.format(task_instructions=task_instructions)
        messages = [
            {
                "role": "user",
                "content": f"Generate execution plan options from this Idea Brief:\n\n{json.dumps(clean_brief, indent=2)}",
            }
        ]

        t0 = time.perf_counter()
        try:
            content = await _invoke_with_retry(client, system, messages)
            result = _parse_json_response(content)
        except json.JSONDecodeError:
            log.warning("json_parse_failed_retrying", user_id=user_id, session_id=session_id, tier=tier)
            strict_system = (
                "IMPORTANT: Your response MUST be valid JSON only. "
                "Do not include any explanation, markdown, or code fences. "
                "Start your response with { .\n\n" + system
            )
            content = await _invoke_with_retry(client, strict_system, messages)
            result = _parse_json_response(content)
        await emit_llm_latency(
            method_name="generate_execution_options",
            duration_ms=(time.perf_counter() - t0) * 1000,
            model=client.model,
        )
        return result

    async def generate_strategy_graph(self, idea: str, brief: dict, onboarding_answers: dict) -> dict:
        """Generate a strategy graph with anchor nodes from verbatim user phrases.

        Args:
            idea: Original idea text
            brief: Rationalised Idea Brief content dict
            onboarding_answers: Raw onboarding answers dict

        Returns:
            Dict with keys: nodes, edges, anchor_phrases
            - nodes: list of {id, type ("anchor"|"strategy"), label, description, status}
            - edges: list of {source, target, relation}
            - anchor_phrases: list of verbatim phrases extracted from founder's answers

        Raises:
            RuntimeError: If LLM call fails after retries
        """
        log = logger.bind(method="generate_strategy_graph")
        user_id = brief.get("_user_id", "system")
        session_id = brief.get("_session_id", "default")

        # Clean brief for prompt (remove internal keys)
        clean_brief = {k: v for k, v in brief.items() if not k.startswith("_")}
        # Clean answers for prompt
        clean_answers = {k: v for k, v in onboarding_answers.items() if not k.startswith("_")}

        client = await create_tracked_llm(user_id=user_id, role="architect", session_id=session_id)

        task_instructions = """Generate a strategy graph that visualizes the founder's go-to-market strategy.

CRITICAL: Extract 5-8 key phrases VERBATIM from the founder's answers — these become anchor nodes. The user must recognize their exact words.

Then create 8-12 strategy nodes connecting the anchors: go-to-market steps, business model components, competitive moat elements, validation milestones.

Create edges showing relationships between anchors and strategy nodes.

Return ONLY a JSON object:
{
  "nodes": [
    {
      "id": "anchor_1",
      "type": "anchor",
      "label": "exact phrase from founder",
      "description": "why this phrase anchors the strategy",
      "status": "validated"
    },
    {
      "id": "strategy_1",
      "type": "strategy",
      "label": "go-to-market step name",
      "description": "what this strategy node means for us",
      "status": "planned"
    }
  ],
  "edges": [
    {
      "source": "anchor_1",
      "target": "strategy_1",
      "relation": "enables"
    }
  ],
  "anchor_phrases": ["exact phrase 1", "exact phrase 2"]
}

Node status rules:
- anchor nodes: "validated" (these are real words from the founder)
- strategy nodes: "validated" if already proven, "planned" if next steps

Use "we" voice in descriptions."""

        system = COFOUNDER_SYSTEM.format(task_instructions=task_instructions)
        messages = [
            {
                "role": "user",
                "content": (
                    f"Idea: {idea}\n\n"
                    f"Idea Brief:\n{json.dumps(clean_brief, indent=2)}\n\n"
                    f"Founder's Answers:\n{json.dumps(clean_answers, indent=2)}"
                ),
            }
        ]

        t0 = time.perf_counter()
        try:
            content = await _invoke_with_retry(client, system, messages)
            result = _parse_json_response(content)
        except json.JSONDecodeError:
            log.warning("json_parse_failed_retrying", user_id=user_id, session_id=session_id)
            strict_system = (
                "IMPORTANT: Your response MUST be valid JSON only. "
                "Do not include any explanation, markdown, or code fences. "
                "Start your response with { .\n\n" + system
            )
            content = await _invoke_with_retry(client, strict_system, messages)
            result = _parse_json_response(content)
        await emit_llm_latency(
            method_name="generate_strategy_graph",
            duration_ms=(time.perf_counter() - t0) * 1000,
            model=client.model,
        )
        return result

    async def generate_mvp_timeline(self, idea: str, brief: dict, tier: str) -> dict:
        """Generate a tier-adapted MVP timeline with relative-week milestones.

        Args:
            idea: Original idea text
            brief: Rationalised Idea Brief content dict
            tier: User's plan tier ("bootstrapper", "partner", "cto_scale")

        Returns:
            Dict with keys: milestones, long_term_roadmap, total_mvp_weeks, adapted_for
            - milestones: list of {week, title, deliverables: list[str], duration_weeks, description}
            - long_term_roadmap: list of {phase, title, description, estimated_weeks}
            - total_mvp_weeks: int
            - adapted_for: tier string

        Raises:
            RuntimeError: If LLM call fails after retries
        """
        log = logger.bind(method="generate_mvp_timeline")
        user_id = brief.get("_user_id", "system")
        session_id = brief.get("_session_id", "default")

        # Tier-based MVP scope adaptation
        tier_guidance = {
            "bootstrapper": "smaller MVP scope + longer phases (8-12 weeks total). Start with a no-code validation sprint in Week 1-2. Favor managed services over custom code. Each milestone should be achievable by a solo non-technical founder.",
            "partner": "moderate MVP scope + moderate timeline (6-8 weeks total). Balance speed and quality. Include technical milestones but keep scope focused.",
            "cto_scale": "aggressive MVP scope + compressed timeline (4-6 weeks total). Assume technical team available. Include architecture decisions and team coordination milestones.",
        }
        scope_note = tier_guidance.get(tier, tier_guidance["bootstrapper"])

        # Clean brief for prompt (remove internal keys)
        clean_brief = {k: v for k, v in brief.items() if not k.startswith("_")}

        client = await create_tracked_llm(user_id=user_id, role="architect", session_id=session_id)

        task_instructions = f"""Generate a personalized MVP timeline adapted for the {tier} tier.

Tier adaptation: {scope_note}

RULES:
- Use RELATIVE WEEKS only (Week 1, Week 3) — never calendar dates. The founder decides when to start.
- Each milestone must list 2-3 CONCRETE deliverables (e.g., "landing page live", "50 signups", "5 user interviews completed")
- Adapt both scope AND duration to the {tier} tier
- Use "we" voice in descriptions ("We'll validate...", "Our goal here is...")
- Each milestone must have a clear "done" state the founder can recognize

Return ONLY a JSON object:
{{
  "milestones": [
    {{
      "week": 1,
      "title": "Milestone name",
      "description": "What we're doing and why this matters",
      "deliverables": ["concrete thing 1", "concrete thing 2"],
      "duration_weeks": 2
    }}
  ],
  "long_term_roadmap": [
    {{
      "phase": "Phase 2",
      "title": "Post-MVP Growth",
      "description": "What comes after MVP launch",
      "estimated_weeks": 8
    }}
  ],
  "total_mvp_weeks": 10,
  "adapted_for": "{tier}"
}}"""

        system = COFOUNDER_SYSTEM.format(task_instructions=task_instructions)
        messages = [
            {
                "role": "user",
                "content": f"Idea: {idea}\n\nIdea Brief:\n{json.dumps(clean_brief, indent=2)}\n\nTier: {tier}",
            }
        ]

        t0 = time.perf_counter()
        try:
            content = await _invoke_with_retry(client, system, messages)
            result = _parse_json_response(content)
        except json.JSONDecodeError:
            log.warning("json_parse_failed_retrying", user_id=user_id, session_id=session_id, tier=tier)
            strict_system = (
                "IMPORTANT: Your response MUST be valid JSON only. "
                "Do not include any explanation, markdown, or code fences. "
                "Start your response with { .\n\n" + system
            )
            content = await _invoke_with_retry(client, strict_system, messages)
            result = _parse_json_response(content)
        await emit_llm_latency(
            method_name="generate_mvp_timeline",
            duration_ms=(time.perf_counter() - t0) * 1000,
            model=client.model,
        )
        return result

    async def generate_app_architecture(self, idea: str, brief: dict, tier: str) -> dict:
        """Generate an app architecture diagram with cost estimates.

        Args:
            idea: Original idea text
            brief: Rationalised Idea Brief content dict
            tier: User's plan tier ("bootstrapper", "partner", "cto_scale")

        Returns:
            Dict with keys: components, connections, cost_estimate, integration_recommendations
            - components: list of {name, type, description, tech_recommendation, alternatives, detail_level}
            - connections: list of {from_component, to_component, protocol, description}
            - cost_estimate: {startup_monthly, scale_monthly, breakdown: [{component, cost, note}]}
            - integration_recommendations: list of strings

        Raises:
            RuntimeError: If LLM call fails after retries
        """
        log = logger.bind(method="generate_app_architecture")
        user_id = brief.get("_user_id", "system")
        session_id = brief.get("_session_id", "default")

        # Clean brief for prompt (remove internal keys)
        clean_brief = {k: v for k, v in brief.items() if not k.startswith("_")}

        client = await create_tracked_llm(user_id=user_id, role="architect", session_id=session_id)

        task_instructions = f"""Generate a simplified app architecture diagram for a non-technical founder.

RULES:
- Simplified by default for non-technical founders. Use plain English component names.
- No jargon. The founder should understand what each component does without Googling.
- Include rough cost estimates: startup monthly (~$50/mo) and scale monthly (~$200/mo at 1k users)
- For each component, recommend a specific technology and list 1-2 alternatives
- Favor managed services (e.g., Vercel, Render, Supabase, Clerk, Resend) for the {tier} tier

Component types: "frontend" | "backend" | "database" | "auth" | "storage" | "other"
Detail levels: "simplified" (plain English) | "expanded" (includes technical terms)

Return ONLY a JSON object:
{{
  "components": [
    {{
      "name": "Your Website (Frontend)",
      "type": "frontend",
      "description": "What users see and click on — your app's interface",
      "tech_recommendation": "Next.js on Vercel",
      "alternatives": ["React on Netlify", "Webflow"],
      "detail_level": "simplified"
    }}
  ],
  "connections": [
    {{
      "from_component": "Your Website (Frontend)",
      "to_component": "Your API (Backend)",
      "protocol": "HTTPS",
      "description": "Users' actions are sent here for processing"
    }}
  ],
  "cost_estimate": {{
    "startup_monthly": 45,
    "scale_monthly": 180,
    "breakdown": [
      {{
        "component": "Hosting (Vercel)",
        "cost": 20,
        "note": "Includes frontend + serverless functions"
      }}
    ]
  }},
  "integration_recommendations": [
    "Start with Stripe for payments — easiest to set up",
    "Use Clerk for auth to avoid building login from scratch"
  ]
}}"""

        system = COFOUNDER_SYSTEM.format(task_instructions=task_instructions)
        messages = [
            {
                "role": "user",
                "content": f"Idea: {idea}\n\nIdea Brief:\n{json.dumps(clean_brief, indent=2)}\n\nTier: {tier}",
            }
        ]

        t0 = time.perf_counter()
        try:
            content = await _invoke_with_retry(client, system, messages)
            result = _parse_json_response(content)
        except json.JSONDecodeError:
            log.warning("json_parse_failed_retrying", user_id=user_id, session_id=session_id, tier=tier)
            strict_system = (
                "IMPORTANT: Your response MUST be valid JSON only. "
                "Do not include any explanation, markdown, or code fences. "
                "Start your response with { .\n\n" + system
            )
            content = await _invoke_with_retry(client, strict_system, messages)
            result = _parse_json_response(content)
        await emit_llm_latency(
            method_name="generate_app_architecture",
            duration_ms=(time.perf_counter() - t0) * 1000,
            model=client.model,
        )
        return result

    async def generate_artifacts(self, brief: dict) -> dict:
        """Generate documentation artifacts from the product brief.

        Args:
            brief: The structured product brief

        Returns:
            Artifacts dict with 5 keys: brief, mvp_scope, milestones, risk_log, how_it_works

        Raises:
            RuntimeError: If LLM call fails after retries
        """
        log = logger.bind(method="generate_artifacts")
        user_id = brief.get("_user_id", "system")
        session_id = brief.get("_session_id", "default")
        # _tier is injected by service layer
        tier = brief.get("_tier", "bootstrapper")

        # Tier-conditional artifact richness instruction
        tier_sections = ARTIFACT_TIER_SECTIONS.get(tier, ARTIFACT_TIER_SECTIONS["bootstrapper"])

        # Filter out internal keys
        clean_brief = {k: v for k, v in brief.items() if not k.startswith("_")}

        client = await create_tracked_llm(user_id=user_id, role="architect", session_id=session_id)

        task_instructions = f"""Generate a complete set of project artifacts from the product brief.
These artifacts are the founder's project documentation — they'll share these with advisors,
investors, and team members.

Use "we" voice throughout. Plain English — no jargon.

Artifact richness level: {tier_sections}

Return ONLY a JSON object with these 5 keys:
{{
  "brief": {{
    "_schema_version": 1,
    "problem_statement": "...",
    "target_user": "...",
    "value_proposition": "...",
    "key_constraint": "...",
    "differentiation_points": ["..."],
    "market_analysis": "...",
    "competitive_strategy": "..."
  }},
  "mvp_scope": {{
    "_schema_version": 1,
    "core_features": [{{"name": "...", "description": "...", "priority": "high|medium|low"}}],
    "out_of_scope": ["..."],
    "success_metrics": ["..."],
    "technical_architecture": "...",
    "scalability_plan": "..."
  }},
  "milestones": {{
    "_schema_version": 1,
    "milestones": [{{"title": "...", "description": "...", "success_criteria": ["..."], "estimated_weeks": 1}}],
    "critical_path": ["..."],
    "total_duration_weeks": 4,
    "resource_plan": "...",
    "risk_mitigation_timeline": "..."
  }},
  "risk_log": {{
    "_schema_version": 1,
    "technical_risks": [{{"title": "...", "description": "...", "severity": "high|medium|low", "mitigation": "..."}}],
    "market_risks": [{{"title": "...", "description": "...", "severity": "high|medium|low", "mitigation": "..."}}],
    "execution_risks": [{{"title": "...", "description": "...", "severity": "high|medium|low", "mitigation": "..."}}]
  }},
  "how_it_works": {{
    "_schema_version": 1,
    "user_journey": [{{"step_number": 1, "title": "...", "description": "..."}}],
    "architecture": "...",
    "data_flow": "...",
    "integration_points": "..."
  }}
}}

Each artifact should cross-reference others (e.g., milestones reference MVP features,
risk log references brief assumptions)."""

        system = COFOUNDER_SYSTEM.format(task_instructions=task_instructions)
        messages = [
            {
                "role": "user",
                "content": f"Generate project artifacts from this brief:\n\n{json.dumps(clean_brief, indent=2)}",
            }
        ]

        t0 = time.perf_counter()
        try:
            content = await _invoke_with_retry(client, system, messages)
            result = _parse_json_response(content)
        except json.JSONDecodeError:
            log.warning("json_parse_failed_retrying", user_id=user_id, session_id=session_id, tier=tier)
            strict_system = (
                "IMPORTANT: Your response MUST be valid JSON only. "
                "Do not include any explanation, markdown, or code fences. "
                "Start your response with { .\n\n" + system
            )
            content = await _invoke_with_retry(client, strict_system, messages)
            result = _parse_json_response(content)
        await emit_llm_latency(
            method_name="generate_artifacts",
            duration_ms=(time.perf_counter() - t0) * 1000,
            model=client.model,
        )
        return result

    async def run_agent_loop(self, context: dict) -> dict:
        """Execute the autonomous TAOR agent loop for a build session.

        Phase 41 will implement the full TAOR loop here.

        Args:
            context: Dict with keys: project_id, user_id, idea_brief, execution_plan

        Returns:
            Dict with keys: status, project_id, phases_completed, result

        Raises:
            NotImplementedError: Full TAOR implementation in Phase 41
        """
        raise NotImplementedError("RunnerReal.run_agent_loop() not yet implemented — Phase 41")
