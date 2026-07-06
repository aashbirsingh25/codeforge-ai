from app.tools.base import BaseTool
from app.tools.registry import registry, ToolRegistry
from app.tools.exceptions import (
    ToolError,
    ToolValidationError,
    ToolExecutionError,
    PathTraversalError,
    ToolFileNotFoundError,
    CommandTimeoutError,
    CommandExecutionError,
    GitError
)
from app.tools.filesystem.read_file import ReadFileTool
from app.tools.filesystem.write_file import WriteFileTool
from app.tools.filesystem.list_directory import ListDirectoryTool
from app.tools.filesystem.search_files import SearchFilesTool
from app.tools.terminal.run_command import RunCommandTool
from app.tools.git.status import GitStatusTool

from app.tools.filesystem.create_file import CreateFileTool
from app.tools.filesystem.update_file import UpdateFileTool
from app.tools.filesystem.delete_file import DeleteFileTool
from app.tools.filesystem.create_directory import CreateDirectoryTool
from app.tools.codegen import GenerateCodeTool
from app.tools.execute_python import ExecutePythonTool

# Automatically register built-in core tools on initialization
registry.register(ReadFileTool())
registry.register(WriteFileTool())
registry.register(ListDirectoryTool())
registry.register(SearchFilesTool())
registry.register(RunCommandTool())
registry.register(GitStatusTool())

registry.register(CreateFileTool())
registry.register(UpdateFileTool())
registry.register(DeleteFileTool())
registry.register(CreateDirectoryTool())
registry.register(GenerateCodeTool())
registry.register(ExecutePythonTool())


__all__ = [
    "BaseTool",
    "registry",
    "ToolRegistry",
    
    # Exceptions
    "ToolError",
    "ToolValidationError",
    "ToolExecutionError",
    "PathTraversalError",
    "ToolFileNotFoundError",
    "CommandTimeoutError",
    "CommandExecutionError",
    "GitError",
    
    # Tool Classes
    "ReadFileTool",
    "WriteFileTool",
    "ListDirectoryTool",
    "SearchFilesTool",
    "RunCommandTool",
    "GitStatusTool",
    "CreateFileTool",
    "UpdateFileTool",
    "DeleteFileTool",
    "CreateDirectoryTool",
    "GenerateCodeTool",
    "ExecutePythonTool"
]
