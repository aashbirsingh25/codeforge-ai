import os
from pathlib import Path
from typing import Union
from app.tools.exceptions import PathTraversalError


class BaseFileSystemTool:
    """Helper base class for filesystem tools to configure the workspace root

    and prevent path traversal violations.
    """
    def __init__(self, workspace_root: Union[str, Path, None] = None):
        if workspace_root is None:
            from app.core.config import settings
            self.workspace_root = Path(settings.WORKSPACE_DIR).resolve()
        else:
            self.workspace_root = Path(workspace_root).resolve()

    def resolve_path(self, relative_path: Union[str, Path]) -> Path:
        """Resolves a path relative to the workspace root and checks for path traversal.

        Raises PathTraversalError if resolved path is outside workspace root.
        """
        rel_p = Path(relative_path)
        
        # If absolute path is passed, check if it's already in the workspace
        if rel_p.is_absolute():
            resolved_target = rel_p.resolve()
        else:
            # Strip leading slashes to prevent resolving to system root
            # e.g. path "/etc/passwd" becomes relative to workspace root
            rel_str = str(rel_p).lstrip("\\/")
            resolved_target = (self.workspace_root / rel_str).resolve()

        try:
            if not resolved_target.is_relative_to(self.workspace_root):
                raise PathTraversalError(
                    f"Security Violation: Access denied to path outside workspace."
                )
        except ValueError:
            raise PathTraversalError(
                f"Security Violation: Access denied to path outside workspace."
            )

        return resolved_target


from app.tools.filesystem.read_file import ReadFileTool
from app.tools.filesystem.write_file import WriteFileTool
from app.tools.filesystem.list_directory import ListDirectoryTool
from app.tools.filesystem.search_files import SearchFilesTool

__all__ = [
    "BaseFileSystemTool",
    "ReadFileTool",
    "WriteFileTool",
    "ListDirectoryTool",
    "SearchFilesTool"
]
