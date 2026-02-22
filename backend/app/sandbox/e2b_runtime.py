"""E2B Sandbox Runtime: Secure code execution environment.

This module provides a sandboxed environment for the AI Co-Founder to:
- Write and read files safely
- Execute shell commands
- Run long-running processes in the background
- Sync files between sandbox and persistent storage
"""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from e2b_code_interpreter import AsyncSandbox

from app.core.config import get_settings
from app.core.exceptions import SandboxError

logger = logging.getLogger(__name__)


class E2BSandboxRuntime:
    """Manages E2B sandbox instances for secure code execution."""

    def __init__(self, template: str = "base"):
        """Initialize the E2B runtime.

        Args:
            template: E2B template to use. Options: "base", "python", "node"
        """
        self.settings = get_settings()
        self.template = template
        self._sandbox: AsyncSandbox | None = None
        self._background_processes: dict[str, any] = {}

    @asynccontextmanager
    async def session(self) -> AsyncGenerator["E2BSandboxRuntime", None]:
        """Context manager for sandbox sessions.

        Usage:
            async with E2BSandboxRuntime().session() as runtime:
                await runtime.write_file("main.py", "print('hello')")
                result = await runtime.run_command("python main.py")
        """
        try:
            await self.start()
            yield self
        finally:
            await self.stop()

    async def start(self) -> None:
        """Start a new sandbox instance."""
        import os

        if self._sandbox:
            return

        try:
            # E2B v1.x API - set API key via environment variable
            os.environ["E2B_API_KEY"] = self.settings.e2b_api_key

            self._sandbox = await AsyncSandbox.create()
        except Exception as e:
            raise SandboxError(f"Failed to start sandbox: {e}") from e

    async def connect(self, sandbox_id: str) -> None:
        """Reconnect to an existing sandbox by its sandbox_id.

        Used for iteration builds (GENL-02): patches existing sandbox instead of
        creating a new one. If the sandbox has expired, raises SandboxError.

        Args:
            sandbox_id: E2B sandbox ID to reconnect to

        Raises:
            SandboxError: If sandbox has expired or connection fails
        """
        import os

        try:
            os.environ["E2B_API_KEY"] = self.settings.e2b_api_key
            self._sandbox = await AsyncSandbox.connect(sandbox_id)
        except Exception as e:
            raise SandboxError(f"Failed to connect to sandbox {sandbox_id}: {e}") from e

    async def stop(self) -> None:
        """Stop the sandbox instance and clean up."""
        if not self._sandbox:
            return

        # Kill all background processes
        for pid in list(self._background_processes.keys()):
            await self.kill_process(pid)

        try:
            await self._sandbox.kill()
        except Exception:
            pass  # Best effort cleanup

        self._sandbox = None

    async def set_timeout(self, seconds: int) -> None:
        """Extend sandbox lifetime. Must be awaited.

        Args:
            seconds: New timeout in seconds
        """
        if not self._sandbox:
            return
        await self._sandbox.set_timeout(seconds)

    async def beta_pause(self) -> None:
        """Pause (snapshot) the sandbox for later reconnection via connect().

        Per locked decision: always use explicit beta_pause(), never auto_pause=True
        (E2B #884 bug: file loss on multi-resume).

        Wraps in try/except because E2B Hobby plan does not support pause —
        if it fails, logs a warning and returns without raising.
        """
        if not self._sandbox:
            return
        try:
            await self._sandbox.beta_pause()
        except Exception as e:
            logger.warning(
                "beta_pause() failed (may be unsupported on Hobby tier): %s", e
            )

    @property
    def sandbox_id(self) -> str | None:
        """Return the sandbox ID for reconnection."""
        return self._sandbox.sandbox_id if self._sandbox else None

    def get_host(self, port: int) -> str:
        """Get the public hostname for a port. Synchronous — no await needed.

        Args:
            port: Port number to get public hostname for

        Returns:
            Public hostname string
        """
        if not self._sandbox:
            raise SandboxError("Sandbox not started")
        return self._sandbox.get_host(port)

    async def write_file(self, path: str, content: str) -> None:
        """Write content to a file in the sandbox.

        Args:
            path: File path relative to sandbox root (e.g., "src/main.py")
            content: File content to write
        """
        if not self._sandbox:
            raise SandboxError("Sandbox not started")

        try:
            # E2B expects absolute paths - prepend /home/user if relative
            abs_path = path if path.startswith("/") else f"/home/user/{path}"
            # E2B files.write() accepts str, bytes, or IO directly
            await self._sandbox.files.write(abs_path, content)
        except Exception as e:
            raise SandboxError(f"Failed to write file {path}: {e}") from e

    async def read_file(self, path: str) -> str:
        """Read content from a file in the sandbox.

        Args:
            path: File path relative to sandbox root

        Returns:
            File content as string
        """
        if not self._sandbox:
            raise SandboxError("Sandbox not started")

        try:
            # E2B expects absolute paths
            abs_path = path if path.startswith("/") else f"/home/user/{path}"
            content = await self._sandbox.files.read(abs_path)
            # Content may be bytes, decode if needed
            if isinstance(content, bytes):
                return content.decode("utf-8")
            return content
        except Exception as e:
            raise SandboxError(f"Failed to read file {path}: {e}") from e

    async def list_files(self, path: str = "/") -> list[str]:
        """List files in a directory.

        Args:
            path: Directory path relative to sandbox root

        Returns:
            List of file/directory names
        """
        if not self._sandbox:
            raise SandboxError("Sandbox not started")

        try:
            # E2B expects absolute paths
            abs_path = path if path.startswith("/") else f"/home/user/{path}"
            files = await self._sandbox.files.list(abs_path)
            return [f.name for f in files]
        except Exception as e:
            raise SandboxError(f"Failed to list files in {path}: {e}") from e

    async def make_dir(self, path: str) -> None:
        """Create a directory in the sandbox.

        Args:
            path: Directory path to create
        """
        if not self._sandbox:
            raise SandboxError("Sandbox not started")

        try:
            # E2B expects absolute paths
            abs_path = path if path.startswith("/") else f"/home/user/{path}"
            await self._sandbox.files.make_dir(abs_path)
        except Exception as e:
            raise SandboxError(f"Failed to create directory {path}: {e}") from e

    async def run_command(
        self,
        command: str,
        timeout: int = 120,
        cwd: str | None = None,
    ) -> dict:
        """Run a shell command in the sandbox.

        Args:
            command: Shell command to execute
            timeout: Timeout in seconds (default 120)
            cwd: Working directory (optional, defaults to /home/user)

        Returns:
            Dict with keys: stdout, stderr, exit_code
        """
        if not self._sandbox:
            raise SandboxError("Sandbox not started")

        try:
            # Default to user home directory
            work_dir = cwd if cwd else "/home/user"
            if not work_dir.startswith("/"):
                work_dir = f"/home/user/{work_dir}"

            result = await self._sandbox.commands.run(
                command,
                timeout=float(timeout),
                cwd=work_dir,
            )
            return {
                "stdout": result.stdout,
                "stderr": result.stderr,
                "exit_code": result.exit_code,
            }
        except Exception as e:
            raise SandboxError(f"Failed to run command '{command}': {e}") from e

    async def run_background(self, command: str, cwd: str | None = None) -> str:
        """Run a command in the background (e.g., dev server).

        Args:
            command: Shell command to execute
            cwd: Working directory (optional)

        Returns:
            Process ID for later reference
        """
        if not self._sandbox:
            raise SandboxError("Sandbox not started")

        try:
            # Default to user home directory
            work_dir = cwd if cwd else "/home/user"
            if not work_dir.startswith("/"):
                work_dir = f"/home/user/{work_dir}"

            # Use commands.run with background=True to get a CommandHandle
            handle = await self._sandbox.commands.run(command, background=True, cwd=work_dir)
            pid = str(handle.pid)
            self._background_processes[pid] = handle
            return pid
        except Exception as e:
            raise SandboxError(f"Failed to start background command '{command}': {e}") from e

    async def get_process_output(self, pid: str) -> dict:
        """Get output from a background process.

        Args:
            pid: Process ID from run_background

        Returns:
            Dict with keys: stdout, stderr, running
        """
        if pid not in self._background_processes:
            raise SandboxError(f"Process {pid} not found")

        _handle = self._background_processes[pid]
        # CommandHandle tracks the process - check if it's still running
        # by checking if pid is in the list of running processes
        try:
            processes = await self._sandbox.commands.list()
            running = any(p.pid == int(pid) for p in processes)
            return {
                "stdout": "",  # Output streams in background, not accessible directly
                "stderr": "",
                "running": running,
            }
        except Exception:
            return {
                "stdout": "",
                "stderr": "",
                "running": False,
            }

    async def kill_process(self, pid: str) -> None:
        """Kill a background process.

        Args:
            pid: Process ID from run_background
        """
        if pid not in self._background_processes:
            return

        try:
            # Use commands.kill(pid) to kill the process
            await self._sandbox.commands.kill(int(pid))
        except Exception:
            pass  # Best effort
        finally:
            del self._background_processes[pid]

    async def install_packages(self, packages: list[str], manager: str = "pip") -> dict:
        """Install packages in the sandbox.

        Args:
            packages: List of package names to install
            manager: Package manager ("pip", "npm", "yarn")

        Returns:
            Command result dict
        """
        if manager == "pip":
            cmd = f"pip install {' '.join(packages)}"
        elif manager == "npm":
            cmd = f"npm install {' '.join(packages)}"
        elif manager == "yarn":
            cmd = f"yarn add {' '.join(packages)}"
        else:
            raise SandboxError(f"Unknown package manager: {manager}")

        return await self.run_command(cmd, timeout=300)


# Convenience function for one-off commands
async def execute_in_sandbox(
    files: dict[str, str],
    command: str,
    template: str = "base",
) -> dict:
    """Execute a command in a fresh sandbox with the given files.

    Args:
        files: Dict of file paths to content
        command: Command to execute after writing files
        template: Sandbox template to use

    Returns:
        Command result dict with stdout, stderr, exit_code
    """
    runtime = E2BSandboxRuntime(template=template)

    async with runtime.session():
        # Write all files
        for path, content in files.items():
            # Create parent directories
            if "/" in path:
                parent = "/".join(path.split("/")[:-1])
                try:
                    await runtime.make_dir(parent)
                except SandboxError:
                    pass  # Directory might exist

            await runtime.write_file(path, content)

        # Run command
        return await runtime.run_command(command)
