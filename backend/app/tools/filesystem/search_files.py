import re
from pathlib import Path
from typing import Union, List

from app.tools.base import BaseTool
from app.tools.filesystem import BaseFileSystemTool
from app.tools.schemas import SearchFilesRequest, SearchFilesResponse, SearchResult
from app.tools.exceptions import ToolFileNotFoundError, ToolExecutionError, ToolValidationError


class SearchFilesTool(BaseFileSystemTool, BaseTool):
    """Tool to search for text patterns (regex) within workspace files."""
    tool_name = "search_files"
    description = (
        "Search for a regular expression pattern within files in the workspace. "
        "Returns matching files, line numbers, and line contents."
    )
    category = "filesystem"
    input_schema = SearchFilesRequest
    output_schema = SearchFilesResponse

    # Common directories to skip during recursion
    EXCLUDED_DIRS = {
        ".git",
        "node_modules",
        "__pycache__",
        "dist",
        "build",
        ".pytest_cache",
        "venv",
        ".venv"
    }

    def __init__(self, workspace_root: Union[str, Path, None] = None):
        BaseFileSystemTool.__init__(self, workspace_root)

    def execute(self, query: str, path: str = ".") -> SearchFilesResponse:
        """Searches files recursively for regex pattern and returns structured results."""
        target_path = self.resolve_path(path)

        if not target_path.exists():
            raise ToolFileNotFoundError(f"Search path '{path}' does not exist.")

        try:
            regex = re.compile(query, re.IGNORECASE)
        except re.error as e:
            raise ToolValidationError(f"Invalid regular expression pattern '{query}': {str(e)}") from e

        results: List[SearchResult] = []

        def search_file(file_path: Path):
            try:
                # Read as utf-8, ignoring decoding errors to handle binaries safely
                content = file_path.read_text(encoding="utf-8", errors="ignore")
                for line_idx, line in enumerate(content.splitlines(), 1):
                    if regex.search(line):
                        rel_path = file_path.relative_to(self.workspace_root).as_posix()
                        results.append(
                            SearchResult(
                                path=rel_path,
                                line_number=line_idx,
                                line_content=line.strip()
                            )
                        )
                        # Avoid huge results, limit to 200 matches
                        if len(results) >= 200:
                            return True
            except Exception:
                pass  # Skip files that cannot be read
            return False

        def walk_and_search(dir_path: Path) -> bool:
            for item in dir_path.iterdir():
                if item.name in self.EXCLUDED_DIRS or item.name.startswith('.'):
                    continue
                if item.is_dir():
                    if walk_and_search(item):
                        return True
                elif item.is_file():
                    if search_file(item):
                        return True
            return False

        try:
            if target_path.is_file():
                search_file(target_path)
            else:
                walk_and_search(target_path)

            return SearchFilesResponse(query=query, results=results)
        except Exception as e:
            raise ToolExecutionError(f"Error searching files at '{path}': {str(e)}") from e
