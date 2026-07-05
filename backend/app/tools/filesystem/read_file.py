from pathlib import Path
from typing import Union

from app.tools.base import BaseTool
from app.tools.filesystem import BaseFileSystemTool
from app.tools.schemas import ReadFileRequest, ReadFileResponse
from app.tools.exceptions import ToolFileNotFoundError, ToolExecutionError


class ReadFileTool(BaseFileSystemTool, BaseTool):
    """Tool to read file contents from the workspace."""
    tool_name = "read_file"
    description = "Read the text content of a file in the workspace. Returns the file's content."
    category = "filesystem"
    input_schema = ReadFileRequest
    output_schema = ReadFileResponse

    def __init__(self, workspace_root: Union[str, Path, None] = None):
        # Explicit call to initialize BaseFileSystemTool
        BaseFileSystemTool.__init__(self, workspace_root)

    def execute(self, path: str) -> ReadFileResponse:
        """Reads a file and returns its content."""
        target_path = self.resolve_path(path)
        
        if not target_path.exists():
            raise ToolFileNotFoundError(f"File '{path}' does not exist.")
        
        if not target_path.is_file():
            raise ToolExecutionError(f"'{path}' is a directory, not a file.")

        try:
            content = target_path.read_text(encoding="utf-8")
            return ReadFileResponse(path=path, content=content)
        except Exception as e:
            raise ToolExecutionError(f"Error reading file '{path}': {str(e)}") from e
