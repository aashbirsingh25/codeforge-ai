import os
import shutil
import pytest
from pathlib import Path
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock, AsyncMock

from fastapi.testclient import TestClient
from app.main import app

from app.core.config import settings
from app.memory.exceptions import (
    MemoryException,
    MemoryNotFoundException,
    MemoryPersistenceException,
    MemoryValidationException
)
from app.memory.schemas import (
    MemoryEntry,
    MemorySummary,
    MemoryStatistics,
    MemorySearchResponse,
)
from app.memory.store import MemoryStore
from app.memory.manager import MemoryManager
from app.memory.service import MemoryService
from app.planner.schemas import PlanningRequest, ExecutionPlan, Task, TaskPriority, Complexity
from app.planner.service import PlannerService
from app.agents.executor import AgentExecutor
from app.agents.schemas import AgentAction, AgentObservation, Thought, Action, Observation, ReActStep

# Set up test client
client = TestClient(app)

# Autouse fixture to isolate memory storage directory for all tests
@pytest.fixture(autouse=True)
def setup_test_memory(tmp_path):
    temp_dir = tmp_path / "memory_test"
    temp_dir.mkdir(parents=True, exist_ok=True)
    store = MemoryStore(memory_dir=temp_dir)
    # Re-initialize MemoryManager singleton with the test store
    MemoryManager(store=store)
    yield store
    # Cleanup
    if temp_dir.exists():
        shutil.rmtree(temp_dir)

def test_exceptions():
    exc = MemoryException("error", status_code=500)
    assert exc.message == "error"
    assert exc.status_code == 500

    exc_nf = MemoryNotFoundException("not found")
    assert exc_nf.message == "not found"
    assert exc_nf.status_code == 404

    exc_pe = MemoryPersistenceException("persist error")
    assert exc_pe.message == "persist error"
    assert exc_pe.status_code == 500

    exc_va = MemoryValidationException("validation error")
    assert exc_va.message == "validation error"
    assert exc_va.status_code == 422

def test_memory_store_lifecycle(setup_test_memory):
    store = setup_test_memory
    
    entry = MemoryEntry(
        id="test-id-1",
        timestamp=datetime.now(timezone.utc),
        category="execution",
        title="Test Execution",
        content="This is a test run content.",
        metadata={"exec_id": "exec-123"},
        tags=["test", "exec"]
    )
    
    # Save
    store.save(entry)
    
    # File exists check
    file_path = store.memory_dir / "test-id-1.json"
    assert file_path.exists()
    
    # Load
    loaded = store.load("test-id-1")
    assert loaded is not None
    assert loaded.id == "test-id-1"
    assert loaded.title == "Test Execution"
    assert loaded.tags == ["test", "exec"]
    
    # Reload / Restart test (new store instance pointing to same directory)
    new_store = MemoryStore(memory_dir=store.memory_dir)
    loaded_new = new_store.load("test-id-1")
    assert loaded_new is not None
    assert loaded_new.id == "test-id-1"
    
    # List
    entries = store.list()
    assert len(entries) == 1
    assert entries[0].id == "test-id-1"
    
    # Statistics
    stats = store.statistics()
    assert stats.total_entries == 1
    assert stats.category_counts == {"execution": 1}
    assert stats.tag_counts == {"test": 1, "exec": 1}
    assert stats.storage_size_bytes > 0
    assert stats.last_updated is not None
    
    # Delete
    deleted = store.delete("test-id-1")
    assert deleted is True
    assert store.load("test-id-1") is None
    
    # Delete non-existent
    assert store.delete("test-id-1") is False

def test_memory_store_search(setup_test_memory):
    store = setup_test_memory
    
    entry1 = MemoryEntry(
        id="id-1",
        timestamp=datetime.now(timezone.utc),
        category="plan",
        title="Python code generation plan",
        content="Build a FastAPI router with full dependencies.",
        metadata={},
        tags=["python", "fastapi"]
    )
    
    entry2 = MemoryEntry(
        id="id-2",
        timestamp=datetime.now(timezone.utc),
        category="tool_output",
        title="Git status outputs",
        content="Files modified: backend/app/main.py",
        metadata={},
        tags=["git", "vcs"]
    )
    
    store.save(entry1)
    store.save(entry2)
    
    # Empty query search
    empty_results = store.search("")
    assert len(empty_results) == 2
    
    # Python query search
    results_py = store.search("python")
    assert len(results_py) == 1
    assert results_py[0].entry.id == "id-1"
    assert results_py[0].score > 0
    
    # Category and tag filtered search
    results_filtered = store.search("router", category="plan", tags=["python"])
    assert len(results_filtered) == 1
    assert results_filtered[0].entry.id == "id-1"
    
    results_no_match = store.search("router", category="tool_output")
    assert len(results_no_match) == 0

def test_memory_store_persistence_failures(setup_test_memory):
    with patch("pathlib.Path.mkdir", side_effect=OSError("permission denied")):
        with pytest.raises(MemoryPersistenceException):
            MemoryStore(memory_dir=Path("/non_existent_folder_xyz/123"))

def test_memory_manager(setup_test_memory):
    store = setup_test_memory
    manager = MemoryManager(store=store)
    
    # save_execution
    exec_entry = manager.save_execution(
        execution_id="exec-1",
        goal="Build feature A",
        status="COMPLETED",
        tasks=["task1"],
        duration=10.5
    )
    assert exec_entry.category == "execution"
    assert "execution" in exec_entry.tags
    assert "completed" in exec_entry.tags
    assert "success" in exec_entry.tags
    
    # save_plan
    plan_entry = manager.save_plan(
        goal="Planning goal",
        plan={"tasks": [{"id": "t1", "title": "t1_title"}]}
    )
    assert plan_entry.category == "plan"
    
    # save_tool_output
    tool_entry = manager.save_tool_output(
        tool_name="git_status",
        args={},
        output="modified files",
        success=True
    )
    assert tool_entry.category == "tool_output"
    
    # save_observation
    obs_entry = manager.save_observation(
        task_id="task-1",
        content="file exists",
        success=True
    )
    assert obs_entry.category == "observation"
    
    # save_conversation
    conv_entry = manager.save_conversation(
        conversation_id="conv-1",
        message="Hello AI",
        role="user"
    )
    assert conv_entry.category == "conversation"
    
    # retrieve helper methods
    assert len(manager.retrieve_recent(limit=2)) == 2
    assert len(manager.retrieve_by_category("plan")) == 1
    assert len(manager.retrieve_by_tag("git_status")) == 1
    assert len(manager.retrieve_similar("Planning", category="plan")) == 1
    
    # summarize
    summary = manager.summarize()
    assert summary.total_entries == 5
    assert summary.category_counts["plan"] == 1
    assert len(summary.recent_entries) <= 5
    
    # clear_history
    manager.clear_history()
    assert len(store.list()) == 0

@pytest.mark.asyncio
async def test_memory_service(setup_test_memory):
    store = setup_test_memory
    manager = MemoryManager(store=store)
    service = MemoryService(manager=manager)
    
    # Populate memory
    manager.save_plan(
        goal="Deploy frontend",
        plan={"tasks": [{"id": "t1", "title": "Build site", "estimated_complexity": "EASY"}]}
    )
    manager.save_execution(
        execution_id="exec-123",
        goal="Deploy frontend",
        status="FAILED",
        tasks=["t1"],
        duration=1.2,
        error="build command failed"
    )
    manager.save_tool_output(
        tool_name="run_command",
        args={"cmd": "npm run build"},
        output="exit code 1",
        success=False
    )
    
    context = await service.get_planning_context("Deploy frontend")
    assert "--- PREVIOUS SIMILAR PLANS ---" in context
    assert "--- RECENT EXECUTIONS ---" in context
    assert "--- RECENT FAILURES & ERRORS ---" in context
    assert "--- RECENT TOOL OUTPUTS ---" in context
    assert "Deploy frontend" in context
    assert "exit code 1" in context

@pytest.mark.asyncio
async def test_planner_service_integration(setup_test_memory):
    store = setup_test_memory
    test_manager = MemoryManager(store=store)
    test_service = MemoryService(manager=test_manager)
    
    planner_service = PlannerService()
    req = PlanningRequest(goal="Test custom planning goal", strategy="sequential", provider="gemini")
    
    mock_chat_response = MagicMock()
    mock_chat_response.content = """
    {
      "goal": "Test custom planning goal",
      "tasks": [
        {
          "id": "task-1",
          "title": "Task 1",
          "description": "Desc 1",
          "priority": "MEDIUM",
          "estimated_complexity": "EASY",
          "estimated_duration": "30m",
          "dependencies": [],
          "status": "PENDING",
          "subtasks": []
        }
      ]
    }
    """
    
    mock_provider = MagicMock()
    mock_provider.generate = AsyncMock(return_value=mock_chat_response)
    
    with patch("app.llm.factory.ProviderFactory.get_provider", return_value=mock_provider), \
         patch("app.memory.service.memory_service.get_planning_context", new=test_service.get_planning_context):
        
        test_manager.save_execution("prev-exec", "Test custom planning goal", "FAILED", [], 2.0, "API timeout")
        
        response = await planner_service.generate_plan(req)
        assert response.plan.goal == "Test custom planning goal"
        
        saved_plans = store.list(category="plan")
        assert len(saved_plans) == 1
        assert saved_plans[0].metadata["goal"] == "Test custom planning goal"

@pytest.mark.asyncio
async def test_agent_executor_integration(setup_test_memory):
    store = setup_test_memory
    test_manager = MemoryManager(store=store)
    
    plan = ExecutionPlan(
        goal="Integration agent test",
        tasks=[
            Task(
                id="task-1",
                title="Integrate tool",
                description="Call write_file tool",
                priority=TaskPriority.HIGH,
                estimated_complexity=Complexity.EASY,
                estimated_duration="10m",
                dependencies=[],
                status="PENDING",
                subtasks=[]
            )
        ]
    )
    
    mock_agent = MagicMock()
    
    async def simulate_execute(task_id, context):
        context["react_trace_callback"](ReActStep(
            thought=Thought(reasoning="Checking dependencies first"),
            duration_seconds=0.2
        ))
        context["action_recorder"](
            AgentAction(tool_name="write_file", tool_args={"path": "test.txt", "content": "hello"}),
            AgentObservation(content="File written successfully", success=True)
        )
        from app.agents.schemas import AgentResult
        return AgentResult(success=True, output="Finished writing file")
        
    mock_agent.execute = simulate_execute
    
    with patch("app.agents.registry.agent_registry.get_agent", return_value=mock_agent):
             
        executor = AgentExecutor(plan=plan, execution_id="exec-abc-123")
        res = await executor.execute()
        assert res.status == "COMPLETED"
        
        obs_memories = store.list(category="observation")
        assert len(obs_memories) >= 2
        reasons = [m.content for m in obs_memories]
        assert "Thought reasoning: Checking dependencies first" in reasons
        assert "File written successfully" in reasons
        
        tool_memories = store.list(category="tool_output")
        assert len(tool_memories) == 1
        assert tool_memories[0].metadata["tool_name"] == "write_file"
        
        exec_memories = store.list(category="execution")
        assert len(exec_memories) == 1
        assert exec_memories[0].metadata["execution_id"] == "exec-abc-123"

def test_api_endpoints_mocked(setup_test_memory):
    store = setup_test_memory
    test_manager = MemoryManager(store=store)
    
    test_manager.save_plan("Goal 1", {"tasks": []})
    test_manager.save_execution("exec-1", "Goal 1", "COMPLETED", [], 5.0)
    
    # GET /memory
    resp = client.get("/api/v1/memory")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_entries"] == 2
    assert data["category_counts"]["plan"] == 1
    
    # GET /memory/list
    resp = client.get("/api/v1/memory/list")
    assert resp.status_code == 200
    entries = resp.json()
    assert len(entries) == 2
    
    # GET /memory/search
    resp = client.get("/api/v1/memory/search?query=Goal")
    assert resp.status_code == 200
    search_res = resp.json()
    assert len(search_res["results"]) == 2
    assert search_res["results"][0]["score"] > 0
    
    # GET /memory/statistics
    resp = client.get("/api/v1/memory/statistics")
    assert resp.status_code == 200
    stats = resp.json()
    assert stats["total_entries"] == 2
    assert stats["category_counts"]["execution"] == 1
    
    # DELETE /memory
    resp = client.delete("/api/v1/memory")
    assert resp.status_code == 204
    
    assert len(store.list()) == 0

def test_corrupted_json_file(setup_test_memory):
    store = setup_test_memory
    
    # Write a corrupted json file
    corrupt_file = store.memory_dir / "corrupted.json"
    with open(corrupt_file, "w", encoding="utf-8") as f:
        f.write("{invalid_json:")
        
    # Listing should skip the corrupted file and not raise exception
    entries = store.list()
    assert len(entries) == 0

@pytest.mark.asyncio
async def test_memory_service_exception(setup_test_memory):
    store = setup_test_memory
    manager = MemoryManager(store=store)
    service = MemoryService(manager=manager)
    
    # Mock manager to raise an exception on retrieve_similar
    with patch.object(manager, "retrieve_similar", side_effect=Exception("Database connection error")):
        context = await service.get_planning_context("some goal")
        assert context == ""

def test_memory_store_save_load_exceptions(setup_test_memory):
    store = setup_test_memory
    
    # Test save exception by patching json.dump to raise an error
    entry = MemoryEntry(
        id="test-err",
        timestamp=datetime.now(timezone.utc),
        category="plan",
        title="Title",
        content="Content"
    )
    with patch("json.dump", side_effect=TypeError("Not serializable")):
        with pytest.raises(MemoryPersistenceException):
            store.save(entry)
            
    corrupt_file = store.memory_dir / "test-err.json"
    with open(corrupt_file, "w", encoding="utf-8") as f:
        f.write("{invalid")
    with pytest.raises(MemoryPersistenceException):
        store.load("test-err")

def test_memory_store_other_exceptions(setup_test_memory):
    store = setup_test_memory
    
    # Test delete exception
    with patch("pathlib.Path.unlink", side_effect=PermissionError("Permission denied")):
        entry = MemoryEntry(
            id="test-del",
            timestamp=datetime.now(timezone.utc),
            category="plan",
            title="Title",
            content="Content"
        )
        store.save(entry)
        with pytest.raises(MemoryPersistenceException):
            store.delete("test-del")
            
    # Test clear exception
    with patch("pathlib.Path.glob", side_effect=RuntimeError("Glob error")):
        with pytest.raises(MemoryPersistenceException):
            store.clear()
            
    # Test statistics exception
    with patch("app.memory.store.MemoryStore.list", side_effect=Exception("List error")):
        with pytest.raises(MemoryPersistenceException):
            store.statistics()

def test_memory_store_search_exception(setup_test_memory):
    store = setup_test_memory
    with patch("app.memory.store.MemoryStore.list", side_effect=Exception("List error")):
        with pytest.raises(MemoryPersistenceException):
            store.search("query")

def test_memory_manager_save_plan_fallback(setup_test_memory):
    store = setup_test_memory
    manager = MemoryManager(store=store)
    
    plan_dict = {"goal": "test", "tasks": []}
    entry = manager.save_plan("Goal text", plan_dict)
    assert entry.metadata["plan"] == plan_dict
