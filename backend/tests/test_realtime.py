import os
import time
import pytest
import json
import asyncio
import shutil
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient

from app.main import app
from tests.conftest import TEST_AUTH_HEADERS

client = TestClient(app, headers=TEST_AUTH_HEADERS)


from app.core.events import event_publisher
from app.core.metrics import metrics_tracker
from app.core.middleware import rate_limiter
from app.agents.service import execution_service
from app.memory.store import MemoryStore
from app.memory.manager import MemoryManager
from app.planner.schemas import ExecutionPlan, Task, TaskPriority
from app.core.config import settings
from app.agents.schemas import ExecutionRequest, ExecutionResponse, ExecutionState, ReActTrace


@pytest.fixture(autouse=True)
def setup_test_memory(tmp_path):
    temp_dir = tmp_path / "memory_test"
    temp_dir.mkdir(parents=True, exist_ok=True)
    store = MemoryStore(memory_dir=temp_dir)
    MemoryManager(store=store)
    yield store
    if temp_dir.exists():
        shutil.rmtree(temp_dir)

@pytest.fixture(autouse=True)
def reset_metrics_and_limiter():
    metrics_tracker.start_time = time.time()
    metrics_tracker.request_count = 0
    metrics_tracker.provider_usage = {}
    metrics_tracker.completed_executions = 0
    metrics_tracker.failed_executions = 0
    metrics_tracker.cancelled_executions = 0
    metrics_tracker.execution_durations = []
    
    execution_service._executions.clear()
    execution_service._active_tasks.clear()
    execution_service._active_executors.clear()
    
    rate_limiter.history.clear()

def test_structured_logging():
    from app.core.logging import log_structured_event
    with patch("app.core.logging.structured_logger.info") as mock_info:
        log_structured_event(
            event="test_event",
            request_id="req-1",
            execution_id="exec-1",
            provider="gemini",
            tool="git_status",
            duration=1.23,
            status="completed",
            extra={"custom_key": "custom_val"}
        )
        mock_info.assert_called_once()
        log_str = mock_info.call_args[0][0]
        assert "event=test_event" in log_str
        assert "request_id=req-1" in log_str
        assert "execution_id=exec-1" in log_str
        assert "provider=gemini" in log_str
        assert "tool=git_status" in log_str
        assert "duration=1.2300s" in log_str
        assert "status=completed" in log_str
        assert "custom_key=custom_val" in log_str

def test_metrics_endpoint():
    resp = client.get("/api/v1/metrics")
    assert resp.status_code == 200
    data = resp.json()
    assert data["uptime_seconds"] >= 0
    assert data["active_executions"] == 0
    assert data["completed_executions"] == 0
    assert data["failed_executions"] == 0
    assert data["request_count"] > 0
    
    metrics_tracker.track_provider("gemini")
    metrics_tracker.track_execution("COMPLETED", 1.5)
    metrics_tracker.track_execution("FAILED", 2.5)
    metrics_tracker.track_execution("CANCELLED", 0.5)
    
    resp = client.get("/api/v1/metrics")
    data = resp.json()
    assert data["completed_executions"] == 1
    assert data["failed_executions"] == 1
    assert data["cancelled_executions"] == 1
    assert data["provider_usage"]["gemini"] == 1
    assert data["average_execution_duration_seconds"] == 1.5

def test_rate_limiting():
    with patch("app.core.config.settings.RATE_LIMIT_CALLS", 2):
        with patch("app.core.config.settings.RATE_LIMIT_WINDOW_SECONDS", 10):
            resp = client.get("/api/v1/health")
            assert resp.status_code == 200
            
            resp = client.get("/api/v1/metrics")
            assert resp.status_code == 200
            
            resp = client.get("/api/v1/metrics")
            assert resp.status_code == 200
            
            resp = client.get("/api/v1/metrics")
            assert resp.status_code == 429
            data = resp.json()
            assert "Rate limit exceeded" in data["error"]["message"]
            assert data["error"]["type"] == "RateLimitExceeded"
            
            resp = client.get("/api/v1/health")
            assert resp.status_code == 200

@pytest.mark.asyncio
async def test_chat_streaming():
    mock_provider = MagicMock()
    async def mock_stream(request):
        yield "Hello "
        yield "there "
        yield "world!"
    mock_provider.generate_stream = mock_stream
    
    with patch("app.llm.factory.ProviderFactory.get_provider", return_value=mock_provider):
        resp = client.post("/api/v1/chat/stream", json={"message": "hi"})
        assert resp.status_code == 200
        assert "text/event-stream" in resp.headers["content-type"]
        
        lines = []
        for line in resp.iter_lines():
            if line:
                lines.append(line)
        
        assert "event: started" in lines[0]
        assert 'data: {"status": "started"}' in lines[1]
        
        assert "event: token" in lines[2]
        assert 'data: {"token": "Hello "}' in lines[3]
        
        assert "event: token" in lines[4]
        assert 'data: {"token": "there "}' in lines[5]
        
        assert "event: token" in lines[6]
        assert 'data: {"token": "world!"}' in lines[7]
        
        assert "event: completed" in lines[8]
        assert "world!" in lines[9]

@pytest.mark.asyncio
async def test_agent_events_and_cancellation(setup_test_memory):
    plan = ExecutionPlan(
        goal="Test Cancellation",
        tasks=[
            Task(
                id="task-1",
                title="T1",
                description="Wait a bit",
                priority=TaskPriority.LOW,
                estimated_complexity="EASY",
                estimated_duration="1 hour",
                dependencies=[]
            )
        ]
    )
    
    mock_agent = MagicMock()
    async def slow_execute(task_id, context):
        from app.agents.schemas import AgentAction, AgentObservation, ReActStep, Thought
        
        context["react_trace_callback"](ReActStep(thought=Thought(reasoning="I need to call tool"), action=None, observation=None, duration_seconds=0.1))
        
        action = AgentAction(tool_name="git_status", tool_args={})
        observation = AgentObservation(success=True, content="clean repo", error=None)
        context["action_recorder"](action, observation)
        
        await asyncio.sleep(1.0)
        return MagicMock()
        
    mock_agent.execute = slow_execute
    
    with patch("app.agents.registry.AgentRegistry.get_agent", return_value=mock_agent):
        with patch("app.llm.factory.ProviderFactory.get_provider", return_value=MagicMock()):
            # Run in the same event loop (in-process background task)
            exec_task = asyncio.create_task(execution_service.execute_request(
                request=ExecutionRequest(plan=plan),
                provider="gemini"
            ))
            
            await asyncio.sleep(0.05)
            
            active_ids = list(execution_service._active_tasks.keys())
            assert len(active_ids) == 1
            exec_id = active_ids[0]
            
            # Subscribing in the same event loop is thread-safe and deadlock-proof
            queue = event_publisher.subscribe(exec_id)
            
            # Check historical events cached
            history = event_publisher.get_history(exec_id)
            assert len(history) >= 4
            assert any(e["type"] == "started" for e in history)
            assert any(e["type"] == "thinking" for e in history)
            assert any(e["type"] == "tool_call" for e in history)
            assert any(e["type"] == "observation" for e in history)
            
            # Trigger cancellation directly on the service (in-process call)
            success = execution_service.cancel_execution(exec_id)
            assert success is True
            
            with pytest.raises(asyncio.CancelledError):
                await exec_task
                
            # Verify cancelled event is emitted on the subscriber queue
            queued_events = []
            while not queue.empty():
                queued_events.append(queue.get_nowait())
                
            assert any(e["type"] == "cancelled" for e in queued_events)
            event_publisher.unsubscribe(exec_id, queue)
            
            # Verify response is recorded as CANCELLED
            status_resp = execution_service.get_status(exec_id)
            assert status_resp is not None
            assert status_resp.status == "CANCELLED"
            
            # Verify Memory Engine persistence
            assert len(setup_test_memory.list(category="execution")) == 1
            entry = setup_test_memory.list(category="execution")[0]
            assert entry.metadata["status"] == "CANCELLED"

@pytest.mark.asyncio
async def test_events_endpoint_routing():
    # 1. Non-existent ID returns 404
    resp = client.get("/api/v1/agents/non-existent-id/events")
    assert resp.status_code == 404
    assert "not found" in resp.json()["error"]["message"]
    
    # 2. Valid running ID returns 200 text/event-stream (tested in-process to avoid deadlock)
    from app.api.v1.endpoints.agents import get_execution_events
    from app.agents.schemas import ExecutionMetrics
    
    state_instance = ExecutionState(
        goal="Test", tasks=[], current_task=None, completed_tasks=[], failed_tasks=[], status="RUNNING"
    )
    dummy = ExecutionResponse(
        execution_id="mock-running-id",
        status="RUNNING",
        plan=ExecutionPlan(goal="Test", tasks=[]),
        state=state_instance,
        metrics=ExecutionMetrics(
            start_time="2026-07-06T12:00:00Z", end_time=None, duration_seconds=0.0, retry_count=0
        ),
        react_trace=ReActTrace(execution_id="mock-running-id", steps=[])
    )
    with patch.object(execution_service, "get_status", return_value=dummy):
        resp = await get_execution_events(
            execution_id="mock-running-id",
            service=execution_service
        )
        assert resp.media_type == "text/event-stream"

def test_cancel_execution_endpoint():
    with patch("app.agents.service.execution_service.cancel_execution", return_value=True):
        resp = client.post("/api/v1/agents/some-id/cancel")
        assert resp.status_code == 200
        assert "Cancellation request for execution" in resp.json()["message"]

def test_cancel_non_existent_or_completed_execution():
    resp = client.post("/api/v1/agents/non-existent-id/cancel")
    assert resp.status_code == 404
    assert "not found or is not running" in resp.json()["error"]["message"]

def test_events_non_existent_execution():
    resp = client.get("/api/v1/agents/non-existent-id/events")
    assert resp.status_code == 404
    assert "not found" in resp.json()["error"]["message"]

@pytest.mark.asyncio
async def test_stale_execution_cleanup_and_timeouts():
    from app.agents.schemas import ExecutionMetrics, ExecutionResponse
    
    past_iso = "2026-07-06T12:00:00Z"
    
    state_instance = ExecutionState(
        goal="Stale",
        tasks=[],
        current_task=None,
        completed_tasks=[],
        failed_tasks=[],
        status="COMPLETED"
    )
    trace_instance = ReActTrace(execution_id="stale-completed", steps=[])
    
    dummy_response = ExecutionResponse(
        execution_id="stale-completed",
        status="COMPLETED",
        plan=ExecutionPlan(goal="Stale", tasks=[]),
        state=state_instance,
        metrics=ExecutionMetrics(
            start_time=past_iso,
            end_time=past_iso,
            duration_seconds=1.0,
            retry_count=0
        ),
        react_trace=trace_instance
    )
    execution_service._executions["stale-completed"] = dummy_response
    
    execution_service.cleanup_stale_executions(timeout_seconds=5.0)
    assert "stale-completed" not in execution_service._executions
    
    slow_plan = ExecutionPlan(
        goal="Stale Running",
        tasks=[
            Task(
                id="slow-1",
                title="S1",
                description="Slow task",
                priority=TaskPriority.LOW,
                estimated_complexity="EASY",
                estimated_duration="1 hour",
                dependencies=[]
            )
        ]
    )
    
    mock_agent = MagicMock()
    async def slow_execute(task_id, context):
        await asyncio.sleep(10.0)
        return MagicMock()
    mock_agent.execute = slow_execute
    
    with patch("app.agents.registry.AgentRegistry.get_agent", return_value=mock_agent):
        with patch("app.llm.factory.ProviderFactory.get_provider", return_value=MagicMock()):
            with patch("app.core.config.settings.AGENT_TIMEOUT", 0.1):
                loop = asyncio.get_event_loop()
                exec_task = loop.create_task(execution_service.execute_request(
                    request=ExecutionRequest(plan=slow_plan),
                    provider="gemini"
                ))
                
                await asyncio.sleep(0.05)
                exec_id = list(execution_service._active_tasks.keys())[0]
                
                assert execution_service._executions[exec_id].status == "RUNNING"
                
                await asyncio.sleep(0.1)
                
                execution_service.cleanup_stale_executions(timeout_seconds=3600.0)
                
                with pytest.raises(asyncio.CancelledError):
                    await exec_task
                    
                assert execution_service._executions[exec_id].status == "CANCELLED"
