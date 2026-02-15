"""Debugger Node: Analyzes errors and proposes fixes.

Uses Claude Sonnet for fast iterative debugging.
"""

from langchain_core.messages import HumanMessage, SystemMessage

from app.agent.state import CoFounderState, ErrorInfo
from app.core.llm_config import create_tracked_llm

DEBUGGER_SYSTEM_PROMPT = """You are an expert debugger analyzing test failures and errors.
Your task is to identify the root cause and propose a fix.

Guidelines:
1. Carefully analyze the error message and stack trace
2. Look at the relevant code that caused the error
3. Propose a specific, minimal fix
4. Explain your reasoning briefly

Output your analysis in this format:
===ANALYSIS===
<your analysis of what went wrong>
===FIX===
<description of the fix needed>
===FILES===
<list of files that need to be modified, one per line>
"""


async def debugger_node(state: CoFounderState) -> dict:
    """Analyze errors and prepare fix instructions for the coder."""
    settings = get_settings()

    # Check retry count
    new_retry_count = state["retry_count"] + 1

    if new_retry_count > state["max_retries"]:
        # Too many retries, escalate to human
        return {
            "retry_count": new_retry_count,
            "needs_human_review": True,
            "current_node": "debugger",
            "status_message": f"Retry limit ({state['max_retries']}) exceeded. Needs human review.",
            "messages": [
                {
                    "role": "assistant",
                    "content": f"I've tried {state['max_retries']} times but couldn't fix this issue. Requesting human review.",
                    "node": "debugger",
                }
            ],
        }

    llm = await create_tracked_llm(
        user_id=state["user_id"],
        role="debugger",
        session_id=state["session_id"],
    )

    # Build context from errors
    context = _build_debug_context(state)

    messages = [
        SystemMessage(content=DEBUGGER_SYSTEM_PROMPT),
        HumanMessage(content=context),
    ]

    response = await llm.ainvoke(messages)

    # Parse the analysis
    analysis = _parse_debug_response(response.content)

    # Update messages with debug info for the coder
    return {
        "retry_count": new_retry_count,
        "current_node": "debugger",
        "status_message": f"Debug analysis complete (attempt {new_retry_count}/{state['max_retries']})",
        "messages": [
            {
                "role": "assistant",
                "content": f"Debug Analysis:\n{analysis['analysis']}\n\nProposed Fix:\n{analysis['fix']}",
                "node": "debugger",
                "files_to_fix": analysis["files"],
            }
        ],
    }


def _build_debug_context(state: CoFounderState) -> str:
    """Build context for debugging."""
    current_step = state["plan"][state["current_step_index"]]

    # Get relevant file contents
    file_contents = []
    for path, change in state["working_files"].items():
        file_contents.append(f"=== {path} ===\n{change['new_content'][:2000]}")

    return f"""
Current Step: {current_step["description"]}

Errors:
{_format_errors(state["active_errors"])}

Last Output:
{state.get("last_tool_output", "N/A")[:2000]}

Relevant Files:
{chr(10).join(file_contents)}

Retry attempt: {state["retry_count"] + 1} of {state["max_retries"]}
"""


def _format_errors(errors: list[ErrorInfo]) -> str:
    """Format errors for the debugger."""
    if not errors:
        return "No errors recorded"

    formatted = []
    for err in errors:
        formatted.append(f"""
Error Type: {err["error_type"]}
Message: {err["message"]}
File: {err.get("file_path", "N/A")}
Stdout: {err.get("stdout", "")[:500]}
Stderr: {err.get("stderr", "")[:500]}
""")
    return "\n---\n".join(formatted)


def _parse_debug_response(content: str) -> dict:
    """Parse the debugger's response."""
    import re

    analysis = ""
    fix = ""
    files = []

    # Extract analysis
    analysis_match = re.search(r"===ANALYSIS===\s*(.*?)(?====|$)", content, re.DOTALL)
    if analysis_match:
        analysis = analysis_match.group(1).strip()

    # Extract fix
    fix_match = re.search(r"===FIX===\s*(.*?)(?====|$)", content, re.DOTALL)
    if fix_match:
        fix = fix_match.group(1).strip()

    # Extract files
    files_match = re.search(r"===FILES===\s*(.*?)(?====|$)", content, re.DOTALL)
    if files_match:
        files = [f.strip() for f in files_match.group(1).strip().split("\n") if f.strip()]

    return {
        "analysis": analysis or content[:500],
        "fix": fix or "See analysis above",
        "files": files,
    }
