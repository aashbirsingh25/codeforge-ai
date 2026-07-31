import pytest
import os
import shutil
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock, patch
from fastapi.testclient import TestClient

from app.main import app
from tests.conftest import TEST_AUTH_HEADERS

client = TestClient(app, headers=TEST_AUTH_HEADERS)


from app.workspace import WorkspaceManager
from app.tools.exceptions import PathTraversalError, ToolFileNotFoundError, ToolExecutionError
from app.tools.registry import registry as tool_registry
from app.llm.schemas import ChatCompletionResponse
from app.llm.exceptions import LLMException

# Test workspace setup/cleanup fixture
@pytest.fixture
def temp_workspace():
    # Create a temporary directory to act as workspace
    temp_dir = tempfile.mkdtemp()
    workspace_path = Path(temp_dir).resolve()
    
    # Save original workspace root
    from app.workspace import workspace_manager
    original_root = workspace_manager.workspace_root
    
    # Update singleton config
    workspace_manager.workspace_root = workspace_path
    
    # Instantiate test manager
    manager = WorkspaceManager(workspace_root=workspace_path)
    
    yield manager
    
    # Restore original workspace root
    workspace_manager.workspace_root = original_root
    
    # Clean up temp directory
    shutil.rmtree(temp_dir)


def test_path_traversal_prevention(temp_workspace):
    manager = temp_workspace
    
    # Try creating/reading files outside workspace root
    outside_rel = "../outside.txt"
    outside_abs = Path(temp_workspace.workspace_root.parent / "outside.txt").as_posix()
    
    with pytest.raises(PathTraversalError):
        manager.resolve_path(outside_rel)
        
    with pytest.raises(PathTraversalError):
        manager.resolve_path(outside_abs)
        
    with pytest.raises(PathTraversalError):
        manager.create_file(outside_rel, "content")

    with pytest.raises(PathTraversalError):
        manager.read_file(outside_rel)

    with pytest.raises(PathTraversalError):
        manager.delete_file(outside_rel)

    with pytest.raises(PathTraversalError):
        manager.create_directory(outside_rel)


def test_file_crud_operations(temp_workspace):
    manager = temp_workspace
    
    # 1. Create a file
    msg = manager.create_file("test.txt", "hello world")
    assert "successfully created" in msg
    assert manager.read_file("test.txt") == "hello world"
    
    # Verify tracking status
    status = manager.get_tracking_status()
    assert "test.txt" in status["created"]
    
    # 2. Try creating duplicate without overwrite
    with pytest.raises(ToolExecutionError) as exc:
        manager.create_file("test.txt", "duplicate content", overwrite=False)
    assert "already exists" in str(exc.value)
    
    # 3. Create duplicate with overwrite
    msg = manager.create_file("test.txt", "new hello world", overwrite=True)
    assert "successfully updated" in msg
    assert manager.read_file("test.txt") == "new hello world"
    
    status = manager.get_tracking_status()
    assert "test.txt" in status["modified"]
    
    # 4. Partial edits / updates
    applied, msg, diff = manager.update_file("test.txt", "universe", target_content="world", confirm=True)
    assert applied is True
    assert "successfully updated" in msg
    assert "universe" in manager.read_file("test.txt")
    assert diff is not None
    
    # Update without confirm just returns diff
    applied, msg, diff = manager.update_file("test.txt", "galaxy", target_content="universe", confirm=False)
    assert applied is False
    assert "galaxy" not in manager.read_file("test.txt")
    assert diff is not None

    # Check non-existent file update
    with pytest.raises(ToolFileNotFoundError):
        manager.update_file("nonexistent.txt", "hello")
        
    # Check mismatched target content update
    with pytest.raises(ToolExecutionError) as exc:
        manager.update_file("test.txt", "galaxy", target_content="nonexistent-block")
    assert "not found" in str(exc.value)

    # 5. List directory contents
    manager.create_directory("subdir")
    manager.create_file("subdir/nested.txt", "nested content")
    
    entries = manager.list_directory(".")
    # Expect: subdir (directory), test.txt (file)
    assert len(entries) == 2
    assert entries[0]["name"] == "subdir"
    assert entries[0]["type"] == "directory"
    assert entries[1]["name"] == "test.txt"
    assert entries[1]["type"] == "file"
    
    # 6. List all files recursively
    files = manager.list_files(".")
    assert "test.txt" in files
    assert "subdir/nested.txt" in files
    
    # 7. Rename / Move file
    manager.rename_file("test.txt", "renamed.txt")
    assert not Path(manager.workspace_root / "test.txt").exists()
    assert Path(manager.workspace_root / "renamed.txt").exists()
    
    with pytest.raises(ToolFileNotFoundError):
        manager.rename_file("nonexistent.txt", "dest.txt")
    with pytest.raises(ToolExecutionError):
        manager.rename_file("renamed.txt", "subdir/nested.txt")
        
    # 8. Delete file & dir
    msg = manager.delete_file("renamed.txt")
    assert "successfully deleted" in msg
    
    msg = manager.delete_file("subdir")
    assert "successfully deleted" in msg
    assert not Path(manager.workspace_root / "subdir").exists()
    
    with pytest.raises(ToolFileNotFoundError):
        manager.delete_file("nonexistent_path")

    # Clear tracking
    manager.clear_tracking()
    status = manager.get_tracking_status()
    assert len(status["created"]) == 0
    assert len(status["modified"]) == 0
    assert len(status["deleted"]) == 0


def test_project_generation(temp_workspace):
    manager = temp_workspace
    
    # FastAPI project
    msg = manager.create_project("fastapi", "my_fastapi")
    assert "successfully generated" in msg
    assert Path(manager.workspace_root / "my_fastapi" / "main.py").exists()
    assert Path(manager.workspace_root / "my_fastapi" / "requirements.txt").exists()
    assert Path(manager.workspace_root / "my_fastapi" / "README.md").exists()
    
    # Flask project
    manager.create_project("flask", "my_flask")
    assert Path(manager.workspace_root / "my_flask" / "app.py").exists()
    
    # CLI application
    manager.create_project("cli", "my_cli")
    assert Path(manager.workspace_root / "my_cli" / "cli.py").exists()
    
    # Package application
    manager.create_project("package", "my_package")
    assert Path(manager.workspace_root / "my_package" / "pyproject.toml").exists()
    assert Path(manager.workspace_root / "my_package" / "my_package" / "__init__.py").exists()
    
    # Script application
    manager.create_project("script", "my_script")
    assert Path(manager.workspace_root / "my_script" / "script.py").exists()
    
    # Invalid type
    with pytest.raises(ToolExecutionError):
        manager.create_project("invalid_type", "my_invalid")


# API endpoints integration tests
def test_workspace_api_endpoints(temp_workspace):

    
    # Test POST /workspace/file
    res = client.post("/api/v1/workspace/file", json={
        "path": "api_test.txt",
        "content": "API created content",
        "overwrite": False
    })
    assert res.status_code == 200
    assert res.json()["success"] is True
    
    # Duplicate POST fails
    res = client.post("/api/v1/workspace/file", json={
        "path": "api_test.txt",
        "content": "mismatched",
        "overwrite": False
    })
    assert res.status_code == 400
    
    # Test GET /workspace/file
    res = client.get("/api/v1/workspace/file", params={"path": "api_test.txt"})
    assert res.status_code == 200
    assert res.json()["content"] == "API created content"
    
    # Read non-existent
    res = client.get("/api/v1/workspace/file", params={"path": "nonexistent.txt"})
    assert res.status_code == 404
    
    # Test PUT /workspace/file (full update)
    res = client.put("/api/v1/workspace/file", json={
        "path": "api_test.txt",
        "content": "API updated content",
        "confirm": True
    })
    assert res.status_code == 200
    assert res.json()["applied"] is True
    
    # Test GET /workspace/files
    res = client.get("/api/v1/workspace/files")
    assert res.status_code == 200
    assert "api_test.txt" in res.json()["files"]
    
    # Test POST /workspace/project
    res = client.post("/api/v1/workspace/project", json={
        "project_type": "script",
        "name": "api_script"
    })
    assert res.status_code == 200
    assert "successfully generated" in res.json()["message"]
    
    # Test DELETE /workspace/file
    res = client.delete("/api/v1/workspace/file", params={"path": "api_test.txt"})
    assert res.status_code == 200
    assert res.json()["success"] is True


def test_workspace_tools_execution(temp_workspace):
    # 1. create_file tool
    create_tool = tool_registry.get_tool("create_file")
    res = create_tool.execute(path="tool_test.txt", content="created via tool")
    assert res.success is True
    
    # 2. update_file tool
    update_tool = tool_registry.get_tool("update_file")
    res = update_tool.execute(path="tool_test.txt", content="updated", target_content="created via tool")
    assert res.applied is True
    
    # 3. delete_file tool
    delete_tool = tool_registry.get_tool("delete_file")
    res = delete_tool.execute(path="tool_test.txt")
    assert res.success is True
    
    # 4. create_directory tool
    dir_tool = tool_registry.get_tool("create_directory")
    res = dir_tool.execute(path="tool_dir")
    assert res.success is True


def test_python_execution_tool(temp_workspace):
    exec_tool = tool_registry.get_tool("execute_python")
    
    # Success scenario
    code = "import sys\nprint('hello from python')\nsys.exit(0)"
    res = exec_tool.execute(code=code, timeout=10.0)
    assert res.exit_code == 0
    assert "hello from python" in res.stdout
    assert res.timeout_expired is False
    
    # Error scenario
    code = "import sys\nprint('error in execution', file=sys.stderr)\nsys.exit(42)"
    res = exec_tool.execute(code=code, timeout=10.0)
    assert res.exit_code == 42
    assert "error in execution" in res.stderr
    
    # Timeout scenario
    code = "import time\ntime.sleep(2)"
    res = exec_tool.execute(code=code, timeout=0.1)
    assert res.exit_code == -1
    assert res.timeout_expired is True


@pytest.mark.asyncio
async def test_generate_code_tool_and_agent(temp_workspace):
    mock_provider = MagicMock()
    mock_provider.generate = AsyncMock(return_value=ChatCompletionResponse(
        content="Here is code:\n```python\ndef test_hello():\n    return 'hello'\n```",
        model="gemini"
    ))
    
    # Test agent directly
    from app.agents.registry import agent_registry
    agent = agent_registry.get_agent("CodeGenerationAgent")
    assert agent.description == "Generates source code from natural language requirements."
    
    context = {"requirements": "Write a greeting function", "provider": "gemini"}
    with patch("app.llm.factory.ProviderFactory.get_provider", return_value=mock_provider):
        res = await agent.execute("test_task", context)
        assert res.success is True
        assert "def test_hello()" in res.output
        assert "```python" not in res.output
        
    # Test generate_code tool
    codegen_tool = tool_registry.get_tool("generate_code")
    with patch("app.llm.factory.ProviderFactory.get_provider", return_value=mock_provider):
        res = codegen_tool.execute(requirements="Write a greeting function")
        assert res.success is True
        assert "def test_hello()" in res.code


def test_workspace_manager_additional_branches(temp_workspace):
    manager = temp_workspace
    
    # 1. list_files dir not exist
    with pytest.raises(ToolFileNotFoundError):
        manager.list_files("nonexistent")
        
    # 2. list_files path is a file
    manager.create_file("test.txt", "content")
    with pytest.raises(ToolExecutionError):
        manager.list_files("test.txt")
        
    # 3. read_file path is a directory
    manager.create_directory("subdir")
    with pytest.raises(ToolExecutionError):
        manager.read_file("subdir")
        
    # 4. update_file no changes detected
    applied, msg, diff = manager.update_file("test.txt", "content", confirm=True)
    assert applied is True
    assert "No changes detected" in msg
    assert diff is None
    
    # 5. rename_file directory recursive rename coverage
    manager.create_file("subdir/nested.txt", "nested")
    manager.rename_file("subdir", "subdir_moved")
    assert Path(manager.workspace_root / "subdir_moved" / "nested.txt").exists()
    assert not Path(manager.workspace_root / "subdir" / "nested.txt").exists()


def test_workspace_api_endpoints_error_mappings(temp_workspace):

    
    # GET files path traversal
    res = client.get("/api/v1/workspace/files", params={"path": "../outside"})
    assert res.status_code == 400
    
    # GET files nonexistent
    res = client.get("/api/v1/workspace/files", params={"path": "nonexistent"})
    assert res.status_code == 404
    
    # GET files path is file
    temp_workspace.create_file("test.txt", "content")
    res = client.get("/api/v1/workspace/files", params={"path": "test.txt"})
    assert res.status_code == 400

    # GET file path traversal
    res = client.get("/api/v1/workspace/file", params={"path": "../outside.txt"})
    assert res.status_code == 400
    
    # GET file path is directory
    temp_workspace.create_directory("subdir")
    res = client.get("/api/v1/workspace/file", params={"path": "subdir"})
    assert res.status_code == 400

    # POST file path traversal
    res = client.post("/api/v1/workspace/file", json={"path": "../outside.txt", "content": "err"})
    assert res.status_code == 400

    # PUT file path traversal
    res = client.put("/api/v1/workspace/file", json={"path": "../outside.txt", "content": "err"})
    assert res.status_code == 400

    # PUT file nonexistent
    res = client.put("/api/v1/workspace/file", json={"path": "nonexistent.txt", "content": "err"})
    assert res.status_code == 404

    # PUT file target mismatched
    res = client.put("/api/v1/workspace/file", json={"path": "test.txt", "content": "err", "target_content": "mismatched"})
    assert res.status_code == 400

    # DELETE file path traversal
    res = client.delete("/api/v1/workspace/file", params={"path": "../outside.txt"})
    assert res.status_code == 400

    # DELETE file nonexistent
    res = client.delete("/api/v1/workspace/file", params={"path": "nonexistent.txt"})
    assert res.status_code == 404

    # POST project invalid type
    res = client.post("/api/v1/workspace/project", json={"project_type": "invalid", "name": "err"})
    assert res.status_code == 400

    # POST project path traversal
    res = client.post("/api/v1/workspace/project", json={"project_type": "script", "name": "../outside"})
    assert res.status_code == 400


def test_workspace_api_unexpected_exceptions(temp_workspace):

    
    # Mock list_files RuntimeError
    with patch("app.workspace.workspace_manager.list_files", side_effect=RuntimeError("Unexpected")):
        res = client.get("/api/v1/workspace/files")
        assert res.status_code == 500
        
    # Mock read_file RuntimeError
    with patch("app.workspace.workspace_manager.read_file", side_effect=RuntimeError("Unexpected")):
        res = client.get("/api/v1/workspace/file", params={"path": "test.txt"})
        assert res.status_code == 500

    # Mock create_file RuntimeError
    with patch("app.workspace.workspace_manager.create_file", side_effect=RuntimeError("Unexpected")):
        res = client.post("/api/v1/workspace/file", json={"path": "test.txt", "content": "c"})
        assert res.status_code == 500

    # Mock update_file RuntimeError
    with patch("app.workspace.workspace_manager.update_file", side_effect=RuntimeError("Unexpected")):
        res = client.put("/api/v1/workspace/file", json={"path": "test.txt", "content": "u"})
        assert res.status_code == 500

    # Mock delete_file RuntimeError
    with patch("app.workspace.workspace_manager.delete_file", side_effect=RuntimeError("Unexpected")):
        res = client.delete("/api/v1/workspace/file", params={"path": "test.txt"})
        assert res.status_code == 500

    # Mock create_project RuntimeError
    with patch("app.workspace.workspace_manager.create_project", side_effect=RuntimeError("Unexpected")):
        res = client.post("/api/v1/workspace/project", json={"project_type": "script", "name": "app"})
        assert res.status_code == 500


def test_codegen_tool_unexpected_failures(temp_workspace):
    codegen_tool = tool_registry.get_tool("generate_code")
    
    # Mock agent execution to raise exception -> ToolExecutionError
    with patch("app.agents.registry.CodeGenerationAgent.execute", side_effect=RuntimeError("Failure")):
        with pytest.raises(ToolExecutionError):
            codegen_tool.execute(requirements="req")
            
    # Mock agent execution to return success=False -> ToolExecutionError
    mock_res = MagicMock()
    mock_res.success = False
    mock_res.error = "Agent error"
    with patch("app.agents.registry.CodeGenerationAgent.execute", return_value=mock_res):
        with pytest.raises(ToolExecutionError) as exc:
            codegen_tool.execute(requirements="req")
        assert "Agent error" in str(exc.value)


def test_execute_python_tool_unexpected_failures(temp_workspace):
    exec_tool = tool_registry.get_tool("execute_python")
    
    # Mock subprocess.run to raise Exception -> ToolExecutionError
    with patch("subprocess.run", side_effect=RuntimeError("OS Error")):
        with pytest.raises(ToolExecutionError):
            exec_tool.execute(code="print(1)")
            
    # Mock unlink to raise Exception to cover finally exception catch block
    with patch("pathlib.Path.unlink", side_effect=RuntimeError("Unlink failed")):
        # Should complete execution but not throw exception from unlink
        res = exec_tool.execute(code="print(1)")
        assert res.exit_code == 0


@pytest.mark.asyncio
async def test_codegen_agent_no_requirements():
    from app.agents.registry import agent_registry
    agent = agent_registry.get_agent("CodeGenerationAgent")
    res = await agent.execute("test", {})
    assert res.success is False
    assert "No requirements" in res.error


@pytest.mark.asyncio
async def test_codegen_agent_gemini_provider_error():
    from app.agents.registry import agent_registry
    agent = agent_registry.get_agent("CodeGenerationAgent")
    
    # Mock provider factory to raise error
    with patch("app.llm.factory.ProviderFactory.get_provider", side_effect=ValueError("Invalid provider")):
        res = await agent.execute("test", {"requirements": "req"})
        assert res.success is False
        assert "Failed to load LLM provider" in res.error


@pytest.mark.asyncio
async def test_codegen_agent_markdown_block_parsing():
    from app.agents.registry import agent_registry
    agent = agent_registry.get_agent("CodeGenerationAgent")
    
    mock_provider = MagicMock()
    # Response block wrapped in generic code fence (not ```python)
    mock_provider.generate = AsyncMock(return_value=ChatCompletionResponse(
        content="```\ndef hello():\n    pass\n```",
        model="gemini"
    ))
    
    context = {"requirements": "req", "provider": "gemini"}
    with patch("app.llm.factory.ProviderFactory.get_provider", return_value=mock_provider):
        res = await agent.execute("test", context)
        assert res.success is True
        assert res.output == "def hello():\n    pass"


def test_workspace_manager_errors_unit(temp_workspace):
    manager = temp_workspace
    
    # 1. Path.relative_to ValueError -> PathTraversalError
    with patch("pathlib.Path.relative_to", side_effect=ValueError("Mismatched")):
        with pytest.raises(PathTraversalError):
            manager.get_relative_path(Path("some_file.txt"))
            
    # 2. read_text IOError -> ToolExecutionError
    manager.create_file("read_err.txt", "content")
    with patch("pathlib.Path.read_text", side_effect=OSError("Read failed")):
        with pytest.raises(ToolExecutionError):
            manager.read_file("read_err.txt")
            
    # 3. write_text IOError -> ToolExecutionError
    with patch("pathlib.Path.write_text", side_effect=OSError("Write failed")):
        with pytest.raises(ToolExecutionError):
            manager.update_file("read_err.txt", "new content", confirm=True)
            
    # 4. shutil.rmtree IOError -> ToolExecutionError
    manager.create_directory("subdir")
    with patch("shutil.rmtree", side_effect=OSError("Remove failed")):
        with pytest.raises(ToolExecutionError):
            manager.delete_file("subdir")
            
    # 5. mkdir IOError -> ToolExecutionError
    with patch("pathlib.Path.mkdir", side_effect=OSError("Mkdir failed")):
        with pytest.raises(ToolExecutionError):
            manager.create_directory("new_subdir")
            
    # 6. iterdir IOError -> ToolExecutionError
    with patch("pathlib.Path.iterdir", side_effect=OSError("Iterdir failed")):
        with pytest.raises(ToolExecutionError):
            manager.list_directory(".")
            
    # 7. shutil.move IOError -> ToolExecutionError
    with patch("shutil.move", side_effect=OSError("Move failed")):
        with pytest.raises(ToolExecutionError):
            manager.rename_file("read_err.txt", "moved.txt")


