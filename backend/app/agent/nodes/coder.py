"""Coder Node: Generates code changes for the current plan step.

Uses Claude Sonnet for efficient code generation.
"""

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage

from app.agent.state import CoFounderState, FileChange
from app.core.config import get_settings

CODER_SYSTEM_PROMPT = """You are an expert software engineer implementing code changes.
Your task is to write or modify code according to the current plan step.

Guidelines:
1. Write clean, production-ready code
2. Follow existing patterns in the codebase
3. Include proper error handling
4. Add type hints where applicable
5. DO NOT include TODO comments - implement everything fully

For each file change, output in this exact format:
===FILE: path/to/file.py===
<complete file content>
===END FILE===

You can output multiple files. Each file should contain the COMPLETE content, not just changes.
If modifying an existing file, include the full modified content.
"""


async def coder_node(state: CoFounderState) -> dict:
    """Generate code for the current plan step."""
    settings = get_settings()

    llm = ChatAnthropic(
        model=settings.coder_model,
        api_key=settings.anthropic_api_key,
        max_tokens=8192,
    )

    current_step = state["plan"][state["current_step_index"]]

    # Build context
    context = f"""
Project Path: {state["project_path"]}
Overall Goal: {state["current_goal"]}

Current Step ({current_step["index"] + 1}/{len(state["plan"])}):
{current_step["description"]}

Files to modify: {current_step["files_to_modify"]}

Previous errors (if any):
{_format_errors(state["active_errors"])}

Existing working files:
{_format_working_files(state["working_files"])}
"""

    messages = [
        SystemMessage(content=CODER_SYSTEM_PROMPT),
        HumanMessage(content=context),
    ]

    response = await llm.ainvoke(messages)

    # Parse file changes from response
    working_files = dict(state["working_files"])
    new_files = _parse_file_changes(response.content)
    working_files.update(new_files)

    # Mark current step as in progress
    plan = list(state["plan"])
    plan[state["current_step_index"]] = {
        **plan[state["current_step_index"]],
        "status": "in_progress",
    }

    return {
        "working_files": working_files,
        "plan": plan,
        "current_node": "coder",
        "status_message": f"Generated code for step {current_step['index'] + 1}",
        "active_errors": [],  # Clear errors after new code generation
        "messages": [
            {
                "role": "assistant",
                "content": f"Generated code for: {current_step['description']}",
                "node": "coder",
                "files": list(new_files.keys()),
            }
        ],
    }


def _format_errors(errors: list) -> str:
    """Format errors for context."""
    if not errors:
        return "None"

    formatted = []
    for err in errors:
        formatted.append(
            f"- {err['error_type']}: {err['message']}\n"
            f"  File: {err.get('file_path', 'N/A')}\n"
            f"  Stderr: {err.get('stderr', 'N/A')[:200]}"
        )
    return "\n".join(formatted)


def _format_working_files(files: dict) -> str:
    """Format working files for context."""
    if not files:
        return "None"

    return "\n".join(f"- {path}: {change['change_type']}" for path, change in files.items())


def _parse_file_changes(content: str) -> dict[str, FileChange]:
    """Parse file changes from LLM response."""
    import re

    files: dict[str, FileChange] = {}

    pattern = r"===FILE:\s*(.+?)===\n(.*?)===END FILE==="
    matches = re.findall(pattern, content, re.DOTALL)

    for path, file_content in matches:
        path = path.strip()
        files[path] = FileChange(
            path=path,
            original_content=None,  # Will be populated when we read existing files
            new_content=file_content.strip(),
            change_type="create",  # Assume create, executor will determine actual type
        )

    return files
