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

# Automatically register built-in core tools on initialization
registry.register(ReadFileTool())
registry.register(WriteFileTool())
registry.register(ListDirectoryTool())
registry.register(SearchFilesTool())
registry.register(RunCommandTool())
registry.register(GitStatusTool())

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
    "GitStatusTool"
]
