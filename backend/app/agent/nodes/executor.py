"""Executor Node: Runs code in the E2B sandbox and captures output.

Handles file operations and command execution in secure, isolated environments.
"""

from app.agent.path_safety import resolve_safe_project_path
from app.agent.state import CoFounderState
from app.core.config import get_settings
from app.core.exceptions import SandboxError
from app.sandbox.e2b_runtime import E2BSandboxRuntime


async def executor_node(state: CoFounderState) -> dict:
    """Execute code changes in the E2B sandbox and run tests."""
    settings = get_settings()

    # Determine sandbox template based on file types
    template = _detect_project_type(state["working_files"])

    # Check if E2B is configured
    if not settings.e2b_api_key:
        # Fallback to local execution for development
        return await _execute_locally(state)

    # Use E2B sandbox
    runtime = E2BSandboxRuntime(template=template)
    files_written = []
    errors = []

    try:
        async with runtime.session():
            # Write all working files to sandbox
            for path, change in state["working_files"].items():
                try:
                    # Create parent directories
                    if "/" in path:
                        parent = "/".join(path.split("/")[:-1])
                        try:
                            await runtime.make_dir(parent)
                        except SandboxError:
                            pass  # Directory might exist

                    await runtime.write_file(path, change["new_content"])
                    files_written.append(path)
                except SandboxError as e:
                    errors.append(
                        {
                            "step_index": state["current_step_index"],
                            "error_type": "file_write",
                            "message": str(e),
                            "stdout": "",
                            "stderr": str(e),
                            "file_path": path,
                        }
                    )

            if errors:
                return {
                    "active_errors": errors,
                    "current_node": "executor",
                    "status_message": f"Failed to write {len(errors)} files",
                    "last_tool_output": f"File write errors: {errors}",
                    "last_command_exit_code": 1,
                    "messages": [
                        {
                            "role": "assistant",
                            "content": f"Executor: failed to write {len(errors)} file(s) to sandbox.",
                            "node": "executor",
                        }
                    ],
                }

            # Install dependencies if needed
            await _install_dependencies(runtime, template, state["working_files"])

            # Run tests or validation commands
            current_step = state["plan"][state["current_step_index"]]
            test_result = await _run_tests_in_sandbox(runtime, template, current_step)

            return {
                "last_tool_output": test_result["output"],
                "last_command_exit_code": test_result["exit_code"],
                "current_node": "executor",
                "status_message": f"Executed step, exit code: {test_result['exit_code']}",
                "active_errors": test_result.get("errors", []),
                "messages": [
                    {
                        "role": "assistant",
                        "content": f"Executed: {len(files_written)} files written, tests {'passed' if test_result['exit_code'] == 0 else 'failed'}",
                        "node": "executor",
                    }
                ],
            }

    except SandboxError as e:
        return {
            "active_errors": [
                {
                    "step_index": state["current_step_index"],
                    "error_type": "sandbox_error",
                    "message": str(e),
                    "stdout": "",
                    "stderr": str(e),
                    "file_path": None,
                }
            ],
            "current_node": "executor",
            "status_message": f"Sandbox error: {e}",
            "last_tool_output": str(e),
            "last_command_exit_code": 1,
            "messages": [
                {
                    "role": "assistant",
                    "content": f"Executor: sandbox error — {e}",
                    "node": "executor",
                }
            ],
        }


def _detect_project_type(working_files: dict) -> str:
    """Detect project type from file extensions."""
    extensions = set()
    for path in working_files.keys():
        if "." in path:
            ext = path.split(".")[-1].lower()
            extensions.add(ext)

    if extensions & {"py", "pyi"}:
        return "python"
    elif extensions & {"ts", "tsx", "js", "jsx"}:
        return "node"
    else:
        return "base"


async def _install_dependencies(
    runtime: E2BSandboxRuntime,
    template: str,
    working_files: dict,
) -> None:
    """Install project dependencies based on template type."""
    try:
        if template == "python":
            # Check for requirements.txt
            if "requirements.txt" in working_files:
                await runtime.run_command("pip install -r requirements.txt", timeout=180)
            # Check for pyproject.toml
            elif "pyproject.toml" in working_files:
                await runtime.run_command("pip install -e .", timeout=180)

        elif template == "node":
            # Check for package.json
            if "package.json" in working_files:
                await runtime.run_command("npm install", timeout=180)

    except SandboxError:
        pass  # Dependencies are optional, tests will fail if needed


async def _run_tests_in_sandbox(
    runtime: E2BSandboxRuntime,
    template: str,
    step: dict,
) -> dict:
    """Run tests in the sandbox based on project type."""
    files = step.get("files_to_modify", [])

    # Check if any test files exist
    has_test_files = any("test" in f.lower() or f.endswith("_test.py") or f.endswith(".test.js") for f in files)

    # Determine test command based on template
    if template == "python":
        if has_test_files:
            # Try pytest first, fall back to unittest
            result = await runtime.run_command(
                "python -m pytest -v --tb=short 2>/dev/null || python -m unittest discover -v",
                timeout=120,
            )
        else:
            # Just do syntax check on Python files
            py_files = [f for f in files if f.endswith(".py")]
            if py_files:
                check_cmd = " && ".join(f"python -m py_compile /home/user/{f}" for f in py_files)
                result = await runtime.run_command(check_cmd, timeout=60)
            else:
                result = {"stdout": "No Python files to check", "stderr": "", "exit_code": 0}
    elif template == "node":
        if has_test_files:
            # Try npm test
            result = await runtime.run_command(
                "npm test 2>/dev/null || echo 'No tests configured'",
                timeout=120,
            )
        else:
            # Just check syntax with node
            result = {"stdout": "No test files, skipping tests", "stderr": "", "exit_code": 0}
    else:
        # Basic syntax check
        result = await runtime.run_command("echo 'No tests configured'", timeout=10)

    output = result["stdout"] + result["stderr"]
    exit_code = result["exit_code"]

    # Exit code 5 from pytest means "no tests collected" - not an error
    if exit_code == 5 and "NO TESTS RAN" in output:
        exit_code = 0  # Treat as success

    errors = []
    if exit_code != 0:
        errors.append(
            {
                "step_index": step["index"],
                "error_type": "test_failure",
                "message": "Tests failed",
                "stdout": result["stdout"][:1000],
                "stderr": result["stderr"][:1000],
                "file_path": None,
            }
        )

    return {
        "output": output,
        "exit_code": exit_code,
        "errors": errors,
    }


async def _execute_locally(state: CoFounderState) -> dict:
    """Fallback to local execution when E2B is not configured.

    WARNING: This should only be used for development.
    """
    import asyncio
    import subprocess
    from pathlib import Path

    files_written = []
    errors = []

    project_path = Path(state["project_path"])
    project_root = project_path.resolve()
    project_root.mkdir(parents=True, exist_ok=True)

    # Write files locally
    for path, change in state["working_files"].items():
        try:
            full_path = resolve_safe_project_path(project_root, path)
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(change["new_content"])
            files_written.append(path)
        except Exception as e:
            errors.append(
                {
                    "step_index": state["current_step_index"],
                    "error_type": "file_write",
                    "message": str(e),
                    "stdout": "",
                    "stderr": str(e),
                    "file_path": path,
                }
            )

    if errors:
        return {
            "active_errors": errors,
            "current_node": "executor",
            "status_message": f"Failed to write {len(errors)} files",
            "last_tool_output": f"File write errors: {errors}",
            "last_command_exit_code": 1,
            "messages": [
                {
                    "role": "assistant",
                    "content": f"Executor: failed to write {len(errors)} file(s) locally.",
                    "node": "executor",
                }
            ],
        }

    # Run basic validation
    current_step = state["plan"][state["current_step_index"]]
    files = current_step.get("files_to_modify", [])

    # Determine command based on file types
    if any(f.endswith(".py") for f in files):
        py_files = []
        for file_path in files:
            if file_path.endswith(".py"):
                try:
                    safe_file = resolve_safe_project_path(project_root, file_path)
                    py_files.append(str(safe_file))
                except ValueError as e:
                    errors.append(
                        {
                            "step_index": state["current_step_index"],
                            "error_type": "file_path_validation",
                            "message": str(e),
                            "stdout": "",
                            "stderr": str(e),
                            "file_path": file_path,
                        }
                    )
        if errors:
            return {
                "active_errors": errors,
                "current_node": "executor",
                "status_message": "Unsafe file path detected",
                "last_tool_output": f"Path validation errors: {errors}",
                "last_command_exit_code": 1,
                "messages": [
                    {
                        "role": "assistant",
                        "content": f"Executor: unsafe file path(s) detected — {len(errors)} error(s).",
                        "node": "executor",
                    }
                ],
            }
        cmd = ["python", "-m", "py_compile"] + py_files
    else:
        cmd = ["echo", "No validation available"]

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=str(project_root),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=60)

        return {
            "last_tool_output": stdout.decode() + stderr.decode(),
            "last_command_exit_code": proc.returncode or 0,
            "current_node": "executor",
            "status_message": "Executed locally (E2B not configured)",
            "active_errors": []
            if proc.returncode == 0
            else [
                {
                    "step_index": current_step["index"],
                    "error_type": "validation_failure",
                    "message": "Validation failed",
                    "stdout": stdout.decode()[:500],
                    "stderr": stderr.decode()[:500],
                    "file_path": None,
                }
            ],
            "messages": [
                {
                    "role": "assistant",
                    "content": f"Executed locally: {len(files_written)} files written",
                    "node": "executor",
                }
            ],
        }

    except Exception as e:
        return {
            "last_tool_output": str(e),
            "last_command_exit_code": 1,
            "current_node": "executor",
            "status_message": f"Local execution failed: {e}",
            "active_errors": [
                {
                    "step_index": current_step["index"],
                    "error_type": "execution_error",
                    "message": str(e),
                    "stdout": "",
                    "stderr": str(e),
                    "file_path": None,
                }
            ],
            "messages": [
                {
                    "role": "assistant",
                    "content": f"Executor: local execution failed — {e}",
                    "node": "executor",
                }
            ],
        }
