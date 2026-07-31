import os
import sys
import pytest
import logging
from pathlib import Path
from unittest.mock import patch, MagicMock

from app.tools.exceptions import (
    ToolValidationError,
    PathTraversalError,
    ToolFileNotFoundError,
    CommandExecutionError
)
from app.tools.registry import ToolRegistry
from app.tools.filesystem import (
    ReadFileTool,
    WriteFileTool,
    ListDirectoryTool,
    SearchFilesTool
)
from app.tools.terminal import RunCommandTool
from app.tools.git import GitStatusTool


# --- 1. Registry Tests ---

def test_registry_lifecycle():
    registry = ToolRegistry()
    assert len(registry.list_tools()) == 0

    # Instantiate mock tool
    tool = ReadFileTool()
    registry.register(tool)
    assert registry.has_tool("read_file")
    assert registry.get_tool("read_file") == tool

    registry.unregister("read_file")
    assert not registry.has_tool("read_file")
    with pytest.raises(ToolValidationError):
        registry.get_tool("read_file")


def test_registry_invalid_type():
    registry = ToolRegistry()
    with pytest.raises(TypeError):
        registry.register("not a tool")  # type: ignore


def test_registry_discovery():
    registry = ToolRegistry()
    # Discover in current tools packages
    registry.discover_tools(["app.tools.filesystem", "app.tools.terminal", "app.tools.git"])
    
    assert registry.has_tool("read_file")
    assert registry.has_tool("write_file")
    assert registry.has_tool("list_directory")
    assert registry.has_tool("search_files")
    assert registry.has_tool("run_command")
    assert registry.has_tool("git_status")


# --- 2. Schema Validation & Base Tool Logging Tests ---

def test_base_tool_validation_and_logging(tmp_path, caplog):
    write_tool = WriteFileTool(workspace_root=tmp_path)
    
    # Validation failure: missing required field 'content'
    with pytest.raises(ToolValidationError) as excinfo:
        write_tool.execute(path="test.txt")  # type: ignore
    assert "Input validation failed" in str(excinfo.value)

    # Enable propagation so caplog can intercept logs
    import logging
    logging.getLogger("app").propagate = True

    # Success execution check logging
    with caplog.at_level(logging.INFO, logger="app.tools"):
        response = write_tool.execute(path="test.txt", content="hello")
        assert response.success
        assert response.path == "test.txt"
        
        # Check logs contain execution details
        log_messages = [rec.message for rec in caplog.records]
        assert any("Tool Invocation: tool=write_file" in msg for msg in log_messages)


# --- 3. Filesystem Tools Tests ---

def test_filesystem_read_write(tmp_path):
    read_tool = ReadFileTool(workspace_root=tmp_path)
    write_tool = WriteFileTool(workspace_root=tmp_path)

    # Write a new file
    write_resp = write_tool.execute(path="sub/test.txt", content="Hello, Python!")
    assert write_resp.success
    assert (tmp_path / "sub" / "test.txt").exists()
    assert (tmp_path / "sub" / "test.txt").read_text(encoding="utf-8") == "Hello, Python!"

    # Read the file back
    read_resp = read_tool.execute(path="sub/test.txt")
    assert read_resp.content == "Hello, Python!"
    assert read_resp.path == "sub/test.txt"


def test_filesystem_missing_file(tmp_path):
    read_tool = ReadFileTool(workspace_root=tmp_path)
    with pytest.raises(ToolFileNotFoundError):
        read_tool.execute(path="does_not_exist.txt")


def test_filesystem_read_directory_as_file(tmp_path):
    read_tool = ReadFileTool(workspace_root=tmp_path)
    (tmp_path / "my_dir").mkdir()
    with pytest.raises(Exception):  # ToolExecutionError or specific wrapper
        read_tool.execute(path="my_dir")


def test_filesystem_path_traversal_prevention(tmp_path):
    read_tool = ReadFileTool(workspace_root=tmp_path)
    write_tool = WriteFileTool(workspace_root=tmp_path)

    # Traverse outside workspace using relative dot-dot
    with pytest.raises(PathTraversalError):
        read_tool.execute(path="../../outside.txt")

    with pytest.raises(PathTraversalError):
        write_tool.execute(path="sub/../../../outside.txt", content="data")


def test_list_directory_tool(tmp_path):
    list_tool = ListDirectoryTool(workspace_root=tmp_path)

    # Setup directories and files
    (tmp_path / "dir_a").mkdir()
    (tmp_path / "file_b.txt").write_text("b", encoding="utf-8")
    (tmp_path / "file_c.txt").write_text("c", encoding="utf-8")

    # List root
    resp = list_tool.execute(path=".")
    assert resp.path == "."
    assert len(resp.entries) == 3

    # Sort checks directories first
    assert resp.entries[0].name == "dir_a"
    assert resp.entries[0].type == "directory"
    assert resp.entries[1].name == "file_b.txt"
    assert resp.entries[1].type == "file"
    assert resp.entries[1].size == 1

    # Directory missing
    with pytest.raises(ToolFileNotFoundError):
        list_tool.execute(path="non_existent_folder")


def test_search_files_tool(tmp_path):
    search_tool = SearchFilesTool(workspace_root=tmp_path)

    # Setup files with content
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.py").write_text("def my_func():\n    return 'CodeForge'\n", encoding="utf-8")
    (tmp_path / "src" / "test.py").write_text("def test_func():\n    # Test CodeForge\n    pass", encoding="utf-8")
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "some.js").write_text("CodeForge in node_modules", encoding="utf-8")

    # Search for pattern
    resp = search_tool.execute(query="CodeForge", path=".")
    assert len(resp.results) == 2
    
    paths = [r.path for r in resp.results]
    assert "src/main.py" in paths
    assert "src/test.py" in paths
    # node_modules should be ignored
    assert "node_modules/some.js" not in paths

    # Verify search result structure
    first_res = next(r for r in resp.results if r.path == "src/main.py")
    assert first_res.line_number == 2
    assert "CodeForge" in first_res.line_content

    # Invalid regex
    with pytest.raises(ToolValidationError):
        search_tool.execute(query="[invalid-regex", path=".")


# --- 4. Terminal Tool Tests ---

def test_run_command_success(tmp_path):
    cmd_tool = RunCommandTool(workspace_root=tmp_path)
    
    # Run a simple Python inline script using currently active python executable
    py_expr = "import sys; sys.stdout.write('stdout response'); sys.stderr.write('stderr error')"
    cmd = f'"{sys.executable}" -c "{py_expr}"'
    
    resp = cmd_tool.execute(command=cmd)
    assert resp.exit_code == 0
    assert resp.stdout == "stdout response"
    assert resp.stderr == "stderr error"
    assert not resp.timeout_expired


def test_run_command_timeout(tmp_path):
    cmd_tool = RunCommandTool(workspace_root=tmp_path)
    
    # Run a script that sleeps to force timeout
    py_expr = "import time; import sys; sys.stdout.write('early output\\n'); sys.stdout.flush(); time.sleep(10)"
    cmd = f'"{sys.executable}" -c "{py_expr}"'
    
    # Run with small timeout
    resp = cmd_tool.execute(command=cmd, timeout=0.5)
    assert resp.timeout_expired
    assert resp.exit_code == -1
    # Check that we captured stdout output generated before timeout
    assert "early output" in resp.stdout


def test_run_command_cwd_check(tmp_path):
    cmd_tool = RunCommandTool(workspace_root=tmp_path)

    # Allowed subdirectory
    (tmp_path / "build").mkdir()
    resp = cmd_tool.execute(command=f'"{sys.executable}" -c "import os; print(os.getcwd())"', cwd="build")
    assert resp.exit_code == 0
    # The output from python will be the resolved path of build subdirectory
    expected_cwd = (tmp_path / "build").resolve()
    assert str(expected_cwd).lower() in resp.stdout.strip().lower()

    # Outside workspace cwd restriction
    with pytest.raises(PathTraversalError):
        cmd_tool.execute(command="whoami", cwd="../outside")


def test_run_command_missing_executable(tmp_path):
    cmd_tool = RunCommandTool(workspace_root=tmp_path)
    # Use an allowed binary name targeting a path that does not exist to trigger FileNotFoundError
    missing_git_cmd = f'"{tmp_path / "git"}"'
    with pytest.raises(CommandExecutionError) as excinfo:
        cmd_tool.execute(command=missing_git_cmd)
    assert "not found" in str(excinfo.value)


def test_run_command_blocked_executable(tmp_path):
    cmd_tool = RunCommandTool(workspace_root=tmp_path)
    with pytest.raises(CommandExecutionError) as excinfo:
        cmd_tool.execute(command="curl https://example.com")
    assert "not allowed" in str(excinfo.value)


def test_run_command_env_secret_isolation(tmp_path, monkeypatch):
    monkeypatch.setenv("API_SECRET_KEY", "super_secret_key_12345")
    monkeypatch.setenv("GEMINI_API_KEY", "secret_gemini_key_67890")
    cmd_tool = RunCommandTool(workspace_root=tmp_path)
    
    py_expr = "import os; print('KEYS:', list(os.environ.keys()))"
    cmd = f'"{sys.executable}" -c "{py_expr}"'
    resp = cmd_tool.execute(command=cmd)
    
    assert resp.exit_code == 0
    assert "super_secret_key_12345" not in resp.stdout
    assert "secret_gemini_key_67890" not in resp.stdout
    assert "API_SECRET_KEY" not in resp.stdout
    assert "GEMINI_API_KEY" not in resp.stdout


def test_run_command_output_truncation(tmp_path):
    cmd_tool = RunCommandTool(workspace_root=tmp_path)
    # Generate >1MB output from Python script
    py_expr = "import sys; sys.stdout.write('A' * (1024 * 1024 + 50000))"
    cmd = f'"{sys.executable}" -c "{py_expr}"'
    resp = cmd_tool.execute(command=cmd)
    
    assert resp.exit_code == 0
    assert "[...output truncated at 1MB...]" in resp.stdout
    assert len(resp.stdout) <= 1024 * 1024 + len("\n[...output truncated at 1MB...]")


def test_run_command_resource_limits_func():
    from app.tools.terminal.run_command import _set_resource_limits
    # Calling _set_resource_limits should not raise an exception on any platform
    _set_resource_limits()



# --- 5. Git Status Tool Tests ---

def test_git_status_tool_success(tmp_path):
    # Setup mock subprocess run to avoid depending on host system git installation / state
    git_tool = GitStatusTool(workspace_root=tmp_path)

    mock_run_results = [
        # First call: git status
        MagicMock(returncode=0, stdout="On branch main\nnothing to commit, working tree clean", stderr=""),
        # Second call: git status --porcelain
        MagicMock(returncode=0, stdout="", stderr="")
    ]

    with patch("subprocess.run", side_effect=mock_run_results) as mock_run:
        resp = git_tool.execute()
        assert resp.exit_code == 0
        assert "working tree clean" in resp.status_output
        assert resp.is_clean
        
        # Verify subprocess parameters
        mock_run.assert_any_call(
            ["git", "status"],
            cwd=git_tool.workspace_root,
            stdout=-1, stderr=-1, text=True, shell=False
        )
        mock_run.assert_any_call(
            ["git", "status", "--porcelain"],
            cwd=git_tool.workspace_root,
            stdout=-1, stderr=-1, text=True, shell=False
        )


def test_git_status_tool_dirty(tmp_path):
    git_tool = GitStatusTool(workspace_root=tmp_path)

    mock_run_results = [
        # First call: git status
        MagicMock(returncode=0, stdout="On branch main\nChanges not staged for commit:\n  modified:   file.txt", stderr=""),
        # Second call: git status --porcelain
        MagicMock(returncode=0, stdout=" M file.txt", stderr="")
    ]

    with patch("subprocess.run", side_effect=mock_run_results):
        resp = git_tool.execute()
        assert resp.exit_code == 0
        assert not resp.is_clean


# --- 6. Framework & Tool Edge Cases for 100% Coverage ---

def test_tool_generic_execution_error():
    # Test that wrap_tool_execute wraps generic exceptions in ToolExecutionError
    from app.tools.base import BaseTool
    from pydantic import BaseModel

    class DummyInput(BaseModel):
        val: int

    class DummyOutput(BaseModel):
        res: str

    class FailTool(BaseTool):
        tool_name = "fail_tool"
        description = "always fails"
        category = "test"
        input_schema = DummyInput
        output_schema = DummyOutput

        def execute(self, val: int) -> DummyOutput:
            raise RuntimeError("something went wrong inside")

    tool = FailTool()
    from app.tools.exceptions import ToolExecutionError
    with pytest.raises(ToolExecutionError) as excinfo:
        tool.execute(val=10)
    assert "something went wrong inside" in str(excinfo.value)


def test_tool_invalid_output_type():
    from app.tools.base import BaseTool
    from pydantic import BaseModel

    class DummyInput(BaseModel):
        pass

    class DummyOutput(BaseModel):
        res: str

    class OtherModel(BaseModel):
        val: int

    class BadReturnTool(BaseTool):
        tool_name = "bad_return"
        description = "returns wrong model type"
        category = "test"
        input_schema = DummyInput
        output_schema = DummyOutput

        def execute(self) -> DummyOutput:
            return OtherModel(val=42)  # type: ignore

    tool = BadReturnTool()
    with pytest.raises(ToolValidationError) as excinfo:
        tool.execute()
    assert "returned invalid response type" in str(excinfo.value) or "output error" in str(excinfo.value)


def test_filesystem_resolve_path_edge_cases(tmp_path):
    # Setup filesystem tool instance
    tool = ReadFileTool(workspace_root=tmp_path)
    
    # Test absolute path inside workspace root
    abs_inside = (tmp_path / "inside.txt").resolve()
    assert tool.resolve_path(abs_inside) == abs_inside

    # Test absolute path outside workspace root
    # Note: On Windows, C:\Windows or C:\Temp is outside typical tmp_path (which is under C:\Users\...)
    # But to be safe, we can use a generated path outside tmp_path
    abs_outside = Path(tmp_path.parent / "outside_workspace_directory_123.txt").resolve()
    with pytest.raises(PathTraversalError):
        tool.resolve_path(abs_outside)


def test_filesystem_tool_errors(tmp_path):
    # Verify that errors during read/write file raise ToolExecutionError
    read_tool = ReadFileTool(workspace_root=tmp_path)
    write_tool = WriteFileTool(workspace_root=tmp_path)

    # 1. Read Error: Mock target path read_text to raise an OSError
    (tmp_path / "locked.txt").write_text("locked content")
    from app.tools.exceptions import ToolExecutionError
    with patch.object(Path, "read_text", side_effect=OSError("Permission denied")):
        with pytest.raises(ToolExecutionError) as excinfo:
            read_tool.execute(path="locked.txt")
        assert "Error reading file" in str(excinfo.value)

    # 2. Write Error: Mock target path parent directory creation to raise an OSError
    with patch.object(Path, "mkdir", side_effect=OSError("Write failed")):
        with pytest.raises(ToolExecutionError) as excinfo:
            write_tool.execute(path="fail_dir/test.txt", content="hi")
        assert "Error writing file" in str(excinfo.value)


def test_search_files_recursive_edge_cases(tmp_path):
    search_tool = SearchFilesTool(workspace_root=tmp_path)
    
    # Create a hidden subdirectory starting with dot (e.g. .hidden) and directories to skip
    (tmp_path / ".hidden").mkdir()
    (tmp_path / ".hidden" / "file.txt").write_text("target query pattern", encoding="utf-8")
    
    # Verify that hidden directories are skipped
    resp = search_tool.execute(query="pattern", path=".")
    assert len(resp.results) == 0

    # Search with target path pointing to a missing directory
    with pytest.raises(ToolFileNotFoundError):
        search_tool.execute(query="pattern", path="missing_folder")


def test_run_command_edge_cases(tmp_path):
    cmd_tool = RunCommandTool(workspace_root=tmp_path)

    # 1. Empty command
    with pytest.raises(CommandExecutionError) as excinfo:
        cmd_tool.execute(command="   ")
    assert "cannot be empty" in str(excinfo.value)

    # 2. Command parse ValueError (e.g. mismatched quotes)
    with pytest.raises(CommandExecutionError) as excinfo:
        cmd_tool.execute(command='echo "mismatched quote')
    assert "parse command" in str(excinfo.value).lower()

    # 3. Path Traversal relative to CWD in resolve_cwd
    with pytest.raises(PathTraversalError):
        cmd_tool.resolve_cwd("..")


def test_git_status_command_not_found(tmp_path):
    git_tool = GitStatusTool(workspace_root=tmp_path)

    # Mock FileNotFoundError on subprocess execution
    with patch("subprocess.run", side_effect=FileNotFoundError("git command not found")):
        from app.tools.exceptions import GitError
        with pytest.raises(GitError) as excinfo:
            git_tool.execute()
        assert "git command not found" in str(excinfo.value)


def test_git_status_non_zero_exit(tmp_path):
    git_tool = GitStatusTool(workspace_root=tmp_path)

    # Mock non-zero exit code
    mock_res = MagicMock(returncode=128, stderr="fatal: not a git repository")
    with patch("subprocess.run", return_value=mock_res):
        from app.tools.exceptions import GitError
        with pytest.raises(GitError) as excinfo:
            git_tool.execute()
        assert "Git command failed" in str(excinfo.value)


def test_registry_discovery_edge_cases(caplog):
    import logging
    logging.getLogger("app").propagate = True
    registry = ToolRegistry()
    
    # Test discovery on non-existent package package
    with caplog.at_level(logging.ERROR, logger="app.tools"):
        registry.discover_tools(["app.non_existent_tools_package"])
        # Should not raise error, but log error/warning
        log_messages = [rec.message for rec in caplog.records]
        assert any("Failed to import package" in msg for msg in log_messages)

