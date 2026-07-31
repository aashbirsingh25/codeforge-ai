import pytest
import logging
from typing import AsyncGenerator
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi.testclient import TestClient

from app.main import app
from tests.conftest import TEST_AUTH_HEADERS

client = TestClient(app, headers=TEST_AUTH_HEADERS)


from app.planner.exceptions import (
    PlanningParseError,
    PlanningValidationError,
    PlanningStrategyError,
    PlanningError
)
from app.planner.parser import PlanParser
from app.planner.validator import PlanValidator
from app.planner.strategy import SequentialPlanningStrategy, HierarchicalPlanningStrategy
from app.planner.schemas import (
    ExecutionPlan,
    Task,
    SubTask,
    TaskStatus,
    TaskPriority,
    Complexity,
    PlanningRequest
)
from app.planner.planner import Planner
from app.planner.service import PlannerService
from app.llm.schemas import ChatCompletionResponse



# --- 1. Parser Tests ---

def test_parser_valid_json():
    parser = PlanParser()
    raw = '{"goal": "test goal", "tasks": []}'
    parsed = parser.parse(raw)
    assert parsed["goal"] == "test goal"
    assert parsed["tasks"] == []


def test_parser_markdown_wrap_and_commas():
    parser = PlanParser()
    raw = """
    ```json
    {
        "goal": "repaired goal",
        "tasks": [
            {
                "id": "t1",
                "title": "t1 title",
            },
        ]
    }
    ```
    """
    parsed = parser.parse(raw)
    assert parsed["goal"] == "repaired goal"
    assert len(parsed["tasks"]) == 1
    assert parsed["tasks"][0]["id"] == "t1"


def test_parser_single_quotes():
    parser = PlanParser()
    raw = "{'goal': 'single quote goal', 'tasks': []}"
    parsed = parser.parse(raw)
    assert parsed["goal"] == "single quote goal"


def test_parser_invalid_json():
    parser = PlanParser()
    with pytest.raises(PlanningParseError) as excinfo:
        parser.parse("not json at all")
    assert "No valid JSON object boundaries" in str(excinfo.value)

    with pytest.raises(PlanningParseError) as excinfo:
        parser.parse("{'goal': unmatched_quotes}")
    assert "Failed to parse LLM response" in str(excinfo.value)


def test_parser_empty_text():
    parser = PlanParser()
    with pytest.raises(PlanningParseError):
        parser.parse("   ")


# --- 2. Validator Tests ---

def test_validator_valid_plan():
    validator = PlanValidator()
    plan = ExecutionPlan(
        goal="build api",
        tasks=[
            Task(
                id="task-1",
                title="design",
                description="desc",
                priority=TaskPriority.HIGH,
                estimated_complexity=Complexity.EASY,
                estimated_duration="1h",
                dependencies=[],
                status=TaskStatus.PENDING,
                subtasks=[]
            )
        ]
    )
    # Should not raise any error
    validator.validate(plan)


def test_validator_empty_goal():
    validator = PlanValidator()
    plan = ExecutionPlan(goal="  ", tasks=[])
    with pytest.raises(PlanningValidationError) as excinfo:
        validator.validate(plan)
    assert "goal description cannot be empty" in str(excinfo.value)


def test_validator_empty_tasks():
    validator = PlanValidator()
    plan = ExecutionPlan(goal="build app", tasks=[])
    with pytest.raises(PlanningValidationError) as excinfo:
        validator.validate(plan)
    assert "must contain at least one task" in str(excinfo.value)


def test_validator_invalid_task_fields():
    validator = PlanValidator()
    
    # Empty ID
    plan = ExecutionPlan(
        goal="build app",
        tasks=[
            Task(id=" ", title="title", description="desc", priority=TaskPriority.LOW,
                 estimated_complexity=Complexity.TRIVIAL, estimated_duration="1h", status=TaskStatus.PENDING)
        ]
    )
    with pytest.raises(PlanningValidationError) as excinfo:
        validator.validate(plan)
    assert "Task ID cannot be empty" in str(excinfo.value)

    # Empty Title
    plan = ExecutionPlan(
        goal="build app",
        tasks=[
            Task(id="t1", title=" ", description="desc", priority=TaskPriority.LOW,
                 estimated_complexity=Complexity.TRIVIAL, estimated_duration="1h", status=TaskStatus.PENDING)
        ]
    )
    with pytest.raises(PlanningValidationError) as excinfo:
        validator.validate(plan)
    assert "must have a non-empty title" in str(excinfo.value)


def test_validator_duplicate_task_ids():
    validator = PlanValidator()
    plan = ExecutionPlan(
        goal="build app",
        tasks=[
            Task(id="t1", title="title 1", description="desc", priority=TaskPriority.LOW,
                 estimated_complexity=Complexity.TRIVIAL, estimated_duration="1h", status=TaskStatus.PENDING),
            Task(id="t1", title="title 2", description="desc", priority=TaskPriority.LOW,
                 estimated_complexity=Complexity.TRIVIAL, estimated_duration="1h", status=TaskStatus.PENDING)
        ]
    )
    with pytest.raises(PlanningValidationError) as excinfo:
        validator.validate(plan)
    assert "Duplicate Task ID detected" in str(excinfo.value)


def test_validator_duplicate_subtask_ids():
    validator = PlanValidator()
    plan = ExecutionPlan(
        goal="build app",
        tasks=[
            Task(
                id="t1", title="title", description="desc", priority=TaskPriority.LOW,
                estimated_complexity=Complexity.TRIVIAL, estimated_duration="1h", status=TaskStatus.PENDING,
                subtasks=[
                    SubTask(id="sub-1", title="sub title 1", description="desc"),
                    SubTask(id="sub-1", title="sub title 2", description="desc")
                ]
            )
        ]
    )
    with pytest.raises(PlanningValidationError) as excinfo:
        validator.validate(plan)
    assert "Duplicate subtask ID 'sub-1'" in str(excinfo.value)


def test_validator_unknown_dependency():
    validator = PlanValidator()
    plan = ExecutionPlan(
        goal="build app",
        tasks=[
            Task(id="t1", title="title", description="desc", priority=TaskPriority.LOW,
                 estimated_complexity=Complexity.TRIVIAL, estimated_duration="1h", status=TaskStatus.PENDING,
                 dependencies=["t2"])
        ]
    )
    with pytest.raises(PlanningValidationError) as excinfo:
        validator.validate(plan)
    assert "references an unknown dependency" in str(excinfo.value)


def test_validator_self_dependency():
    validator = PlanValidator()
    plan = ExecutionPlan(
        goal="build app",
        tasks=[
            Task(id="t1", title="title", description="desc", priority=TaskPriority.LOW,
                 estimated_complexity=Complexity.TRIVIAL, estimated_duration="1h", status=TaskStatus.PENDING,
                 dependencies=["t1"])
        ]
    )
    with pytest.raises(PlanningValidationError) as excinfo:
        validator.validate(plan)
    assert "cannot list itself as a dependency" in str(excinfo.value)


def test_validator_circular_dependency():
    validator = PlanValidator()
    plan = ExecutionPlan(
        goal="build app",
        tasks=[
            Task(id="t1", title="title 1", description="desc", priority=TaskPriority.LOW,
                 estimated_complexity=Complexity.TRIVIAL, estimated_duration="1h", status=TaskStatus.PENDING,
                 dependencies=["t2"]),
            Task(id="t2", title="title 2", description="desc", priority=TaskPriority.LOW,
                 estimated_complexity=Complexity.TRIVIAL, estimated_duration="1h", status=TaskStatus.PENDING,
                 dependencies=["t1"])
        ]
    )
    with pytest.raises(PlanningValidationError) as excinfo:
        validator.validate(plan)
    assert "Circular dependencies detected" in str(excinfo.value)


# --- 3. Strategy Pattern Tests ---

def test_strategies_system_prompts():
    seq = SequentialPlanningStrategy()
    hier = HierarchicalPlanningStrategy()

    assert seq.name == "sequential"
    assert "SEQUENTIAL STRATEGY" in seq.get_system_prompt()
    assert "strictly linear sequence" in seq.get_system_prompt()

    assert hier.name == "hierarchical"
    assert "HIERARCHICAL STRATEGY" in hier.get_system_prompt()
    assert "phased, hierarchical" in hier.get_system_prompt()

    goal = "Test Goal"
    assert seq.get_user_prompt(goal) == f'\nDecompose the following software engineering goal into a plan:\nGoal: "{goal}"\n'


# --- 4. Planner Class Tests ---

def test_planner_orchestration():
    strategy = SequentialPlanningStrategy()
    planner = Planner(strategy)

    sys_p, user_p = planner.get_prompts("build")
    assert "SEQUENTIAL" in sys_p
    assert "build" in user_p

    # Test parser + schema validation + rule validation
    raw_response = """
    {
        "goal": "build api",
        "tasks": [
            {
                "id": "t1",
                "title": "design",
                "description": "desc",
                "priority": "HIGH",
                "estimated_complexity": "MEDIUM",
                "estimated_duration": "30m",
                "dependencies": [],
                "status": "PENDING",
                "subtasks": []
            }
        ]
    }
    """
    plan = planner.parse_and_validate(raw_response)
    assert plan.goal == "build api"
    assert len(plan.tasks) == 1
    assert plan.tasks[0].priority == TaskPriority.HIGH


# --- 5. API and Service Tests (with Mocks) ---

def test_api_list_strategies():
    response = client.get("/api/v1/planner/strategies")
    assert response.status_code == 200
    strategies = response.json()
    assert "sequential" in strategies
    assert "hierarchical" in strategies


@pytest.mark.asyncio
async def test_service_strategy_error():
    service = PlannerService()
    req = PlanningRequest(goal="build", strategy="invalid-strategy")
    with pytest.raises(PlanningStrategyError) as excinfo:
        await service.generate_plan(req)
    assert "Unsupported planning strategy" in str(excinfo.value)


@pytest.mark.asyncio
async def test_service_provider_error():
    service = PlannerService()
    req = PlanningRequest(goal="build", provider="invalid-provider")
    with pytest.raises(PlanningStrategyError) as excinfo:
        await service.generate_plan(req)
    assert "Failed to load provider" in str(excinfo.value)


@pytest.mark.asyncio
async def test_service_llm_generation_error():
    service = PlannerService()
    req = PlanningRequest(goal="build", provider="gemini")
    
    mock_provider = MagicMock()
    mock_provider.generate = AsyncMock(side_effect=RuntimeError("connection timeout"))

    with patch("app.llm.factory.ProviderFactory.get_provider", return_value=mock_provider):
        with pytest.raises(PlanningError) as excinfo:
            await service.generate_plan(req)
        assert "LLM Generation call failed" in str(excinfo.value)


@pytest.mark.asyncio
async def test_service_validation_error_logging(caplog):
    # Enable propagation so caplog captures app logs
    logging.getLogger("app").propagate = True

    service = PlannerService()
    req = PlanningRequest(goal="build", provider="gemini")

    # Mock response with invalid JSON
    mock_provider = MagicMock()
    mock_response = ChatCompletionResponse(content="{'goal': 'broken json, missing fields", model="mock")
    mock_provider.generate = AsyncMock(return_value=mock_response)

    with patch("app.llm.factory.ProviderFactory.get_provider", return_value=mock_provider):
        with caplog.at_level(logging.ERROR, logger="app.planner"):
            with pytest.raises(PlanningParseError):
                await service.generate_plan(req)
            
            # Verify error log
            log_messages = [rec.message for rec in caplog.records]
            assert any("Plan verification failed" in msg for msg in log_messages)


def test_api_generate_plan_success():
    # Mock LLM provider generation
    mock_provider = MagicMock()
    raw_json = """
    {
        "goal": "Build FastAPI",
        "tasks": [
            {
                "id": "t1",
                "title": "Set up server",
                "description": "Initialize FastAPI app instance",
                "priority": "CRITICAL",
                "estimated_complexity": "EASY",
                "estimated_duration": "10m",
                "dependencies": [],
                "status": "PENDING",
                "subtasks": []
            }
        ]
    }
    """
    mock_response = ChatCompletionResponse(content=raw_json, model="gemini-1.5-flash")
    # Wrap generate in AsyncMock since it's async
    mock_provider.generate = AsyncMock(return_value=mock_response)

    with patch("app.llm.factory.ProviderFactory.get_provider", return_value=mock_provider):
        response = client.post(
            "/api/v1/planner/plan",
            json={"goal": "Build FastAPI", "strategy": "sequential", "provider": "gemini"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["strategy"] == "sequential"
        assert data["provider"] == "gemini"
        assert data["plan"]["goal"] == "Build FastAPI"
        assert len(data["plan"]["tasks"]) == 1
        assert data["plan"]["tasks"][0]["priority"] == "CRITICAL"


def test_api_generate_plan_invalid_strategy():
    response = client.post(
        "/api/v1/planner/plan",
        json={"goal": "Build FastAPI", "strategy": "tot"}
    )
    assert response.status_code == 400
    assert "unsupported planning strategy" in response.json()["error"]["message"].lower()


def test_api_generate_plan_llm_malformed_json():
    mock_provider = MagicMock()
    mock_response = ChatCompletionResponse(content="not json", model="gemini-1.5-flash")
    mock_provider.generate = AsyncMock(return_value=mock_response)

    with patch("app.llm.factory.ProviderFactory.get_provider", return_value=mock_provider):
        response = client.post(
            "/api/v1/planner/plan",
            json={"goal": "Build FastAPI"}
        )
        assert response.status_code == 422
        assert "no valid json object boundaries" in response.json()["error"]["message"].lower()
