import os
import pytest
import shutil
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient
from app.main import app
from app.chat.exceptions import ChatProviderException, ChatException
from app.chat.service import ChatService
from app.chat.schemas import ChatRequest, ChatResponse, ChatHistoryMessage
from app.memory.store import MemoryStore
from app.memory.manager import MemoryManager
from app.llm.exceptions import LLMException

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_test_memory(tmp_path):
    temp_dir = tmp_path / "memory_test"
    temp_dir.mkdir(parents=True, exist_ok=True)
    store = MemoryStore(memory_dir=temp_dir)
    # Re-initialize MemoryManager singleton with the test store
    MemoryManager(store=store)
    yield store
    if temp_dir.exists():
        shutil.rmtree(temp_dir)

def test_chat_exceptions():
    exc = ChatException("base chat error", status_code=500)
    assert exc.message == "base chat error"
    assert exc.status_code == 500
    
    exc_p = ChatProviderException("provider failed")
    assert exc_p.message == "provider failed"
    assert exc_p.status_code == 502

@pytest.mark.asyncio
async def test_chat_service_success(setup_test_memory):
    # Setup mock LLM response
    mock_chat_response = MagicMock()
    mock_chat_response.content = "Test assistant reply"
    mock_provider = MagicMock()
    mock_provider.generate = AsyncMock(return_value=mock_chat_response)

    # Seed execution & tool output memories to verify context is retrieved
    mgr = MemoryManager()
    mgr.save_plan("Verify chat goal", {"tasks": []})
    mgr.save_execution("exec-1", "Verify chat goal", "COMPLETED", [], 1.5)
    mgr.save_tool_output("git_status", {}, "clean status", True)

    with patch("app.llm.factory.ProviderFactory.get_provider", return_value=mock_provider):
        service = ChatService()
        response = await service.send_message("Hello, tell me about Verify chat goal with git_status")
        assert response.response == "Test assistant reply"
        assert response.provider is not None
        assert response.duration_seconds > 0

        # Check conversation memory has both user message and assistant reply
        history = await service.get_chat_history()
        assert len(history) == 2
        assert history[0].role == "user"
        assert history[0].content == "Hello, tell me about Verify chat goal with git_status"
        assert history[1].role == "assistant"
        assert history[1].content == "Test assistant reply"

@pytest.mark.asyncio
async def test_chat_service_provider_failure(setup_test_memory):
    mock_provider = MagicMock()
    mock_provider.generate = AsyncMock(side_effect=LLMException("LLM down", provider="gemini"))

    with patch("app.llm.factory.ProviderFactory.get_provider", return_value=mock_provider):
        service = ChatService()
        with pytest.raises(ChatProviderException) as exc_info:
            await service.send_message("Hello")
        assert "LLM Provider failure" in str(exc_info.value)

@pytest.mark.asyncio
async def test_chat_service_unhandled_failure(setup_test_memory):
    mock_provider = MagicMock()
    mock_provider.generate = AsyncMock(side_effect=Exception("Unknown network error"))

    with patch("app.llm.factory.ProviderFactory.get_provider", return_value=mock_provider):
        service = ChatService()
        with pytest.raises(ChatProviderException) as exc_info:
            await service.send_message("Hello")
        assert "Chat failed" in str(exc_info.value)

@pytest.mark.asyncio
async def test_chat_api_endpoints(setup_test_memory):
    mock_chat_response = MagicMock()
    mock_chat_response.content = "Test API Response"
    mock_provider = MagicMock()
    mock_provider.generate = AsyncMock(return_value=mock_chat_response)

    with patch("app.llm.factory.ProviderFactory.get_provider", return_value=mock_provider):
        # 1. POST /api/v1/chat
        resp = client.post("/api/v1/chat", json={"message": "Hey assistant"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["response"] == "Test API Response"
        assert "provider" in data
        assert "duration_seconds" in data

        # 2. GET /api/v1/chat/history
        resp = client.get("/api/v1/chat/history")
        assert resp.status_code == 200
        history = resp.json()
        assert len(history) == 2
        assert history[0]["role"] == "user"
        assert history[0]["content"] == "Hey assistant"
        assert history[1]["role"] == "assistant"
        assert history[1]["content"] == "Test API Response"

        # Seed plan data
        MemoryManager().save_plan("Other Goal", {"tasks": []})

        # 3. DELETE /api/v1/chat/history (Clear chat only)
        resp = client.delete("/api/v1/chat/history")
        assert resp.status_code == 204

        # Verify chat history is cleared
        resp = client.get("/api/v1/chat/history")
        assert len(resp.json()) == 0

        # Verify plan survives deletion
        assert len(setup_test_memory.list(category="plan")) == 1

def test_chat_invalid_requests():
    # POST /api/v1/chat with missing body
    resp = client.post("/api/v1/chat", json={})
    assert resp.status_code == 422

    # POST /api/v1/chat with wrong field name
    resp = client.post("/api/v1/chat", json={"msg": "wrong"})
    assert resp.status_code == 422

def test_chat_history_persistence_after_reload(setup_test_memory):
    # Save conversation entries
    mgr = MemoryManager(store=setup_test_memory)
    mgr.save_conversation("default", "Message 1", "user")
    mgr.save_conversation("default", "Message 2", "assistant")

    # Simulate backend restart (new instance of MemoryStore/MemoryManager pointing to same directory)
    new_store = MemoryStore(memory_dir=setup_test_memory.memory_dir)
    new_mgr = MemoryManager(store=new_store)
    
    # Retrieve history
    service = ChatService(manager=new_mgr)
    import asyncio
    history = asyncio.run(service.get_chat_history())
    assert len(history) == 2
    assert history[0].content == "Message 1"
    assert history[1].content == "Message 2"

@pytest.mark.asyncio
async def test_chat_service_exceptions_handling(setup_test_memory):
    service = ChatService()
    with patch.object(service.manager, "retrieve_by_category", side_effect=Exception("Database error")):
        history = await service.get_chat_history()
        assert history == []

    with patch.object(service.manager.store, "list", side_effect=Exception("Store list error")):
        await service.clear_chat_history()

@pytest.mark.asyncio
async def test_chat_service_save_user_message_failure(setup_test_memory):
    mock_chat_response = MagicMock()
    mock_chat_response.content = "Reply"
    mock_provider = MagicMock()
    mock_provider.generate = AsyncMock(return_value=mock_chat_response)

    service = ChatService()
    with patch.object(service.manager, "save_conversation", side_effect=Exception("Disk write error")):
        with patch("app.llm.factory.ProviderFactory.get_provider", return_value=mock_provider):
            response = await service.send_message("Hello")
            assert response.response == "Reply"

@pytest.mark.asyncio
async def test_chat_service_save_assistant_message_failure(setup_test_memory):
    mock_chat_response = MagicMock()
    mock_chat_response.content = "Reply"
    mock_provider = MagicMock()
    mock_provider.generate = AsyncMock(return_value=mock_chat_response)

    service = ChatService()
    original_save = service.manager.save_conversation
    def mock_save(conversation_id, message, role):
        if role == "assistant":
            raise Exception("Disk full")
        return original_save(conversation_id, message, role)
        
    with patch.object(service.manager, "save_conversation", side_effect=mock_save):
        with patch("app.llm.factory.ProviderFactory.get_provider", return_value=mock_provider):
            response = await service.send_message("Hello")
            assert response.response == "Reply"

@pytest.mark.asyncio
async def test_chat_service_unsupported_provider(setup_test_memory):
    service = ChatService()
    with patch.dict(os.environ, {"LLM_PROVIDER": "unsupported_provider"}):
        with pytest.raises(ChatProviderException) as exc_info:
            await service.send_message("Hello")
        assert "Failed to load provider" in str(exc_info.value)

@pytest.mark.asyncio
async def test_chat_service_retrieve_similar_failure(setup_test_memory):
    mock_chat_response = MagicMock()
    mock_chat_response.content = "Reply"
    mock_provider = MagicMock()
    mock_provider.generate = AsyncMock(return_value=mock_chat_response)

    service = ChatService()
    with patch.object(service.manager, "retrieve_similar", side_effect=Exception("Search index down")):
        with patch("app.llm.factory.ProviderFactory.get_provider", return_value=mock_provider):
            response = await service.send_message("Hello")
            assert response.response == "Reply"

@pytest.mark.asyncio
async def test_chat_service_openai_provider(setup_test_memory):
    mock_chat_response = MagicMock()
    mock_chat_response.content = "OpenAI Reply"
    mock_provider = MagicMock()
    mock_provider.generate = AsyncMock(return_value=mock_chat_response)

    service = ChatService()
    with patch.dict(os.environ, {"LLM_PROVIDER": "openai"}):
        with patch("app.llm.factory.ProviderFactory.get_provider", return_value=mock_provider):
            response = await service.send_message("Hello")
            assert response.response == "OpenAI Reply"
            assert response.provider == "openai"

@pytest.mark.asyncio
async def test_chat_service_other_provider(setup_test_memory):
    mock_chat_response = MagicMock()
    mock_chat_response.content = "Other Reply"
    mock_provider = MagicMock()
    mock_provider.generate = AsyncMock(return_value=mock_chat_response)

    service = ChatService()
    with patch.dict(os.environ, {"LLM_PROVIDER": "custom"}):
        with patch("app.llm.factory.ProviderFactory.get_provider", return_value=mock_provider):
            response = await service.send_message("Hello")
            assert response.response == "Other Reply"
