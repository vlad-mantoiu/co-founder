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

import httpx
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
            logger.warning("beta_pause() failed (may be unsupported on Hobby tier): %s", e)

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
        on_stdout=None,  # Optional[Callable[[str], Awaitable[None]]]
        on_stderr=None,  # Optional[Callable[[str], Awaitable[None]]]
    ) -> dict:
        """Run a shell command in the sandbox.

        Args:
            command: Shell command to execute
            timeout: Timeout in seconds (default 120)
            cwd: Working directory (optional, defaults to /home/user)
            on_stdout: Optional async callback for stdout chunks (e.g. LogStreamer.on_stdout)
            on_stderr: Optional async callback for stderr chunks (e.g. LogStreamer.on_stderr)

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
                on_stdout=on_stdout,
                on_stderr=on_stderr,
            )
            return {
                "stdout": result.stdout,
                "stderr": result.stderr,
                "exit_code": result.exit_code,
            }
        except Exception as e:
            raise SandboxError(f"Failed to run command '{command}': {e}") from e

    async def run_background(
        self,
        command: str,
        cwd: str | None = None,
        on_stdout=None,  # Optional[Callable[[str], Awaitable[None]]]
        on_stderr=None,  # Optional[Callable[[str], Awaitable[None]]]
    ) -> str:
        """Run a command in the background (e.g., dev server).

        Args:
            command: Shell command to execute
            cwd: Working directory (optional)
            on_stdout: Optional async callback for stdout chunks (e.g. LogStreamer.on_stdout)
            on_stderr: Optional async callback for stderr chunks (e.g. LogStreamer.on_stderr)

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
            handle = await self._sandbox.commands.run(
                command,
                background=True,
                cwd=work_dir,
                on_stdout=on_stdout,
                on_stderr=on_stderr,
            )
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

    @staticmethod
    def _detect_framework(package_json_content: str) -> tuple[str, int]:
        """Detect framework from package.json and return (start_command, port).

        Detection priority:
        1. Next.js (deps: "next") → "npm run dev", 3000
        2. Vite (deps: "vite") → "npm run dev", 5173
        3. Create React App (deps: "react-scripts") → "npm start", 3000
        4. Express/Hono (deps: "express" or "@hono/node-server") → "npm start", 3000
        5. Fallback: check scripts.dev → "npm run dev", 3000
        6. Last resort: "npm run dev", 3000
        """
        import json

        try:
            pkg = json.loads(package_json_content)
        except (json.JSONDecodeError, TypeError):
            return ("npm run dev", 3000)

        deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
        scripts = pkg.get("scripts", {})

        if "next" in deps:
            return ("npm run dev", 3000)
        if "vite" in deps:
            return ("npm run dev", 5173)
        if "react-scripts" in deps:
            return ("npm start", 3000)
        if "express" in deps or "@hono/node-server" in deps:
            return ("npm start", 3000)

        if "dev" in scripts:
            return ("npm run dev", 3000)
        if "start" in scripts:
            return ("npm start", 3000)

        return ("npm run dev", 3000)

    async def _wait_for_dev_server(self, url: str, timeout: int = 120, interval: float = 3.0) -> None:
        """Poll URL with httpx until a non-5xx response or timeout.

        Args:
            url: Full HTTPS preview URL to poll
            timeout: Max seconds to wait (default: 120)
            interval: Seconds between poll attempts (default: 3.0)

        Raises:
            SandboxError: If server doesn't respond within timeout
        """
        import asyncio

        deadline = asyncio.get_event_loop().time() + timeout
        async with httpx.AsyncClient(verify=False, timeout=10.0) as client:
            while asyncio.get_event_loop().time() < deadline:
                try:
                    resp = await client.get(url, follow_redirects=True)
                    if resp.status_code < 500:
                        return  # Server is up
                except (httpx.ConnectError, httpx.TimeoutException, httpx.RemoteProtocolError):
                    pass  # Server not ready yet
                await asyncio.sleep(interval)

        raise SandboxError(f"Dev server did not become ready within {timeout}s at {url}")

    async def start_dev_server(
        self,
        workspace_path: str,
        working_files: dict | None = None,
        on_stdout=None,  # Optional[Callable[[str], Awaitable[None]]]
        on_stderr=None,  # Optional[Callable[[str], Awaitable[None]]]
    ) -> str:
        """Detect framework, start dev server, wait for readiness, return preview_url.

        Args:
            workspace_path: Absolute path to project root in sandbox (e.g., /home/user/project)
            working_files: Dict of file paths to FileChange dicts. Used to read package.json
                           for framework detection without a sandbox filesystem read.
            on_stdout: Optional async callback for stdout chunks (e.g. LogStreamer.on_stdout)
            on_stderr: Optional async callback for stderr chunks (e.g. LogStreamer.on_stderr)

        Returns:
            HTTPS preview URL that is confirmed live (non-5xx response)

        Raises:
            SandboxError: If sandbox not started, or server fails to become ready
        """
        if not self._sandbox:
            raise SandboxError("Sandbox not started")

        # Detect framework from package.json
        package_json_content = None
        if working_files:
            # Try to find package.json in working_files (may be at root or workspace-relative path)
            for key in ["package.json", f"{workspace_path}/package.json", "/home/user/project/package.json"]:
                fc = working_files.get(key)
                if fc:
                    package_json_content = fc.get("new_content", "") if isinstance(fc, dict) else str(fc)
                    break

        if package_json_content is None:
            # Read from sandbox filesystem as fallback
            try:
                package_json_content = await self.read_file(f"{workspace_path}/package.json")
            except SandboxError:
                package_json_content = ""

        start_cmd, port = self._detect_framework(package_json_content)

        # Install dependencies first
        install_result = await self.run_command(
            "npm install", timeout=300, cwd=workspace_path, on_stdout=on_stdout, on_stderr=on_stderr
        )
        if install_result.get("exit_code", 1) != 0:
            stderr = install_result.get("stderr", "")
            # Retry once on network errors
            if any(keyword in stderr.lower() for keyword in ["econnreset", "network", "etimedout"]):
                import asyncio

                await asyncio.sleep(10)
                install_result = await self.run_command(
                    "npm install", timeout=300, cwd=workspace_path, on_stdout=on_stdout, on_stderr=on_stderr
                )
                if install_result.get("exit_code", 1) != 0:
                    raise SandboxError(f"npm install failed after retry: {install_result.get('stderr', '')[:500]}")
            else:
                raise SandboxError(f"npm install failed: {install_result.get('stderr', '')[:500]}")

        # Start dev server in background
        await self.run_background(start_cmd, cwd=workspace_path, on_stdout=on_stdout, on_stderr=on_stderr)

        # Build preview URL
        host = self.get_host(port)
        preview_url = f"https://{host}"

        # Poll until server responds
        await self._wait_for_dev_server(preview_url, timeout=120)

        return preview_url

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
