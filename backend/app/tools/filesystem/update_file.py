from typing import Optional
from app.tools.base import BaseTool
from app.workspace import workspace_manager
from app.tools.schemas import UpdateFileRequest, UpdateFileResponse

class UpdateFileTool(BaseTool):
    tool_name = "update_file"
    description = "Update an existing file with new content. Can do full writes, partial writes of a specific target block, and return diffs."
    category = "filesystem"
    input_schema = UpdateFileRequest
    output_schema = UpdateFileResponse

    def execute(self, path: str, content: str, target_content: Optional[str] = None, confirm: bool = True) -> UpdateFileResponse:
        try:
            applied, msg, diff = workspace_manager.update_file(path, content, confirm=confirm, target_content=target_content)
            return UpdateFileResponse(path=path, applied=applied, message=msg, diff=diff)
        except Exception as e:
            from app.tools.exceptions import ToolExecutionError
            raise ToolExecutionError(str(e)) from e
