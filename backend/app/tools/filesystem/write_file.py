from pathlib import Path
from typing import Union

from app.tools.base import BaseTool
from app.tools.filesystem import BaseFileSystemTool
from app.tools.schemas import WriteFileRequest, WriteFileResponse
from app.tools.exceptions import ToolExecutionError


class WriteFileTool(BaseFileSystemTool, BaseTool):
    """Tool to write/overwrite content to a file in the workspace."""
    tool_name = "write_file"
    description = "Write or overwrite content to a file in the workspace. Automatically creates parent folders."
    category = "filesystem"
    input_schema = WriteFileRequest
    output_schema = WriteFileResponse

    def __init__(self, workspace_root: Union[str, Path, None] = None):
        BaseFileSystemTool.__init__(self, workspace_root)

    def execute(self, path: str, content: str) -> WriteFileResponse:
        """Writes content to the file and returns a success response."""
        target_path = self.resolve_path(path)

        try:
            # Ensure parent directories exist
            target_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write content
            target_path.write_text(content, encoding="utf-8")
            
            return WriteFileResponse(
                path=path,
                success=True,
                message=f"File '{path}' successfully written."
            )
        except Exception as e:
            raise ToolExecutionError(f"Error writing file '{path}': {str(e)}") from e
