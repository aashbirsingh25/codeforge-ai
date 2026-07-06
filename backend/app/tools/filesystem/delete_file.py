from app.tools.base import BaseTool
from app.workspace import workspace_manager
from app.tools.schemas import DeleteFileRequest, DeleteFileResponse

class DeleteFileTool(BaseTool):
    tool_name = "delete_file"
    description = "Deletes a file or directory recursively from the workspace."
    category = "filesystem"
    input_schema = DeleteFileRequest
    output_schema = DeleteFileResponse

    def execute(self, path: str) -> DeleteFileResponse:
        try:
            msg = workspace_manager.delete_file(path)
            return DeleteFileResponse(path=path, success=True, message=msg)
        except Exception as e:
            from app.tools.exceptions import ToolExecutionError
            raise ToolExecutionError(str(e)) from e
