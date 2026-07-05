from typing import List, Optional
from pydantic import BaseModel, Field

# --- Filesystem Schemas ---

class ReadFileRequest(BaseModel):
    path: str = Field(..., description="Path to the file to read, relative to workspace root")


class ReadFileResponse(BaseModel):
    path: str = Field(..., description="The path of the file that was read")
    content: str = Field(..., description="The text content of the file")


class WriteFileRequest(BaseModel):
    path: str = Field(..., description="Path to the file to write, relative to workspace root")
    content: str = Field(..., description="The content to write to the file")


class WriteFileResponse(BaseModel):
    path: str = Field(..., description="The path of the file that was written")
    success: bool = Field(..., description="Indicates if the write operation was successful")
    message: str = Field(..., description="Status message detailing the outcome")


class ListDirectoryRequest(BaseModel):
    path: str = Field(".", description="Path to list contents of, relative to workspace root")


class DirectoryEntry(BaseModel):
    name: str = Field(..., description="The name of the entry (file or folder)")
    type: str = Field(..., description="The type of the entry, either 'file' or 'directory'")
    size: int = Field(..., description="Size of the file in bytes, 0 for directories")


class ListDirectoryResponse(BaseModel):
    path: str = Field(..., description="The directory path that was listed")
    entries: List[DirectoryEntry] = Field(..., description="List of entries in the directory")


class SearchFilesRequest(BaseModel):
    query: str = Field(..., description="Text query or regular expression to search for")
    path: str = Field(".", description="Path to start the search from, relative to workspace root")


class SearchResult(BaseModel):
    path: str = Field(..., description="The path to the file containing the match")
    line_number: int = Field(..., description="The 1-indexed line number of the match")
    line_content: str = Field(..., description="The content of the matching line")


class SearchFilesResponse(BaseModel):
    query: str = Field(..., description="The search pattern that was run")
    results: List[SearchResult] = Field(..., description="List of search result matches")


# --- Terminal Schemas ---

class RunCommandRequest(BaseModel):
    command: str = Field(..., description="The command to execute in the shell")
    timeout: Optional[float] = Field(None, description="Optional command execution timeout in seconds")
    cwd: Optional[str] = Field(None, description="Optional subdirectory relative to workspace root to run command in")


class RunCommandResponse(BaseModel):
    stdout: str = Field(..., description="Standard output from command execution")
    stderr: str = Field(..., description="Standard error output from command execution")
    exit_code: int = Field(..., description="The exit status code of the command execution")
    timeout_expired: bool = Field(..., description="Whether the execution timed out")


# --- Git Schemas ---

class GitStatusRequest(BaseModel):
    pass


class GitStatusResponse(BaseModel):
    status_output: str = Field(..., description="Output from git status command")
    is_clean: bool = Field(..., description="True if workspace contains no uncommitted or modified files")
    exit_code: int = Field(..., description="Exit status code of the git status execution")
