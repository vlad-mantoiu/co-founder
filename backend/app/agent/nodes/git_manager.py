"""GitManager Node: Handles git operations and PR creation.

Uses GitHub App integration for real repository operations.
"""

from langchain_core.messages import HumanMessage, SystemMessage

from app.agent.state import CoFounderState
from app.core.config import get_settings
from app.core.llm_config import create_tracked_llm
from app.integrations.github import get_github_client

COMMIT_MESSAGE_PROMPT = """Generate a concise git commit message for these changes.
Follow conventional commits format: type(scope): description

Types: feat, fix, refactor, test, docs, chore

Output ONLY the commit message, nothing else.
"""

PR_DESCRIPTION_PROMPT = """Generate a pull request description for these changes.

Use this format:
## Summary
<2-3 sentences describing what changed>

## Changes
<bullet list of specific changes>

## Testing
<how to test these changes>

Output ONLY the PR description in markdown, nothing else.
"""


async def git_manager_node(state: CoFounderState) -> dict:
    """Handle git operations: branch, commit, push, PR."""
    settings = get_settings()

    # Check if GitHub integration is configured
    if not settings.github_app_id or not settings.github_private_key:
        # Fall back to local git operations
        return await _local_git_operations(state)

    # Parse repo info from project path or metadata
    # Expected format: "owner/repo" in project metadata
    repo_info = _parse_repo_info(state)
    if not repo_info:
        return await _local_git_operations(state)

    owner, repo, installation_id = repo_info

    # Generate commit message
    llm = await create_tracked_llm(
        user_id=state["user_id"],
        role="coder",
        session_id=state["session_id"],
    )

    changes_summary = _summarize_changes(state)

    commit_response = await llm.ainvoke(
        [
            SystemMessage(content=COMMIT_MESSAGE_PROMPT),
            HumanMessage(content=changes_summary),
        ]
    )
    commit_message = commit_response.content.strip()

    pr_response = await llm.ainvoke(
        [
            SystemMessage(content=PR_DESCRIPTION_PROMPT),
            HumanMessage(content=changes_summary),
        ]
    )
    pr_description = pr_response.content.strip()

    # Execute GitHub operations
    try:
        github = get_github_client(installation_id)

        # Create branch if needed
        branch = state["git_branch"]
        try:
            await github.create_branch(
                owner=owner,
                repo=repo,
                branch_name=branch,
                from_branch=state["git_base_branch"],
            )
        except Exception:
            # Branch might already exist
            pass

        # Commit all changed files
        files_to_commit = {path: change["new_content"] for path, change in state["working_files"].items()}

        if files_to_commit:
            await github.commit_multiple_files(
                owner=owner,
                repo=repo,
                branch=branch,
                files=files_to_commit,
                message=commit_message,
            )

        # Check for existing PR
        existing_prs = await github.list_pull_requests(
            owner=owner,
            repo=repo,
            head=branch,
            state="open",
        )

        if existing_prs:
            # Update existing PR with comment
            pr = existing_prs[0]
            await github.add_pr_comment(
                owner=owner,
                repo=repo,
                pr_number=pr["number"],
                body=f"Updated with new changes:\n\n{commit_message}",
            )
            pr_url = pr["html_url"]
        else:
            # Create new PR
            pr = await github.create_pull_request(
                owner=owner,
                repo=repo,
                title=_generate_pr_title(state),
                body=pr_description,
                head=branch,
                base=state["git_base_branch"],
            )
            pr_url = pr["html_url"]

        return {
            "commit_messages": state["commit_messages"] + [commit_message],
            "current_node": "git_manager",
            "status_message": f"PR created/updated: {pr_url}",
            "is_complete": True,
            "messages": [
                {
                    "role": "assistant",
                    "content": f"Changes committed and PR ready for review:\n\n**Commit:** {commit_message}\n\n**PR:** {pr_url}",
                    "node": "git_manager",
                    "pr_url": pr_url,
                }
            ],
        }

    except Exception as e:
        return {
            "current_node": "git_manager",
            "status_message": f"GitHub operation failed: {e}",
            "needs_human_review": True,
            "messages": [
                {
                    "role": "assistant",
                    "content": f"GitHub operation failed: {e}\n\nPlease review and manually create the PR if needed.",
                    "node": "git_manager",
                }
            ],
        }


def _parse_repo_info(state: CoFounderState) -> tuple[str, str, str] | None:
    """Parse repository info from state.

    Expected: project metadata contains github_repo (owner/repo format)
    and github_installation_id.
    """
    # Check messages for repo info (would be set during project linking)
    for msg in reversed(state["messages"]):
        # Handle both dict messages and LangChain Message objects
        if isinstance(msg, dict):
            if msg.get("github_repo"):
                parts = msg["github_repo"].split("/")
                if len(parts) == 2:
                    return (
                        parts[0],
                        parts[1],
                        msg.get("github_installation_id", ""),
                    )
        # Skip LangChain Message objects (they don't contain repo info)

    # Check project path for owner/repo pattern
    project_path = state["project_path"]
    if "/" in project_path:
        parts = project_path.strip("/").split("/")
        if len(parts) >= 2:
            # Assume last two parts are owner/repo
            return parts[-2], parts[-1], ""

    return None


def _summarize_changes(state: CoFounderState) -> str:
    """Summarize changes for commit message generation."""
    completed_steps = [step["description"] for step in state["plan"] if step["status"] == "completed"]

    files_changed = list(state["working_files"].keys())

    return f"""
Goal: {state["current_goal"]}

Completed Steps:
{chr(10).join(f"- {s}" for s in completed_steps)}

Files Changed:
{chr(10).join(f"- {f}" for f in files_changed)}
"""


def _generate_pr_title(state: CoFounderState) -> str:
    """Generate a PR title from the goal."""
    goal = state["current_goal"]

    # Truncate and clean
    title = goal[:60]
    if len(goal) > 60:
        title += "..."

    # Determine type prefix
    goal_lower = goal.lower()
    if any(w in goal_lower for w in ["fix", "bug", "error", "issue"]):
        prefix = "fix"
    elif any(w in goal_lower for w in ["add", "create", "implement", "new"]):
        prefix = "feat"
    elif any(w in goal_lower for w in ["refactor", "clean", "improve"]):
        prefix = "refactor"
    elif any(w in goal_lower for w in ["test"]):
        prefix = "test"
    elif any(w in goal_lower for w in ["doc", "readme"]):
        prefix = "docs"
    else:
        prefix = "feat"

    return f"{prefix}: {title}"


async def _local_git_operations(state: CoFounderState) -> dict:
    """Fallback to local git operations when GitHub is not configured."""
    import asyncio
    import subprocess
    from pathlib import Path

    project_path = Path(state["project_path"])

    # Generate commit message
    llm = await create_tracked_llm(
        user_id=state["user_id"],
        role="coder",
        session_id=state["session_id"],
    )

    changes_summary = _summarize_changes(state)
    response = await llm.ainvoke(
        [
            SystemMessage(content=COMMIT_MESSAGE_PROMPT),
            HumanMessage(content=changes_summary),
        ]
    )
    commit_message = response.content.strip()

    async def run_git(args: list[str]) -> tuple[int, str, str]:
        proc = await asyncio.create_subprocess_exec(
            "git",
            *args,
            cwd=str(project_path),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        return proc.returncode or 0, stdout.decode(), stderr.decode()

    try:
        # Check if repo is initialized
        code, _, _ = await run_git(["status"])
        if code != 0:
            await run_git(["init"])
            await run_git(["checkout", "-b", state["git_base_branch"]])

        # Create/checkout branch
        branch = state["git_branch"]
        code, _, _ = await run_git(["checkout", "-b", branch])
        if code != 0:
            await run_git(["checkout", branch])

        # Write files and stage
        for path, change in state["working_files"].items():
            full_path = project_path / path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(change["new_content"])
            await run_git(["add", path])

        # Commit
        code, stdout, stderr = await run_git(["commit", "-m", commit_message])
        if code != 0 and "nothing to commit" not in stderr:
            return {
                "current_node": "git_manager",
                "status_message": f"Commit failed: {stderr}",
                "needs_human_review": True,
                "messages": [
                    {
                        "role": "assistant",
                        "content": f"Local commit failed: {stderr}",
                        "node": "git_manager",
                    }
                ],
            }

        return {
            "commit_messages": state["commit_messages"] + [commit_message],
            "current_node": "git_manager",
            "status_message": f"Changes committed locally to branch: {branch}",
            "is_complete": True,
            "messages": [
                {
                    "role": "assistant",
                    "content": f"Changes committed locally:\n\n**Branch:** {branch}\n**Commit:** {commit_message}\n\n*Note: GitHub integration not configured. Push manually to create PR.*",
                    "node": "git_manager",
                }
            ],
        }

    except Exception as e:
        return {
            "current_node": "git_manager",
            "status_message": f"Git operation failed: {e}",
            "needs_human_review": True,
            "messages": [
                {
                    "role": "assistant",
                    "content": f"Git operation failed: {e}",
                    "node": "git_manager",
                }
            ],
        }
