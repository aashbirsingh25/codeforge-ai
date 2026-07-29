from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings

client = TestClient(app, headers={"X-API-Key": settings.API_SECRET_KEY})


def test_health_check():
    # Test client without auth header to ensure public health endpoint works
    unauthenticated_client = TestClient(app)
    response = unauthenticated_client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "CodeForge AI API" in data["service"]

def test_api_key_auth_missing():
    unauthenticated_client = TestClient(app)
    response = unauthenticated_client.get("/api/v1/projects")
    assert response.status_code == 401
    assert "Invalid or missing API Key" in response.text

def test_api_key_auth_invalid():
    bad_client = TestClient(app)
    bad_client.headers["X-API-Key"] = "wrong-key-123"
    response = bad_client.get("/api/v1/projects")
    assert response.status_code == 401
    assert "Invalid or missing API Key" in response.text

def test_api_key_auth_valid():
    response = client.get("/api/v1/projects")
    assert response.status_code == 200


def test_placeholder_endpoints():
    # Projects Route
    res_proj = client.get("/api/v1/projects")
    assert res_proj.status_code == 200
    assert "projects" in res_proj.json()

    # Agents Route
    res_ag = client.get("/api/v1/agents")
    assert res_ag.status_code == 200
    assert "agents" in res_ag.json()

    # Memory Route
    res_mem = client.get("/api/v1/memory")
    assert res_mem.status_code == 200
    assert "short_term_contexts_count" in res_mem.json()

    # Settings Route
    res_sett = client.get("/api/v1/settings")
    assert res_sett.status_code == 200
    assert "workspace_dir" in res_sett.json()

def test_get_providers_settings():
    response = client.get("/api/v1/settings/providers")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    providers = [p["name"] for p in data]
    assert "gemini" in providers
    assert "openai" in providers

def test_get_providers_health_offline():
    import os
    from unittest.mock import patch
    with patch.dict(os.environ, {}, clear=True):
        response = client.get("/api/v1/settings/providers/health")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        for p in data:
            assert p["status"] == "unhealthy"
            assert "not set" in p["error_message"].lower()

def test_list_tools_endpoint():
    response = client.get("/api/v1/tools")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 6
    names = [t["name"] for t in data]
    assert "read_file" in names
    assert "write_file" in names
    assert "list_directory" in names
    assert "search_files" in names
    assert "run_command" in names
    assert "git_status" in names

def test_get_tool_endpoint_success():
    response = client.get("/api/v1/tools/read_file")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "read_file"
    assert data["category"] == "filesystem"
    assert "properties" in data["input_schema"]
    assert "properties" in data["output_schema"]

def test_get_tool_endpoint_not_found():
    response = client.get("/api/v1/tools/non_existent_tool_123")
    assert response.status_code == 404
    assert "not found" in response.json()["error"]["message"].lower()


from unittest.mock import patch, MagicMock, AsyncMock
from app.llm.exceptions import (
    LLMAuthenticationException,
    LLMUnsupportedModelException,
    LLMRateLimitException,
    LLMTimeoutException
)
from app.planner.exceptions import PlanningValidationError
from app.core.exceptions import WorkspaceException

def test_api_error_invalid_api_key():
    with patch("app.planner.service.PlannerService.generate_plan", side_effect=LLMAuthenticationException("auth failed", provider="gemini")):
        response = client.post("/api/v1/planner/plan", json={"goal": "Build FastAPI"})
        assert response.status_code == 401
        data = response.json()
        assert "error" in data
        assert data["error"]["type"] == "LLMAuthenticationException"
        assert data["error"]["message"] == "auth failed"
        assert data["error"]["provider"] == "gemini"
        assert "timestamp" in data["error"]
        assert "request_id" in data["error"]

def test_api_error_unsupported_model():
    with patch("app.planner.service.PlannerService.generate_plan", side_effect=LLMUnsupportedModelException("model unsupported", provider="gemini")):
        response = client.post("/api/v1/planner/plan", json={"goal": "Build FastAPI"})
        assert response.status_code == 400
        data = response.json()
        assert data["error"]["type"] == "LLMUnsupportedModelException"
        assert data["error"]["message"] == "model unsupported"

def test_api_error_rate_limit():
    with patch("app.planner.service.PlannerService.generate_plan", side_effect=LLMRateLimitException("rate limited", provider="gemini")):
        response = client.post("/api/v1/planner/plan", json={"goal": "Build FastAPI"})
        assert response.status_code == 429
        data = response.json()
        assert data["error"]["type"] == "LLMRateLimitException"
        assert data["error"]["message"] == "rate limited"

def test_api_error_timeout():
    with patch("app.planner.service.PlannerService.generate_plan", side_effect=LLMTimeoutException("timed out", provider="gemini")):
        response = client.post("/api/v1/planner/plan", json={"goal": "Build FastAPI"})
        assert response.status_code == 504
        data = response.json()
        assert data["error"]["type"] == "LLMTimeoutException"
        assert data["error"]["message"] == "timed out"

def test_api_error_validation_error():
    with patch("app.planner.service.PlannerService.generate_plan", side_effect=PlanningValidationError("invalid plan schema")):
        response = client.post("/api/v1/planner/plan", json={"goal": "Build FastAPI"})
        assert response.status_code == 422
        data = response.json()
        assert data["error"]["type"] == "PlanningValidationError"
        assert data["error"]["message"] == "invalid plan schema"

def test_api_error_workspace_permission():
    with patch("app.planner.service.PlannerService.generate_plan", side_effect=WorkspaceException("workspace violation")):
        response = client.post("/api/v1/planner/plan", json={"goal": "Build FastAPI"})
        assert response.status_code == 403
        data = response.json()
        assert data["error"]["type"] == "WorkspaceException"
        assert data["error"]["message"] == "workspace violation"


def test_agents_execute_quota_exceeded():
    from app.planner.schemas import ExecutionPlan, Task, TaskPriority, Complexity
    plan = ExecutionPlan(
        goal="build app",
        tasks=[
            Task(id="t1", title="T1", description="D1", priority=TaskPriority.LOW,
                 estimated_complexity=Complexity.TRIVIAL, estimated_duration="1h")
        ]
    )
    mock_provider = MagicMock()
    mock_provider.generate = AsyncMock(side_effect=LLMRateLimitException("Gemini quota exceeded", provider="gemini"))

    with patch("app.llm.factory.ProviderFactory.get_provider", return_value=mock_provider):
        payload = {"plan": plan.model_dump()}
        response = client.post("/api/v1/agents/execute", json=payload)
        
        assert response.status_code == 429
        data = response.json()
        assert "error" in data
        assert data["error"]["type"] == "LLMRateLimitException"
        assert data["error"]["message"] == "Gemini quota exceeded"
        assert data["error"]["provider"] == "gemini"


def test_agents_execute_invalid_api_key():
    from app.planner.schemas import ExecutionPlan, Task, TaskPriority, Complexity
    plan = ExecutionPlan(
        goal="build app",
        tasks=[
            Task(id="t1", title="T1", description="D1", priority=TaskPriority.LOW,
                 estimated_complexity=Complexity.TRIVIAL, estimated_duration="1h")
        ]
    )
    mock_provider = MagicMock()
    mock_provider.generate = AsyncMock(side_effect=LLMAuthenticationException("Invalid API key", provider="gemini"))

    with patch("app.llm.factory.ProviderFactory.get_provider", return_value=mock_provider):
        payload = {"plan": plan.model_dump()}
        response = client.post("/api/v1/agents/execute", json=payload)
        
        assert response.status_code == 401
        data = response.json()
        assert "error" in data
        assert data["error"]["type"] == "LLMAuthenticationException"
        assert data["error"]["message"] == "Invalid API key"
        assert data["error"]["provider"] == "gemini"


def test_agents_execute_unsupported_model():
    from app.planner.schemas import ExecutionPlan, Task, TaskPriority, Complexity
    plan = ExecutionPlan(
        goal="build app",
        tasks=[
            Task(id="t1", title="T1", description="D1", priority=TaskPriority.LOW,
                 estimated_complexity=Complexity.TRIVIAL, estimated_duration="1h")
        ]
    )
    mock_provider = MagicMock()
    mock_provider.generate = AsyncMock(side_effect=LLMUnsupportedModelException("Unsupported model", provider="gemini"))

    with patch("app.llm.factory.ProviderFactory.get_provider", return_value=mock_provider):
        payload = {"plan": plan.model_dump()}
        response = client.post("/api/v1/agents/execute", json=payload)
        
        assert response.status_code == 400
        data = response.json()
        assert "error" in data
        assert data["error"]["type"] == "LLMUnsupportedModelException"
        assert data["error"]["message"] == "Unsupported model"
        assert data["error"]["provider"] == "gemini"


def test_agents_execute_success():
    from app.planner.schemas import ExecutionPlan, Task, TaskPriority, Complexity
    from app.agents.schemas import AgentResult
    plan = ExecutionPlan(
        goal="build app",
        tasks=[
            Task(id="t1", title="T1", description="D1", priority=TaskPriority.LOW,
                 estimated_complexity=Complexity.TRIVIAL, estimated_duration="1h")
        ]
    )
    mock_executor_agent = MagicMock()
    mock_executor_agent.execute = AsyncMock(return_value=AgentResult(success=True, output="T1 complete"))

    with patch("app.agents.registry.agent_registry.get_agent", return_value=mock_executor_agent):
        payload = {"plan": plan.model_dump()}
        response = client.post("/api/v1/agents/execute", json=payload)
        
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "COMPLETED"
        assert "t1" in data["state"]["completed_tasks"]

