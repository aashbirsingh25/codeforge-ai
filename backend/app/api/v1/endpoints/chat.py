from pathlib import Path
from typing import List
from fastapi import APIRouter, status, Depends
from fastapi.responses import StreamingResponse
from app.chat.schemas import ChatRequest, ChatResponse, ChatHistoryMessage
from app.chat.service import ChatService
from app.core.config import settings
from app.core.auth import get_current_user
from app.db.models import User
from app.memory.store import MemoryStore
from app.memory.manager import MemoryManager

router = APIRouter()

def get_chat_service(current_user: User = Depends(get_current_user)) -> ChatService:
    user_memory_dir = (Path(settings.WORKSPACE_DIR).resolve() / "users" / str(current_user.id) / ".memory").resolve()
    user_memory_dir.mkdir(parents=True, exist_ok=True)
    store = MemoryStore(memory_dir=user_memory_dir)
    manager = MemoryManager(store=store)
    return ChatService(manager=manager, user_id=str(current_user.id))

@router.post(
    "",
    response_model=ChatResponse,
    status_code=status.HTTP_200_OK,
    summary="Send a message to the assistant",
    description="Accepts a user query, fetches context (executions, plans, tools) from memory, retrieves history, requests completions from the active LLM provider, and logs entries.",
    responses={
        200: {
            "description": "Successfully completed assistant response",
            "content": {
                "application/json": {
                    "example": {
                        "response": "Here is how you can build a FastAPI chat server...",
                        "provider": "gemini",
                        "duration_seconds": 1.15
                    }
                }
            }
        }
    }
)
async def send_chat_message(
    request: ChatRequest,
    service: ChatService = Depends(get_chat_service)
):
    return await service.send_message(request.message)

@router.get(
    "/history",
    response_model=List[ChatHistoryMessage],
    status_code=status.HTTP_200_OK,
    summary="Get recent chat logs",
    description="Retrieve the chronological message logs of user prompts and corresponding assistant answers.",
    responses={
        200: {
            "description": "Chronological history logs",
            "content": {
                "application/json": {
                    "example": [
                        {
                            "role": "user",
                            "content": "Hello CodeForge!",
                            "timestamp": "2026-07-06T12:00:00Z"
                        },
                        {
                            "role": "assistant",
                            "content": "Hello! How can I assist you in coding today?",
                            "timestamp": "2026-07-06T12:00:02Z"
                        }
                    ]
                }
            }
        }
    }
)
async def get_history(
    service: ChatService = Depends(get_chat_service)
):
    return await service.get_chat_history()

@router.delete(
    "/history",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Clear conversation history",
    description="Permanently delete conversation logs from memory while preserving other categories (such as plans or tool logs).",
    responses={
        204: {
            "description": "Conversation history successfully cleared"
        }
    }
)
async def clear_history(
    service: ChatService = Depends(get_chat_service)
):
    await service.clear_chat_history()
    return None

@router.post(
    "/stream",
    summary="Send a message to the assistant and stream the response",
    description="Accepts a user query, retrieves relevant planning/execution context from Memory, and yields SSE chunks.",
    responses={
        200: {
            "description": "SSE Event stream with token chunks",
            "content": {
                "text/event-stream": {}
            }
        }
    }
)
async def stream_chat_message(
    request: ChatRequest,
    service: ChatService = Depends(get_chat_service)
):
    return StreamingResponse(
        service.send_message_stream(request.message),
        media_type="text/event-stream"
    )
