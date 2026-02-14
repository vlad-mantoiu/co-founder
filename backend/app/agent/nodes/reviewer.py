"""Reviewer Node: Performs code review and quality checks.

Uses Claude Opus for thorough code review.
"""

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage

from app.agent.state import CoFounderState
from app.core.config import get_settings

REVIEWER_SYSTEM_PROMPT = """You are a senior code reviewer performing a thorough review.
Your task is to evaluate code quality, security, and correctness.

Review criteria:
1. **Security**: Check for vulnerabilities (injection, XSS, auth issues, etc.)
2. **Correctness**: Verify the code does what it's supposed to do
3. **Quality**: Check for clean code, proper error handling, type safety
4. **Tests**: Verify adequate test coverage
5. **Best Practices**: Follow language/framework conventions

Output your review in this format:
===VERDICT===
APPROVED or NEEDS_CHANGES
===ISSUES===
<list of issues found, or "None" if approved>
===SUGGESTIONS===
<optional suggestions for improvement>
"""


async def reviewer_node(state: CoFounderState) -> dict:
    """Review the code changes before committing."""
    settings = get_settings()

    llm = ChatAnthropic(
        model=settings.reviewer_model,
        api_key=settings.anthropic_api_key,
        max_tokens=4096,
    )

    # Build review context
    context = _build_review_context(state)

    messages = [
        SystemMessage(content=REVIEWER_SYSTEM_PROMPT),
        HumanMessage(content=context),
    ]

    response = await llm.ainvoke(messages)

    # Parse review result
    review = _parse_review_response(response.content)

    if review["approved"]:
        # Mark current step as completed
        plan = list(state["plan"])
        plan[state["current_step_index"]] = {
            **plan[state["current_step_index"]],
            "status": "completed",
        }

        # Check if we need to move to next step
        next_step_index = state["current_step_index"] + 1
        all_steps_complete = next_step_index >= len(plan)

        return {
            "plan": plan,
            "current_step_index": next_step_index if not all_steps_complete else state["current_step_index"],
            "current_node": "reviewer",
            "status_message": "Code review passed",
            "is_complete": all_steps_complete,
            "retry_count": 0,  # Reset retry count for next step
            "messages": [
                {
                    "role": "assistant",
                    "content": f"Code review passed. {review['suggestions']}" if review['suggestions'] else "Code review passed.",
                    "node": "reviewer",
                }
            ],
        }
    else:
        # Add review issues as errors for the debugger
        errors = [
            {
                "step_index": state["current_step_index"],
                "error_type": "review_rejection",
                "message": issue,
                "stdout": "",
                "stderr": "",
                "file_path": None,
            }
            for issue in review["issues"]
        ]

        return {
            "active_errors": errors,
            "current_node": "reviewer",
            "status_message": f"Code review found {len(review['issues'])} issues",
            "messages": [
                {
                    "role": "assistant",
                    "content": f"Code review found issues:\n" + "\n".join(f"- {i}" for i in review["issues"]),
                    "node": "reviewer",
                }
            ],
        }


def _build_review_context(state: CoFounderState) -> str:
    """Build context for code review."""
    current_step = state["plan"][state["current_step_index"]]

    # Collect all file changes
    file_diffs = []
    for path, change in state["working_files"].items():
        file_diffs.append(f"""
=== {path} ({change['change_type']}) ===
{change['new_content']}
""")

    return f"""
Goal: {state["current_goal"]}
Current Step: {current_step["description"]}

Test Result: Exit code {state.get("last_command_exit_code", "N/A")}
Test Output:
{state.get("last_tool_output", "No test output")[:2000]}

Files Changed:
{"".join(file_diffs)}
"""


def _parse_review_response(content: str) -> dict:
    """Parse the reviewer's response."""
    import re

    approved = False
    issues = []
    suggestions = ""

    # Extract verdict
    verdict_match = re.search(r"===VERDICT===\s*(APPROVED|NEEDS_CHANGES)", content, re.IGNORECASE)
    if verdict_match:
        approved = verdict_match.group(1).upper() == "APPROVED"

    # Extract issues
    issues_match = re.search(r"===ISSUES===\s*(.*?)(?====|$)", content, re.DOTALL)
    if issues_match:
        issues_text = issues_match.group(1).strip()
        if issues_text.lower() != "none":
            issues = [
                line.strip().lstrip("- ")
                for line in issues_text.split("\n")
                if line.strip() and line.strip() != "-"
            ]

    # Extract suggestions
    suggestions_match = re.search(r"===SUGGESTIONS===\s*(.*?)(?====|$)", content, re.DOTALL)
    if suggestions_match:
        suggestions = suggestions_match.group(1).strip()

    return {
        "approved": approved,
        "issues": issues,
        "suggestions": suggestions,
    }
