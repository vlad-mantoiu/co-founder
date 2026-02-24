"""System prompt builder for the TAOR autonomous agent loop.

Assembles the agent's identity (co-founder persona), verbatim founder context
(Idea Brief + Understanding Interview QnA), and structured build plan into a
single system prompt string that is passed once at session start.

Per CONTEXT.md locked decisions:
- Full verbatim injection of Idea Brief and QnA — nothing summarized
- Persona shapes narration voice: collaborative "we/us", first-person "I" for reasoning
- Minimal critical-only guardrails (no data deletion, no external prod API calls)
- Agent executes the provided build plan in sequence — does not decide what to build
"""

from __future__ import annotations

import json


_PERSONA_SECTION = """\
## Identity & Behavior

You are the founder's AI co-founder — a senior technical partner building their product together.

**Voice:**
- Use "we" and "us" for shared decisions and direction ("Let's get auth working next.")
- Use "I" for internal reasoning and specific actions ("I'm creating the user model.")
- Collaborative pair-programming tone — think of it as two technical co-founders working in sync.

**Narration (mandatory):**
- Narrate before every tool call: "I'm creating the auth module..." or "Let's scaffold the project structure."
- Narrate after every tool call: "Auth module created. Moving to routes."
- Narrate reasoning alongside actions — share WHY decisions are made.
- After each major group of work, provide a section summary: e.g. "Authentication complete: created login/register endpoints, JWT middleware, and user model. Moving to routes."
- Use distinct labeled phases in the narration stream so the founder sees named stages.

**Formatting:**
- Light markdown — **bold** for phase names, `inline code` for file paths.
- Errors narrated honestly and reassuringly: "Hit an issue with X. Trying a different approach..." — never panicked, always has a plan.
- No action counts or raw progress percentages — phases and section summaries provide structure.

**Guardrails (non-negotiable):**
- Do not delete data. Do not drop tables, truncate databases, or remove files unless the build plan explicitly requires it and the action is reversible.
- Do not make external API calls to production services. All network calls must target sandbox or stub endpoints.
- Execute the provided build plan in sequence. Do not deviate from the plan order or decide to add unplanned features.\
"""


def build_system_prompt(
    idea_brief: dict,
    understanding_qna: list[dict],
    build_plan: dict,
) -> str:
    """Assemble the agent's system prompt from founder context and build plan.

    Parameters
    ----------
    idea_brief:
        The founder's Idea Brief as a dict (from the project onboarding form).
        Injected verbatim as JSON — the agent sees the founder's exact words.
    understanding_qna:
        The Understanding Interview question-and-answer pairs as a list of dicts
        with "question" and "answer" keys. Injected verbatim. Empty list is valid.
    build_plan:
        The structured build plan the agent must execute. Injected verbatim as JSON.
        The agent does not decide what to build — it follows this plan in sequence.

    Returns
    -------
    str
        The complete system prompt string ready to pass as the ``system`` parameter
        of an Anthropic ``messages.create()`` call.
    """
    # --- Section 1: Persona & behavior instructions ---
    persona_section = _PERSONA_SECTION

    # --- Section 2: Idea Brief (verbatim JSON injection) ---
    idea_brief_section = "\n".join([
        "## Founder's Idea Brief",
        "",
        json.dumps(idea_brief, indent=2),
    ])

    # --- Section 3: Understanding Interview QnA (verbatim) ---
    if understanding_qna:
        qna_lines = ["## Understanding Interview (Founder's Answers)", ""]
        for entry in understanding_qna:
            qna_lines.append(f"Q: {entry['question']}")
            qna_lines.append(f"A: {entry['answer']}")
            qna_lines.append("")
        qna_section = "\n".join(qna_lines).rstrip()
    else:
        qna_section = "\n".join([
            "## Understanding Interview (Founder's Answers)",
            "",
            "(No interview responses provided)",
        ])

    # --- Section 4: Build Plan (verbatim JSON injection) ---
    build_plan_section = "\n".join([
        "## Build Plan (Execute in Order)",
        "",
        json.dumps(build_plan, indent=2),
    ])

    return "\n\n".join([
        persona_section,
        idea_brief_section,
        qna_section,
        build_plan_section,
    ])
