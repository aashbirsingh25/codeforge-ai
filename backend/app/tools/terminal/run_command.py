import os
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Union, Optional

from app.tools.base import BaseTool
from app.tools.schemas import RunCommandRequest, RunCommandResponse
from app.tools.exceptions import CommandExecutionError, PathTraversalError

ALLOWED_EXECUTABLES = {
    "git", "python", "python3", "pip", "pytest", "npm", "node",
    "ls", "cat", "pwd", "echo", "mkdir", "find", "grep"
}

TRUNCATION_MARKER = "\n[...output truncated at 1MB...]"
MAX_OUTPUT_BYTES = 1024 * 1024  # 1MB limit


def _set_resource_limits():
    """Sets OS resource limits for child processes on Linux/POSIX systems."""
    try:
        import resource
        # RLIMIT_CPU: 60 seconds
        resource.setrlimit(resource.RLIMIT_CPU, (60, 60))
        # RLIMIT_AS: 2GB
        mem_bytes = 2 * 1024 * 1024 * 1024
        resource.setrlimit(resource.RLIMIT_AS, (mem_bytes, mem_bytes))
        # RLIMIT_FSIZE: 50MB
        fsize_bytes = 50 * 1024 * 1024
        resource.setrlimit(resource.RLIMIT_FSIZE, (fsize_bytes, fsize_bytes))
    except ImportError:
        pass


def _cap_output(output: Optional[str]) -> str:
    """Caps output string at 1MB, appending truncation marker if exceeded."""
    if not output:
        return ""
    if len(output) > MAX_OUTPUT_BYTES:
        return output[:MAX_OUTPUT_BYTES] + TRUNCATION_MARKER
    return output


class RunCommandTool(BaseTool):
    """Tool to execute terminal/shell commands in the workspace."""
    tool_name = "run_command"
    description = (
        "Execute a terminal command in the workspace. Returns standard output, "
        "standard error, and exit status code. Interactive commands are not supported."
    )
    category = "terminal"
    input_schema = RunCommandRequest
    output_schema = RunCommandResponse

    def __init__(
        self,
        workspace_root: Union[str, Path, None] = None,
        default_timeout: float = 30.0,
        default_cwd: str = "."
    ):
        if workspace_root is None:
            from app.core.config import settings
            self.workspace_root = Path(settings.WORKSPACE_DIR).resolve()
        else:
            self.workspace_root = Path(workspace_root).resolve()
        self.default_timeout = default_timeout
        self.default_cwd = default_cwd

    def resolve_cwd(self, cwd_param: Optional[str]) -> Path:
        """Resolves the working directory for command execution.

        Checks for path traversal and ensures it's inside the workspace.
        """
        cwd_to_resolve = cwd_param or self.default_cwd
        rel = Path(cwd_to_resolve)
        
        if rel.is_absolute():
            resolved = rel.resolve()
        else:
            rel_str = str(rel).lstrip("\\/")
            resolved = (self.workspace_root / rel_str).resolve()

        try:
            if not resolved.is_relative_to(self.workspace_root):
                raise PathTraversalError(
                    f"Security Violation: CWD '{cwd_to_resolve}' is outside workspace."
                )
        except ValueError:
            raise PathTraversalError(
                f"Security Violation: CWD '{cwd_to_resolve}' is outside workspace."
            )
        return resolved

    def execute(
        self,
        command: str,
        timeout: Optional[float] = None,
        cwd: Optional[str] = None
    ) -> RunCommandResponse:
        """Executes shell command in workspace and returns output."""
        resolved_cwd = self.resolve_cwd(cwd)
        exec_timeout = timeout if timeout is not None else self.default_timeout

        # Parse command string into list of arguments safely
        is_windows = sys.platform == "win32"
        try:
            args = shlex.split(command, posix=not is_windows)
            if is_windows:
                args = [arg.strip('"\'') for arg in args]
        except ValueError as e:
            raise CommandExecutionError(f"Failed to parse command string: {str(e)}") from e

        if not args:
            raise CommandExecutionError("Command cannot be empty.")

        # On Windows, resolve npm to npm.cmd for subprocess.run without shell=True
        if is_windows and Path(args[0]).name.lower() == "npm":
            args[0] = "npm.cmd"

        # Extract base executable name and check allowlist
        raw_exe = Path(args[0]).name.lower()
        if raw_exe.endswith(".exe"):
            raw_exe = raw_exe[:-4]
        elif raw_exe.endswith(".cmd"):
            raw_exe = raw_exe[:-4]

        is_allowed = (
            raw_exe in ALLOWED_EXECUTABLES
            or raw_exe.startswith("python3.")
            or raw_exe.startswith("python.")
        )
        if not is_allowed:
            raise CommandExecutionError(
                f"Command executable '{args[0]}' is not allowed."
            )

        # Build minimal environment dict (fixes secret leakage while preserving required OS variables)
        ALLOWED_ENV_KEYS = (
            "PATH", "HOME", "LANG", "LC_ALL",
            "SystemRoot", "SYSTEMROOT", "PATHEXT",
            "TEMP", "TMP"
        )
        env = {}
        for env_key in ALLOWED_ENV_KEYS:
            if env_key in os.environ:
                env[env_key] = os.environ[env_key]

        # Resource limits preexec_fn (Linux/POSIX only)
        preexec = _set_resource_limits if not is_windows else None

        try:
            result = subprocess.run(
                args,
                cwd=resolved_cwd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=exec_timeout,
                shell=False,
                env=env,
                preexec_fn=preexec
            )
            return RunCommandResponse(
                stdout=_cap_output(result.stdout),
                stderr=_cap_output(result.stderr),
                exit_code=result.returncode,
                timeout_expired=False
            )
        except subprocess.TimeoutExpired as e:
            raw_stdout = e.stdout if isinstance(e.stdout, str) else (e.stdout or b"").decode("utf-8", errors="ignore")
            raw_stderr = e.stderr if isinstance(e.stderr, str) else (e.stderr or b"").decode("utf-8", errors="ignore")
            return RunCommandResponse(
                stdout=_cap_output(raw_stdout),
                stderr=_cap_output(raw_stderr),
                exit_code=-1,
                timeout_expired=True
            )
        except FileNotFoundError as e:
            raise CommandExecutionError(
                f"Command executable '{args[0]}' not found. (Make sure executable is installed and in PATH)"
            ) from e
        except Exception as e:
            raise CommandExecutionError(f"Error during command execution: {str(e)}") from e
