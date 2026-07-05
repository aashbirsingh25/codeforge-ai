import subprocess
from pathlib import Path
from typing import Union

from app.tools.base import BaseTool
from app.tools.schemas import GitStatusRequest, GitStatusResponse
from app.tools.exceptions import GitError


class GitStatusTool(BaseTool):
    """Tool to execute 'git status' and check if workspace has uncommitted changes."""
    tool_name = "git_status"
    description = "Run 'git status' in the workspace root to check for modified, deleted, or untracked files."
    category = "git"
    input_schema = GitStatusRequest
    output_schema = GitStatusResponse

    def __init__(self, workspace_root: Union[str, Path, None] = None):
        if workspace_root is None:
            from app.core.config import settings
            self.workspace_root = Path(settings.WORKSPACE_DIR).resolve()
        else:
            self.workspace_root = Path(workspace_root).resolve()

    def execute(self) -> GitStatusResponse:
        """Runs git status and checks if workspace is clean."""
        # 1. Run git status for human readable output
        try:
            res = subprocess.run(
                ["git", "status"],
                cwd=self.workspace_root,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                shell=False
            )
            if res.returncode != 0:
                raise GitError(f"Git command failed (Exit Code {res.returncode}): {res.stderr}")
            
            # 2. Run git status --porcelain to accurately determine if clean
            res_porcelain = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=self.workspace_root,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                shell=False
            )
            is_clean = len(res_porcelain.stdout.strip()) == 0

            return GitStatusResponse(
                status_output=res.stdout or "",
                is_clean=is_clean,
                exit_code=res.returncode
            )
        except FileNotFoundError as e:
            raise GitError("git command not found on host machine. Make sure Git is installed and in PATH.") from e
        except Exception as e:
            raise GitError(f"Error executing git status: {str(e)}") from e
