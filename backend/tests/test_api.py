import uuid
import os
import pytest
import pytest_asyncio
from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.core.config import settings
from app.core.security import create_access_token, hash_password
from app.core.auth import get_current_user
from app.api.v1.endpoints.auth import get_db_session
from app.db.models import User
from tests.conftest import TEST_AUTH_HEADERS, TEST_USER

client = TestClient(app, headers=TEST_AUTH_HEADERS)


def test_health_check():
    # Test client without auth header to ensure public health endpoint works
    unauthenticated_client = TestClient(app)
    response = unauthenticated_client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "CodeForge AI API" in data["service"]


def test_jwt_auth_missing():
    app.dependency_overrides.pop(get_current_user, None)
    unauthenticated_client = TestClient(app)
    response = unauthenticated_client.get("/api/v1/projects")
    assert response.status_code == 401
    assert "Could not validate credentials" in response.text


def test_jwt_auth_malformed():
    app.dependency_overrides.pop(get_current_user, None)
    bad_client = TestClient(app)
    bad_client.headers["Authorization"] = "Bearer invalid-malformed-token"
    response = bad_client.get("/api/v1/projects")
    assert response.status_code == 401
    assert "Could not validate credentials" in response.text


def test_jwt_auth_expired():
    app.dependency_overrides.pop(get_current_user, None)
    expired_token = create_access_token("test-user-id", expires_delta=timedelta(seconds=-10))
    expired_client = TestClient(app)
    expired_client.headers["Authorization"] = f"Bearer {expired_token}"
    response = expired_client.get("/api/v1/projects")
    assert response.status_code == 401
    assert "Could not validate credentials" in response.text


def test_jwt_auth_valid():
    response = client.get("/api/v1/projects")
    assert response.status_code == 200


def test_signup_success():
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = None
    mock_db.execute.return_value = mock_result
    mock_db.commit = AsyncMock()
    
    async def mock_refresh(u):
        u.id = uuid.uuid4()
    mock_db.refresh = AsyncMock(side_effect=mock_refresh)

    app.dependency_overrides[get_db_session] = lambda: mock_db
    unauth_client = TestClient(app)
    res = unauth_client.post(
        "/api/v1/auth/signup",
        json={"email": "newuser@example.com", "password": "securepassword123"}
    )
    app.dependency_overrides.pop(get_db_session, None)

    assert res.status_code == 201
    data = res.json()
    assert "access_token" in data
    assert data["user"]["email"] == "newuser@example.com"


def test_signup_short_password():
    unauth_client = TestClient(app)
    res = unauth_client.post(
        "/api/v1/auth/signup",
        json={"email": "shortpass@example.com", "password": "short"}
    )
    assert res.status_code == 422


def test_signup_duplicate_email():
    existing_user = User(
        id=uuid.uuid4(),
        email="existing@example.com",
        hashed_password=hash_password("password123")
    )
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = existing_user
    mock_db.execute.return_value = mock_result

    app.dependency_overrides[get_db_session] = lambda: mock_db
    unauth_client = TestClient(app)
    res = unauth_client.post(
        "/api/v1/auth/signup",
        json={"email": "existing@example.com", "password": "securepassword123"}
    )
    app.dependency_overrides.pop(get_db_session, None)

    assert res.status_code == 400
    assert "User with this email already exists" in res.text


def test_login_success():
    hashed_pw = hash_password("secretpass123")
    user = User(
        id=uuid.uuid4(),
        email="user@example.com",
        hashed_password=hashed_pw
    )
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = user
    mock_db.execute.return_value = mock_result

    app.dependency_overrides[get_db_session] = lambda: mock_db
    unauth_client = TestClient(app)
    res = unauth_client.post(
        "/api/v1/auth/login",
        json={"email": "user@example.com", "password": "secretpass123"}
    )
    app.dependency_overrides.pop(get_db_session, None)

    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["user"]["email"] == "user@example.com"


def test_login_wrong_password():
    hashed_pw = hash_password("secretpass123")
    user = User(
        id=uuid.uuid4(),
        email="user@example.com",
        hashed_password=hashed_pw
    )
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.first.return_value = user
    mock_db.execute.return_value = mock_result

    app.dependency_overrides[get_db_session] = lambda: mock_db
    unauth_client = TestClient(app)
    res = unauth_client.post(
        "/api/v1/auth/login",
        json={"email": "user@example.com", "password": "wrongpassword"}
    )
    app.dependency_overrides.pop(get_db_session, None)

    assert res.status_code == 401
    assert "Incorrect email or password" in res.text


@pytest.mark.asyncio
async def test_placeholder_endpoints(db_session):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test", headers=TEST_AUTH_HEADERS) as ac:
        # Projects Route
        res_proj = await ac.get("/api/v1/projects")
        assert res_proj.status_code == 200
        assert "projects" in res_proj.json()

        # Agents Route
        res_ag = await ac.get("/api/v1/agents")
        assert res_ag.status_code == 200
        assert "agents" in res_ag.json()

        # Memory Route
        res_mem = await ac.get("/api/v1/memory")
        assert res_mem.status_code == 200
        assert "total_entries" in res_mem.json()

        # Settings Route
        res_sett = await ac.get("/api/v1/settings")
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
