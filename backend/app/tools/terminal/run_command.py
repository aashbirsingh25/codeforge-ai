import shlex
import subprocess
import sys
from pathlib import Path
from typing import Union, Optional

from app.tools.base import BaseTool
from app.tools.schemas import RunCommandRequest, RunCommandResponse
from app.tools.exceptions import CommandTimeoutError, CommandExecutionError, PathTraversalError


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
        # Use Windows-friendly parsing (posix=False) on Windows to avoid swallowing backslashes
        is_windows = sys.platform == "win32"
        try:
            args = shlex.split(command, posix=not is_windows)
            if is_windows:
                # Strip leading and trailing quotes from each argument since posix=False preserves them
                args = [arg.strip('"\'') for arg in args]
        except ValueError as e:
            raise CommandExecutionError(f"Failed to parse command string: {str(e)}") from e

        if not args:
            raise CommandExecutionError("Command cannot be empty.")

        try:
            # shell=False ensures command args are passed directly, preventing shell injection
            result = subprocess.run(
                args,
                cwd=resolved_cwd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=exec_timeout,
                shell=False
            )
            return RunCommandResponse(
                stdout=result.stdout or "",
                stderr=result.stderr or "",
                exit_code=result.returncode,
                timeout_expired=False
            )
        except subprocess.TimeoutExpired as e:
            # Retrieve whatever stdout/stderr was generated before timeout
            stdout_str = e.stdout if isinstance(e.stdout, str) else (e.stdout or b"").decode("utf-8", errors="ignore")
            stderr_str = e.stderr if isinstance(e.stderr, str) else (e.stderr or b"").decode("utf-8", errors="ignore")
            return RunCommandResponse(
                stdout=stdout_str,
                stderr=stderr_str,
                exit_code=-1,
                timeout_expired=True
            )
        except FileNotFoundError as e:
            # Raised when executable is not found
            raise CommandExecutionError(
                f"Command executable '{args[0]}' not found. (Make sure executable is installed and in PATH)"
            ) from e
        except Exception as e:
            raise CommandExecutionError(f"Error during command execution: {str(e)}") from e
