import os
import shutil
import difflib
from pathlib import Path
from typing import List, Dict, Set, Optional, Tuple, Any
from app.core.config import settings
from app.tools.exceptions import PathTraversalError, ToolFileNotFoundError, ToolExecutionError

class WorkspaceManager:
    def __init__(self, workspace_root: Optional[Path] = None):
        self.workspace_root = Path(workspace_root).resolve() if workspace_root else Path(settings.WORKSPACE_DIR).resolve()
        # Initialize tracking lists / sets
        self.created_files: Set[str] = set()
        self.modified_files: Set[str] = set()
        self.deleted_files: Set[str] = set()

    def resolve_path(self, relative_path: str) -> Path:
        """Resolves a path relative to the workspace root and checks for path traversal."""
        rel_p = Path(relative_path)
        if rel_p.is_absolute():
            resolved = rel_p.resolve()
        else:
            # Strip leading slashes to prevent resolving to system root
            rel_str = str(rel_p).lstrip("\\/")
            resolved = (self.workspace_root / rel_str).resolve()
        
        try:
            if not resolved.is_relative_to(self.workspace_root):
                raise PathTraversalError("Security Violation: Access denied to path outside workspace.")
        except ValueError:
            raise PathTraversalError("Security Violation: Access denied to path outside workspace.")
        return resolved

    def get_relative_path(self, absolute_path: Path) -> str:
        """Returns relative path from workspace root, using forward slashes."""
        try:
            return absolute_path.resolve().relative_to(self.workspace_root).as_posix()
        except ValueError:
            raise PathTraversalError("Path is outside workspace root.")

    def list_files(self, relative_path: str = ".") -> List[str]:
        """Recursively lists all files in the workspace (relative paths)."""
        target = self.resolve_path(relative_path)
        if not target.exists():
            raise ToolFileNotFoundError(f"Directory '{relative_path}' does not exist.")
        if not target.is_dir():
            raise ToolExecutionError(f"'{relative_path}' is not a directory.")
        
        files = []
        for root, _, filenames in os.walk(target):
            for f in filenames:
                abs_path = Path(root) / f
                files.append(self.get_relative_path(abs_path))
        return sorted(files)

    def read_file(self, relative_path: str) -> str:
        """Reads a file and returns its content."""
        target = self.resolve_path(relative_path)
        if not target.exists():
            raise ToolFileNotFoundError(f"File '{relative_path}' does not exist.")
        if not target.is_file():
            raise ToolExecutionError(f"'{relative_path}' is not a file.")
        
        try:
            return target.read_text(encoding="utf-8")
        except Exception as e:
            raise ToolExecutionError(f"Error reading file '{relative_path}': {e}")

    def create_file(self, relative_path: str, content: str, overwrite: bool = False) -> str:
        """Creates a new file with content. Logs creation."""
        target = self.resolve_path(relative_path)
        rel_path = self.get_relative_path(target)
        
        if target.exists():
            if not overwrite:
                raise ToolExecutionError(f"File '{rel_path}' already exists.")
            # If overwriting, it counts as modified
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
            self.modified_files.add(rel_path)
            self.deleted_files.discard(rel_path)
            return f"File '{rel_path}' successfully updated."
        
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        self.created_files.add(rel_path)
        self.deleted_files.discard(rel_path)
        return f"File '{rel_path}' successfully created."

    def update_file(self, relative_path: str, content: str, confirm: bool = True, target_content: Optional[str] = None) -> Tuple[bool, str, Optional[str]]:
        """Updates a file. Can generate unified diff first. Returns (applied, message, diff)."""
        target = self.resolve_path(relative_path)
        rel_path = self.get_relative_path(target)
        
        if not target.exists():
            raise ToolFileNotFoundError(f"File '{rel_path}' does not exist.")
        
        original_content = target.read_text(encoding="utf-8")
        
        # Determine the new content
        new_content = content
        if target_content is not None:
            # This is a partial edit: replace target_content in original with content
            if target_content not in original_content:
                raise ToolExecutionError(f"Target content block to replace not found in '{rel_path}'.")
            new_content = original_content.replace(target_content, content, 1)

        # Generate unified diff
        original_lines = original_content.splitlines(keepends=True)
        new_lines = new_content.splitlines(keepends=True)
        diff_lines = list(difflib.unified_diff(
            original_lines,
            new_lines,
            fromfile=f"a/{rel_path}",
            tofile=f"b/{rel_path}"
        ))
        diff_str = "".join(diff_lines) if diff_lines else None

        if not diff_str:
            return True, f"No changes detected in '{rel_path}'.", None

        if not confirm:
            # We don't apply the changes, just return the diff
            return False, f"Diff generated for '{rel_path}'. Confirmation required.", diff_str

        # Apply changes
        try:
            target.write_text(new_content, encoding="utf-8")
            self.modified_files.add(rel_path)
            self.deleted_files.discard(rel_path)
            return True, f"File '{rel_path}' successfully updated.", diff_str
        except Exception as e:
            raise ToolExecutionError(f"Error updating file '{rel_path}': {e}")

    def delete_file(self, relative_path: str) -> str:
        """Deletes a file or directory recursively."""
        target = self.resolve_path(relative_path)
        rel_path = self.get_relative_path(target)
        
        if not target.exists():
            raise ToolFileNotFoundError(f"Path '{rel_path}' does not exist.")
            
        try:
            if target.is_dir():
                # Recursively log deletion of all files inside this directory
                for root, _, filenames in os.walk(target):
                    for f in filenames:
                        file_p = Path(root) / f
                        f_rel = self.get_relative_path(file_p)
                        self.deleted_files.add(f_rel)
                        self.created_files.discard(f_rel)
                        self.modified_files.discard(f_rel)
                shutil.rmtree(target)
                return f"Directory '{rel_path}' successfully deleted."
            else:
                target.unlink()
                self.deleted_files.add(rel_path)
                self.created_files.discard(rel_path)
                self.modified_files.discard(rel_path)
                return f"File '{rel_path}' successfully deleted."
        except Exception as e:
            raise ToolExecutionError(f"Error deleting path '{rel_path}': {e}")

    def create_directory(self, relative_path: str) -> str:
        """Creates a directory."""
        target = self.resolve_path(relative_path)
        rel_path = self.get_relative_path(target)
        try:
            target.mkdir(parents=True, exist_ok=True)
            return f"Directory '{rel_path}' successfully created."
        except Exception as e:
            raise ToolExecutionError(f"Error creating directory '{rel_path}': {e}")

    def list_directory(self, relative_path: str = ".") -> List[Dict[str, Any]]:
        """Lists contents of a directory (name, type, size)."""
        target = self.resolve_path(relative_path)
        rel_path = self.get_relative_path(target)
        if not target.exists():
            raise ToolFileNotFoundError(f"Directory '{rel_path}' does not exist.")
        if not target.is_dir():
            raise ToolExecutionError(f"'{rel_path}' is not a directory.")
            
        entries = []
        try:
            for entry in target.iterdir():
                entry_type = "directory" if entry.is_dir() else "file"
                size = 0 if entry.is_dir() else entry.stat().st_size
                entries.append({
                    "name": entry.name,
                    "type": entry_type,
                    "size": size
                })
            return sorted(entries, key=lambda x: (x["type"], x["name"]))
        except Exception as e:
            raise ToolExecutionError(f"Error listing directory '{rel_path}': {e}")

    def rename_file(self, source_path: str, target_path: str) -> str:
        """Renames/moves a file or directory."""
        src = self.resolve_path(source_path)
        dst = self.resolve_path(target_path)
        src_rel = self.get_relative_path(src)
        dst_rel = self.get_relative_path(dst)
        
        if not src.exists():
            raise ToolFileNotFoundError(f"Source path '{src_rel}' does not exist.")
        if dst.exists():
            raise ToolExecutionError(f"Destination path '{dst_rel}' already exists.")
            
        try:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(src), str(dst))
            
            # Update tracking for renaming
            if dst.is_dir():
                # For directories, log all contained files recursively as moved/created
                for root, _, filenames in os.walk(dst):
                    for f in filenames:
                        file_p = Path(root) / f
                        f_rel = self.get_relative_path(file_p)
                        self.created_files.add(f_rel)
                        self.deleted_files.discard(f_rel)
            else:
                self.deleted_files.add(src_rel)
                self.created_files.discard(src_rel)
                self.modified_files.discard(src_rel)
                
                self.created_files.add(dst_rel)
            return f"Moved '{src_rel}' to '{dst_rel}'."
        except Exception as e:
            raise ToolExecutionError(f"Error moving '{src_rel}' to '{dst_rel}': {e}")

    def create_project(self, project_type: str, name: str) -> str:
        """Generates starter template project files inside a new subdirectory."""
        proj_dir = Path(name)
        type_lower = project_type.lower().strip()
        
        # Verify no path traversal for the folder name
        resolved_proj = self.resolve_path(str(proj_dir))
        
        # Standard templates
        if type_lower == "fastapi":
            self.create_file(str(proj_dir / "main.py"), (
                "from fastapi import FastAPI\n\n"
                f"app = FastAPI(title='{name}')\n\n"
                "@app.get('/')\n"
                "def read_root():\n"
                "    return {'message': 'Hello from FastAPI!'}\n"
            ))
            self.create_file(str(proj_dir / "requirements.txt"), (
                "fastapi>=0.100.0\n"
                "uvicorn>=0.22.0\n"
            ))
            self.create_file(str(proj_dir / "README.md"), (
                f"# {name}\n\n"
                "A FastAPI project generated by CodeForge AI.\n"
            ))
        elif type_lower == "flask":
            self.create_file(str(proj_dir / "app.py"), (
                "from flask import Flask, jsonify\n\n"
                "app = Flask(__name__)\n\n"
                "@app.route('/')\n"
                "def hello():\n"
                "    return jsonify(message='Hello from Flask!')\n\n"
                "if __name__ == '__main__':\n"
                "    app.run(port=5000)\n"
            ))
            self.create_file(str(proj_dir / "requirements.txt"), (
                "Flask>=2.3.0\n"
            ))
            self.create_file(str(proj_dir / "README.md"), (
                f"# {name}\n\n"
                "A Flask project generated by CodeForge AI.\n"
            ))
        elif type_lower == "cli":
            self.create_file(str(proj_dir / "cli.py"), (
                "import argparse\n\n"
                "def main():\n"
                "    parser = argparse.ArgumentParser(description='CLI application.')\n"
                "    parser.add_argument('name', nargs='?', default='World', help='Name to greet')\n"
                "    args = parser.parse_args()\n"
                "    print(f'Hello, {args.name}!')\n\n"
                "if __name__ == '__main__':\n"
                "    main()\n"
            ))
            self.create_file(str(proj_dir / "README.md"), (
                f"# {name}\n\n"
                "A Python CLI app generated by CodeForge AI.\n"
            ))
        elif type_lower == "package":
            self.create_file(str(proj_dir / "pyproject.toml"), (
                "[build-system]\n"
                "requires = ['setuptools>=61.0']\n"
                "build-backend = 'setuptools.build_meta'\n\n"
                "[project]\n"
                f"name = '{name}'\n"
                "version = '0.1.0'\n"
                "dependencies = []\n"
            ))
            self.create_file(str(proj_dir / name / "__init__.py"), "__version__ = '0.1.0'\n")
            self.create_file(str(proj_dir / name / "main.py"), (
                "def hello():\n"
                "    return 'Hello from package!'\n"
            ))
            self.create_file(str(proj_dir / "tests" / "__init__.py"), "")
            self.create_file(str(proj_dir / "tests" / "test_main.py"), (
                f"from {name}.main import hello\n\n"
                "def test_hello():\n"
                "    assert hello() == 'Hello from package!'\n"
            ))
            self.create_file(str(proj_dir / "README.md"), (
                f"# {name}\n\n"
                "A Python package structure generated by CodeForge AI.\n"
            ))
        elif type_lower == "script":
            self.create_file(str(proj_dir / "script.py"), (
                "def main():\n"
                "    print('Hello from simple script!')\n\n"
                "if __name__ == '__main__':\n"
                "    main()\n"
            ))
            self.create_file(str(proj_dir / "README.md"), (
                f"# {name}\n\n"
                "A simple Python script generated by CodeForge AI.\n"
            ))
        else:
            raise ToolExecutionError(f"Unsupported project type '{project_type}'. Supported: fastapi, flask, cli, package, script.")
            
        return f"Project '{name}' of type '{project_type}' successfully generated."

    def get_tracking_status(self) -> Dict[str, List[str]]:
        """Returns lists of created, modified, and deleted files."""
        return {
            "created": sorted(list(self.created_files)),
            "modified": sorted(list(self.modified_files)),
            "deleted": sorted(list(self.deleted_files))
        }

    def clear_tracking(self):
        self.created_files.clear()
        self.modified_files.clear()
        self.deleted_files.clear()
