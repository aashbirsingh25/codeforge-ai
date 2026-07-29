import pytest
import logging
import json
import asyncio
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi import status
from fastapi.testclient import TestClient

from app.main import app
from app.core.config import settings

client = TestClient(app, headers={"X-API-Key": settings.API_SECRET_KEY})

from app.agents.exceptions import (
    AgentExecutionError,
    AgentDependencyError,
    AgentToolError,
    AgentRetryExceededError,
    AgentTimeoutError,
    AgentMaxIterationsError,
    AgentMaxToolCallsError,
    AgentRecursionError,
    AgentInvalidToolError,
)
from app.agents.schemas import (
    ExecutionRequest,
    ExecutionResponse,
    ExecutionState,
    AgentAction,
    AgentObservation,
    AgentResult,
    ExecutionStep,
    ExecutionMetrics,
    Thought,
    Action,
    Observation,
    ReActStep,
    ReActTrace,
)
from app.agents.registry import (
    BaseAgent,
    PlannerAgent,
    ExecutorAgent,
    agent_registry,
)
from app.agents.executor import AgentExecutor, topological_sort
from app.agents.state import ExecutionStateManager
from app.agents.service import execution_service, AgentExecutionService
from app.planner.schemas import ExecutionPlan, Task, TaskStatus, TaskPriority, Complexity, PlanningResponse
from app.llm.schemas import ChatCompletionResponse
from app.llm.exceptions import LLMException
from app.tools.registry import registry as tool_registry
from app.tools.base import BaseTool
from pydantic import BaseModel



# --- 1. Agent Registry Tests ---

def test_agent_registry_initialization():
    agents = agent_registry.list_agents()
    assert "planneragent" in agents
    assert "executoragent" in agents

    planner = agent_registry.get_agent("PlannerAgent")
    assert isinstance(planner, PlannerAgent)
    assert planner.name == "PlannerAgent"
    assert "Decomposes goals" in planner.description

    executor = agent_registry.get_agent("ExecutorAgent")
    assert isinstance(executor, ExecutorAgent)
    assert executor.name == "ExecutorAgent"


def test_agent_registry_custom_registration():
    class DummyAgent(BaseAgent):
        @property
        def name(self) -> str:
            return "DummyAgent"
        
        @property
        def description(self) -> str:
            return "A dummy agent for testing registry"

        async def execute(self, task_id, context, *args, **kwargs):
            return AgentResult(success=True)

    agent_registry.register(DummyAgent)
    assert "dummyagent" in agent_registry.list_agents()
    dummy = agent_registry.get_agent("DummyAgent")
    assert isinstance(dummy, DummyAgent)

    with pytest.raises(AgentExecutionError) as excinfo:
        agent_registry.get_agent("NonExistentAgent")
    assert "is not registered" in str(excinfo.value)

    with pytest.raises(TypeError):
        agent_registry.register(object)  # Not inheriting from BaseAgent


# --- 2. Topological Sort Tests ---

def test_topological_sort_valid():
    tasks = [
        Task(id="task-1", title="T1", description="D1", priority=TaskPriority.LOW,
             estimated_complexity=Complexity.TRIVIAL, estimated_duration="1h", dependencies=[]),
        Task(id="task-2", title="T2", description="D2", priority=TaskPriority.LOW,
             estimated_complexity=Complexity.TRIVIAL, estimated_duration="1h", dependencies=["task-1"]),
        Task(id="task-3", title="T3", description="D3", priority=TaskPriority.LOW,
             estimated_complexity=Complexity.TRIVIAL, estimated_duration="1h", dependencies=["task-1", "task-2"]),
    ]
    sorted_tasks = topological_sort(tasks)
    assert [t.id for t in sorted_tasks] == ["task-1", "task-2", "task-3"]


def test_topological_sort_missing_dependency():
    tasks = [
        Task(id="task-1", title="T1", description="D1", priority=TaskPriority.LOW,
             estimated_complexity=Complexity.TRIVIAL, estimated_duration="1h", dependencies=["missing-task"]),
    ]
    with pytest.raises(AgentDependencyError) as excinfo:
        topological_sort(tasks)
    assert "depends on missing task" in str(excinfo.value)


def test_topological_sort_circular_dependency():
    tasks = [
        Task(id="task-1", title="T1", description="D1", priority=TaskPriority.LOW,
             estimated_complexity=Complexity.TRIVIAL, estimated_duration="1h", dependencies=["task-2"]),
        Task(id="task-2", title="T2", description="D2", priority=TaskPriority.LOW,
             estimated_complexity=Complexity.TRIVIAL, estimated_duration="1h", dependencies=["task-1"]),
    ]
    with pytest.raises(AgentDependencyError) as excinfo:
        topological_sort(tasks)
    assert "Circular dependency detected" in str(excinfo.value)


# --- 3. State Manager Tests ---

def test_state_manager_lifecycle():
    plan = ExecutionPlan(
        goal="test state manager",
        tasks=[
            Task(id="t1", title="T1", description="D1", priority=TaskPriority.LOW,
                 estimated_complexity=Complexity.TRIVIAL, estimated_duration="1h", dependencies=[]),
            Task(id="t2", title="T2", description="D2", priority=TaskPriority.LOW,
                 estimated_complexity=Complexity.TRIVIAL, estimated_duration="1h", dependencies=["t1"]),
        ]
    )
    mgr = ExecutionStateManager(plan)
    assert mgr.state.pending_tasks == ["t1", "t2"]
    assert mgr.state.current_task is None

    mgr.start_task("t1")
    assert mgr.state.current_task == "t1"
    assert mgr.state.pending_tasks == ["t2"]
    assert "task_start_t1" in mgr.state.timestamps

    # Record action & observation
    action = AgentAction(tool_name="read_file", tool_args={"path": "test.txt"}, description="reading file")
    observation = AgentObservation(content="file contents", success=True)
    mgr.record_action_and_observation("t1", action, observation)
    assert len(mgr.state.observations["t1"]) == 1
    assert mgr.state.observations["t1"][0].content == "file contents"

    mgr.complete_task("t1", "Completed task 1")
    assert "t1" in mgr.state.completed_tasks
    assert mgr.state.current_task is None
    assert "task_end_t1" in mgr.state.timestamps

    # Test retry count
    mgr.start_task("t2")
    count = mgr.increment_retry("t2")
    assert count == 1
    assert mgr.state.retry_count["t2"] == 1
    step = mgr.get_step("t2")
    assert step.retry_count == 1

    mgr.fail_task("t2", "execution failed")
    assert "t2" in mgr.state.failed_tasks
    assert "t2" not in mgr.state.completed_tasks


# --- 4. Executor Retry Logic Tests ---

@pytest.mark.asyncio
async def test_executor_retry_exceeded():
    plan = ExecutionPlan(
        goal="test retry exceed",
        tasks=[
            Task(id="t1", title="T1", description="D1", priority=TaskPriority.LOW,
                 estimated_complexity=Complexity.TRIVIAL, estimated_duration="1h", dependencies=[]),
        ]
    )
    # Mock ExecutorAgent to fail
    mock_agent = MagicMock()
    mock_agent.execute = AsyncMock(return_value=AgentResult(success=False, error="Simulated failure"))

    with patch("app.agents.registry.agent_registry.get_agent", return_value=mock_agent):
        executor = AgentExecutor(plan, max_retries=2)
        with pytest.raises(AgentRetryExceededError) as excinfo:
            await executor.execute()
        assert "failed after 2 retries" in str(excinfo.value)
        assert "t1" in executor.state_mgr.state.failed_tasks


# --- 5. Executor Failure Propagation Tests ---

@pytest.mark.asyncio
async def test_executor_dependency_failure_propagation():
    plan = ExecutionPlan(
        goal="test propagation",
        tasks=[
            Task(id="t1", title="T1", description="D1", priority=TaskPriority.LOW,
                 estimated_complexity=Complexity.TRIVIAL, estimated_duration="1h", dependencies=[]),
            Task(id="t2", title="T2", description="D2", priority=TaskPriority.LOW,
                 estimated_complexity=Complexity.TRIVIAL, estimated_duration="1h", dependencies=["t1"]),
        ]
    )
    
    # Mock t1 agent to fail, so retry is exceeded and t1 fails
    mock_agent = MagicMock()
    mock_agent.execute = AsyncMock(return_value=AgentResult(success=False, error="Simulated failure"))
    
    with patch("app.agents.registry.agent_registry.get_agent", return_value=mock_agent):
        executor = AgentExecutor(plan, max_retries=0)
        with pytest.raises(AgentRetryExceededError):
            await executor.execute()
        
        assert "t1" in executor.state_mgr.state.failed_tasks
        
        # Run again (or resume) or check sorting
        # Let's verify that a run with pre-failed dependency raises AgentDependencyError immediately
        # We manually seed the failed state for t1 to check propagation
        executor2 = AgentExecutor(plan)
        executor2.state_mgr.state.failed_tasks.append("t1")
        with pytest.raises(AgentDependencyError) as excinfo:
            await executor2.execute()
        assert "cannot be executed due to failed dependencies" in str(excinfo.value)
        assert "t2" in executor2.state_mgr.state.failed_tasks


# --- 6. Tool Invocation & ReAct Loop Tests ---

class DummyToolInput(BaseModel):
    name: str

class DummyToolOutput(BaseModel):
    message: str

class DummyTestTool(BaseTool):
    tool_name = "dummy_test_tool"
    description = "A dummy test tool for agents verification"
    category = "test"
    input_schema = DummyToolInput
    output_schema = DummyToolOutput

    def execute(self, name: str) -> DummyToolOutput:
        return DummyToolOutput(message=f"Hello, {name}!")

# Register dummy tool
tool_registry.register(DummyTestTool())


@pytest.mark.asyncio
async def test_executor_agent_react_loop():
    task = Task(id="t1", title="Use Dummy Tool", description="Call dummy tool", priority=TaskPriority.LOW,
                estimated_complexity=Complexity.TRIVIAL, estimated_duration="1h")
    
    context = {"task": task, "provider": "gemini"}

    # Mock the LLM provider responses: first call tool, then finish
    mock_provider = MagicMock()
    
    # 1st LLM call returns JSON for calling the dummy tool
    call_tool_json = json.dumps({
        "action": "call_tool",
        "tool_name": "dummy_test_tool",
        "tool_args": {"name": "World"},
        "thought": "I should call the dummy test tool"
    })
    # 2nd LLM call returns JSON finishing the task
    finish_json = json.dumps({
        "action": "finish",
        "success": True,
        "output": "Successfully greeted the world",
        "thought": "Greeting completed"
    })
    
    mock_provider.generate = AsyncMock()
    mock_provider.generate.side_effect = [
        ChatCompletionResponse(content=call_tool_json, model="gemini-3.5-flash"),
        ChatCompletionResponse(content=finish_json, model="gemini-3.5-flash")
    ]

    with patch("app.llm.factory.ProviderFactory.get_provider", return_value=mock_provider):
        agent = ExecutorAgent()
        # Track actions via a callback
        actions_logged = []
        def recorder(action, obs):
            actions_logged.append((action, obs))
        
        context["action_recorder"] = recorder
        result = await agent.execute("t1", context)

        assert result.success is True
        assert result.output == "Successfully greeted the world"
        assert len(actions_logged) == 1
        assert actions_logged[0][0].tool_name == "dummy_test_tool"
        assert actions_logged[0][0].tool_args == {"name": "World"}
        assert "Hello, World!" in actions_logged[0][1].content
        assert actions_logged[0][1].success is True


# --- 7. Planner Integration Tests ---

@pytest.mark.asyncio
async def test_planner_integration_generate_and_execute():
    # Setup mock plan
    mock_plan = ExecutionPlan(
        goal="integrate planner",
        tasks=[
            Task(id="task-1", title="T1", description="D1", priority=TaskPriority.LOW,
                 estimated_complexity=Complexity.TRIVIAL, estimated_duration="1h")
        ]
    )
    
    # Mock PlannerService to return a PlanningResponse
    mock_planning_response = PlanningResponse(
        plan=mock_plan,
        strategy="sequential",
        provider="gemini",
        duration_seconds=0.1
    )
    
    mock_planner_service = MagicMock()
    mock_planner_service.generate_plan = AsyncMock(return_value=mock_planning_response)
    
    # Mock ExecutorAgent execution
    mock_executor_agent = MagicMock()
    mock_executor_agent.execute = AsyncMock(return_value=AgentResult(success=True, output="Task 1 complete"))

    with patch("app.agents.service.PlannerService", return_value=mock_planner_service):
        with patch("app.agents.registry.agent_registry.get_agent", return_value=mock_executor_agent):
            # Instantiate clean execution service
            service = AgentExecutionService()
            req = ExecutionRequest(goal="integrate planner")
            
            response = await service.execute_request(req)
            assert response.status == "COMPLETED"
            assert response.plan.goal == "integrate planner"
            assert len(response.state.completed_tasks) == 1
            assert "task-1" in response.state.completed_tasks


# --- 8. API Endpoints Tests ---

def test_api_execute_with_plan_success():
    # Setup test plan
    plan = ExecutionPlan(
        goal="build app",
        tasks=[
            Task(id="t1", title="T1", description="D1", priority=TaskPriority.LOW,
                 estimated_complexity=Complexity.TRIVIAL, estimated_duration="1h")
        ]
    )
    
    # Mock ExecutorAgent execution
    mock_executor_agent = MagicMock()
    mock_executor_agent.execute = AsyncMock(return_value=AgentResult(success=True, output="T1 complete"))

    with patch("app.agents.registry.agent_registry.get_agent", return_value=mock_executor_agent):
        # Call API
        payload = {"plan": plan.model_dump()}
        response = client.post("/api/v1/agents/execute", json=payload)
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["status"] == "COMPLETED"
        assert data["plan"]["goal"] == "build app"
        assert "t1" in data["state"]["completed_tasks"]


def test_api_execute_plan_direct_route():
    plan = ExecutionPlan(
        goal="direct route goal",
        tasks=[
            Task(id="t1", title="T1", description="D1", priority=TaskPriority.LOW,
                 estimated_complexity=Complexity.TRIVIAL, estimated_duration="1h")
        ]
    )
    
    mock_executor_agent = MagicMock()
    mock_executor_agent.execute = AsyncMock(return_value=AgentResult(success=True, output="T1 complete"))

    with patch("app.agents.registry.agent_registry.get_agent", return_value=mock_executor_agent):
        response = client.post("/api/v1/agents/execute/plan", json=plan.model_dump())
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["status"] == "COMPLETED"


def test_api_get_status_and_history():
    # First, let's execute something to populate history & status
    plan = ExecutionPlan(
        goal="status history goal",
        tasks=[
            Task(id="t1", title="T1", description="D1", priority=TaskPriority.LOW,
                 estimated_complexity=Complexity.TRIVIAL, estimated_duration="1h")
        ]
    )
    
    mock_executor_agent = MagicMock()
    mock_executor_agent.execute = AsyncMock(return_value=AgentResult(success=True, output="T1 complete"))

    with patch("app.agents.registry.agent_registry.get_agent", return_value=mock_executor_agent):
        response = client.post("/api/v1/agents/execute/plan", json=plan.model_dump())
        assert response.status_code == status.HTTP_201_CREATED
        execution_id = response.json()["execution_id"]

        # Test status endpoint with ID
        status_resp = client.get(f"/api/v1/agents/status?execution_id={execution_id}")
        assert status_resp.status_code == status.HTTP_200_OK
        assert status_resp.json()["execution_id"] == execution_id

        # Test status endpoint without ID (should return latest)
        status_latest = client.get("/api/v1/agents/status")
        assert status_latest.status_code == status.HTTP_200_OK
        assert status_latest.json()["execution_id"] == execution_id

        # Test history endpoint
        history_resp = client.get("/api/v1/agents/history")
        assert history_resp.status_code == status.HTTP_200_OK
        history_data = history_resp.json()
        assert len(history_data) >= 1
        assert any(item["execution_id"] == execution_id for item in history_data)


def test_api_status_not_found():
    response = client.get("/api/v1/agents/status?execution_id=non-existent-uuid")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "No execution found" in response.json()["error"]["message"]


# --- 9. Additional Coverage Tests ---

@pytest.mark.asyncio
async def test_planner_agent_execute():
    planner = PlannerAgent()
    # Missing goal in context
    res = await planner.execute("t1", {})
    assert res.success is False
    assert "No goal provided" in res.error

    # Valid goal
    mock_plan = ExecutionPlan(goal="test goal", tasks=[])
    mock_resp = PlanningResponse(plan=mock_plan, strategy="sequential", provider="gemini", duration_seconds=0.1)
    
    mock_planner_service = MagicMock()
    mock_planner_service.generate_plan = AsyncMock(return_value=mock_resp)
    
    with patch("app.planner.service.PlannerService", return_value=mock_planner_service):
        res2 = await planner.execute("t1", {"goal": "test goal"})
        assert res2.success is True
        assert "test goal" in res2.output

    # Error case in PlannerService
    mock_planner_service.generate_plan = AsyncMock(side_effect=ValueError("planner failure"))
    with patch("app.planner.service.PlannerService", return_value=mock_planner_service):
        res3 = await planner.execute("t1", {"goal": "test goal"})
        assert res3.success is False
        assert "planner failure" in res3.error


@pytest.mark.asyncio
async def test_executor_agent_react_failures():
    agent = ExecutorAgent()
    task = Task(id="t1", title="T1", description="D1", priority=TaskPriority.LOW,
                estimated_complexity=Complexity.TRIVIAL, estimated_duration="1h")

    # 1. Missing task in context
    res1 = await agent.execute("t1", {})
    assert res1.success is False
    assert "No task provided" in res1.error

    # 2. Provider factory error
    res2 = await agent.execute("t1", {"task": task, "provider": "invalid_provider"})
    assert res2.success is False
    assert "Failed to load LLM provider" in res2.error

    # 3. LLM generation error
    mock_provider = MagicMock()
    mock_provider.generate = AsyncMock(side_effect=RuntimeError("connection dropped"))
    with patch("app.llm.factory.ProviderFactory.get_provider", return_value=mock_provider):
        res3 = await agent.execute("t1", {"task": task})
        assert res3.success is False
        assert "LLM generation failed" in res3.error

    # 4. JSON parsing / malformed response from LLM
    mock_provider.generate = AsyncMock(return_value=ChatCompletionResponse(content="not a json", model="gemini"))
    with patch("app.llm.factory.ProviderFactory.get_provider", return_value=mock_provider):
        # Executor agent should run until it exceeds maximum steps (5) due to repeatedly failing to parse JSON
        res4 = await agent.execute("t1", {"task": task})
        assert res4.success is False
        assert "exceeded maximum ReAct steps" in res4.error

    # 5. Invalid action type
    bad_action_json = json.dumps({"action": "unknown_action", "thought": "doing something strange"})
    mock_provider.generate = AsyncMock(return_value=ChatCompletionResponse(content=bad_action_json, model="gemini"))
    with patch("app.llm.factory.ProviderFactory.get_provider", return_value=mock_provider):
        res5 = await agent.execute("t1", {"task": task})
        assert res5.success is False
        assert "exceeded maximum ReAct steps" in res5.error

    # 6. Tool not found
    bad_tool_json = json.dumps({"action": "call_tool", "tool_name": "non_existent_tool", "thought": "calling a fake tool"})
    finish_json = json.dumps({"action": "finish", "success": False, "output": "Failed tool"})
    mock_provider.generate = AsyncMock()
    mock_provider.generate.side_effect = [
        ChatCompletionResponse(content=bad_tool_json, model="gemini"),
        ChatCompletionResponse(content=finish_json, model="gemini")
    ]
    with patch("app.llm.factory.ProviderFactory.get_provider", return_value=mock_provider):
        actions = []
        def act_recorder(action, obs):
            actions.append((action, obs))
        res6 = await agent.execute("t1", {"task": task, "action_recorder": act_recorder})
        assert len(actions) == 1
        assert actions[0][1].success is False
        assert "not found in registry" in actions[0][1].error


@pytest.mark.asyncio
async def test_executor_completed_skipping():
    plan = ExecutionPlan(
        goal="test skip completed",
        tasks=[
            Task(id="t1", title="T1", description="D1", priority=TaskPriority.LOW,
                 estimated_complexity=Complexity.TRIVIAL, estimated_duration="1h")
        ]
    )
    executor = AgentExecutor(plan)
    # Manually seed task-1 as completed
    executor.state_mgr.state.completed_tasks.append("t1")
    response = await executor.execute()
    # It should skip execution and succeed
    assert response.status == "COMPLETED"
    assert "t1" in response.state.completed_tasks


@pytest.mark.asyncio
async def test_executor_cycle_exception():
    plan = ExecutionPlan(
        goal="cycle plan",
        tasks=[
            Task(id="t1", title="T1", description="D1", priority=TaskPriority.LOW,
                 estimated_complexity=Complexity.TRIVIAL, estimated_duration="1h", dependencies=["t2"]),
            Task(id="t2", title="T2", description="D2", priority=TaskPriority.LOW,
                 estimated_complexity=Complexity.TRIVIAL, estimated_duration="1h", dependencies=["t1"])
        ]
    )
    executor = AgentExecutor(plan)
    with pytest.raises(AgentDependencyError) as excinfo:
        await executor.execute()
    assert "Circular dependency detected" in str(excinfo.value)


@pytest.mark.asyncio
async def test_service_invalid_request():
    service = AgentExecutionService()
    # Missing both goal and plan
    with pytest.raises(ValueError) as excinfo:
        await service.execute_request(ExecutionRequest(goal=None, plan=None))
    assert "Either 'goal' or 'plan' must be provided" in str(excinfo.value)


@pytest.mark.asyncio
async def test_service_execution_exception_updates_status():
    service = AgentExecutionService()
    plan = ExecutionPlan(
        goal="failing service run",
        tasks=[
            Task(id="t1", title="T1", description="D1", priority=TaskPriority.LOW,
                 estimated_complexity=Complexity.TRIVIAL, estimated_duration="1h")
        ]
    )
    
    # Mock ExecutorAgent to raise a raw Exception
    mock_agent = MagicMock()
    mock_agent.execute = AsyncMock(side_effect=RuntimeError("unexpected runtime crash"))

    with patch("app.agents.registry.agent_registry.get_agent", return_value=mock_agent):
        with pytest.raises(AgentRetryExceededError) as excinfo:
            await service.execute_request(ExecutionRequest(plan=plan))
        assert "unexpected runtime crash" in str(excinfo.value)
        
        # Verify status is recorded as FAILED in history
        latest = service.get_status()
        assert latest.status == "FAILED"


def test_state_manager_edge_cases():
    plan = ExecutionPlan(
        goal="edge cases",
        tasks=[
            Task(id="t1", title="T1", description="D1", priority=TaskPriority.LOW,
                 estimated_complexity=Complexity.TRIVIAL, estimated_duration="1h")
        ]
    )
    mgr = ExecutionStateManager(plan)
    # Start task when not in pending_tasks (e.g. starting again)
    mgr.start_task("t1")
    mgr.start_task("t1") # should still work safely
    assert mgr.state.current_task == "t1"
    
    # complete task multiple times
    mgr.complete_task("t1")
    mgr.complete_task("t1")
    assert "t1" in mgr.state.completed_tasks

    # lookup nonexistent step
    assert mgr.get_step("non_existent") is None


# --- 9. ReAct Engine Upgrade Comprehensive Tests ---

@pytest.mark.asyncio
async def test_react_successful_reasoning():
    # Test successful reasoning and action steps trace recording
    task = Task(id="t1", title="Task 1", description="Success test", priority=TaskPriority.LOW,
                estimated_complexity=Complexity.TRIVIAL, estimated_duration="1h")
    
    agent = ExecutorAgent()
    
    call_tool_json = json.dumps({
        "action": "call_tool",
        "tool_name": "dummy_test_tool",
        "tool_args": {"name": "Test"},
        "thought": "I need to call the dummy tool to greet"
    })
    finish_json = json.dumps({
        "action": "finish",
        "success": True,
        "output": "Greeted successfully",
        "thought": "Greeting done"
    })
    
    mock_provider = MagicMock()
    mock_provider.generate = AsyncMock(side_effect=[
        ChatCompletionResponse(content=call_tool_json, model="gemini"),
        ChatCompletionResponse(content=finish_json, model="gemini")
    ])
    
    steps = []
    def step_cb(step):
        steps.append(step)
        
    context = {
        "task": task,
        "provider": "gemini",
        "react_trace_callback": step_cb
    }
    
    with patch("app.llm.factory.ProviderFactory.get_provider", return_value=mock_provider):
        res = await agent.execute("t1", context)
        
        assert res.success is True
        assert res.output == "Greeted successfully"
        assert len(steps) == 2
        # First step checks
        assert steps[0].thought.reasoning == "I need to call the dummy tool to greet"
        assert steps[0].action.tool_name == "dummy_test_tool"
        assert steps[0].action.tool_args == {"name": "Test"}
        assert steps[0].observation.success is True
        assert "Hello, Test!" in steps[0].observation.content
        assert steps[0].duration_seconds >= 0
        # Second step checks
        assert steps[1].thought.reasoning == "Greeting done"
        assert steps[1].action is None
        assert steps[1].observation is None


@pytest.mark.asyncio
async def test_react_invalid_tool():
    # Test invalid tool name results in a recorded failed observation
    task = Task(id="t1", title="Task 1", description="Invalid tool", priority=TaskPriority.LOW,
                estimated_complexity=Complexity.TRIVIAL, estimated_duration="1h")
    
    agent = ExecutorAgent()
    
    bad_tool_json = json.dumps({
        "action": "call_tool",
        "tool_name": "fake_nonexistent_tool",
        "tool_args": {},
        "thought": "Calling a nonexistent tool"
    })
    finish_json = json.dumps({
        "action": "finish",
        "success": False,
        "output": "Tool execution failed",
        "thought": "I failed"
    })
    
    mock_provider = MagicMock()
    mock_provider.generate = AsyncMock(side_effect=[
        ChatCompletionResponse(content=bad_tool_json, model="gemini"),
        ChatCompletionResponse(content=finish_json, model="gemini")
    ])
    
    steps = []
    def step_cb(step):
        steps.append(step)
        
    context = {
        "task": task,
        "provider": "gemini",
        "react_trace_callback": step_cb
    }
    
    with patch("app.llm.factory.ProviderFactory.get_provider", return_value=mock_provider):
        res = await agent.execute("t1", context)
        assert res.success is False
        assert len(steps) == 2
        assert steps[0].action.tool_name == "fake_nonexistent_tool"
        assert steps[0].observation.success is False
        assert "not found in registry" in steps[0].observation.error


@pytest.mark.asyncio
async def test_react_repeated_failures_recursion_protection():
    # Test consecutive identical tool calls triggers recursion protection
    task = Task(id="t1", title="Task 1", description="Recursion test", priority=TaskPriority.LOW,
                estimated_complexity=Complexity.TRIVIAL, estimated_duration="1h")
    
    agent = ExecutorAgent()
    
    identical_call_json = json.dumps({
        "action": "call_tool",
        "tool_name": "dummy_test_tool",
        "tool_args": {"name": "Same"},
        "thought": "Calling same tool consecutively"
    })
    
    mock_provider = MagicMock()
    mock_provider.generate = AsyncMock(return_value=ChatCompletionResponse(content=identical_call_json, model="gemini"))
    
    # Let's set recursion limit to 2
    context = {
        "task": task,
        "provider": "gemini",
        "recursion_limit": 2,
        "propagate_exceptions": True
    }
    
    with patch("app.llm.factory.ProviderFactory.get_provider", return_value=mock_provider):
        with pytest.raises(AgentRecursionError) as excinfo:
            await agent.execute("t1", context)
        assert "Recursion protection triggered" in str(excinfo.value)
        assert "dummy_test_tool" in str(excinfo.value)


@pytest.mark.asyncio
async def test_react_timeout():
    task = Task(id="t1", title="Task 1", description="Timeout test", priority=TaskPriority.LOW,
                estimated_complexity=Complexity.TRIVIAL, estimated_duration="1h")
    
    agent = ExecutorAgent()
    
    async def delayed_generate(*args, **kwargs):
        await asyncio.sleep(0.05)
        return ChatCompletionResponse(
            content=json.dumps({"action": "finish", "success": True, "output": "ok"}),
            model="gemini"
        )
        
    mock_provider = MagicMock()
    mock_provider.generate = AsyncMock(side_effect=delayed_generate)
    
    context = {
        "task": task,
        "provider": "gemini",
        "timeout": 0.01,  # extremely short timeout
        "propagate_exceptions": True
    }
    
    with patch("app.llm.factory.ProviderFactory.get_provider", return_value=mock_provider):
        with pytest.raises(AgentTimeoutError) as excinfo:
            await agent.execute("t1", context)
        assert "timed out after" in str(excinfo.value)


@pytest.mark.asyncio
async def test_react_max_iteration_exceeded():
    task = Task(id="t1", title="Task 1", description="Max iteration test", priority=TaskPriority.LOW,
                estimated_complexity=Complexity.TRIVIAL, estimated_duration="1h")
    
    agent = ExecutorAgent()
    
    call_tool_json = json.dumps({
        "action": "call_tool",
        "tool_name": "dummy_test_tool",
        "tool_args": {"name": "Test"},
        "thought": "Let's call tool"
    })
    
    mock_provider = MagicMock()
    mock_provider.generate = AsyncMock(return_value=ChatCompletionResponse(content=call_tool_json, model="gemini"))
    
    context = {
        "task": task,
        "provider": "gemini",
        "max_iterations": 2,
        "propagate_exceptions": True
    }
    
    with patch("app.llm.factory.ProviderFactory.get_provider", return_value=mock_provider):
        with pytest.raises(AgentMaxIterationsError) as excinfo:
            await agent.execute("t1", context)
        assert "exceeded maximum ReAct steps" in str(excinfo.value)


@pytest.mark.asyncio
async def test_react_tool_execution_error():
    task = Task(id="t1", title="Task 1", description="Tool error test", priority=TaskPriority.LOW,
                estimated_complexity=Complexity.TRIVIAL, estimated_duration="1h")
    
    agent = ExecutorAgent()
    
    # We will invoke dummy_test_tool without passing required argument 'name' to trigger schema validation error
    bad_args_json = json.dumps({
        "action": "call_tool",
        "tool_name": "dummy_test_tool",
        "tool_args": {}, # missing name
        "thought": "I'm calling the tool with bad args"
    })
    finish_json = json.dumps({
        "action": "finish",
        "success": False,
        "output": "Ended due to tool errors",
        "thought": "Too many validation issues"
    })
    
    mock_provider = MagicMock()
    mock_provider.generate = AsyncMock(side_effect=[
        ChatCompletionResponse(content=bad_args_json, model="gemini"),
        ChatCompletionResponse(content=finish_json, model="gemini")
    ])
    
    steps = []
    def step_cb(step):
        steps.append(step)
        
    context = {
        "task": task,
        "provider": "gemini",
        "react_trace_callback": step_cb
    }
    
    with patch("app.llm.factory.ProviderFactory.get_provider", return_value=mock_provider):
        res = await agent.execute("t1", context)
        assert res.success is False
        assert len(steps) == 2
        assert steps[0].observation.success is False
        assert "Validation Error" in steps[0].observation.error or "Input validation failed" in steps[0].observation.error


@pytest.mark.asyncio
async def test_react_llm_malformed_response():
    task = Task(id="t1", title="Task 1", description="Malformed JSON test", priority=TaskPriority.LOW,
                estimated_complexity=Complexity.TRIVIAL, estimated_duration="1h")
    
    agent = ExecutorAgent()
    
    malformed_response = "Here is some raw text that is not JSON at all."
    finish_json = json.dumps({
        "action": "finish",
        "success": True,
        "output": "Recovered and finished",
        "thought": "JSON format fixed"
    })
    
    mock_provider = MagicMock()
    mock_provider.generate = AsyncMock(side_effect=[
        ChatCompletionResponse(content=malformed_response, model="gemini"),
        ChatCompletionResponse(content=finish_json, model="gemini")
    ])
    
    steps = []
    def step_cb(step):
        steps.append(step)
        
    context = {
        "task": task,
        "provider": "gemini",
        "react_trace_callback": step_cb
    }
    
    with patch("app.llm.factory.ProviderFactory.get_provider", return_value=mock_provider):
        res = await agent.execute("t1", context)
        assert res.success is True
        assert len(steps) == 2
        # First step should be marked as malformed
        assert steps[0].thought.reasoning == f"Malformed LLM response: {malformed_response}"
        assert steps[0].action is None
        assert steps[0].observation.success is False
        assert "valid JSON" in steps[0].observation.error
        
        # Second step succeeds
        assert steps[1].thought.reasoning == "JSON format fixed"


@pytest.mark.asyncio
async def test_react_successful_completion_api_trace():
    # Setup test plan
    plan = ExecutionPlan(
        goal="testing react trace endpoint",
        tasks=[
            Task(id="task-1", title="T1", description="D1", priority=TaskPriority.LOW,
                 estimated_complexity=Complexity.TRIVIAL, estimated_duration="1h")
        ]
    )
    
    call_tool_json = json.dumps({
        "action": "call_tool",
        "tool_name": "dummy_test_tool",
        "tool_args": {"name": "API"},
        "thought": "Call dummy tool"
    })
    finish_json = json.dumps({
        "action": "finish",
        "success": True,
        "output": "Completed plan",
        "thought": "Done"
    })
    
    mock_provider = MagicMock()
    mock_provider.generate = AsyncMock(side_effect=[
        ChatCompletionResponse(content=call_tool_json, model="gemini"),
        ChatCompletionResponse(content=finish_json, model="gemini")
    ])
    
    with patch("app.llm.factory.ProviderFactory.get_provider", return_value=mock_provider):
        # Trigger execute via service
        req = ExecutionRequest(plan=plan)
        response = await execution_service.execute_request(req)
        
        execution_id = response.execution_id
        assert response.status == "COMPLETED"
        assert response.react_trace is not None
        assert len(response.react_trace.steps) == 2
        
        # Test endpoint
        api_res = client.get(f"/api/v1/agents/{execution_id}/trace")
        assert api_res.status_code == status.HTTP_200_OK
        data = api_res.json()
        assert data["execution_id"] == execution_id
        assert len(data["steps"]) == 2
        assert data["steps"][0]["thought"]["reasoning"] == "Call dummy tool"
        assert data["steps"][1]["thought"]["reasoning"] == "Done"
        
        # Test nonexistent execution trace
        nonexistent_res = client.get("/api/v1/agents/some-nonexistent-uuid/trace")
        assert nonexistent_res.status_code == status.HTTP_404_NOT_FOUND


def test_executor_agent_properties():
    agent = ExecutorAgent()
    assert agent.description == "Executes tasks by dynamically invoking workspace tools."


@pytest.mark.asyncio
async def test_react_openai_provider_model_resolution():
    task = Task(id="t1", title="T1", description="D1", priority=TaskPriority.LOW,
                estimated_complexity=Complexity.TRIVIAL, estimated_duration="1h")
    agent = ExecutorAgent()
    mock_provider = MagicMock()
    mock_provider.generate = AsyncMock(return_value=ChatCompletionResponse(content=json.dumps({"action": "finish", "success": True, "output": "ok"}), model="gpt-4o"))
    
    context = {"task": task, "provider": "openai"}
    with patch("app.llm.factory.ProviderFactory.get_provider", return_value=mock_provider):
        res = await agent.execute("t1", context)
        assert res.success is True


@pytest.mark.asyncio
async def test_react_max_tool_calls_exceeded():
    task = Task(id="t1", title="Task 1", description="Max tools test", priority=TaskPriority.LOW,
                estimated_complexity=Complexity.TRIVIAL, estimated_duration="1h")
    agent = ExecutorAgent()
    call_tool_json = json.dumps({
        "action": "call_tool",
        "tool_name": "dummy_test_tool",
        "tool_args": {"name": "Test"},
        "thought": "Let's call tool"
    })
    mock_provider = MagicMock()
    mock_provider.generate = AsyncMock(return_value=ChatCompletionResponse(content=call_tool_json, model="gemini"))
    
    context = {
        "task": task,
        "provider": "gemini",
        "max_tool_calls": 1,
        "propagate_exceptions": True
    }
    with patch("app.llm.factory.ProviderFactory.get_provider", return_value=mock_provider):
        with pytest.raises(AgentMaxToolCallsError) as excinfo:
            await agent.execute("t1", context)
        assert "exceeded maximum tool calls" in str(excinfo.value)


@pytest.mark.asyncio
async def test_react_markdown_json_parsing():
    task = Task(id="t1", title="Task 1", description="Markdown JSON test", priority=TaskPriority.LOW,
                estimated_complexity=Complexity.TRIVIAL, estimated_duration="1h")
    agent = ExecutorAgent()
    markdown_json = "```json\n" + json.dumps({
        "action": "finish",
        "success": True,
        "output": "Parsed markdown JSON block successfully"
    }) + "\n```"
    mock_provider = MagicMock()
    mock_provider.generate = AsyncMock(return_value=ChatCompletionResponse(content=markdown_json, model="gemini"))
    
    context = {"task": task, "provider": "gemini"}
    with patch("app.llm.factory.ProviderFactory.get_provider", return_value=mock_provider):
        res = await agent.execute("t1", context)
        assert res.success is True
        assert res.output == "Parsed markdown JSON block successfully"


@pytest.mark.asyncio
async def test_react_llm_exception_propagation():
    task = Task(id="t1", title="T1", description="D1", priority=TaskPriority.LOW,
                estimated_complexity=Complexity.TRIVIAL, estimated_duration="1h")
    agent = ExecutorAgent()
    mock_provider = MagicMock()
    mock_provider.generate = AsyncMock(side_effect=LLMException("LLM quota exceeded"))
    
    context = {"task": task, "provider": "gemini", "propagate_exceptions": True}
    with patch("app.llm.factory.ProviderFactory.get_provider", return_value=mock_provider):
        with pytest.raises(LLMException):
            await agent.execute("t1", context)


def test_exceptions_coverage():
    err1 = AgentToolError("tool error")
    assert err1.status_code == 422
    err2 = AgentInvalidToolError("invalid tool")
    assert err2.status_code == 400



