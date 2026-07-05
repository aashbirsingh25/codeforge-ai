class ToolError(Exception):
    """Base exception for all errors in the tool framework."""
    pass


class ToolValidationError(ToolError):
    """Raised when there is an input validation error or output schema mismatch."""
    pass


class PathTraversalError(ToolValidationError):
    """Raised when a path targets a location outside the restricted workspace."""
    pass


class ToolExecutionError(ToolError):
    """Raised when execution of a tool fails."""
    pass


class ToolFileNotFoundError(ToolExecutionError):
    """Raised when a required file or directory does not exist."""
    pass


class CommandTimeoutError(ToolExecutionError):
    """Raised when a shell/process execution times out."""
    pass


class CommandExecutionError(ToolExecutionError):
    """Raised when a shell command fails with a non-zero exit status or error."""
    pass


class GitError(ToolExecutionError):
    """Raised when a Git command execution fails."""
    pass
