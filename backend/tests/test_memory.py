import os
import uuid
import pytest
import pytest_asyncio
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock, AsyncMock

from sqlalchemy import select, delete
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.core.security import create_access_token
from app.db.base import AsyncSessionLocal
from app.db.models import User, Memory
from tests.conftest import TEST_USER_ID, TEST_USER, TEST_AUTH_HEADERS

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
from app.memory.embeddings import generate_embedding
from app.planner.schemas import PlanningRequest, ExecutionPlan, Task, TaskPriority, Complexity
from app.planner.service import PlannerService
from app.agents.executor import AgentExecutor
from app.agents.schemas import AgentAction, AgentObservation, Thought, Action, Observation, ReActStep


@pytest_asyncio.fixture
async def setup_test_memory(db_session):
    await db_session.execute(delete(Memory).where(Memory.user_id == TEST_USER_ID))
    await db_session.commit()
    
    store = MemoryStore(db=db_session, user_id=TEST_USER_ID)
    manager = MemoryManager(store=store)
    
    from app.api.v1.endpoints.memory import get_memory_manager
    from app.api.v1.endpoints.chat import get_chat_service
    from app.chat.service import ChatService
    
    app.dependency_overrides[get_memory_manager] = lambda: manager
    app.dependency_overrides[get_chat_service] = lambda: ChatService(manager=manager, user_id=str(TEST_USER_ID))
    
    yield store
    
    app.dependency_overrides.pop(get_memory_manager, None)
    app.dependency_overrides.pop(get_chat_service, None)


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


@pytest.mark.asyncio
async def test_memory_store_lifecycle(setup_test_memory):
    store = setup_test_memory
    
    entry = MemoryEntry(
        id="11111111-1111-1111-1111-222222222222",
        timestamp=datetime.now(timezone.utc),
        category="execution",
        title="Test Execution",
        content="This is a test run content.",
        metadata={"exec_id": "exec-123"},
        tags=["test", "exec"]
    )
    
    with patch("app.memory.store.generate_embedding", return_value=[0.1] * 768):
        # Save
        await store.save(entry)
        
        # Load
        loaded = await store.load("11111111-1111-1111-1111-222222222222")
        assert loaded is not None
        assert loaded.id == "11111111-1111-1111-1111-222222222222"
        assert loaded.title == "Test Execution"
        assert loaded.tags == ["test", "exec"]
        
        # List
        entries = await store.list()
        assert len(entries) == 1
        assert entries[0].id == "11111111-1111-1111-1111-222222222222"
        
        # Statistics
        stats = await store.statistics()
        assert stats.total_entries == 1
        assert stats.category_counts == {"execution": 1}
        assert stats.tag_counts == {"test": 1, "exec": 1}
        assert stats.storage_size_bytes > 0
        assert stats.last_updated is not None
        
        # Delete
        deleted = await store.delete("11111111-1111-1111-1111-222222222222")
        assert deleted is True
        assert await store.load("11111111-1111-1111-1111-222222222222") is None
        
        # Delete non-existent
        assert await store.delete("11111111-1111-1111-1111-222222222222") is False


@pytest.mark.asyncio
async def test_memory_store_search(setup_test_memory):
    store = setup_test_memory
    
    entry1 = MemoryEntry(
        id="11111111-1111-1111-1111-333333333333",
        timestamp=datetime.now(timezone.utc),
        category="plan",
        title="Python code generation plan",
        content="Build a FastAPI router with full dependencies.",
        metadata={},
        tags=["python", "fastapi"]
    )
    
    entry2 = MemoryEntry(
        id="11111111-1111-1111-1111-444444444444",
        timestamp=datetime.now(timezone.utc),
        category="tool_output",
        title="Git status outputs",
        content="Files modified: backend/app/main.py",
        metadata={},
        tags=["git", "vcs"]
    )
    
    with patch("app.memory.store.generate_embedding", return_value=[0.1] * 768):
        await store.save(entry1)
        await store.save(entry2)
        
        # Empty query search
        empty_results = await store.search("")
        assert len(empty_results) == 2
        
        # Vector search query
        results_py = await store.search("python")
        assert len(results_py) >= 1
        
        # Category and tag filtered search
        results_filtered = await store.search("router", category="plan", tags=["python"])
        assert len(results_filtered) == 1
        assert results_filtered[0].entry.id == "11111111-1111-1111-1111-333333333333"
        
        results_no_match = await store.search("router", category="non_existent_category")
        assert len(results_no_match) == 0

        # Fallback keyword search path (when embedding returns None)
        with patch("app.memory.store.generate_embedding", return_value=None):
            fallback_results = await store.search("python")
            assert len(fallback_results) == 1
            assert fallback_results[0].entry.id == "11111111-1111-1111-1111-333333333333"
            assert fallback_results[0].score > 0


@pytest.mark.asyncio
async def test_memory_manager(setup_test_memory):
    store = setup_test_memory
    manager = MemoryManager(store=store)
    
    with patch("app.memory.store.generate_embedding", return_value=[0.1] * 768):
        # save_execution
        exec_entry = await manager.save_execution(
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
        plan_entry = await manager.save_plan(
            goal="Planning goal",
            plan={"tasks": [{"id": "t1", "title": "t1_title"}]}
        )
        assert plan_entry.category == "plan"
        
        # save_tool_output
        tool_entry = await manager.save_tool_output(
            tool_name="git_status",
            args={},
            output="modified files",
            success=True
        )
        assert tool_entry.category == "tool_output"
        
        # save_observation
        obs_entry = await manager.save_observation(
            task_id="task-1",
            content="file exists",
            success=True
        )
        assert obs_entry.category == "observation"
        
        # save_conversation
        conv_entry = await manager.save_conversation(
            conversation_id="conv-1",
            message="Hello AI",
            role="user"
        )
        assert conv_entry.category == "conversation"
        
        # retrieve helper methods
        recent = await manager.retrieve_recent(limit=2)
        assert len(recent) == 2
        plans = await manager.retrieve_by_category("plan")
        assert len(plans) == 1
        git_tools = await manager.retrieve_by_tag("git_status")
        assert len(git_tools) == 1
        similar = await manager.retrieve_similar("Planning", category="plan")
        assert len(similar) == 1
        
        # summarize
        summary = await manager.summarize()
        assert summary.total_entries == 5
        assert summary.category_counts["plan"] == 1
        assert len(summary.recent_entries) <= 5
        
        # clear_history
        await manager.clear_history()
        listed = await store.list()
        assert len(listed) == 0


@pytest.mark.asyncio
async def test_memory_service(setup_test_memory):
    store = setup_test_memory
    manager = MemoryManager(store=store)
    service = MemoryService(manager=manager)
    
    with patch("app.memory.store.generate_embedding", return_value=[0.1] * 768):
        # Populate memory
        await manager.save_plan(
            goal="Deploy frontend",
            plan={"tasks": [{"id": "t1", "title": "Build site", "estimated_complexity": "EASY"}]}
        )
        await manager.save_execution(
            execution_id="exec-123",
            goal="Deploy frontend",
            status="FAILED",
            tasks=["t1"],
            duration=1.2,
            error="build command failed"
        )
        await manager.save_tool_output(
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
         patch("app.memory.service.memory_service.get_planning_context", new=test_service.get_planning_context), \
         patch("app.memory.store.generate_embedding", return_value=[0.1] * 768):
        
        await test_manager.save_execution("prev-exec", "Test custom planning goal", "FAILED", [], 2.0, "API timeout")
        
        response = await planner_service.generate_plan(req, memory_manager=test_manager)
        assert response.plan.goal == "Test custom planning goal"
        
        saved_plans = await store.list(category="plan")
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
    
    with patch("app.agents.registry.agent_registry.get_agent", return_value=mock_agent), \
         patch("app.memory.store.generate_embedding", return_value=[0.1] * 768):
             
        executor = AgentExecutor(plan=plan, execution_id="exec-abc-123", memory_manager=test_manager)
        res = await executor.execute()
        assert res.status == "COMPLETED"
        
        obs_memories = await store.list(category="observation")
        assert len(obs_memories) >= 2
        reasons = [m.content for m in obs_memories]
        assert "Thought reasoning: Checking dependencies first" in reasons
        assert "File written successfully" in reasons
        
        tool_memories = await store.list(category="tool_output")
        assert len(tool_memories) == 1
        assert tool_memories[0].metadata["tool_name"] == "write_file"
        
        exec_memories = await store.list(category="execution")
        assert len(exec_memories) == 1
        assert exec_memories[0].metadata["execution_id"] == "exec-abc-123"


@pytest.mark.asyncio
async def test_api_endpoints_mocked(setup_test_memory):
    store = setup_test_memory
    test_manager = MemoryManager(store=store)
    
    with patch("app.memory.store.generate_embedding", return_value=[0.1] * 768):
        await test_manager.save_plan("Goal 1", {"tasks": []})
        await test_manager.save_execution("exec-1", "Goal 1", "COMPLETED", [], 5.0)
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test", headers=TEST_AUTH_HEADERS) as ac:
            # GET /memory
            resp = await ac.get("/api/v1/memory")
            assert resp.status_code == 200
            data = resp.json()
            assert data["total_entries"] == 2
            assert data["category_counts"]["plan"] == 1
            
            # GET /memory/list
            resp = await ac.get("/api/v1/memory/list")
            assert resp.status_code == 200
            entries = resp.json()
            assert len(entries) == 2
            
            # GET /memory/search
            resp = await ac.get("/api/v1/memory/search?query=Goal")
            assert resp.status_code == 200
            search_res = resp.json()
            assert len(search_res["results"]) == 2
            assert search_res["results"][0]["score"] > 0
            
            # GET /memory/statistics
            resp = await ac.get("/api/v1/memory/statistics")
            assert resp.status_code == 200
            stats = resp.json()
            assert stats["total_entries"] == 2
            assert stats["category_counts"]["execution"] == 1
            
            # DELETE /memory
            resp = await ac.delete("/api/v1/memory")
            assert resp.status_code == 204
            
            listed = await store.list()
            assert len(listed) == 0


@pytest.mark.asyncio
async def test_memory_service_exception(setup_test_memory):
    store = setup_test_memory
    manager = MemoryManager(store=store)
    service = MemoryService(manager=manager)
    
    with patch.object(manager, "retrieve_similar", side_effect=Exception("Database connection error")):
        context = await service.get_planning_context("some goal")
        assert context == ""


@pytest.mark.asyncio
async def test_multi_user_memory_isolation(db_session):
    from app.core.auth import get_current_user
    from app.api.v1.endpoints.memory import get_memory_manager
    from app.api.v1.endpoints.chat import get_chat_service

    app.dependency_overrides.pop(get_memory_manager, None)
    app.dependency_overrides.pop(get_chat_service, None)

    user_a_id = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
    user_b_id = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")

    user_a = User(id=user_a_id, email="usera@example.com", hashed_password="pw", created_at=datetime.now(timezone.utc))
    user_b = User(id=user_b_id, email="userb@example.com", hashed_password="pw", created_at=datetime.now(timezone.utc))

    token_a = create_access_token(str(user_a_id))
    token_b = create_access_token(str(user_b_id))

    with patch("app.memory.store.generate_embedding", return_value=[0.1] * 768):
        app.dependency_overrides[get_current_user] = lambda: user_a

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test", headers={"Authorization": f"Bearer {token_a}"}) as ac_a:
            res_list_a = await ac_a.get("/api/v1/memory/list")
            assert res_list_a.status_code == 200

            with patch("app.llm.providers.base.BaseLLMProvider.generate") as mock_gen:
                mock_gen.return_value = MagicMock(content="Hello User A!")
                res_chat = await ac_a.post("/api/v1/chat", json={"message": "Secret message from User A"})
                assert res_chat.status_code == 200

        # Switch current user to User B
        app.dependency_overrides[get_current_user] = lambda: user_b

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test", headers={"Authorization": f"Bearer {token_b}"}) as ac_b:
            res_mem_b = await ac_b.get("/api/v1/memory/list")
            assert res_mem_b.status_code == 200
            b_memories = res_mem_b.json()
            assert len(b_memories) == 0

            res_chat_b = await ac_b.get("/api/v1/chat/history")
            assert res_chat_b.status_code == 200
            b_history = res_chat_b.json()
            assert len(b_history) == 0


@pytest.mark.skip(reason="Requires external live GEMINI_API_KEY")
def test_real_gemini_embedding_api():
    vec = generate_embedding("Hello CodeForge vector test!")
    assert vec is not None
    assert len(vec) == 768
