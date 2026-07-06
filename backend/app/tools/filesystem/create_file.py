from app.tools.base import BaseTool
from app.workspace import workspace_manager
from app.tools.schemas import CreateFileRequest, CreateFileResponse

class CreateFileTool(BaseTool):
    tool_name = "create_file"
    description = "Create a new file with the specified content inside the workspace. Fails if the file already exists unless overwrite=True."
    category = "filesystem"
    input_schema = CreateFileRequest
    output_schema = CreateFileResponse

    def execute(self, path: str, content: str, overwrite: bool = False) -> CreateFileResponse:
        try:
            msg = workspace_manager.create_file(path, content, overwrite=overwrite)
            return CreateFileResponse(path=path, success=True, message=msg)
        except Exception as e:
            from app.tools.exceptions import ToolExecutionError
            raise ToolExecutionError(str(e)) from e
