from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health_check():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "CodeForge AI API" in data["service"]

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


from unittest.mock import patch
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
