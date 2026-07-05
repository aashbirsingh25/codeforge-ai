import os
import re
from pathlib import Path
from app.core.config import settings
from app.tools.base import registry

def resolve_workspace_path(relative_path: str) -> Path:
    base = settings.WORKSPACE_DIR.resolve()
    target = Path(base / relative_path).resolve(strict=False)
    if not str(target).startswith(str(base)):
        raise ValueError("Security Violation: Access denied outside workspace directory.")
    return target

@registry.register(
    name="read_file",
    description="Read the text content of a file in the workspace. Returns the file's content."
)
def read_file(path: str) -> str:
    try:
        target_path = resolve_workspace_path(path)
        if not target_path.exists():
            return f"Error: File '{path}' does not exist."
        if not target_path.is_file():
            return f"Error: '{path}' is a directory, not a file."
        return target_path.read_text(encoding="utf-8")
    except Exception as e:
        return f"Error reading file '{path}': {str(e)}"

@registry.register(
    name="write_file",
    description="Write or overwrite content to a file in the workspace. Automatically creates parent folders."
)
def write_file(path: str, content: str) -> str:
    try:
        target_path = resolve_workspace_path(path)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_text(content, encoding="utf-8")
        return f"File '{path}' successfully written."
    except Exception as e:
        return f"Error writing file '{path}': {str(e)}"

@registry.register(
    name="list_directory",
    description="List contents of a directory in the workspace. Defaults to the workspace root '.'."
)
def list_directory(path: str = ".") -> str:
    try:
        target_path = resolve_workspace_path(path)
        if not target_path.exists():
            return f"Error: Directory '{path}' does not exist."
        if not target_path.is_dir():
            return f"Error: '{path}' is a file, not a directory."
        
        entries = []
        for entry in os.scandir(target_path):
            rel_path = Path(entry.path).relative_to(settings.WORKSPACE_DIR).as_posix()
            entry_type = "directory" if entry.is_dir() else "file"
            size = entry.stat().st_size if entry.is_file() else 0
            entries.append(f"{entry_type:10} | {rel_path} | {size} bytes")
            
        if not entries:
            return f"Directory '{path}' is empty."
        return "\n".join(entries)
    except Exception as e:
        return f"Error listing directory '{path}': {str(e)}"

@registry.register(
    name="grep_search",
    description="Search for a regular expression pattern within files in the workspace."
)
def grep_search(pattern: str, path: str = ".") -> str:
    try:
        target_path = resolve_workspace_path(path)
        regex = re.compile(pattern, re.IGNORECASE)
        matches = []
        
        def walk_and_search(dir_path: Path):
            for item in dir_path.iterdir():
                if item.name.startswith(('.', '__pycache__', 'node_modules', 'dist', '.git')):
                    continue
                if item.is_dir():
                    walk_and_search(item)
                elif item.is_file():
                    try:
                        content = item.read_text(encoding="utf-8", errors="ignore")
                        for idx, line in enumerate(content.splitlines(), 1):
                            if regex.search(line):
                                rel_path = item.relative_to(settings.WORKSPACE_DIR).as_posix()
                                matches.append(f"{rel_path}:{idx}: {line.strip()}")
                    except Exception:
                        pass
        
        if target_path.is_file():
            try:
                content = target_path.read_text(encoding="utf-8", errors="ignore")
                for idx, line in enumerate(content.splitlines(), 1):
                    if regex.search(line):
                        rel_path = target_path.relative_to(settings.WORKSPACE_DIR).as_posix()
                        matches.append(f"{rel_path}:{idx}: {line.strip()}")
            except Exception as e:
                return f"Error reading file '{path}': {str(e)}"
        else:
            walk_and_search(target_path)
            
        if not matches:
            return f"No matches found for pattern '{pattern}' in path '{path}'."
        return "\n".join(matches[:100])
    except Exception as e:
        return f"Error during grep search: {str(e)}"
