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
