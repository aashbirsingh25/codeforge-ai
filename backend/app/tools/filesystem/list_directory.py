import os
from pathlib import Path
from typing import Union, List

from app.tools.base import BaseTool
from app.tools.filesystem import BaseFileSystemTool
from app.tools.schemas import ListDirectoryRequest, ListDirectoryResponse, DirectoryEntry
from app.tools.exceptions import ToolFileNotFoundError, ToolExecutionError


class ListDirectoryTool(BaseFileSystemTool, BaseTool):
    """Tool to list directory contents inside the workspace."""
    tool_name = "list_directory"
    description = "List contents of a directory in the workspace. Defaults to the workspace root '.'."
    category = "filesystem"
    input_schema = ListDirectoryRequest
    output_schema = ListDirectoryResponse

    def __init__(self, workspace_root: Union[str, Path, None] = None):
        BaseFileSystemTool.__init__(self, workspace_root)

    def execute(self, path: str = ".") -> ListDirectoryResponse:
        """Lists directory files and folders and returns a structured response."""
        target_path = self.resolve_path(path)

        if not target_path.exists():
            raise ToolFileNotFoundError(f"Directory '{path}' does not exist.")

        if not target_path.is_dir():
            raise ToolExecutionError(f"'{path}' is a file, not a directory.")

        try:
            entries: List[DirectoryEntry] = []
            for entry in os.scandir(target_path):
                is_dir = entry.is_dir()
                size = 0 if is_dir else entry.stat().st_size
                entry_type = "directory" if is_dir else "file"
                entries.append(
                    DirectoryEntry(
                        name=entry.name,
                        type=entry_type,
                        size=size
                    )
                )

            # Sort entries: directories first, then files alphabetically
            entries.sort(key=lambda x: (x.type != "directory", x.name.lower()))
            
            return ListDirectoryResponse(path=path, entries=entries)
        except Exception as e:
            raise ToolExecutionError(f"Error listing directory '{path}': {str(e)}") from e
