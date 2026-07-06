from app.tools.base import BaseTool
from app.workspace import workspace_manager
from app.tools.schemas import CreateDirectoryRequest, CreateDirectoryResponse

class CreateDirectoryTool(BaseTool):
    tool_name = "create_directory"
    description = "Creates a directory inside the workspace, including parent directories."
    category = "filesystem"
    input_schema = CreateDirectoryRequest
    output_schema = CreateDirectoryResponse

    def execute(self, path: str) -> CreateDirectoryResponse:
        try:
            msg = workspace_manager.create_directory(path)
            return CreateDirectoryResponse(path=path, success=True, message=msg)
        except Exception as e:
            from app.tools.exceptions import ToolExecutionError
            raise ToolExecutionError(str(e)) from e
